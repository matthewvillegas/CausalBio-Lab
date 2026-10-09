"""Offline end-to-end investigation tests for both curated domain packs."""

from __future__ import annotations

import pytest
from causalbio.demo import available_domain_packs, load_domain_pack
from causalbio.domain.enums import (
    CurationStatus,
    InferenceState,
    InvestigationState,
    QuerySafetyClass,
)
from causalbio.investigations import InvestigationService
from causalbio.investigations.service import RestrictedQueryError


@pytest.mark.parametrize(
    ("slug", "question", "safety_class"),
    [
        (
            "memory",
            "How could long-term memory persist after learning?",
            QuerySafetyClass.GENERAL_RESEARCH,
        ),
        (
            "knee-pain",
            "What mechanisms contribute to knee pain after repeated jumping?",
            QuerySafetyClass.SYMPTOM_EDUCATION,
        ),
    ],
)
def test_complete_investigation_is_grounded_ranked_and_reproducible(
    slug: str, question: str, safety_class: QuerySafetyClass
) -> None:
    service = InvestigationService()
    result = service.investigate(question)
    repeated = service.investigate(question)

    assert result.state is InvestigationState.COMPLETE
    assert result.domain_pack == slug
    assert result.id == repeated.id
    assert result.graph == repeated.graph
    assert tuple(item.id for item in result.hypotheses) == tuple(
        item.id for item in repeated.hypotheses
    )
    assert result.random_seed == repeated.random_seed == service.random_seed
    assert result.graph_version == repeated.graph_version
    assert result.safety_notice.query_class is safety_class
    assert result.safety_notice.restricted is False

    assert len(result.hypotheses) >= 2
    hypothesis_scores = [
        max(path.score.display_index for path in hypothesis.mechanism_paths if path.score)
        for hypothesis in result.hypotheses
    ]
    assert hypothesis_scores == sorted(hypothesis_scores, reverse=True)
    assert all(
        path.score is not None
        and path.score.label == "plausibility index"
        and any("not a probability" in line for line in path.score.explanation)
        for hypothesis in result.hypotheses
        for path in hypothesis.mechanism_paths
    )

    graph_entity_ids = {entity.id for entity in result.graph.entities}
    graph_evidence_ids = {record.id for record in result.graph.evidence}
    assert graph_entity_ids
    assert graph_evidence_ids
    assert all(
        assertion.review_status in {CurationStatus.VALIDATED, CurationStatus.CURATED}
        and assertion.subject_id in graph_entity_ids
        and assertion.object_id in graph_entity_ids
        and set(assertion.supporting_evidence_ids).issubset(graph_evidence_ids)
        and set(assertion.contradictory_evidence_ids).issubset(graph_evidence_ids)
        for assertion in result.graph.assertions
    )

    assert result.problem_map_paths
    assert result.key_findings
    assert any("does not estimate an individual outcome" in item for item in result.key_findings)
    assert all(
        intervention.personal_recommendation is False for intervention in result.interventions
    )
    intervention_ranking = [
        (
            item.evidence_strength,
            item.mechanistic_relevance,
            item.translational_maturity,
        )
        for item in result.interventions
    ]
    assert intervention_ranking == sorted(intervention_ranking, reverse=True)

    assert result.petri_model is not None
    assert result.petri_model.curated is True
    assert "not a personalized biological prediction" in result.petri_model.safety_label
    assert result.inference_eligibility.state is InferenceState.INELIGIBLE
    assert result.inference_eligibility.eligible is False
    assert result.inference_eligibility.no_fake_fallback is True
    assert result.completed_at.tzinfo is not None


def test_domain_pack_registry_loads_both_packs_deterministically() -> None:
    metadata = available_domain_packs()
    assert tuple(item["slug"] for item in metadata) == ("memory", "knee-pain")

    for item in metadata:
        slug = item["slug"]
        pack = load_domain_pack(slug)
        repeated = load_domain_pack(slug)
        assert pack == repeated
        assert pack.slug == slug
        assert pack.version == item["version"]
        assert pack.example_questions
        assert len(pack.entities) == len({entity.id for entity in pack.entities})
        assert len(pack.assertions) == len({assertion.id for assertion in pack.assertions})
        assert len(pack.evidence) == len({record.id for record in pack.evidence})
        assert all(record.study.source_url for record in pack.evidence)


def test_end_to_end_context_update_is_preserved_in_result() -> None:
    result = InvestigationService().investigate(
        "What mechanisms contribute to knee pain after repeated jumping?",
        context_updates={"activity": "volleyball jumping", "timing": "the following morning"},
    )

    assert result.question.context.activity == "volleyball jumping"
    assert result.question.context.timing == "the following morning"
    assert result.domain_pack == "knee-pain"


def test_restricted_query_is_stopped_before_an_investigation_is_built() -> None:
    with pytest.raises(RestrictedQueryError, match="cannot provide personal dosing guidance"):
        InvestigationService().investigate(
            "How many mg of a peptide should I take to improve memory?"
        )
