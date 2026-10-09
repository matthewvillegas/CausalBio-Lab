"""Common research boundary; provisional claims never become curated assertions."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import Field, HttpUrl, model_validator

from causalbio.domain.models import (
    DomainModel,
    InvestigationResult,
    ResearchQuestion,
    SafetyNotice,
    utc_now,
)


class ResearchMode(StrEnum):
    CURATED = "CURATED"
    LIVE_RESEARCH = "LIVE_RESEARCH"
    GENERAL_EVIDENCE_SUMMARY = "GENERAL_EVIDENCE_SUMMARY"
    EXPLANATORY = "EXPLANATORY"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    RESTRICTED_WITH_SAFE_ALTERNATIVE = "RESTRICTED_WITH_SAFE_ALTERNATIVE"
    OUT_OF_DOMAIN = "OUT_OF_DOMAIN"
    ERROR = "ERROR"


ResearchDepth = Literal["quick", "research", "deep"]


class EntityHint(DomainModel):
    name: str
    entity_type: str
    aliases: tuple[str, ...] = ()
    identifiers: dict[str, str] = Field(default_factory=dict)


class ResearchInterpretation(DomainModel):
    mode: ResearchMode
    question: ResearchQuestion
    domain_pack: str | None = None
    depth: ResearchDepth = "research"
    entities: tuple[EntityHint, ...] = ()
    search_queries: tuple[str, ...] = ()
    clarifications: tuple[str, ...] = ()
    safe_research_question: str | None = None
    notice: str
    safety_notice: SafetyNotice


class ResearchEvidence(DomainModel):
    id: UUID
    source: str
    source_record_id: str
    title: str
    authors: tuple[str, ...] = ()
    year: int | None = None
    doi: str | None = None
    pmid: str | None = None
    source_url: HttpUrl
    abstract: str | None = Field(default=None, max_length=50000)
    organism: str | None = None
    population: str | None = None
    tissue: str | None = None
    cell_type: str | None = None
    study_type: str | None = None
    primary_or_review: Literal["primary", "review", "unspecified"] = "unspecified"
    experimental_context: str | None = None
    annotation_evidence: tuple[dict[str, str | None], ...] = ()
    result_direction: Literal[
        "supports", "contradicts", "mixed", "contextualizes", "unspecified"
    ] = "unspecified"
    effect_estimate: str | None = None
    sample_size: int | None = Field(default=None, ge=1)
    limitations: tuple[str, ...] = ()
    retrieved_at: datetime
    cache_status: Literal["fetched", "fresh_cache", "stale_cache", "local_curated"]
    evidence_status: Literal["provisional", "curated"] = "provisional"


class ResearchClaim(DomainModel):
    id: UUID
    text: str = Field(min_length=1, max_length=2500)
    evidence_ids: tuple[UUID, ...] = Field(min_length=1)
    kind: Literal["source_extract", "curated_summary", "structured_annotation"]
    source_passage: str | None = None
    relation: Literal["ASSOCIATED_WITH", "SUPPORTED_BY", "CONTRADICTED_BY", "PARTICIPATES_IN"] = (
        "SUPPORTED_BY"
    )
    uncertainty: str = "Provisional source extraction; independent review is needed."


class ResearchMechanism(DomainModel):
    id: UUID
    title: str
    description: str
    claims: tuple[ResearchClaim, ...] = Field(min_length=1)
    uncertainties: tuple[str, ...] = ()
    evidence_dimensions: dict[str, str] = Field(default_factory=dict)
    model_eligibility: Literal[
        "GRAPH_ONLY",
        "QUALITATIVE_MODEL_AVAILABLE",
        "PETRI_MODEL_AVAILABLE",
        "ODE_MODEL_AVAILABLE",
        "BAYESIAN_MODEL_AVAILABLE",
    ] = "GRAPH_ONLY"


class ResearchNode(DomainModel):
    id: UUID
    name: str
    entity_type: str
    identifiers: dict[str, str] = Field(default_factory=dict)


class ResearchEdge(DomainModel):
    id: UUID
    subject_id: UUID
    object_id: UUID
    relation: Literal["SUPPORTED_BY", "CONTRADICTED_BY", "ASSOCIATED_WITH", "PARTICIPATES_IN"]
    claim_id: UUID | None = None
    evidence_ids: tuple[UUID, ...]
    status: Literal["provisional"] = "provisional"


class TemporaryGraph(DomainModel):
    nodes: tuple[ResearchNode, ...] = ()
    edges: tuple[ResearchEdge, ...] = ()
    notice: str = (
        "Provisional evidence map. Source links and topic membership are not causal effects."
    )


class SourceRun(DomainModel):
    source: str
    provider_version: str | None = None
    query: str
    status: Literal["available", "cached", "unavailable", "offline"]
    record_count: int = Field(ge=0)
    retrieved_at: datetime | None = None
    detail: str | None = None


class UniversalResearchResult(DomainModel):
    id: UUID
    mode: ResearchMode
    interpretation: ResearchInterpretation
    direct_answer: tuple[ResearchClaim, ...] = ()
    mechanisms: tuple[ResearchMechanism, ...] = ()
    evidence: tuple[ResearchEvidence, ...] = ()
    graph: TemporaryGraph = Field(default_factory=TemporaryGraph)
    complications: tuple[ResearchClaim, ...] = ()
    modifiers: tuple[ResearchClaim, ...] = ()
    source_runs: tuple[SourceRun, ...] = ()
    limitations: tuple[str, ...]
    notices: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)
    curated_result: InvestigationResult | None = None
    saved_locally: bool = False
    synthesis_method: str = (
        "Deterministic grouping of cited source extracts; no LLM-generated biological claims."
    )

    @model_validator(mode="after")
    def validate_provisional_references(self) -> UniversalResearchResult:
        records = {item.id for item in self.evidence}
        nodes = {item.id for item in self.graph.nodes}
        if len(records) != len(self.evidence) or len(nodes) != len(self.graph.nodes):
            raise ValueError("Research evidence and node identifiers must be unique")
        claims = (
            *self.direct_answer,
            *self.complications,
            *self.modifiers,
            *(claim for mechanism in self.mechanisms for claim in mechanism.claims),
        )
        claim_map: dict[UUID, ResearchClaim] = {}
        for claim in claims:
            if claim.id in claim_map and claim_map[claim.id] != claim:
                raise ValueError("Repeated claim identifiers must have identical content")
            claim_map[claim.id] = claim
            if not set(claim.evidence_ids) <= records:
                raise ValueError("Research claims must cite evidence in the same result")
            if claim.kind in {"source_extract", "structured_annotation"} and (
                claim.source_passage != claim.text
                or not any(
                    claim.text in (item.abstract or "")
                    for item in self.evidence
                    if item.id in claim.evidence_ids
                )
            ):
                raise ValueError("Extracted claims must preserve text from their cited source")
            if claim.kind == "curated_summary" and any(
                item.evidence_status != "curated" or item.source != "local_curated"
                for item in self.evidence
                if item.id in claim.evidence_ids
            ):
                raise ValueError("Curated summaries require locally curated source evidence")
        timestamps = [
            self.created_at,
            *(item.retrieved_at for item in self.evidence),
            *(item.retrieved_at for item in self.source_runs if item.retrieved_at is not None),
        ]
        if any(item.tzinfo is None or item.utcoffset() is None for item in timestamps):
            raise ValueError("Research timestamps must be timezone-aware")
        if len({edge.id for edge in self.graph.edges}) != len(self.graph.edges):
            raise ValueError("Research edge identifiers must be unique")
        for edge in self.graph.edges:
            if edge.subject_id not in nodes or edge.object_id not in nodes:
                raise ValueError("Research edge endpoints must exist")
            if not edge.evidence_ids or not set(edge.evidence_ids) <= records:
                raise ValueError("Research edges require source evidence")
            if edge.claim_id is not None:
                if edge.claim_id not in claim_map:
                    raise ValueError("Research edge claim reference is missing")
                if not set(edge.evidence_ids) <= set(claim_map[edge.claim_id].evidence_ids):
                    raise ValueError("Research edge evidence must support its referenced claim")
        return self
