"""Graph integrity tests for duplicate, directional, provenance and freshness failures."""

from __future__ import annotations

from datetime import date

import pytest
from causalbio.domain.enums import CurationStatus
from causalbio.domain.models import MechanismPath
from causalbio.graph.repository import GraphValidationError, LocalKnowledgeGraph
from factories import make_assertion, make_entity, make_evidence, uid


@pytest.mark.parametrize("collection", ["entities", "assertions", "evidence"])
def test_duplicate_ids_reject_before_dictionary_overwrite(collection: str) -> None:
    left, right = make_entity(1, "Left"), make_entity(2, "Right")
    record = make_evidence(1)
    edge = make_assertion(1, left.id, right.id, supporting=(record.id,))
    with pytest.raises(GraphValidationError, match=r"Duplicate .* identifier"):
        LocalKnowledgeGraph(
            (left, right, left) if collection == "entities" else (left, right),
            (edge, edge) if collection == "assertions" else (edge,),
            (record, record) if collection == "evidence" else (record,),
            graph_id=uid(100),
            version="fixture",
        )


def test_duplicate_contextual_assertions_are_rejected_but_opposite_polarity_is_retained() -> None:
    left, right = make_entity(1, "Left"), make_entity(2, "Right")
    record = make_evidence(1)
    edge = make_assertion(1, left.id, right.id, supporting=(record.id,))
    duplicate = edge.model_copy(update={"id": uid(2)})
    with pytest.raises(GraphValidationError, match="Duplicate contextual assertion"):
        LocalKnowledgeGraph(
            (left, right), (edge, duplicate), (record,), graph_id=uid(100), version="fixture"
        )
    opposite = duplicate.model_copy(update={"polarity": -1})
    graph = LocalKnowledgeGraph(
        (left, right), (edge, opposite), (record,), graph_id=uid(100), version="fixture"
    )
    assert len(graph.projection().assertions) == 2


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"source": " "}, "provenance"),
        ({"curator": ""}, "provenance"),
        ({"direction": "undirected"}, "direction"),
        ({"supporting_evidence_ids": ()}, "missing evidence"),
    ],
)
def test_modified_assertions_cannot_bypass_provenance_checks(
    changes: dict[str, object], message: str
) -> None:
    left, right = make_entity(1, "Left"), make_entity(2, "Right")
    record = make_evidence(1)
    edge = make_assertion(1, left.id, right.id, supporting=(record.id,)).model_copy(update=changes)
    with pytest.raises(GraphValidationError, match=message):
        LocalKnowledgeGraph((left, right), (edge,), (record,), graph_id=uid(100), version="fixture")


def test_untrusted_entities_cannot_enter_trusted_assertions() -> None:
    left = make_entity(1, "Left", curation_status=CurationStatus.SUGGESTED)
    right, record = make_entity(2, "Right"), make_evidence(1)
    edge = make_assertion(1, left.id, right.id, supporting=(record.id,))
    with pytest.raises(GraphValidationError, match="untrusted entity"):
        LocalKnowledgeGraph((left, right), (edge,), (record,), graph_id=uid(100), version="fixture")


def test_path_direction_unknown_references_cycles_and_stale_evidence() -> None:
    left, right = make_entity(1, "Left"), make_entity(2, "Right")
    record = make_evidence(1)
    forward = make_assertion(1, left.id, right.id, supporting=(record.id,))
    reverse = make_assertion(2, right.id, left.id, supporting=(record.id,))
    graph = LocalKnowledgeGraph(
        (left, right), (forward, reverse), (record,), graph_id=uid(100), version="fixture"
    )
    path = MechanismPath(id=uid(101), entity_ids=(left.id, right.id), assertion_ids=(forward.id,))
    graph.validate_path(path)
    with pytest.raises(GraphValidationError, match="direction"):
        graph.validate_path(path.model_copy(update={"assertion_ids": (reverse.id,)}))
    with pytest.raises(GraphValidationError, match="unknown"):
        graph.validate_path(path.model_copy(update={"assertion_ids": (uid(999),)}))
    with pytest.raises(GraphValidationError, match="cycle"):
        graph.validate_path(
            MechanismPath(
                id=uid(102),
                entity_ids=(left.id, right.id, left.id),
                assertion_ids=(forward.id, reverse.id),
            )
        )
    summary = graph.integrity_summary(as_of=date(2026, 1, 2))
    assert summary["feedback_components"] == 1
    assert summary["stale_evidence_ids"] == [str(record.id)]
    assert "not a retraction" in str(summary["freshness_note"])


def test_canonical_name_normalization_and_distinct_contexts() -> None:
    left, right = make_entity(1, "Left entity"), make_entity(2, "Right")
    duplicate = make_entity(3, "  LEFT   entity ")
    with pytest.raises(GraphValidationError, match="Duplicate canonical entity"):
        LocalKnowledgeGraph((left, duplicate), (), (), graph_id=uid(100), version="fixture")
    record = make_evidence(1)
    human = make_assertion(1, left.id, right.id, supporting=(record.id,), species="human")
    mouse = make_assertion(2, left.id, right.id, supporting=(record.id,), species="mouse")
    graph = LocalKnowledgeGraph(
        (left, right), (human, mouse), (record,), graph_id=uid(100), version="fixture"
    )
    assert graph.projection(organism="human").assertions == (human,)
    assert graph.projection(organism="mouse").assertions == (mouse,)


def test_path_search_ties_and_limit_are_stable_across_insertion_order() -> None:
    source, first, second, outcome = (
        make_entity(index, name)
        for index, name in enumerate(("Source", "First", "Second", "Outcome"), start=1)
    )
    record = make_evidence(1)
    edges = (
        make_assertion(1, source.id, first.id, supporting=(record.id,)),
        make_assertion(2, first.id, outcome.id, supporting=(record.id,)),
        make_assertion(3, source.id, second.id, supporting=(record.id,)),
        make_assertion(4, second.id, outcome.id, supporting=(record.id,)),
    )
    graph = LocalKnowledgeGraph(
        (source, first, second, outcome), edges, (record,), graph_id=uid(100), version="fixture"
    )
    reversed_graph = LocalKnowledgeGraph(
        (outcome, second, first, source),
        reversed(edges),
        (record,),
        graph_id=uid(100),
        version="fixture",
    )
    assert graph.search_paths(source.id, outcome.id, limit=1) == reversed_graph.search_paths(
        source.id, outcome.id, limit=1
    )
    with pytest.raises(ValueError, match="limit must be between"):
        graph.search_paths(source.id, outcome.id, limit=0)
