"""Weight-policy checks must reveal fragile ordering without inventing probabilities."""

from __future__ import annotations

import pytest
from causalbio.demo.registry import load_domain_pack
from causalbio.domain.enums import CausalStatus, EvidenceGrade
from causalbio.domain.models import MechanismPath, MechanisticHypothesis
from causalbio.domain.scoring_policy import ScoringWeights
from causalbio.evidence.scoring import PathScorer
from causalbio.evidence.sensitivity import ranking_sensitivity
from factories import make_assertion, make_evidence, uid


@pytest.mark.parametrize("value", [-1, float("inf"), float("nan"), 2])
def test_weights_reject_invalid_coefficients(value: float) -> None:
    with pytest.raises(ValueError):
        ScoringWeights(evidence_quality=value)


def test_zero_positive_policy_rejected_and_valid_policy_recorded() -> None:
    with pytest.raises(ValueError, match="nonzero"):
        ScoringWeights(
            evidence_quality=0,
            causal_directness=0,
            human_relevance=0,
            replication=0,
            context_match=0,
        )
    evidence = make_evidence(1)
    edge = make_assertion(1, uid(1), uid(2), supporting=(evidence.id,))
    policy = ScoringWeights(contradiction_penalty=0.4)
    score = PathScorer((evidence,), weights=policy).score((edge,))
    assert score.scoring_weights == policy
    assert score.model_dump(mode="json")["scoring_weights"]["contradiction_penalty"] == 0.4


def test_close_competing_evidence_tradeoff_is_reported_as_unstable() -> None:
    evidence = make_evidence(1)
    edges = (
        make_assertion(
            1,
            uid(1),
            uid(2),
            supporting=(evidence.id,),
            grade=EvidenceGrade.A,
            causal_status=CausalStatus.MECHANISTIC_BIOCHEMICAL,
        ),
        make_assertion(
            2,
            uid(1),
            uid(2),
            supporting=(evidence.id,),
            grade=EvidenceGrade.B,
            causal_status=CausalStatus.CAUSAL_EXPERIMENTAL,
        ),
    )
    hypotheses = tuple(
        MechanisticHypothesis(
            id=uid(100 + index),
            title=f"Synthetic tradeoff {index}",
            plain_language_summary="Synthetic ranking test only.",
            outcome_id=uid(2),
            trigger_id=uid(1),
            mechanism_paths=(
                MechanismPath(
                    id=uid(200 + index), entity_ids=(uid(1), uid(2)), assertion_ids=(edge.id,)
                ),
            ),
            mediator_ids=(),
            evidence_ids=(evidence.id,),
            evidence_label="Synthetic",
            uncertainty=("Synthetic policy tradeoff",),
        )
        for index, edge in enumerate(edges)
    )
    result = ranking_sensitivity((evidence,), edges, hypotheses)
    assert result.tested_configurations == 18
    assert not result.stable
    assert result.changed_configurations > 0
    assert any(rank.best_rank < rank.worst_rank for rank in result.ranks)
    assert result == ranking_sensitivity((evidence,), edges, hypotheses)


@pytest.mark.parametrize("slug", ["memory", "knee-pain"])
def test_bundled_rank_ranges_are_bounded_and_reproducible(slug: str) -> None:
    pack = load_domain_pack(slug)
    result = ranking_sensitivity(pack.evidence, pack.assertions, pack.hypotheses)
    assert len(result.ranks) == len(pack.hypotheses)
    assert all(
        1 <= rank.best_rank <= rank.baseline_rank <= rank.worst_rank <= len(pack.hypotheses)
        for rank in result.ranks
    )
    assert result.stable == (result.changed_configurations == 0)
    assert result == ranking_sensitivity(pack.evidence, pack.assertions, pack.hypotheses)
