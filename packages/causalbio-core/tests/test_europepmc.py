"""Europe PMC contract fixtures, all offline; live smoke is separately opt-in."""

from __future__ import annotations

import json
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier, Event, local
from typing import Any

import pytest
from causalbio.sources import (
    CacheStatus,
    EuropePMCAdapter,
    FileSystemSourceCache,
    HTTPResponse,
    SourceResponseError,
    SourceSearchRequest,
    SourceUnavailableError,
)
from causalbio.sources.europepmc import EUROPE_PMC_SEARCH_URL, plain_source_text
from causalbio.sources.policy import RequestPolicy, SourcePacer

FIXTURE = Path(__file__).parent / "fixtures/source_adapters/europepmc_core.json"
FAST = RequestPolicy(min_interval_seconds=0, initial_retry_seconds=0)


def payload() -> dict[str, Any]:
    value: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return value


def request() -> SourceSearchRequest:
    return SourceSearchRequest(query=payload()["request"]["queryString"], limit=1)


class Transport:
    def __init__(self, data: dict[str, Any] | None = None, fail: bool = False) -> None:
        self.data = data if data is not None else payload()
        self.fail = fail
        self.calls = 0

    def get(
        self, url: str, *, params: Mapping[str, str], headers: Mapping[str, str], timeout: float
    ) -> HTTPResponse:
        self.calls += 1
        assert url == EUROPE_PMC_SEARCH_URL
        assert params["resultType"] == "core"
        assert params["pageSize"] == "1"
        assert headers["accept"] == "application/json"
        assert 0 < timeout <= 8
        if self.fail:
            raise SourceUnavailableError("Synthetic timeout")
        return HTTPResponse(200, json.dumps(self.data).encode("utf-8"))


def adapter(tmp_path: Path, transport: Transport) -> EuropePMCAdapter:
    return EuropePMCAdapter(
        transport=transport, cache=FileSystemSourceCache(tmp_path), request_policy=FAST
    )


def test_authentic_core_fixture_preserves_metadata_abstract_and_cache(tmp_path: Path) -> None:
    transport = Transport()
    source = adapter(tmp_path, transport)
    result = source.search(request())
    article = result.records[0]
    assert article.record_id == "MED:41303871"
    assert article.pmid == "41303871"
    assert article.pmcid == "PMC12654124"
    assert article.doi == "10.3390/medicina61112035"
    assert article.publication_year == 2025
    assert article.license == "cc by"
    assert len(article.authors) > 1
    assert article.abstract is not None and len(article.abstract) == 1895
    assert "<h4>" not in article.abstract
    assert "p < 0.001" in article.abstract
    assert str(article.canonical_url) == "https://europepmc.org/article/MED/41303871"
    assert "species" not in article.model_dump()
    assert result.retrieved_at.tzinfo is not None
    assert source.search(request()).cache_status is CacheStatus.FRESH
    assert transport.calls == 1


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_results",
        "count",
        "excess",
        "duplicate",
        "identity",
        "query",
        "schema",
        "year",
        "abstract_type",
    ],
)
def test_malformed_results_fail_without_cache_or_retry(tmp_path: Path, mutation: str) -> None:
    data = payload()
    query = request()
    if mutation == "missing_results":
        del data["resultList"]
    elif mutation == "count":
        data["hitCount"] = -1
    elif mutation in {"excess", "duplicate"}:
        data["resultList"]["result"] *= 2
        if mutation == "duplicate":
            query = query.model_copy(update={"limit": 2})
            data["request"]["pageSize"] = 2
    elif mutation == "identity":
        data["resultList"]["result"][0]["pmid"] = "456"
    elif mutation == "query":
        data["request"]["queryString"] = "unrelated topic"
    elif mutation == "schema":
        data["resultList"]["result"][0]["title"] = "x" * 2001
    elif mutation == "year":
        data["resultList"]["result"][0]["pubYear"] = "not a year"
    else:
        data["resultList"]["result"][0]["abstractText"] = {"untrusted": "object"}

    # This local variant accepts the altered duplicate-test request size.
    class PermissiveTransport(Transport):
        def get(
            self, url: str, *, params: Mapping[str, str], headers: Mapping[str, str], timeout: float
        ) -> HTTPResponse:
            self.calls += 1
            return HTTPResponse(200, json.dumps(self.data).encode())

    transport = PermissiveTransport(data)
    with pytest.raises(SourceResponseError):
        adapter(tmp_path, transport).search(query)
    assert transport.calls == 1
    assert not list(tmp_path.rglob("*.json"))


def test_missing_abstract_is_not_invented_and_uppercase_core_is_supported(tmp_path: Path) -> None:
    data = payload()
    data["request"]["resultType"] = "CORE"
    data["resultList"]["result"][0].pop("abstractText")
    assert adapter(tmp_path, Transport(data)).search(request()).records[0].abstract is None


def test_markup_is_plain_text_and_script_instructions_are_not_retained() -> None:
    value = "<h4>Methods</h4><p>Rat <i>tendon</i> &amp; control.</p><script>run_bad_code()</script><p>Results</p>"
    assert plain_source_text(value, "abstract") == "Methods Rat tendon & control. Results"


def test_bounded_timeout_attempts_and_response_bytes(tmp_path: Path) -> None:
    failing = Transport(fail=True)
    with pytest.raises(SourceUnavailableError, match="timeout"):
        adapter(tmp_path, failing).search(request())
    assert failing.calls == 3
    oversized = EuropePMCAdapter(
        transport=Transport(),
        cache=FileSystemSourceCache(tmp_path),
        request_policy=FAST,
        max_response_bytes=100,
    )
    with pytest.raises(SourceResponseError, match="100-byte"):
        oversized.search(request())


def test_stale_cache_only_returns_validated_source_identity(tmp_path: Path) -> None:
    now = [datetime(2026, 1, 1, tzinfo=UTC)]
    cache = FileSystemSourceCache(tmp_path, clock=lambda: now[0])
    EuropePMCAdapter(transport=Transport(), cache=cache, request_policy=FAST).search(request())
    now[0] += timedelta(days=2)
    failed = EuropePMCAdapter(transport=Transport(fail=True), cache=cache, request_policy=FAST)
    assert failed.search(request()).cache_status is CacheStatus.STALE
    path = next(tmp_path.rglob("*.json"))
    stored = json.loads(path.read_text(encoding="utf-8"))
    stored["payload"]["records"][0]["pmid"] = "456"
    path.write_text(json.dumps(stored), encoding="utf-8")
    with pytest.raises(SourceUnavailableError):
        failed.search(request())


def test_search_deadline_stops_retrying_after_a_slow_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = [0.0]
    monkeypatch.setattr("causalbio.sources.base.time.monotonic", lambda: now[0])

    class SlowTransport(Transport):
        def get(
            self, url: str, *, params: Mapping[str, str], headers: Mapping[str, str], timeout: float
        ) -> HTTPResponse:
            self.calls += 1
            assert timeout == 1.0
            now[0] += 1.01
            return HTTPResponse(200, json.dumps(self.data).encode())

    transport = SlowTransport()
    source = EuropePMCAdapter(
        transport=transport,
        cache=FileSystemSourceCache(tmp_path),
        request_policy=FAST,
        max_search_seconds=1,
        pacer=SourcePacer(sleep=lambda _: None),
    )
    with pytest.raises(SourceUnavailableError, match="time budget"):
        source.search(request())
    assert transport.calls == 1


def test_one_adapter_keeps_overlapping_search_deadlines_isolated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = local()
    first_entered = Event()
    both_entered = Barrier(2)
    monkeypatch.setattr("causalbio.sources.base.time.monotonic", lambda: clock.now)

    class ConcurrentTransport(Transport):
        def get(
            self, url: str, *, params: Mapping[str, str], headers: Mapping[str, str], timeout: float
        ) -> HTTPResponse:
            if clock.now == 0:
                first_entered.set()
            both_entered.wait(timeout=5)
            if clock.now == 0:
                clock.now = 2.0
            return HTTPResponse(200, json.dumps(self.data).encode())

    source = EuropePMCAdapter(
        transport=ConcurrentTransport(),
        cache=FileSystemSourceCache(tmp_path),
        request_policy=FAST,
        max_search_seconds=1,
        pacer=SourcePacer(sleep=lambda _: None),
    )

    def search(start: float) -> CacheStatus:
        clock.now = start
        return source.search(request()).cache_status

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(search, 0.0)
        assert first_entered.wait(timeout=5)
        second = pool.submit(search, 100.0)
        with pytest.raises(SourceUnavailableError, match="time budget"):
            first.result(timeout=5)
        assert second.result(timeout=5) is CacheStatus.FETCHED


@pytest.mark.parametrize("budget", [0, -1, float("inf"), float("nan"), 121])
def test_invalid_search_budget_rejected(budget: float) -> None:
    with pytest.raises(ValueError, match="max_search_seconds"):
        EuropePMCAdapter(max_search_seconds=budget)
