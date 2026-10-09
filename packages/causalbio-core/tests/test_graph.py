"""Validation, filtering, path, and provenance-export tests for the local graph."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable
from uuid import UUID

import networkx as nx
import pytest
from causalbio.domain.enums import (
    CausalStatus,
    CurationStatus,
    EntityType,
    EvidenceGrade,
    RelationType,
)
from causalbio.domain.models import BiologicalEntity, CausalAssertion, EvidenceRecord
from causalbio.graph import GraphValidationError, LocalKnowledgeGraph
from factories import make_assertion, make_entity, make_evidence, uid


def knowledge_graph(
    entities: Iterable[BiologicalEntity],
    assertions: Iterable[CausalAssertion],
    evidence: Iterable[EvidenceRecord],
    *,
    graph_id: UUID | None = None,
) -> LocalKnowledgeGraph:
    return LocalKnowledgeGraph(
        entities,
        assertions,
        evidence,
        graph_id=graph_id or uid(900_000),
        version="test-1.0.0",
    )


def test_graph_rejects_assertions_with_missing_entities_or_evidence() -> None:
    source = make_entity(1, "Source")
    target = make_entity(2, "Target")
    evidence = make_evidence(1)

    missing_entity = make_assertion(
        1,
        source.id,
        uid(999),
        supporting=(evidence.id,),
    )
    with pytest.raises(GraphValidationError, match="missing entity"):
        knowledge_graph((source, target), (missing_entity,), (evidence,))

    missing_provenance = make_assertion(
        2,
        source.id,
        target.id,
        supporting=(uid(998),),
    )
    with pytest.raises(GraphValidationError, match="missing evidence"):
        knowledge_graph((source, target), (missing_provenance,), (evidence,))


def test_trusted_assertion_cannot_depend_on_untrusted_evidence() -> None:
    source = make_entity(1, "Source")
    target = make_entity(2, "Target")
    extracted = make_evidence(1, curation_status=CurationStatus.EXTRACTED)
    assertion = make_assertion(1, source.id, target.id, supporting=(extracted.id,))

    with pytest.raises(GraphValidationError, match="depends on untrusted evidence"):
        knowledge_graph((source, target), (assertion,), (extracted,))


def test_duplicate_canonical_entities_are_rejected_case_insensitively() -> None:
    first = make_entity(1, "NMDA receptor", entity_type=EntityType.RECEPTOR)
    duplicate = make_entity(2, "nmda RECEPTOR", entity_type=EntityType.RECEPTOR)

    with pytest.raises(GraphValidationError, match="Duplicate canonical entity"):
        knowledge_graph((first, duplicate), (), ())

    different_type = make_entity(3, "NMDA receptor", entity_type=EntityType.PROTEIN)
    graph = knowledge_graph((first, different_type), (), ())
    assert len(graph.entities) == 2


def test_projection_filters_assertions_and_preserves_selected_provenance() -> None:
    first = make_entity(1, "First")
    second = make_entity(2, "Second")
    third = make_entity(3, "Third")
    human_evidence = make_evidence(1, species="human", grade=EvidenceGrade.A)
    mouse_evidence = make_evidence(2, species="mouse", grade=EvidenceGrade.C)
    trusted = make_assertion(
        1,
        first.id,
        second.id,
        supporting=(human_evidence.id,),
        relation=RelationType.ACTIVATES,
        grade=EvidenceGrade.A,
        species="human",
        tissue="hippocampal tissue",
    )
    suggested = make_assertion(
        2,
        second.id,
        third.id,
        supporting=(mouse_evidence.id,),
        relation=RelationType.INHIBITS,
        grade=EvidenceGrade.C,
        review_status=CurationStatus.SUGGESTED,
        species="mouse",
        tissue="patellar tendon",
    )
    graph = knowledge_graph(
        (first, second, third),
        (trusted, suggested),
        (human_evidence, mouse_evidence),
    )

    default_projection = graph.projection()
    assert default_projection.assertions == (trusted,)
    assert {item.id for item in default_projection.entities} == {first.id, second.id}
    assert default_projection.evidence == (human_evidence,)

    filtered = graph.projection(
        trusted_only=False,
        relations={RelationType.INHIBITS},
        grades={EvidenceGrade.C},
        organism="mouse",
        tissue="tendon",
    )
    assert filtered.assertions == (suggested,)
    assert {item.id for item in filtered.entities} == {second.id, third.id}
    assert filtered.evidence == (mouse_evidence,)
    assert "relations=INHIBITS" in filtered.filters_applied
    assert "grades=C" in filtered.filters_applied
    assert "organism=mouse" in filtered.filters_applied
    assert "tissue=tendon" in filtered.filters_applied


def test_exports_are_deterministic_and_keep_claim_to_evidence_links() -> None:
    source = make_entity(1, "Source")
    target = make_entity(2, "Target")
    support = make_evidence(1)
    contradiction = make_evidence(2, result_direction="contradicts")
    assertion = make_assertion(
        1,
        source.id,
        target.id,
        supporting=(support.id,),
        contradictory=(contradiction.id,),
        relation=RelationType.CONTRIBUTES_TO,
    )
    graph = knowledge_graph((source, target), (assertion,), (support, contradiction))

    exports = graph.exports()
    assert exports == graph.exports()

    json_ld = json.loads(exports.json_ld)
    assertion_record = next(
        item for item in json_ld["@graph"] if item["@id"] == f"urn:uuid:{assertion.id}"
    )
    assert assertion_record["subject"]["@id"] == f"urn:uuid:{source.id}"
    assert assertion_record["object"]["@id"] == f"urn:uuid:{target.id}"
    assert assertion_record["supportingEvidence"] == [{"@id": f"urn:uuid:{support.id}"}]
    assert assertion_record["contradictoryEvidence"] == [{"@id": f"urn:uuid:{contradiction.id}"}]

    nodes = list(csv.DictReader(io.StringIO(exports.nodes_csv)))
    edges = list(csv.DictReader(io.StringIO(exports.edges_csv)))
    assert {row["id"] for row in nodes} == {str(source.id), str(target.id)}
    assert edges[0]["assertion_id"] == str(assertion.id)
    assert edges[0]["supporting_evidence_ids"] == str(support.id)
    assert edges[0]["contradictory_evidence_ids"] == str(contradiction.id)

    graphml = nx.parse_graphml(exports.graphml)
    assert set(graphml.nodes) == {str(source.id), str(target.id)}
    graphml_edge = next(iter(graphml.edges(data=True)))[2]
    assert graphml_edge["assertion_id"] == str(assertion.id)
    assert graphml_edge["supporting_evidence"] == str(support.id)


def test_path_search_is_directional_and_cycles_do_not_repeat_entities() -> None:
    first = make_entity(1, "First")
    second = make_entity(2, "Second")
    third = make_entity(3, "Third")
    evidence = make_evidence(1)
    forward = make_assertion(1, first.id, second.id, supporting=(evidence.id,))
    onward = make_assertion(2, second.id, third.id, supporting=(evidence.id,))
    acyclic = knowledge_graph((first, second, third), (forward, onward), (evidence,))

    paths = acyclic.search_paths(first.id, third.id)
    assert tuple(path.entity_ids for path in paths) == ((first.id, second.id, third.id),)
    assert acyclic.search_paths(third.id, first.id) == ()

    cycle = make_assertion(3, third.id, first.id, supporting=(evidence.id,))
    cyclic = knowledge_graph(
        (first, second, third),
        (forward, onward, cycle),
        (evidence,),
    )
    cyclic_paths = cyclic.search_paths(first.id, third.id, max_length=3)
    assert cyclic_paths
    assert all(len(path.entity_ids) == len(set(path.entity_ids)) for path in cyclic_paths)
    assert all(len(path.assertion_ids) <= 3 for path in cyclic_paths)


def test_path_ranking_is_score_driven_and_deterministic_across_input_order() -> None:
    source = make_entity(1, "Trigger")
    high_mediator = make_entity(2, "High-evidence mediator")
    low_mediator = make_entity(3, "Low-evidence mediator")
    outcome = make_entity(4, "Outcome")
    high_evidence = make_evidence(1, species="human", grade=EvidenceGrade.A)
    low_evidence = make_evidence(2, species="mouse", grade=EvidenceGrade.E)
    high_edges = (
        make_assertion(1, source.id, high_mediator.id, supporting=(high_evidence.id,)),
        make_assertion(2, high_mediator.id, outcome.id, supporting=(high_evidence.id,)),
    )
    low_edges = (
        make_assertion(
            3,
            source.id,
            low_mediator.id,
            supporting=(low_evidence.id,),
            grade=EvidenceGrade.E,
            causal_status=CausalStatus.COMPUTATIONAL_PREDICTION,
            species="mouse",
        ),
        make_assertion(
            4,
            low_mediator.id,
            outcome.id,
            supporting=(low_evidence.id,),
            grade=EvidenceGrade.E,
            causal_status=CausalStatus.HYPOTHESIS_ONLY,
            species="mouse",
        ),
    )
    entities = (source, high_mediator, low_mediator, outcome)
    evidence = (high_evidence, low_evidence)

    first_graph = knowledge_graph(entities, (*low_edges, *high_edges), evidence)
    reversed_graph = knowledge_graph(
        reversed(entities),
        reversed((*low_edges, *high_edges)),
        reversed(evidence),
    )
    first_result = first_graph.search_paths(source.id, outcome.id)
    second_result = reversed_graph.search_paths(source.id, outcome.id)

    assert len(first_result) == 2
    assert first_result[0].entity_ids == (source.id, high_mediator.id, outcome.id)
    assert first_result[0].score is not None
    assert first_result[1].score is not None
    assert first_result[0].score.display_index > first_result[1].score.display_index
    assert tuple(path.assertion_ids for path in first_result) == tuple(
        path.assertion_ids for path in second_result
    )
    assert tuple(path.id for path in first_result) == tuple(path.id for path in second_result)


def test_path_search_validates_endpoints_and_limits() -> None:
    source = make_entity(1, "Source")
    graph = knowledge_graph((source,), (), ())

    with pytest.raises(KeyError, match="endpoints"):
        graph.search_paths(source.id, uid(999))
    with pytest.raises(ValueError, match="between 1 and 10"):
        graph.search_paths(source.id, source.id, max_length=11)
