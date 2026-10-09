"""Offline tests for bounded PubMed/UniProt adapters and deterministic cache behavior."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from causalbio.sources import (
    CacheStatus,
    FileSystemSourceCache,
    HTTPResponse,
    PubMedAdapter,
    SourceAdapter,
    SourceCacheError,
    SourceResponseError,
    SourceSearchRequest,
    SourceUnavailableError,
    UniProtAdapter,
)
from causalbio.sources.policy import RequestPolicy, SourcePacer
from causalbio.sources.pubmed import PUBMED_ESEARCH_URL, PUBMED_ESUMMARY_URL
from causalbio.sources.uniprot import UNIPROT_SEARCH_URL
from pydantic import ValidationError

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "source_adapters"


@pytest.fixture(autouse=True)
def offline_pacing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("causalbio.sources.base.DEFAULT_PACER", SourcePacer(sleep=lambda _: None))


@dataclass(frozen=True, slots=True)
class TransportCall:
    url: str
    params: dict[str, str]
    headers: dict[str, str]
    timeout: float


class FixtureTransport:
    def __init__(self) -> None:
        self.calls: list[TransportCall] = []

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
        timeout: float,
    ) -> HTTPResponse:
        self.calls.append(
            TransportCall(
                url=url,
                params=dict(params),
                headers=dict(headers),
                timeout=timeout,
            )
        )
        if url == PUBMED_ESEARCH_URL:
            fixture = FIXTURE_ROOT / "pubmed_esearch.json"
            response_headers: dict[str, str] = {"content-type": "application/json"}
        elif url == PUBMED_ESUMMARY_URL:
            fixture = FIXTURE_ROOT / "pubmed_esummary.json"
            response_headers = {"content-type": "application/json"}
        elif url == UNIPROT_SEARCH_URL:
            fixture = FIXTURE_ROOT / "uniprot_search.json"
            response_headers = {
                "content-type": "application/json",
                "x-total-results": "1",
            }
        else:
            raise AssertionError(f"Unexpected source URL: {url}")
        return HTTPResponse(
            status_code=200,
            body=fixture.read_bytes(),
            headers=response_headers,
        )


class FailingTransport:
    def __init__(self, message: str = "fixture transport is offline") -> None:
        self.message = message
        self.calls = 0

    def get(
        self,
        _url: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
        timeout: float,
    ) -> HTTPResponse:
        del params, headers, timeout
        self.calls += 1
        raise SourceUnavailableError(self.message)


class StaticTransport:
    def __init__(self, response: HTTPResponse) -> None:
        self.response = response
        self.calls = 0

    def get(
        self,
        _url: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
        timeout: float,
    ) -> HTTPResponse:
        del params, headers, timeout
        self.calls += 1
        return self.response


class MutableClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


def source_cache(
    tmp_path: Path,
    clock: MutableClock,
    *,
    ttl: timedelta = timedelta(hours=1),
) -> FileSystemSourceCache:
    return FileSystemSourceCache(tmp_path / "source-cache", ttl=ttl, clock=clock)


def test_search_request_is_bounded_and_adapters_implement_typed_interface(
    tmp_path: Path,
) -> None:
    clock = MutableClock(datetime(2025, 1, 1, tzinfo=UTC))
    cache = source_cache(tmp_path, clock)
    pubmed = PubMedAdapter(transport=FixtureTransport(), cache=cache)
    uniprot = UniProtAdapter(transport=FixtureTransport(), cache=cache)

    assert isinstance(pubmed, SourceAdapter)
    assert isinstance(uniprot, SourceAdapter)
    assert SourceSearchRequest(query="  slow   oscillations ").query == "slow oscillations"
    with pytest.raises(ValidationError):
        SourceSearchRequest(query=" ")
    with pytest.raises(ValidationError):
        SourceSearchRequest(query="valid", limit=51)


def test_pubmed_normalizes_real_response_fixtures_without_fabricating_abstracts(
    tmp_path: Path,
) -> None:
    clock = MutableClock(datetime(2025, 1, 1, 12, tzinfo=UTC))
    cache = source_cache(tmp_path, clock)
    transport = FixtureTransport()
    adapter = PubMedAdapter(
        transport=transport,
        cache=cache,
        api_key="test-secret-api-key",
        email="fixture@example.org",
    )

    result = adapter.search(SourceSearchRequest(query="slow oscillations", limit=2))

    assert result.source == "pubmed"
    assert result.cache_status is CacheStatus.FETCHED
    assert result.total_count == 2
    assert result.retrieved_at == clock.value
    assert tuple(record.record_id for record in result.records) == ("17086200", "30842037")
    assert result.records[0].title == "Boosting slow oscillations during sleep potentiates memory"
    assert result.records[0].authors == ("Marshall L", "Helgadóttir H", "Mölle M", "Born J")
    assert {(item.namespace, item.value) for item in result.records[0].identifiers} == {
        ("PMID", "17086200"),
        ("DOI", "10.1038/nature05278"),
    }
    assert str(result.records[0].canonical_url) == "https://pubmed.ncbi.nlm.nih.gov/17086200/"
    assert [call.url for call in transport.calls] == [PUBMED_ESEARCH_URL, PUBMED_ESUMMARY_URL]
    assert transport.calls[0].params["retmax"] == "2"
    assert transport.calls[1].params["id"] == "17086200,30842037"

    cache_files = tuple(cache.root.rglob("*.json"))
    assert len(cache_files) == 1
    cached_text = cache_files[0].read_text(encoding="utf-8")
    assert "test-secret-api-key" not in cached_text
    assert "fixture@example.org" not in cached_text


def test_fresh_cache_prevents_transport_calls_and_has_a_deterministic_path(
    tmp_path: Path,
) -> None:
    clock = MutableClock(datetime(2025, 1, 1, tzinfo=UTC))
    cache = source_cache(tmp_path, clock)
    request = SourceSearchRequest(query="slow oscillations", limit=2)
    initial = PubMedAdapter(transport=FixtureTransport(), cache=cache).search(request)
    cache_path = next(cache.root.rglob("*.json"))
    failing = FailingTransport()

    cached = PubMedAdapter(transport=failing, cache=cache).search(request)

    assert failing.calls == 0
    assert cached.cache_status is CacheStatus.FRESH
    assert cached.records == initial.records
    assert cached.retrieved_at == initial.retrieved_at
    assert len(cache_path.stem) == 64
    assert "slow" not in cache_path.name
    assert next(cache.root.rglob("*.json")) == cache_path


def test_expired_cache_falls_back_only_when_previously_validated_data_exists(
    tmp_path: Path,
) -> None:
    clock = MutableClock(datetime(2025, 1, 1, tzinfo=UTC))
    cache = source_cache(tmp_path, clock, ttl=timedelta(minutes=30))
    request = SourceSearchRequest(query="slow oscillations", limit=2)
    initial = PubMedAdapter(transport=FixtureTransport(), cache=cache).search(request)
    clock.value += timedelta(hours=1)
    failing = FailingTransport()
    adapter = PubMedAdapter(transport=failing, cache=cache)

    stale = adapter.search(request)

    assert failing.calls == 3
    assert stale.cache_status is CacheStatus.STALE
    assert stale.records == initial.records
    assert stale.retrieved_at == initial.retrieved_at
    assert any("stale cache data" in warning for warning in stale.warnings)

    with pytest.raises(SourceUnavailableError, match="offline"):
        adapter.search(request.model_copy(update={"allow_stale": False}))


def test_expired_cache_is_refreshed_when_the_source_recovers(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2025, 1, 1, tzinfo=UTC))
    cache = source_cache(tmp_path, clock, ttl=timedelta(minutes=30))
    request = SourceSearchRequest(query="slow oscillations", limit=2)
    original = PubMedAdapter(transport=FixtureTransport(), cache=cache).search(request)
    clock.value += timedelta(hours=2)
    transport = FixtureTransport()

    refreshed = PubMedAdapter(transport=transport, cache=cache).search(request)

    assert refreshed.cache_status is CacheStatus.FETCHED
    assert refreshed.retrieved_at == clock.value
    assert refreshed.retrieved_at > original.retrieved_at
    assert len(transport.calls) == 2


def test_unavailable_source_with_no_cache_raises_instead_of_inventing_records(
    tmp_path: Path,
) -> None:
    clock = MutableClock(datetime(2025, 1, 1, tzinfo=UTC))
    failing = FailingTransport("no fixture or source response exists")
    adapter = PubMedAdapter(transport=failing, cache=source_cache(tmp_path, clock))

    with pytest.raises(SourceUnavailableError, match="no fixture or source response exists"):
        adapter.search(SourceSearchRequest(query="uncached biological query"))
    assert not tuple((tmp_path / "source-cache").rglob("*.json"))


def test_uniprot_normalizes_reviewed_protein_metadata_and_uses_fresh_cache(
    tmp_path: Path,
) -> None:
    clock = MutableClock(datetime(2025, 2, 1, tzinfo=UTC))
    cache = source_cache(tmp_path, clock)
    request = SourceSearchRequest(query="AKT1 AND organism_id:9606", limit=5)
    transport = FixtureTransport()
    result = UniProtAdapter(transport=transport, cache=cache).search(request)

    assert result.source == "uniprot"
    assert result.cache_status is CacheStatus.FETCHED
    assert result.total_count == 1
    assert len(result.records) == 1
    protein = result.records[0]
    assert protein.record_id == "P31749"
    assert protein.entry_name == "AKT1_HUMAN"
    assert protein.protein_name == "RAC-alpha serine/threonine-protein kinase"
    assert protein.gene_names == ("AKT1", "PKB", "RAC")
    assert protein.organism_name == "Homo sapiens"
    assert protein.organism_taxon_id == 9606
    assert protein.reviewed is True
    assert protein.sequence_length == 480
    assert protein.functions == ()
    assert str(protein.canonical_url) == "https://www.uniprot.org/uniprotkb/P31749/entry"
    assert transport.calls[0].url == UNIPROT_SEARCH_URL
    assert transport.calls[0].params["size"] == "5"
    assert transport.calls[0].params["format"] == "json"

    failing = FailingTransport()
    cached = UniProtAdapter(transport=failing, cache=cache).search(request)
    assert failing.calls == 0
    assert cached.cache_status is CacheStatus.FRESH
    assert cached.records == result.records


def test_uniprot_keeps_molecule_scope_and_annotation_evidence_in_cache(tmp_path: Path) -> None:
    # Synthetic comments isolate the normalization contract, not biological truth.
    payload = json.loads((FIXTURE_ROOT / "uniprot_search.json").read_text(encoding="utf-8"))
    payload["results"][0]["comments"] = [
        {
            "commentType": "FUNCTION",
            "texts": [{"value": "Unscoped source annotation."}],
        },
        {
            "commentType": "FUNCTION",
            "molecule": "Example precursor form",
            "texts": [
                {
                    "value": "Precursor-specific source annotation.",
                    "evidences": [
                        {"evidenceCode": "ECO:0000269", "source": "PubMed", "id": "24908487"},
                        {"evidenceCode": "ECO:0000250"},
                    ],
                }
            ],
        },
    ]
    clock = MutableClock(datetime(2025, 2, 1, tzinfo=UTC))
    cache = source_cache(tmp_path, clock)
    source = UniProtAdapter(
        transport=StaticTransport(HTTPResponse(200, json.dumps(payload).encode())), cache=cache
    )
    request = SourceSearchRequest(query="synthetic normalization contract")
    result = source.search(request)
    record = result.records[0]
    assert record.functions == (
        "Unscoped source annotation.",
        "Precursor-specific source annotation.",
    )
    unscoped, precursor = record.function_annotations
    assert unscoped.molecule is None
    assert precursor.molecule == "Example precursor form"
    assert precursor.text == "Precursor-specific source annotation."
    assert precursor.evidences[0].identifier == "24908487"
    assert precursor.evidences[0].source == "PubMed"
    assert precursor.evidences[1].evidence_code == "ECO:0000250"
    assert precursor.evidences[1].source is None
    unavailable = FailingTransport()
    offline = UniProtAdapter(
        transport=unavailable,
        cache=cache,
        request_policy=RequestPolicy(max_attempts=1),
    )
    fresh = offline.search(request)
    assert fresh.cache_status is CacheStatus.FRESH
    assert unavailable.calls == 0
    assert fresh.records[0].function_annotations == record.function_annotations
    clock.value += timedelta(hours=2)
    stale = offline.search(request)
    assert stale.cache_status is CacheStatus.STALE
    assert stale.retrieved_at == result.retrieved_at
    assert stale.records[0].function_annotations == record.function_annotations
    assert stale.records[0].functions == record.functions
    assert unavailable.calls == 1
    assert source.adapter_version == "uniprotkb-json-search-3"


@pytest.mark.parametrize("molecule", ["", {}, 4])
def test_uniprot_invalid_molecule_scope_is_rejected_instead_of_silently_lost(
    tmp_path: Path, molecule: object
) -> None:
    payload = json.loads((FIXTURE_ROOT / "uniprot_search.json").read_text(encoding="utf-8"))
    payload["results"][0]["comments"] = [
        {"commentType": "FUNCTION", "molecule": molecule, "texts": [{"value": "Scoped text."}]}
    ]
    source = UniProtAdapter(
        transport=StaticTransport(HTTPResponse(200, json.dumps(payload).encode())),
        cache=FileSystemSourceCache(tmp_path),
    )
    with pytest.raises(SourceResponseError, match="function molecule"):
        source.search(SourceSearchRequest(query="synthetic normalization contract"))


@pytest.mark.parametrize("status_code", [408, 429, 503])
def test_temporary_http_failures_are_explicitly_unavailable(
    tmp_path: Path, status_code: int
) -> None:
    clock = MutableClock(datetime(2025, 1, 1, tzinfo=UTC))
    transport = StaticTransport(HTTPResponse(status_code=status_code, body=b"{}"))
    adapter = UniProtAdapter(transport=transport, cache=source_cache(tmp_path, clock))

    with pytest.raises(SourceUnavailableError, match=f"HTTP {status_code}"):
        adapter.search(SourceSearchRequest(query="AKT1"))


def test_invalid_or_oversized_source_responses_fail_closed(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2025, 1, 1, tzinfo=UTC))
    cache = source_cache(tmp_path, clock)

    invalid_json = UniProtAdapter(
        transport=StaticTransport(HTTPResponse(status_code=200, body=b"not-json")),
        cache=cache,
    )
    with pytest.raises(SourceResponseError, match="invalid UTF-8 JSON"):
        invalid_json.search(SourceSearchRequest(query="AKT1"))

    missing_accession = UniProtAdapter(
        transport=StaticTransport(
            HTTPResponse(
                status_code=200,
                body=json.dumps(
                    {
                        "results": [
                            {
                                "proteinDescription": {},
                                "organism": {"scientificName": "Homo sapiens", "taxonId": 9606},
                            }
                        ]
                    }
                ).encode(),
            )
        ),
        cache=cache,
    )
    with pytest.raises(SourceResponseError, match="primaryAccession"):
        missing_accession.search(SourceSearchRequest(query="missing accession"))

    oversized = UniProtAdapter(
        transport=StaticTransport(HTTPResponse(status_code=200, body=b"{" + b"x" * 100 + b"}")),
        cache=cache,
        max_response_bytes=50,
    )
    with pytest.raises(SourceResponseError, match="50-byte safety limit"):
        oversized.search(SourceSearchRequest(query="large response"))


def test_corrupt_cache_is_ignored_and_replaced_by_valid_source_data(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2025, 1, 1, tzinfo=UTC))
    cache = source_cache(tmp_path, clock)
    request = SourceSearchRequest(query="slow oscillations", limit=2)
    adapter = PubMedAdapter(transport=FixtureTransport(), cache=cache)
    key_material: dict[str, object] = {
        "adapter_version": adapter.adapter_version,
        "query": request.query,
        "limit": request.limit,
    }
    path = cache.path_for(adapter.name, key_material)
    path.parent.mkdir(parents=True)
    path.write_text("{corrupt", encoding="utf-8")

    result = adapter.search(request)

    assert result.cache_status is CacheStatus.FETCHED
    assert any("invalid cache entry" in warning for warning in result.warnings)
    repaired = json.loads(path.read_text(encoding="utf-8"))
    assert repaired["payload"]["records"][0]["record_id"] == "17086200"


def test_cache_key_is_order_independent_and_rejects_unsafe_namespaces(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2025, 1, 1, tzinfo=UTC))
    cache = source_cache(tmp_path, clock)

    first = cache.key_for("pubmed", {"query": "memory", "limit": 2})
    second = cache.key_for("pubmed", {"limit": 2, "query": "memory"})
    assert first == second
    assert len(first) == 64
    with pytest.raises(SourceCacheError, match="Unsafe cache namespace"):
        cache.key_for("../outside", {"query": "memory"})


def test_pubmed_empty_search_does_not_make_an_unnecessary_summary_call(
    tmp_path: Path,
) -> None:
    clock = MutableClock(datetime(2025, 1, 1, tzinfo=UTC))
    transport = StaticTransport(
        HTTPResponse(
            status_code=200,
            body=json.dumps({"esearchresult": {"count": "0", "idlist": []}}).encode("utf-8"),
        )
    )
    result = PubMedAdapter(transport=transport, cache=source_cache(tmp_path, clock)).search(
        SourceSearchRequest(query="no matching records")
    )

    assert result.records == ()
    assert result.total_count == 0
    assert transport.calls == 1
