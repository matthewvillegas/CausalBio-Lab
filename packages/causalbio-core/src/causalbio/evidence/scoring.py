"""Documented plausibility scoring for evidence-backed mechanism paths.

The values returned here are ranking heuristics. They are deliberately named and
presented as a plausibility index, never as a posterior probability or effect size.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping

from causalbio.domain.enums import CausalStatus, EvidenceGrade
from causalbio.domain.models import (
    CausalAssertion,
    EvidenceRecord,
    EvidenceScoreComponents,
    PlausibilityScore,
)
from causalbio.domain.scoring_policy import POSITIVE_COMPONENTS, ScoringWeights

GRADE_SUPPORT: Mapping[EvidenceGrade, float] = {
    EvidenceGrade.A: 0.95,
    EvidenceGrade.B: 0.82,
    EvidenceGrade.C: 0.68,
    EvidenceGrade.D: 0.50,
    EvidenceGrade.E: 0.32,
    EvidenceGrade.U: 0.15,
}

DIRECTNESS: Mapping[CausalStatus, float] = {
    CausalStatus.CAUSAL_EXPERIMENTAL: 0.95,
    CausalStatus.QUASI_EXPERIMENTAL: 0.82,
    CausalStatus.MECHANISTIC_BIOCHEMICAL: 0.80,
    CausalStatus.GENETIC_EVIDENCE: 0.76,
    CausalStatus.LONGITUDINAL_ASSOCIATION: 0.58,
    CausalStatus.EXPERT_CURATION: 0.55,
    CausalStatus.CROSS_SECTIONAL_ASSOCIATION: 0.38,
    CausalStatus.COMPUTATIONAL_PREDICTION: 0.28,
    CausalStatus.HYPOTHESIS_ONLY: 0.12,
}


class PathScorer:
    """Score graph assertions with inspectable, versioned components."""

    rubric_version = "causalbio-evidence-rubric-1.1"

    def __init__(
        self, evidence: Iterable[EvidenceRecord], *, weights: ScoringWeights | None = None
    ) -> None:
        self._evidence = {record.id: record for record in evidence}
        self.weights = weights or ScoringWeights()

    def components_for(
        self,
        assertion: CausalAssertion,
        *,
        requested_species: str = "human",
        requested_context: str | None = None,
    ) -> EvidenceScoreComponents:
        records = [
            self._evidence[evidence_id]
            for evidence_id in assertion.supporting_evidence_ids
            if evidence_id in self._evidence
        ]
        contradictory = [
            self._evidence[evidence_id]
            for evidence_id in assertion.contradictory_evidence_ids
            if evidence_id in self._evidence
        ]

        quality = GRADE_SUPPORT[assertion.confidence_classification]
        directness = DIRECTNESS[assertion.causal_status]
        if not records:
            human_relevance = 0.1
            replication = 0.1
        else:
            human_records = sum(
                requested_species.casefold()
                in f"{record.experimental_context.species} {record.study.population.species}".casefold()
                for record in records
            )
            human_relevance = 0.35 + 0.65 * (human_records / len(records))
            replication = min(1.0, 0.45 + 0.18 * (len(records) - 1))

        context_haystack = " ".join(
            filter(
                None,
                (
                    assertion.biological_context.tissue,
                    assertion.biological_context.cell_type,
                    assertion.biological_context.condition,
                    assertion.biological_context.population,
                ),
            )
        ).casefold()
        if requested_context:
            requested_terms = {
                term
                for term in requested_context.casefold().replace(",", " ").split()
                if len(term) > 3
            }
            context_match = 0.95 if requested_terms & set(context_haystack.split()) else 0.62
        else:
            context_match = 0.8

        contradiction_penalty = min(0.85, 0.22 * len(contradictory))
        nonhuman_fraction = (
            sum(
                requested_species.casefold()
                not in f"{record.experimental_context.species} {record.study.population.species}".casefold()
                for record in records
            )
            / len(records)
            if records
            else 1.0
        )
        extrapolation_penalty = 0.35 * nonhuman_fraction
        if assertion.causal_status in {
            CausalStatus.COMPUTATIONAL_PREDICTION,
            CausalStatus.HYPOTHESIS_ONLY,
        }:
            extrapolation_penalty = min(1.0, extrapolation_penalty + 0.3)

        return EvidenceScoreComponents(
            evidence_quality=quality,
            causal_directness=directness,
            human_relevance=human_relevance,
            replication=replication,
            context_match=context_match,
            contradiction_penalty=contradiction_penalty,
            extrapolation_penalty=extrapolation_penalty,
        )

    def edge_support(self, components: EvidenceScoreComponents) -> float:
        total_weight = sum(float(getattr(self.weights, name)) for name in POSITIVE_COMPONENTS)
        positive = (
            sum(
                float(getattr(self.weights, name)) * float(getattr(components, name))
                for name in POSITIVE_COMPONENTS
            )
            / total_weight
        )
        penalty = (
            self.weights.contradiction_penalty * components.contradiction_penalty
            + self.weights.extrapolation_penalty * components.extrapolation_penalty
        )
        return min(0.99, max(0.03, positive - penalty))

    def score(
        self,
        assertions: Iterable[CausalAssertion],
        *,
        requested_species: str = "human",
        requested_context: str | None = None,
    ) -> PlausibilityScore:
        assertion_list = tuple(assertions)
        if not assertion_list:
            raise ValueError("Cannot score an empty mechanism path")

        components = tuple(
            self.components_for(
                assertion,
                requested_species=requested_species,
                requested_context=requested_context,
            )
            for assertion in assertion_list
        )
        supports = tuple(self.edge_support(component) for component in components)
        path_length_penalty = self.weights.path_length * max(0, len(assertion_list) - 2)
        unsupported_count = sum(
            assertion.confidence_classification in {EvidenceGrade.E, EvidenceGrade.U}
            or assertion.causal_status is CausalStatus.HYPOTHESIS_ONLY
            for assertion in assertion_list
        )
        unsupported_penalty = self.weights.unsupported_link * unsupported_count
        raw = sum(math.log(value + 1e-9) for value in supports)
        raw -= path_length_penalty + unsupported_penalty
        geometric_support = math.exp(raw / len(assertion_list))
        display_index = round(100 * min(1.0, max(0.0, geometric_support)), 1)

        weakest_index = supports.index(min(supports))
        explanation = (
            f"{len(assertion_list)} provenance-bearing assertions were scored.",
            f"The weakest edge support is {supports[weakest_index]:.2f} at step {weakest_index + 1}.",
            f"Path length penalty: {path_length_penalty:.2f}; unsupported-link penalty: {unsupported_penalty:.2f}.",
            "The displayed value is a plausibility index for comparison, not a probability or treatment effect.",
        )
        return PlausibilityScore(
            scoring_weights=self.weights,
            raw_log_support=raw,
            display_index=display_index,
            edge_components=components,
            edge_support_values=supports,
            path_length_penalty=path_length_penalty,
            unsupported_link_penalty=unsupported_penalty,
            explanation=explanation,
        )
