"""Tests for transparent evidence components and path plausibility ranking."""

from __future__ import annotations

import math

import pytest
from causalbio.domain.enums import CausalStatus, CurationStatus, EvidenceGrade
from causalbio.domain.models import PlausibilityScore
from causalbio.evidence import PathScorer
from factories import make_assertion, make_entity, make_evidence


def test_scoring_components_are_explicit_and_replicated_human_evidence_is_recognized() -> None:
    source = make_entity(1, "Source")
    target = make_entity(2, "Target")
    first = make_evidence(1, species="human", grade=EvidenceGrade.B)
    second = make_evidence(2, species="human", grade=EvidenceGrade.B)
    assertion = make_assertion(
        1,
        source.id,
        target.id,
        supporting=(first.id, second.id),
        grade=EvidenceGrade.B,
    )

    components = PathScorer((first, second)).components_for(
        assertion, requested_context="hippocampal neurons"
    )
    assert components.evidence_quality == pytest.approx(0.82)
    assert components.causal_directness == pytest.approx(0.95)
    assert components.human_relevance == pytest.approx(1.0)
    assert components.replication == pytest.approx(0.63)
    assert components.context_match == pytest.approx(0.95)
    assert components.contradiction_penalty == 0.0
    assert components.extrapolation_penalty == 0.0


def test_species_mismatch_reduces_relevance_and_adds_extrapolation_penalty() -> None:
    source = make_entity(1, "Source")
    target = make_entity(2, "Target")
    mouse = make_evidence(1, species="mouse")
    assertion = make_assertion(
        1,
        source.id,
        target.id,
        supporting=(mouse.id,),
        species="mouse",
    )
    scorer = PathScorer((mouse,))

    human_request = scorer.components_for(assertion, requested_species="human")
    mouse_request = scorer.components_for(assertion, requested_species="mouse")
    assert human_request.human_relevance == pytest.approx(0.35)
    assert human_request.extrapolation_penalty == pytest.approx(0.35)
    assert mouse_request.human_relevance == pytest.approx(1.0)
    assert mouse_request.extrapolation_penalty == 0.0
    assert scorer.edge_support(human_request) < scorer.edge_support(mouse_request)


def test_prediction_status_adds_a_separate_extrapolation_penalty() -> None:
    source = make_entity(1, "Source")
    target = make_entity(2, "Target")
    mouse = make_evidence(1, species="mouse")
    assertion = make_assertion(
        1,
        source.id,
        target.id,
        supporting=(mouse.id,),
        species="mouse",
        causal_status=CausalStatus.COMPUTATIONAL_PREDICTION,
    )

    components = PathScorer((mouse,)).components_for(assertion, requested_species="human")
    assert components.extrapolation_penalty == pytest.approx(0.65)
    assert components.causal_directness == pytest.approx(0.28)


def test_contradictory_evidence_is_retained_as_a_penalty_not_silently_dropped() -> None:
    source = make_entity(1, "Source")
    target = make_entity(2, "Target")
    support = make_evidence(1)
    first_contradiction = make_evidence(2, result_direction="contradicts")
    second_contradiction = make_evidence(3, result_direction="mixed")
    baseline = make_assertion(1, source.id, target.id, supporting=(support.id,))
    contested = make_assertion(
        2,
        source.id,
        target.id,
        supporting=(support.id,),
        contradictory=(first_contradiction.id, second_contradiction.id),
    )
    scorer = PathScorer((support, first_contradiction, second_contradiction))

    components = scorer.components_for(contested)
    assert components.contradiction_penalty == pytest.approx(0.44)
    assert scorer.edge_support(components) < scorer.edge_support(scorer.components_for(baseline))
    assert scorer.score((contested,)).display_index < scorer.score((baseline,)).display_index


def test_missing_support_has_low_relevance_and_replication_without_fake_defaults() -> None:
    source = make_entity(1, "Source")
    target = make_entity(2, "Target")
    assertion = make_assertion(
        1,
        source.id,
        target.id,
        supporting=(),
        grade=EvidenceGrade.U,
        causal_status=CausalStatus.HYPOTHESIS_ONLY,
        review_status=CurationStatus.SUGGESTED,
    )

    components = PathScorer(()).components_for(assertion)
    assert components.human_relevance == pytest.approx(0.1)
    assert components.replication == pytest.approx(0.1)
    assert components.extrapolation_penalty == pytest.approx(0.65)


def test_path_score_exposes_length_and_unsupported_link_penalties() -> None:
    entities = tuple(make_entity(index, f"Entity {index}") for index in range(1, 5))
    evidence = make_evidence(1, species="mouse", grade=EvidenceGrade.E)
    assertions = tuple(
        make_assertion(
            index,
            entities[index - 1].id,
            entities[index].id,
            supporting=(evidence.id,),
            grade=EvidenceGrade.E,
            causal_status=CausalStatus.HYPOTHESIS_ONLY,
            species="mouse",
        )
        for index in range(1, 4)
    )

    score = PathScorer((evidence,)).score(assertions)
    assert score.path_length_penalty == pytest.approx(0.1)
    assert score.unsupported_link_penalty == pytest.approx(0.96)
    assert score.label == "plausibility index"
    assert 0.0 <= score.display_index <= 100.0
    assert any("not a probability" in item for item in score.explanation)
    assert score == PathScorer((evidence,)).score(assertions)


def test_empty_path_cannot_receive_a_plausibility_score() -> None:
    with pytest.raises(ValueError, match="empty mechanism path"):
        PathScorer(()).score(())


def test_exported_edge_support_preserves_path_order_and_reconstructs_the_score() -> None:
    entities = tuple(make_entity(index, f"Entity {index}") for index in range(1, 4))
    evidence = make_evidence(1)
    weaker = make_assertion(
        1,
        entities[0].id,
        entities[1].id,
        supporting=(evidence.id,),
        grade=EvidenceGrade.U,
        causal_status=CausalStatus.HYPOTHESIS_ONLY,
    )
    stronger = make_assertion(2, entities[1].id, entities[2].id, supporting=(evidence.id,))
    score = PathScorer((evidence,)).score((weaker, stronger))

    assert len(score.edge_support_values) == 2
    assert 0 < score.edge_support_values[0] < score.edge_support_values[1] < 1
    reconstructed = sum(math.log(value + 1e-9) for value in score.edge_support_values)
    reconstructed -= score.path_length_penalty + score.unsupported_link_penalty
    assert score.raw_log_support == pytest.approx(reconstructed)
    assert score.model_dump(mode="json")["edge_support_values"] == list(score.edge_support_values)
    assert PlausibilityScore.model_validate_json(score.model_dump_json()) == score

    legacy_payload = score.model_dump(exclude={"edge_support_values"})
    assert PlausibilityScore.model_validate(legacy_payload).edge_support_values == ()
    with pytest.raises(ValueError, match="align"):
        PlausibilityScore.model_validate({**legacy_payload, "edge_support_values": [0.5]})
