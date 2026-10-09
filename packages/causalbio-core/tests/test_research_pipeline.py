"""Deterministic source fixtures exercise isolation, provenance, and graceful failures."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from uuid import uuid4

import pytest
from causalbio.demo.registry import DomainPackRegistry
from causalbio.research.models import ResearchMode, UniversalResearchResult
from causalbio.research.service import OfflineTransport, ResearchService, normalize_records
from causalbio.sources.errors import SourceUnavailableError
from causalbio.sources.models import (
    CacheStatus,
    EuropePMCSearchResult,
    NormalizedIdentifier,
    NormalizedLiteratureRecord,
    NormalizedProteinRecord,
    NormalizedResearchArticle,
    ProteinFunctionAnnotation,
    ProteinFunctionEvidence,
    PubMedSearchResult,
    SourceSearchRequest,
    SourceSearchResultBase,
    UniProtSearchResult,
)
from pydantic import ValidationError

STAMP = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
ABSTRACT = (
    "Synthetic tendon fixture: mechanical loading activates fibroblast signaling during tendon repair. "
    "Synthetic tendon fixture: collagen remodeling changes extracellular matrix structure during repair. "
    "However, the synthetic study cannot establish clinical benefit in humans."
)


def article_result(*, status: CacheStatus = CacheStatus.FETCHED) -> EuropePMCSearchResult:
    """The deliberately labeled record is software input, not scientific evidence."""
    return EuropePMCSearchResult(
        query="fixture tendon",
        retrieved_at=STAMP,
        cache_status=status,
        source_endpoint="https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        records=(
            NormalizedResearchArticle(
                record_id="MED:12345678",
                record_source="MED",
                pmid="12345678",
                title="Synthetic tendon repair software fixture",
                abstract=ABSTRACT,
                publication_year=2025,
                publication_types=("Review",),
                identifiers=(
                    NormalizedIdentifier(namespace="MED", value="12345678"),
                    NormalizedIdentifier(namespace="PMID", value="12345678"),
                ),
                canonical_url="https://europepmc.org/article/MED/12345678",
            ),
        ),
    )


def citation_result() -> PubMedSearchResult:
    return PubMedSearchResult(
        query="fixture tendon",
        retrieved_at=STAMP,
        cache_status=CacheStatus.FETCHED,
        source_endpoint="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
        records=(
            NormalizedLiteratureRecord(
                record_id="12345678",
                title="Synthetic tendon repair software fixture",
                publication_date="2025 Oct 1",
                identifiers=(NormalizedIdentifier(namespace="PMID", value="12345678"),),
                canonical_url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
            ),
        ),
    )


def protein_result() -> UniProtSearchResult:
    return UniProtSearchResult(
        query="accession:P23560",
        retrieved_at=STAMP,
        cache_status=CacheStatus.FETCHED,
        source_endpoint="https://rest.uniprot.org/uniprotkb/search",
        records=(
            NormalizedProteinRecord(
                record_id="P23560",
                protein_name="Synthetic BDNF fixture",
                organism_name="Synthetic organism label",
                organism_taxon_id=9606,
                reviewed=True,
                functions=(
                    "Synthetic BDNF fixture: neurotrophin receptor signaling changes neuronal plasticity in this software test.",
                ),
                identifiers=(NormalizedIdentifier(namespace="UniProtKB", value="P23560"),),
                canonical_url="https://www.uniprot.org/uniprotkb/P23560/entry",
            ),
        ),
    )


@dataclass
class FakeProvider:
    name: str
    result: SourceSearchResultBase | None = None
    error: Exception | None = None
    gate: Event | None = None
    adapter_version: str = "software-fixture-1.0"
    calls: list[SourceSearchRequest] = field(default_factory=list)

    def search(self, request: SourceSearchRequest) -> SourceSearchResultBase:
        self.calls.append(request)
        if self.gate is not None:
            self.gate.wait(timeout=1)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result.model_copy(update={"query": request.query})


@pytest.fixture
def empty_registry(tmp_path: Path) -> DomainPackRegistry:
    root = tmp_path / "empty-packs"
    root.mkdir()
    return DomainPackRegistry(root)


@pytest.mark.parametrize(
    "text", ["Where can I buy BPC-157?", "retention", "What is the stock price?"]
)
def test_nonresearch_routes_do_not_call_any_provider(text: str) -> None:
    provider = FakeProvider("europe_pmc", error=AssertionError("must not be called"))
    result = ResearchService(providers={"europe_pmc": provider}).investigate(text)
    assert result.mode in {
        ResearchMode.RESTRICTED_WITH_SAFE_ALTERNATIVE,
        ResearchMode.CLARIFICATION_REQUIRED,
        ResearchMode.OUT_OF_DOMAIN,
    }
    assert provider.calls == []
    assert not result.evidence and not result.graph.edges and not result.source_runs


def test_curated_investigation_uses_pack_without_external_retrieval() -> None:
    provider = FakeProvider("europe_pmc", error=AssertionError("must not be called"))
    result = ResearchService(providers={"europe_pmc": provider}).investigate(
        "How could memory persist after learning?"
    )
    assert result.mode is ResearchMode.CURATED
    assert result.curated_result is not None
    assert provider.calls == []
    assert result.evidence == ()


@pytest.mark.parametrize(
    ("depth", "limit", "queries"), [("quick", 4, 1), ("research", 8, 3), ("deep", 12, 3)]
)
def test_depth_bounds_searches_and_provisional_graph_only_models(
    depth: str,
    limit: int,
    queries: int,
    empty_registry: DomainPackRegistry,
) -> None:
    from typing import cast

    from causalbio.research.models import ResearchDepth

    provider = FakeProvider("europe_pmc", article_result())
    result = ResearchService(
        providers={"europe_pmc": provider}, registry=empty_registry
    ).investigate(
        "What mechanisms influence tendon recovery?",
        depth=cast(ResearchDepth, depth),
    )
    assert result.mode is ResearchMode.LIVE_RESEARCH
    assert len(provider.calls) == queries
    assert provider.calls[0].limit == limit
    review_calls = [call for call in provider.calls if call.query.endswith("PUB_TYPE:review")]
    assert len(review_calls) == (0 if depth == "quick" else 1)
    assert all(call.limit == 3 for call in review_calls)
    assert result.direct_answer and result.mechanisms
    assert all(group.model_eligibility == "GRAPH_ONLY" for group in result.mechanisms)
    assert all(edge.status == "provisional" and edge.evidence_ids for edge in result.graph.edges)
    assert all(
        edge.relation in {"SUPPORTED_BY", "CONTRADICTED_BY", "ASSOCIATED_WITH", "PARTICIPATES_IN"}
        for edge in result.graph.edges
    )
    assert all(run.provider_version == provider.adapter_version for run in result.source_runs)
    assert result.curated_result is None
    assert empty_registry.slugs() == ()


def test_deduplicates_publication_identity_without_counting_metadata_as_replication(
    empty_registry: DomainPackRegistry,
) -> None:
    result = ResearchService(
        providers={
            "europe_pmc": FakeProvider("europe_pmc", article_result()),
            "pubmed": FakeProvider("pubmed", citation_result()),
        },
        registry=empty_registry,
    ).investigate("How does tendon repair work?")
    assert len(result.evidence) == 1
    retained = result.evidence[0]
    assert retained.source == "europe_pmc" and retained.abstract == ABSTRACT
    assert retained.organism is None and retained.tissue is None
    assert retained.sample_size is None and retained.effect_estimate is None
    assert retained.population is None and retained.cell_type is None
    assert retained.primary_or_review == "review"
    assert {claim.evidence_ids[0] for claim in result.direct_answer} == {retained.id}
    assert len(result.source_runs) == 4


def test_citation_metadata_alone_never_generates_mechanism_claims(
    empty_registry: DomainPackRegistry,
) -> None:
    result = ResearchService(
        providers={"pubmed": FakeProvider("pubmed", citation_result())}, registry=empty_registry
    ).investigate("How does tendon repair work?")
    assert len(result.evidence) == 1
    assert not result.direct_answer and not result.mechanisms and not result.graph.edges
    assert any("could not retrieve enough evidence" in item for item in result.notices)


@pytest.mark.parametrize(
    "failure", [SourceUnavailableError("fixture outage"), RuntimeError("fixture parser bug")]
)
def test_partial_provider_failures_retain_validated_evidence(
    failure: Exception, empty_registry: DomainPackRegistry
) -> None:
    result = ResearchService(
        providers={
            "europe_pmc": FakeProvider("europe_pmc", article_result()),
            "pubmed": FakeProvider("pubmed", error=failure),
        },
        registry=empty_registry,
    ).investigate("How does tendon repair work?")
    assert result.evidence and result.mechanisms
    assert any(run.source == "pubmed" and run.status == "unavailable" for run in result.source_runs)
    assert any("partial search" in item for item in result.notices)
    assert all("parser bug" not in (run.detail or "") for run in result.source_runs)


def test_deadline_returns_other_results_without_waiting_for_slow_source(
    empty_registry: DomainPackRegistry,
) -> None:
    gate = Event()
    try:
        result = ResearchService(
            providers={
                "europe_pmc": FakeProvider("europe_pmc", article_result()),
                "pubmed": FakeProvider("pubmed", citation_result(), gate=gate),
            },
            registry=empty_registry,
            deadline_seconds=0.03,
        ).investigate("How does tendon repair work?", depth="quick")
        assert not gate.is_set()
        assert result.evidence
        assert any("deadline" in (run.detail or "") for run in result.source_runs)
    finally:
        gate.set()


@pytest.mark.parametrize("status", [CacheStatus.FRESH, CacheStatus.STALE])
def test_cached_evidence_retains_original_date_and_is_not_labeled_live(
    status: CacheStatus, empty_registry: DomainPackRegistry
) -> None:
    result = ResearchService(
        providers={"europe_pmc": FakeProvider("europe_pmc", article_result(status=status))},
        registry=empty_registry,
    ).investigate("How does tendon repair work?")
    assert result.mode is ResearchMode.GENERAL_EVIDENCE_SUMMARY
    assert all(
        record.retrieved_at == STAMP and record.cache_status == status for record in result.evidence
    )
    assert all(run.status == "cached" for run in result.source_runs)
    assert any("does not imply a current live search" in item for item in result.notices)


def test_offline_without_matching_evidence_is_explicit_and_has_no_fabricated_claims(
    empty_registry: DomainPackRegistry,
) -> None:
    result = ResearchService(
        providers={
            "europe_pmc": FakeProvider("europe_pmc", error=SourceUnavailableError("offline"))
        },
        online=False,
        registry=empty_registry,
    ).investigate("How does tendon repair work?")
    assert result.mode is ResearchMode.GENERAL_EVIDENCE_SUMMARY
    assert not result.evidence and not result.direct_answer
    assert all(run.status == "offline" for run in result.source_runs)
    assert any("Offline mode" in item for item in result.notices)


def test_offline_can_reuse_local_evidence_with_original_scope() -> None:
    result = ResearchService(providers={}, online=False).investigate("What is dopamine?")
    assert result.mode is ResearchMode.EXPLANATORY
    assert result.direct_answer
    assert any("Offline mode" in item for item in result.notices)
    assert any("does not imply a current live search" in item for item in result.notices)
    assert result.evidence
    assert all(
        record.source == "local_curated" and record.cache_status == "local_curated"
        for record in result.evidence
    )
    assert all(record.evidence_status == "curated" for record in result.evidence)
    assert result.curated_result is None
    assert all(group.model_eligibility == "GRAPH_ONLY" for group in result.mechanisms)


def test_offline_transport_never_opens_a_socket() -> None:
    with pytest.raises(SourceUnavailableError, match="external requests are disabled"):
        OfflineTransport().get("https://example.org", params={}, headers={}, timeout=1)


def test_entity_explanation_leads_with_retrieved_annotation_not_guessed_human_data(
    empty_registry: DomainPackRegistry,
) -> None:
    provider = FakeProvider("uniprot", protein_result())
    result = ResearchService(providers={"uniprot": provider}, registry=empty_registry).investigate(
        "What is BDNF?"
    )
    assert result.mode is ResearchMode.EXPLANATORY
    assert provider.calls[0].query == "accession:P23560"
    assert result.direct_answer and "Synthetic BDNF fixture" in result.direct_answer[0].text
    assert result.evidence[0].organism == "Synthetic organism label"
    assert result.evidence[0].population is None
    assert "not a clinical study" in result.evidence[0].limitations[0]


def test_source_extracts_and_citations_are_revalidated_at_result_boundary(
    empty_registry: DomainPackRegistry,
) -> None:
    result = ResearchService(
        providers={"europe_pmc": FakeProvider("europe_pmc", article_result())},
        registry=empty_registry,
    ).investigate("How does tendon repair work?")
    original = result.model_dump(mode="json")
    forged = result.model_dump(mode="json")
    forged["direct_answer"][0]["text"] = "Unsupported new biological claim."
    forged["direct_answer"][0]["source_passage"] = "Unsupported new biological claim."
    with pytest.raises(ValidationError, match="preserve text"):
        UniversalResearchResult.model_validate(forged)
    original["evidence"] = []
    with pytest.raises(ValidationError, match="same result"):
        UniversalResearchResult.model_validate(original)


def test_normalization_preserves_protein_context_and_citation_absence() -> None:
    protein = normalize_records(protein_result())[0]
    citation = normalize_records(citation_result())[0]
    assert protein.organism == "Synthetic organism label"
    assert protein.pmid is None and protein.doi is None
    assert citation.abstract is None and citation.organism is None
    assert citation.year == 2025


@pytest.mark.parametrize("status", [CacheStatus.FETCHED, CacheStatus.FRESH])
def test_protein_forms_keep_separate_source_scope_and_annotation_references(
    status: CacheStatus, empty_registry: DomainPackRegistry
) -> None:
    source = protein_result()
    precursor = ProteinFunctionAnnotation(
        text="Synthetic precursor BDNF fixture activates one receptor mechanism in this software test.",
        molecule="Synthetic proBDNF",
        evidences=(ProteinFunctionEvidence(evidence_code="ECO:0000250"),),
    )
    mature = ProteinFunctionAnnotation(
        text="Synthetic mature BDNF fixture activates another receptor mechanism in this software test.",
        molecule="Synthetic mature BDNF",
        evidences=(
            ProteinFunctionEvidence(
                evidence_code="ECO:0000269", source="PubMed", identifier="12345678"
            ),
        ),
    )
    protein = source.records[0].model_copy(update={"function_annotations": (precursor, mature)})
    source = source.model_copy(update={"records": (protein,), "cache_status": status})
    normalized = normalize_records(source)
    assert len(normalized) == 2
    assert len({item.id for item in normalized}) == 2
    assert {item.source_record_id for item in normalized} == {"P23560"}
    assert normalized[0].abstract == precursor.text
    assert normalized[0].experimental_context == "Specific to Synthetic proBDNF"
    assert normalized[0].annotation_evidence == (
        {"evidence_code": "ECO:0000250", "source": None, "identifier": None},
    )
    assert normalized[1].annotation_evidence[0]["identifier"] == "12345678"
    result = ResearchService(
        providers={"uniprot": FakeProvider("uniprot", source)}, registry=empty_registry
    ).investigate("What is BDNF?")
    assert result.mode is ResearchMode.EXPLANATORY
    assert len(result.evidence) == 2
    assert {claim.text for claim in result.direct_answer} == {precursor.text, mature.text}
    assert all(item.experimental_context and item.annotation_evidence for item in result.evidence)
    assert all("not independent replication" in item.limitations[-1] for item in result.evidence)


@pytest.mark.parametrize("kind", ["structured_annotation", "curated_summary"])
def test_changing_claim_kind_does_not_bypass_grounding(
    kind: str, empty_registry: DomainPackRegistry
) -> None:
    result = ResearchService(
        providers={"europe_pmc": FakeProvider("europe_pmc", article_result())},
        registry=empty_registry,
    ).investigate("How does tendon repair work?")
    forged = result.model_dump(mode="json")
    claim = forged["direct_answer"][0]
    claim["id"] = str(uuid4())
    claim["kind"] = kind
    claim["text"] = "Unsupported new biological claim."
    claim["source_passage"] = claim["text"]
    expected = "preserve text" if kind == "structured_annotation" else "locally curated"
    with pytest.raises(ValidationError, match=expected):
        UniversalResearchResult.model_validate(forged)


@pytest.mark.parametrize(
    "corruption", ["conflicting_claim", "unrelated_edge_evidence", "duplicate_edge"]
)
def test_graph_claim_identity_and_evidence_links_cannot_be_silently_rebound(
    corruption: str,
    empty_registry: DomainPackRegistry,
) -> None:
    result = ResearchService(
        providers={"europe_pmc": FakeProvider("europe_pmc", article_result())},
        registry=empty_registry,
    ).investigate("How does tendon repair work?")
    payload = result.model_dump(mode="json")
    if corruption == "conflicting_claim":
        existing = payload["direct_answer"][0]
        alternate = next(
            claim
            for group in payload["mechanisms"]
            for claim in group["claims"]
            if claim["text"] != existing["text"]
        )
        existing["text"] = alternate["text"]
        existing["source_passage"] = alternate["source_passage"]
    elif corruption == "unrelated_edge_evidence":
        unrelated = {**payload["evidence"][0], "id": str(uuid4())}
        payload["evidence"].append(unrelated)
        payload["graph"]["edges"][0]["evidence_ids"] = [unrelated["id"]]
    else:
        payload["graph"]["edges"].append(payload["graph"]["edges"][0])
    with pytest.raises(ValidationError):
        UniversalResearchResult.model_validate(payload)
