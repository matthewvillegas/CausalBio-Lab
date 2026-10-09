"""NetworkX-backed assertion graph with provenance-preserving exports."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from itertools import pairwise
from typing import Any
from uuid import UUID

import networkx as nx

from causalbio.domain.enums import CurationStatus, EvidenceGrade, RelationType
from causalbio.domain.identifiers import stable_uuid
from causalbio.domain.models import (
    BiologicalEntity,
    CausalAssertion,
    EvidenceRecord,
    GraphProjection,
    MechanismPath,
)
from causalbio.evidence.scoring import PathScorer

TRUSTED_STATES = {CurationStatus.VALIDATED, CurationStatus.CURATED}


class GraphValidationError(ValueError):
    """Raised when graph references or provenance are invalid."""


@dataclass(frozen=True)
class GraphExports:
    json_ld: str
    graphml: str
    nodes_csv: str
    edges_csv: str


class LocalKnowledgeGraph:
    """A validated multigraph where every edge is a typed assertion."""

    def __init__(
        self,
        entities: Iterable[BiologicalEntity],
        assertions: Iterable[CausalAssertion],
        evidence: Iterable[EvidenceRecord],
        *,
        graph_id: UUID,
        version: str,
    ) -> None:
        self.id = graph_id
        self.version = version
        entity_items, assertion_items, evidence_items = (
            tuple(entities),
            tuple(assertions),
            tuple(evidence),
        )
        for label, items in (
            ("entity", entity_items),
            ("assertion", assertion_items),
            ("evidence", evidence_items),
        ):
            identifiers = [item.id for item in items]
            if len(identifiers) != len(set(identifiers)):
                raise GraphValidationError(f"Duplicate {label} identifier")
        self.entities = {entity.id: entity for entity in entity_items}
        self.assertions = {assertion.id: assertion for assertion in assertion_items}
        self.evidence = {record.id: record for record in evidence_items}
        self._validate()
        self._graph: nx.MultiDiGraph = nx.MultiDiGraph(graph_id=str(graph_id), version=version)
        for entity in self.entities.values():
            self._graph.add_node(entity.id, entity=entity)
        for assertion in self.assertions.values():
            self._graph.add_edge(
                assertion.subject_id,
                assertion.object_id,
                key=assertion.id,
                assertion=assertion,
            )

    def _validate(self) -> None:
        duplicate_names: dict[tuple[str, str], UUID] = {}
        for entity in self.entities.values():
            key = (entity.entity_type.value, " ".join(entity.preferred_name.split()).casefold())
            if key in duplicate_names:
                raise GraphValidationError(f"Duplicate canonical entity: {entity.preferred_name}")
            duplicate_names[key] = entity.id

        semantic_keys: set[tuple[object, ...]] = set()
        for assertion in self.assertions.values():
            if assertion.direction != "directed" or assertion.subject_id == assertion.object_id:
                raise GraphValidationError(f"Assertion {assertion.id} has invalid direction")
            if not assertion.curator.strip() or not assertion.source.strip():
                raise GraphValidationError(f"Assertion {assertion.id} has missing provenance")
            semantic_key = (
                assertion.subject_id,
                assertion.relation,
                assertion.object_id,
                assertion.polarity,
                assertion.biological_context.model_dump_json(),
            )
            if semantic_key in semantic_keys:
                raise GraphValidationError("Duplicate contextual assertion; merge its provenance")
            semantic_keys.add(semantic_key)
            if (
                assertion.subject_id not in self.entities
                or assertion.object_id not in self.entities
            ):
                raise GraphValidationError(f"Assertion {assertion.id} references a missing entity")
            missing_evidence = (
                set(assertion.supporting_evidence_ids) | set(assertion.contradictory_evidence_ids)
            ) - self.evidence.keys()
            if missing_evidence:
                raise GraphValidationError(
                    f"Assertion {assertion.id} references missing evidence: {sorted(map(str, missing_evidence))}"
                )
            if assertion.review_status in TRUSTED_STATES:
                if not assertion.supporting_evidence_ids:
                    raise GraphValidationError("Trusted assertion has missing evidence")
                if any(
                    self.entities[entity_id].curation_status not in TRUSTED_STATES
                    for entity_id in (assertion.subject_id, assertion.object_id)
                ):
                    raise GraphValidationError("Trusted assertion references an untrusted entity")
                untrusted = [
                    evidence_id
                    for evidence_id in (
                        *assertion.supporting_evidence_ids,
                        *assertion.contradictory_evidence_ids,
                    )
                    if self.evidence[evidence_id].curation_status not in TRUSTED_STATES
                ]
                if untrusted:
                    raise GraphValidationError(
                        f"Trusted assertion {assertion.id} depends on untrusted evidence"
                    )

    def validate_path(self, path: MechanismPath) -> None:
        """Require a simple, ordered, directed path with graph-local references."""
        if not path.assertion_ids or len(path.entity_ids) != len(path.assertion_ids) + 1:
            raise GraphValidationError("A mechanism path must contain connected assertions")
        if len(set(path.entity_ids)) != len(path.entity_ids):
            raise GraphValidationError("A mechanism path must not repeat entities through a cycle")
        if (
            set(path.entity_ids) - self.entities.keys()
            or set(path.assertion_ids) - self.assertions.keys()
        ):
            raise GraphValidationError("Mechanism path references an unknown entity or assertion")
        if set(path.weak_link_assertion_ids) - set(path.assertion_ids):
            raise GraphValidationError("Weak links must reference assertions on their path")
        for (left, right), assertion_id in zip(
            pairwise(path.entity_ids), path.assertion_ids, strict=True
        ):
            assertion = self.assertions[assertion_id]
            if (assertion.subject_id, assertion.object_id) != (left, right):
                raise GraphValidationError(
                    "Mechanism path assertion direction does not match ordered entities"
                )

    def integrity_summary(
        self, *, as_of: date | None = None, stale_after_days: int = 365
    ) -> dict[str, object]:
        """Report cycles and stale sources without treating feedback or age as falsity."""
        today = as_of or datetime.now(UTC).date()
        cycles = [
            component
            for component in nx.strongly_connected_components(self._graph)
            if len(component) > 1
        ]
        stale = [
            str(record.id)
            for record in self.evidence.values()
            if (today - record.retrieved_at).days > stale_after_days
        ]
        return {
            "entities": len(self.entities),
            "assertions": len(self.assertions),
            "evidence": len(self.evidence),
            "feedback_components": len(cycles),
            "assertions_with_counterevidence": sum(
                bool(item.contradictory_evidence_ids) for item in self.assertions.values()
            ),
            "stale_evidence_ids": stale,
            "freshness_note": "Retrieval age only; not a retraction, completeness, or scientific-validity assessment.",
        }

    def entity(self, entity_id: UUID) -> BiologicalEntity:
        try:
            return self.entities[entity_id]
        except KeyError as exc:
            raise KeyError(f"Unknown biological entity: {entity_id}") from exc

    def assertion(self, assertion_id: UUID) -> CausalAssertion:
        try:
            return self.assertions[assertion_id]
        except KeyError as exc:
            raise KeyError(f"Unknown causal assertion: {assertion_id}") from exc

    def projection(
        self,
        *,
        trusted_only: bool = True,
        relations: set[RelationType] | None = None,
        grades: set[EvidenceGrade] | None = None,
        organism: str | None = None,
        tissue: str | None = None,
    ) -> GraphProjection:
        selected: list[CausalAssertion] = []
        filters: list[str] = []
        if trusted_only:
            filters.append("trusted assertions only")
        if relations:
            filters.append("relations=" + ",".join(sorted(value.value for value in relations)))
        if grades:
            filters.append("grades=" + ",".join(sorted(value.value for value in grades)))
        if organism:
            filters.append(f"organism={organism}")
        if tissue:
            filters.append(f"tissue={tissue}")

        for assertion in self.assertions.values():
            if trusted_only and assertion.review_status not in TRUSTED_STATES:
                continue
            if relations and assertion.relation not in relations:
                continue
            if grades and assertion.confidence_classification not in grades:
                continue
            if (
                organism
                and organism.casefold() not in assertion.biological_context.species.casefold()
            ):
                continue
            if (
                tissue
                and tissue.casefold() not in (assertion.biological_context.tissue or "").casefold()
            ):
                continue
            selected.append(assertion)

        entity_ids = {item.subject_id for item in selected} | {item.object_id for item in selected}
        evidence_ids = {
            evidence_id
            for assertion in selected
            for evidence_id in (
                *assertion.supporting_evidence_ids,
                *assertion.contradictory_evidence_ids,
            )
        }
        return GraphProjection(
            graph_id=self.id,
            entities=tuple(self.entities[item] for item in self.entities if item in entity_ids),
            assertions=tuple(selected),
            evidence=tuple(self.evidence[item] for item in self.evidence if item in evidence_ids),
            filters_applied=tuple(filters),
        )

    def search_paths(
        self,
        source_id: UUID,
        target_id: UUID,
        *,
        max_length: int = 6,
        relations: set[RelationType] | None = None,
        trusted_only: bool = True,
        limit: int = 10,
        requested_context: str | None = None,
    ) -> tuple[MechanismPath, ...]:
        if source_id not in self.entities or target_id not in self.entities:
            raise KeyError("Path endpoints must be present in the graph")
        if max_length < 1 or max_length > 10:
            raise ValueError("max_length must be between 1 and 10")
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")

        candidate_edges: dict[tuple[UUID, UUID], list[CausalAssertion]] = {}
        graph = nx.DiGraph()
        for assertion in sorted(self.assertions.values(), key=lambda item: str(item.id)):
            if trusted_only and assertion.review_status not in TRUSTED_STATES:
                continue
            if relations and assertion.relation not in relations:
                continue
            graph.add_edge(assertion.subject_id, assertion.object_id)
            candidate_edges.setdefault((assertion.subject_id, assertion.object_id), []).append(
                assertion
            )

        if source_id not in graph or target_id not in graph:
            return ()

        scorer = PathScorer(self.evidence.values())
        results: list[MechanismPath] = []
        try:
            node_paths = nx.all_simple_paths(graph, source_id, target_id, cutoff=max_length)
            for node_path in node_paths:
                chosen: list[CausalAssertion] = []
                for left, right in pairwise(node_path):
                    options = candidate_edges[(left, right)]
                    options.sort(
                        key=lambda item: (
                            scorer.edge_support(
                                scorer.components_for(item, requested_context=requested_context)
                            ),
                            str(item.id),
                        ),
                        reverse=True,
                    )
                    chosen.append(options[0])
                score = scorer.score(chosen, requested_context=requested_context)
                weak = tuple(
                    assertion.id
                    for assertion, components in zip(chosen, score.edge_components, strict=True)
                    if scorer.edge_support(components) < 0.5
                )
                results.append(
                    MechanismPath(
                        id=stable_uuid("path", ":".join(str(item.id) for item in chosen)),
                        entity_ids=tuple(node_path),
                        assertion_ids=tuple(item.id for item in chosen),
                        score=score,
                        weak_link_assertion_ids=weak,
                    )
                )
                if len(results) >= limit * 4:
                    break
        except nx.NetworkXNoPath:
            return ()
        results.sort(
            key=lambda item: (item.score.display_index if item.score else 0, str(item.id)),
            reverse=True,
        )
        return tuple(results[:limit])

    def exports(self, *, trusted_only: bool = True) -> GraphExports:
        projection = self.projection(trusted_only=trusted_only)
        return GraphExports(
            json_ld=json.dumps(self._json_ld(projection), indent=2, ensure_ascii=False),
            graphml=self._graphml(projection),
            nodes_csv=self._nodes_csv(projection),
            edges_csv=self._edges_csv(projection),
        )

    @staticmethod
    def _json_ld(projection: GraphProjection) -> dict[str, Any]:
        graph: list[dict[str, Any]] = []
        for entity in projection.entities:
            graph.append(
                {
                    "@id": f"urn:uuid:{entity.id}",
                    "@type": f"causalbio:{entity.entity_type.value}",
                    "name": entity.preferred_name,
                    "description": entity.description,
                    "curationStatus": entity.curation_status.value,
                }
            )
        for assertion in projection.assertions:
            graph.append(
                {
                    "@id": f"urn:uuid:{assertion.id}",
                    "@type": "causalbio:CausalAssertion",
                    "subject": {"@id": f"urn:uuid:{assertion.subject_id}"},
                    "relation": assertion.relation.value,
                    "object": {"@id": f"urn:uuid:{assertion.object_id}"},
                    "causalStatus": assertion.causal_status.value,
                    "evidenceGrade": assertion.confidence_classification.value,
                    "supportingEvidence": [
                        {"@id": f"urn:uuid:{item}"} for item in assertion.supporting_evidence_ids
                    ],
                    "contradictoryEvidence": [
                        {"@id": f"urn:uuid:{item}"} for item in assertion.contradictory_evidence_ids
                    ],
                }
            )
        return {
            "@context": {
                "causalbio": "https://causalbio.example/schema/",
                "name": "https://schema.org/name",
                "description": "https://schema.org/description",
            },
            "@graph": graph,
        }

    @staticmethod
    def _graphml(projection: GraphProjection) -> str:
        graph = nx.MultiDiGraph()
        for entity in projection.entities:
            graph.add_node(
                str(entity.id),
                label=entity.preferred_name,
                entity_type=entity.entity_type.value,
                description=entity.description,
            )
        for assertion in projection.assertions:
            graph.add_edge(
                str(assertion.subject_id),
                str(assertion.object_id),
                key=str(assertion.id),
                assertion_id=str(assertion.id),
                relation=assertion.relation.value,
                causal_status=assertion.causal_status.value,
                evidence_grade=assertion.confidence_classification.value,
                supporting_evidence="|".join(map(str, assertion.supporting_evidence_ids)),
                contradictory_evidence="|".join(map(str, assertion.contradictory_evidence_ids)),
            )
        return "\n".join(nx.generate_graphml(graph, named_key_ids=True))

    @staticmethod
    def _nodes_csv(projection: GraphProjection) -> str:
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(("id", "preferred_name", "entity_type", "description", "curation_status"))
        for entity in projection.entities:
            writer.writerow(
                (
                    entity.id,
                    entity.preferred_name,
                    entity.entity_type.value,
                    entity.description,
                    entity.curation_status.value,
                )
            )
        return stream.getvalue()

    @staticmethod
    def _edges_csv(projection: GraphProjection) -> str:
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(
            (
                "assertion_id",
                "subject_id",
                "relation",
                "object_id",
                "causal_status",
                "evidence_grade",
                "supporting_evidence_ids",
                "contradictory_evidence_ids",
            )
        )
        for assertion in projection.assertions:
            writer.writerow(
                (
                    assertion.id,
                    assertion.subject_id,
                    assertion.relation.value,
                    assertion.object_id,
                    assertion.causal_status.value,
                    assertion.confidence_classification.value,
                    "|".join(map(str, assertion.supporting_evidence_ids)),
                    "|".join(map(str, assertion.contradictory_evidence_ids)),
                )
            )
        return stream.getvalue()
