"""Offline checks for retry bounds, streamed size caps, and source/cache identity."""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from causalbio.sources import (
    CacheStatus,
    FileSystemSourceCache,
    HTTPResponse,
    HttpxTransport,
    PubMedAdapter,
    SourceResponseError,
    SourceSearchRequest,
    SourceUnavailableError,
    UniProtAdapter,
)
from causalbio.sources.policy import RequestPolicy, SourcePacer

FIXTURES = Path(__file__).parent / "fixtures" / "source_adapters"
FAST = RequestPolicy(min_interval_seconds=0, initial_retry_seconds=0)


class ScriptedTransport:
    def __init__(self, *responses: HTTPResponse) -> None:
        self.responses = responses
        self.calls = 0

    def get(
        self, url: str, *, params: Mapping[str, str], headers: Mapping[str, str], timeout: float
    ) -> HTTPResponse:
        del url, params, headers, timeout
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return response


def response(payload: dict[str, Any], status: int = 200, **headers: str) -> HTTPResponse:
    return HTTPResponse(status, json.dumps(payload).encode(), headers)


def protein_payload() -> dict[str, Any]:
    value: dict[str, Any] = json.loads(
        (FIXTURES / "uniprot_search.json").read_text(encoding="utf-8")
    )
    return value


def test_retry_after_and_process_source_pacing_are_bounded(tmp_path: Path) -> None:
    now = [0.0]
    sleeps: list[float] = []

    def sleep(delay: float) -> None:
        sleeps.append(delay)
        now[0] += delay

    pacer = SourcePacer(sleep=sleep, monotonic=lambda: now[0])
    transport = ScriptedTransport(
        response({}, 429, **{"Retry-After": "1"}), response({}, 503), response(protein_payload())
    )
    adapter = UniProtAdapter(
        transport=transport, cache=FileSystemSourceCache(tmp_path), pacer=pacer
    )
    result = adapter.search(SourceSearchRequest(query="AKT1"))
    assert transport.calls == 3
    assert sleeps == [1.0, 0.5]
    assert result.cache_status is CacheStatus.FETCHED
    # A second adapter shares the same source schedule, including the first request.
    second = UniProtAdapter(
        transport=ScriptedTransport(response(protein_payload())),
        cache=FileSystemSourceCache(tmp_path / "second"),
        pacer=pacer,
    )
    second.search(SourceSearchRequest(query="AKT1"))
    assert sleeps[-1] == pytest.approx(0.34)


@pytest.mark.parametrize(
    "status,retry_after,calls", [(429, "600", 1), (429, "invalid", 3), (404, "", 1), (302, "", 1)]
)
def test_nonretryable_or_excessive_backoff_stops(
    tmp_path: Path, status: int, retry_after: str, calls: int
) -> None:
    transport = ScriptedTransport(response({}, status, **{"retry-after": retry_after}))
    adapter = UniProtAdapter(
        transport=transport,
        cache=FileSystemSourceCache(tmp_path),
        request_policy=FAST,
        pacer=SourcePacer(sleep=lambda _: None),
    )
    with pytest.raises((SourceResponseError, SourceUnavailableError)):
        adapter.search(SourceSearchRequest(query="AKT1"))
    assert transport.calls == calls


def test_retry_after_http_date_and_policy_reject_nonfinite_configuration() -> None:
    policy = RequestPolicy()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert policy.retry_delay(0, "Thu, 01 Jan 2026 00:00:01 GMT", now) == 1.0
    assert policy.retry_delay(0, "Thu, 01 Jan 2026 00:00:10 GMT", now) is None
    for kwargs in (
        {"max_attempts": 0},
        {"max_attempts": 2.5},
        {"min_interval_seconds": float("nan")},
    ):
        with pytest.raises(ValueError):
            RequestPolicy(**kwargs)
    with pytest.raises(ValueError):
        UniProtAdapter(timeout_seconds=float("inf"))


class CountedStream(httpx.SyncByteStream):
    def __init__(self) -> None:
        self.read = 0
        self.closed = False

    def __iter__(self) -> Iterator[bytes]:
        for _ in range(100):
            self.read += 1
            yield b"x" * 8192

    def close(self) -> None:
        self.closed = True


def test_production_transport_stops_reading_and_closes_oversized_stream() -> None:
    stream = CountedStream()
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=stream))
    ) as client:
        transport = HttpxTransport(client, max_response_bytes=10_000)
        with pytest.raises(SourceResponseError, match="10000-byte"):
            transport.get(
                "https://rest.uniprot.org/uniprotkb/search", params={}, headers={}, timeout=1
            )
    assert stream.read == 2
    assert stream.closed


def test_small_stream_chunks_are_checked_before_a_buffer_can_hide_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [0.0]
    monkeypatch.setattr("causalbio.sources.transport.time.monotonic", lambda: now[0])

    class TrickleStream(CountedStream):
        def __iter__(self) -> Iterator[bytes]:
            for _ in range(100):
                self.read += 1
                now[0] += 0.6
                yield b"x"

    stream = TrickleStream()
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=stream))
        ) as client,
        pytest.raises(SourceUnavailableError, match="time budget"),
    ):
        HttpxTransport(client).get(
            "https://rest.uniprot.org/uniprotkb/search", params={}, headers={}, timeout=1
        )
    assert stream.read == 2
    assert stream.closed


def test_pacing_respects_remaining_search_budget_without_sleeping() -> None:
    now = [0.0]
    sleeps: list[float] = []
    pacer = SourcePacer(sleep=sleeps.append, monotonic=lambda: now[0])
    pacer.wait("europe_pmc", 0.34)
    with pytest.raises(SourceUnavailableError, match="pacing time budget"):
        pacer.wait("europe_pmc", 0.34, max_wait_seconds=0.1)
    assert not sleeps
    now[0] = 0.34
    pacer.wait("europe_pmc", 0.34, max_wait_seconds=0.1)


def test_production_timeout_has_bounded_retry_and_typed_failure(tmp_path: Path) -> None:
    calls = [0]

    def timeout(_: httpx.Request) -> httpx.Response:
        calls[0] += 1
        raise httpx.ReadTimeout("synthetic timeout")

    with httpx.Client(transport=httpx.MockTransport(timeout)) as client:
        adapter = UniProtAdapter(
            transport=HttpxTransport(client),
            cache=FileSystemSourceCache(tmp_path),
            request_policy=FAST,
        )
        with pytest.raises(SourceUnavailableError):
            adapter.search(SourceSearchRequest(query="AKT1"))
    assert calls[0] == 3


@pytest.mark.parametrize(
    "mutation", ["excess", "duplicate", "accession", "schema", "missing_review", "unknown_review"]
)
def test_invalid_normalized_results_are_not_retried_or_cached(
    tmp_path: Path, mutation: str
) -> None:
    payload = protein_payload()
    limit = 2
    if mutation in {"excess", "duplicate"}:
        payload["results"] *= 2
        limit = 1 if mutation == "excess" else 2
    elif mutation == "accession":
        payload["results"][0]["primaryAccession"] = "../../injected"
    elif mutation == "missing_review":
        payload["results"][0].pop("entryType")
    elif mutation == "unknown_review":
        payload["results"][0]["entryType"] = "invented classification"
    else:
        payload["results"][0]["proteinDescription"]["recommendedName"]["fullName"]["value"] = (
            "x" * 1001
        )
    transport = ScriptedTransport(response(payload))
    adapter = UniProtAdapter(
        transport=transport, cache=FileSystemSourceCache(tmp_path), request_policy=FAST
    )
    with pytest.raises(SourceResponseError):
        adapter.search(SourceSearchRequest(query="AKT1", limit=limit))
    assert transport.calls == 1
    assert not list(tmp_path.rglob("*.json"))


@pytest.mark.parametrize("ids", [["1", "1"], ["1", "2", "3"], ["../bad"]])
def test_pubmed_rejects_bad_search_ids_before_summary(tmp_path: Path, ids: list[str]) -> None:
    transport = ScriptedTransport(response({"esearchresult": {"idlist": ids, "count": "3"}}))
    adapter = PubMedAdapter(
        transport=transport, cache=FileSystemSourceCache(tmp_path), request_policy=FAST
    )
    with pytest.raises(SourceResponseError):
        adapter.search(SourceSearchRequest(query="memory", limit=2))
    assert transport.calls == 1


def test_pubmed_rejects_summary_identity_mismatch(tmp_path: Path) -> None:
    search = json.loads((FIXTURES / "pubmed_esearch.json").read_text(encoding="utf-8"))
    summary = json.loads((FIXTURES / "pubmed_esummary.json").read_text(encoding="utf-8"))
    summary["result"]["17086200"]["uid"] = "30842037"
    adapter = PubMedAdapter(
        transport=ScriptedTransport(response(search), response(summary)),
        cache=FileSystemSourceCache(tmp_path),
        request_policy=FAST,
    )
    with pytest.raises(SourceResponseError, match="uid"):
        adapter.search(SourceSearchRequest(query="memory", limit=2))


@pytest.mark.parametrize("field", ["query", "source_endpoint", "record_url", "schema_version"])
def test_corrupt_cache_identity_is_refetched_and_never_used_as_stale(
    tmp_path: Path, field: str
) -> None:
    clock = [datetime(2026, 1, 1, tzinfo=UTC)]
    cache = FileSystemSourceCache(tmp_path, clock=lambda: clock[0])
    request = SourceSearchRequest(query="AKT1")
    adapter = UniProtAdapter(
        transport=ScriptedTransport(response(protein_payload())), cache=cache, request_policy=FAST
    )
    adapter.search(request)
    path = next(tmp_path.rglob("*.json"))
    content = json.loads(path.read_text(encoding="utf-8"))
    if field == "record_url":
        content["payload"]["records"][0]["canonical_url"] = "https://example.org/unrelated"
    elif field == "schema_version":
        content[field] = 900
    else:
        content["payload"][field] = "unrelated" if field == "query" else "https://example.org/"
    path.write_text(json.dumps(content), encoding="utf-8")
    clock[0] += timedelta(days=2)
    failed = UniProtAdapter(
        transport=ScriptedTransport(response({}, 503)), cache=cache, request_policy=FAST
    )
    with pytest.raises(SourceUnavailableError):
        failed.search(request)
    refreshed = adapter.search(request)
    assert refreshed.cache_status is CacheStatus.FETCHED
    assert refreshed.query == request.query
