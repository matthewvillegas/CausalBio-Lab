"""Compose curated data, graph scoring, safety, and reproducibility metadata."""

from __future__ import annotations

from collections.abc import Mapping

from causalbio import __version__
from causalbio.demo.registry import DomainPackRegistry
from causalbio.domain.enums import InferenceState, InvestigationState
from causalbio.domain.identifiers import stable_uuid
from causalbio.domain.models import (
    InferenceEligibility,
    InvestigationResult,
    MechanismPath,
    MechanisticHypothesis,
)
from causalbio.evidence.scoring import PathScorer
from causalbio.evidence.sensitivity import ranking_sensitivity
from causalbio.graph.repository import LocalKnowledgeGraph
from causalbio.questions.interpreter import interpret_question
from causalbio.safety.classifier import classify_query


class RestrictedQueryError(ValueError):
    """A request asks for restricted operational medical or bioactive guidance."""


class InvestigationService:
    """Build complete, deterministic offline investigations."""

    random_seed = 1729

    def __init__(self, registry: DomainPackRegistry | None = None) -> None:
        self.registry = registry or DomainPackRegistry()

    def investigate(
        self,
        text: str,
        *,
        context_updates: Mapping[str, str | bool | None] | None = None,
    ) -> InvestigationResult:
        safety_notice = classify_query(text)
        if safety_notice.restricted:
            raise RestrictedQueryError(safety_notice.message)
        domain, question = interpret_question(
            text, context_updates=context_updates, registry=self.registry
        )
        pack = self.registry.load(domain)
        metadata = self.registry.metadata(domain)
        graph = LocalKnowledgeGraph(
            pack.entities,
            pack.assertions,
            pack.evidence,
            graph_id=stable_uuid("graph", f"{pack.slug}:{pack.version}"),
            version=pack.version,
        )
        scorer = PathScorer(pack.evidence)
        requested_context = " ".join(
            filter(
                None,
                (
                    question.context.anatomical_region,
                    question.context.tissue,
                    question.context.activity,
                ),
            )
        )
        assertion_lookup = {item.id: item for item in pack.assertions}

        scored_hypotheses: list[MechanisticHypothesis] = []
        for hypothesis in pack.hypotheses:
            scored_paths: list[MechanismPath] = []
            for path in hypothesis.mechanism_paths:
                assertions = [assertion_lookup[item] for item in path.assertion_ids]
                score = scorer.score(
                    assertions,
                    requested_context=requested_context,
                )
                weak_links = tuple(
                    assertion.id
                    for assertion, components in zip(assertions, score.edge_components, strict=True)
                    if scorer.edge_support(components) < 0.5
                )
                scored_paths.append(
                    path.model_copy(update={"score": score, "weak_link_assertion_ids": weak_links})
                )
            scored_paths.sort(
                key=lambda item: item.score.display_index if item.score else 0, reverse=True
            )
            scored_hypotheses.append(
                hypothesis.model_copy(update={"mechanism_paths": tuple(scored_paths)})
            )

        scored_hypotheses.sort(
            key=lambda item: max(
                path.score.display_index if path.score else 0 for path in item.mechanism_paths
            ),
            reverse=True,
        )
        interventions = tuple(
            sorted(
                pack.interventions,
                key=lambda item: (
                    item.evidence_strength,
                    item.mechanistic_relevance,
                    item.translational_maturity,
                ),
                reverse=True,
            )
        )
        projection = graph.projection()
        entity_names = {item.id: item.preferred_name for item in pack.entities}
        problem_paths = tuple(
            tuple(entity_names[entity_id] for entity_id in hypothesis.mechanism_paths[0].entity_ids)
            for hypothesis in scored_hypotheses[:3]
        )
        strongest = scored_hypotheses[0]
        strongest_score = strongest.mechanism_paths[0].score
        contradiction_count = sum(
            bool(assertion.contradictory_evidence_ids) for assertion in projection.assertions
        )
        key_findings = (
            f"{len(scored_hypotheses)} competing mechanism families match the interpreted context.",
            (
                f"The highest-ranked evidence path is “{strongest.title}” with a "
                f"{strongest_score.display_index:.1f}/100 plausibility index."
                if strongest_score
                else f"The highest-ranked mechanism family is “{strongest.title}”."
            ),
            f"{contradiction_count} graph assertion(s) retain explicitly linked contradictory or limiting evidence.",
            "Mechanism ranking compares evidence structure; it does not estimate an individual outcome or treatment effect.",
        )
        eligibility = InferenceEligibility(
            state=InferenceState.INELIGIBLE,
            eligible=False,
            requirements={
                "defined_numerical_model": pack.petri_model is not None,
                "observed_or_curated_numerical_data": metadata.numerical_data.observations_available,
                "unknown_parameters": metadata.numerical_data.unknown_parameters_defined,
                "explicit_priors": metadata.numerical_data.priors_defined,
                "explicit_likelihood": metadata.numerical_data.likelihood_defined,
                "identifiability_review": metadata.numerical_data.identifiability_reviewed,
                "hmc_backend_and_diagnostics": False,
            },
            explanation=(
                "Bayesian parameter inference is unavailable. "
                + metadata.numerical_data.explanation
            ),
        )
        investigation_id = stable_uuid(
            "investigation",
            f"{question.id}:{pack.slug}:{pack.version}:{scorer.rubric_version}:{self.random_seed}",
        )
        return InvestigationResult(
            id=investigation_id,
            state=InvestigationState.COMPLETE,
            question=question,
            domain_pack=pack.slug,
            graph=projection,
            hypotheses=tuple(scored_hypotheses),
            interventions=interventions,
            petri_model=pack.petri_model,
            safety_notice=safety_notice,
            key_findings=key_findings,
            biological_layers=(
                "person-level outcome",
                "anatomy and tissue",
                "cells and signaling",
                "molecular pathway",
                "intervention points",
            ),
            problem_map_paths=problem_paths,
            inference_eligibility=eligibility,
            software_version=__version__,
            graph_version=pack.version,
            evidence_rubric_version=scorer.rubric_version,
            random_seed=self.random_seed,
            ranking_sensitivity=ranking_sensitivity(
                pack.evidence,
                pack.assertions,
                scored_hypotheses,
                requested_context=requested_context,
            ),
        )
