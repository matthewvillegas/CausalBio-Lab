"""Cross-object integrity checks shared by pack loading and the validation CLI."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from causalbio.domain.identifiers import stable_uuid
from causalbio.domain.models import DomainPack
from causalbio.graph.repository import GraphValidationError, LocalKnowledgeGraph
from causalbio.petri.engine import PetriEngine


def _references(values: Iterable[UUID], known: set[UUID], label: str) -> None:
    missing = set(values) - known
    if missing:
        raise GraphValidationError(
            f"{label} references missing objects: {sorted(map(str, missing))}"
        )


def validate_domain_pack(pack: DomainPack) -> LocalKnowledgeGraph:
    graph = LocalKnowledgeGraph(
        pack.entities,
        pack.assertions,
        pack.evidence,
        graph_id=stable_uuid("graph", f"{pack.slug}:{pack.version}"),
        version=pack.version,
    )
    projection = graph.projection()
    entities = {item.id for item in projection.entities}
    assertions = {item.id for item in projection.assertions}
    evidence = {item.id for item in projection.evidence}
    interventions = {item.id for item in pack.interventions}
    if not pack.hypotheses:
        raise GraphValidationError("A domain pack must include at least one mechanism")
    for label, values in (
        ("hypothesis", [item.id for item in pack.hypotheses]),
        ("intervention", [item.id for item in pack.interventions]),
        ("path", [path.id for item in pack.hypotheses for path in item.mechanism_paths]),
    ):
        if len(values) != len(set(values)):
            raise GraphValidationError(f"Duplicate {label} identifier")
    for hypothesis in pack.hypotheses:
        _references(
            (
                hypothesis.trigger_id,
                hypothesis.outcome_id,
                *hypothesis.mediator_ids,
                *hypothesis.tissue_ids,
                *hypothesis.cell_ids,
                *hypothesis.pathway_ids,
            ),
            set(graph.entities),
            "Hypothesis entities",
        )
        _references(
            (*hypothesis.evidence_ids, *hypothesis.contradictory_evidence_ids),
            evidence,
            "Hypothesis evidence",
        )
        _references(hypothesis.intervention_ids, interventions, "Hypothesis interventions")
        if not hypothesis.mechanism_paths or not hypothesis.evidence_ids:
            raise GraphValidationError("Mechanisms require paths and graph-local evidence")
        for path in hypothesis.mechanism_paths:
            graph.validate_path(path)
            _references(path.entity_ids, entities, "Trusted mechanism entities")
            _references(path.assertion_ids, assertions, "Trusted mechanism assertions")
            if (
                path.entity_ids[0] != hypothesis.trigger_id
                or path.entity_ids[-1] != hypothesis.outcome_id
            ):
                raise GraphValidationError(
                    "Mechanism path endpoints do not match its trigger and outcome"
                )
    for item in pack.interventions:
        _references(item.target_entity_ids, entities, "Intervention targets")
        _references(item.downstream_assertion_ids, assertions, "Intervention assertions")
        _references(item.evidence_ids, evidence, "Intervention evidence")
        if not item.evidence_ids or not item.target_entity_ids:
            raise GraphValidationError("Interventions require targets and graph-local evidence")
    if pack.petri_model is not None:
        PetriEngine(pack.petri_model)
        for transition in pack.petri_model.transitions:
            _references(transition.evidence_ids, set(graph.evidence), "Model transition evidence")
    return graph
