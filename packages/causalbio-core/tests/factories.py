"""Small typed factories for focused core tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID

from causalbio.domain.enums import (
    CausalStatus,
    CurationStatus,
    EntityType,
    EvidenceGrade,
    RelationType,
    StudyType,
)
from causalbio.domain.models import (
    BiologicalEntity,
    CausalAssertion,
    EntityIdentifier,
    EvidenceRecord,
    ExperimentalContext,
    Study,
    StudyPopulation,
)

_FIXED_TIME = datetime(2025, 1, 1, tzinfo=UTC)


def uid(value: int) -> UUID:
    """Return a readable deterministic UUID for fixtures."""

    return UUID(int=value)


def make_entity(
    value: int,
    name: str,
    *,
    entity_type: EntityType = EntityType.PROTEIN,
    curation_status: CurationStatus = CurationStatus.CURATED,
) -> BiologicalEntity:
    return BiologicalEntity(
        id=uid(value),
        preferred_name=name,
        entity_type=entity_type,
        description=f"Synthetic entity representing {name} for deterministic tests.",
        source="Synthetic test fixture",
        created_at=_FIXED_TIME,
        updated_at=_FIXED_TIME,
        curation_status=curation_status,
    )


def make_evidence(
    value: int,
    *,
    species: str = "human",
    grade: EvidenceGrade = EvidenceGrade.A,
    curation_status: CurationStatus = CurationStatus.CURATED,
    result_direction: Literal[
        "supports", "contradicts", "mixed", "null", "contextualizes"
    ] = "supports",
) -> EvidenceRecord:
    return EvidenceRecord(
        id=uid(10_000 + value),
        study=Study(
            id=uid(20_000 + value),
            title=f"Synthetic controlled study {value}",
            authors=("Test Author",),
            publication_year=2024,
            journal="Synthetic Fixture Journal",
            identifiers=(EntityIdentifier(namespace="fixture", value=f"study-{value}"),),
            study_type=StudyType.CONTROLLED_EXPERIMENT,
            population=StudyPopulation(
                description=f"Synthetic {species} study population",
                species=species,
                sample_size=20,
            ),
            source_url=f"https://example.org/studies/{value}",
        ),
        experimental_context=ExperimentalContext(
            species=species,
            population=f"synthetic {species} population",
            tissue="hippocampal tissue",
            condition="controlled test condition",
        ),
        result_direction=result_direction,
        limitations=("Synthetic fixture; not scientific evidence.",),
        evidence_note="Synthetic evidence record used only for deterministic software tests.",
        retrieved_at=date(2025, 1, 1),
        source_adapter="test-fixture",
        curation_status=curation_status,
        evidence_grade=grade,
    )


def make_assertion(
    value: int,
    subject_id: UUID,
    object_id: UUID,
    *,
    supporting: tuple[UUID, ...],
    contradictory: tuple[UUID, ...] = (),
    relation: RelationType = RelationType.ACTIVATES,
    grade: EvidenceGrade = EvidenceGrade.A,
    causal_status: CausalStatus = CausalStatus.CAUSAL_EXPERIMENTAL,
    review_status: CurationStatus = CurationStatus.CURATED,
    species: str = "human",
    tissue: str = "hippocampal tissue",
) -> CausalAssertion:
    return CausalAssertion(
        id=uid(30_000 + value),
        subject_id=subject_id,
        relation=relation,
        object_id=object_id,
        confidence_classification=grade,
        causal_status=causal_status,
        biological_context=ExperimentalContext(
            species=species,
            population=f"synthetic {species} research context",
            tissue=tissue,
            condition="controlled test condition",
        ),
        supporting_evidence_ids=supporting,
        contradictory_evidence_ids=contradictory,
        curator="CausalBio test suite",
        extraction_method="manual_curation",
        source="Synthetic test fixture",
        retrieval_date=date(2025, 1, 1),
        review_status=review_status,
        interpretation="Synthetic directional assertion for deterministic testing.",
        limitations=("This assertion is a software fixture, not a biological claim.",),
    )
