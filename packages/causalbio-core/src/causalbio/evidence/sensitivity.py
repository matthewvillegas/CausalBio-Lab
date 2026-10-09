"""Local one-at-a-time ranking sensitivity to explicit policy weights."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from causalbio.domain.models import CausalAssertion, EvidenceRecord, MechanisticHypothesis
from causalbio.domain.scoring_policy import MechanismRankRange, RankingSensitivity, ScoringWeights
from causalbio.evidence.scoring import PathScorer


def ranking_sensitivity(
    evidence: Iterable[EvidenceRecord],
    assertions: Iterable[CausalAssertion],
    hypotheses: Iterable[MechanisticHypothesis],
    *,
    requested_context: str | None = None,
    weights: ScoringWeights | None = None,
    relative_change: float = 0.20,
) -> RankingSensitivity:
    if not 0 < relative_change <= 0.5:
        raise ValueError("Relative sensitivity change must be in (0, 0.5]")
    policy = weights or ScoringWeights()
    records = tuple(evidence)
    families = tuple(hypotheses)
    lookup = {item.id: item for item in assertions}
    if not families or any(not item.mechanism_paths for item in families):
        raise ValueError("Ranking sensitivity requires mechanisms with nonempty paths")

    def ranks(configuration: ScoringWeights) -> dict[UUID, int]:
        scorer = PathScorer(records, weights=configuration)
        scores = {
            item.id: max(
                scorer.score(
                    (lookup[edge] for edge in path.assertion_ids),
                    requested_context=requested_context,
                ).display_index
                for path in item.mechanism_paths
            )
            for item in families
        }
        # Ties share a rank; do not imply stable order among indistinguishable values.
        return {
            key: 1 + sum(other > value for other in scores.values())
            for key, value in scores.items()
        }

    baseline = ranks(policy)
    variants: list[dict[UUID, int]] = []
    for name, value in policy.model_dump().items():
        for factor in (1 - relative_change, 1 + relative_change):
            varied = {**policy.model_dump(), name: min(1.0, value * factor)}
            variants.append(ranks(ScoringWeights.model_validate(varied)))
    changed = sum(item != baseline for item in variants)
    return RankingSensitivity(
        relative_change=relative_change,
        tested_configurations=len(variants),
        changed_configurations=changed,
        stable=not changed,
        ranks=tuple(
            MechanismRankRange(
                hypothesis_id=item.id,
                baseline_rank=baseline[item.id],
                best_rank=min(r[item.id] for r in [baseline, *variants]),
                worst_rank=max(r[item.id] for r in [baseline, *variants]),
            )
            for item in families
        ),
    )
