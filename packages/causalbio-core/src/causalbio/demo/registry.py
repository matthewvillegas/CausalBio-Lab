"""Load reviewable JSON demo packs into the typed scientific domain."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from causalbio.demo.metadata import PackMetadata, question_from_metadata
from causalbio.domain.identifiers import stable_uuid
from causalbio.domain.models import (
    BiologicalEntity,
    CausalAssertion,
    DomainPack,
    EntityIdentifier,
    EvidenceRecord,
    ExperimentalContext,
    Intervention,
    MechanismPath,
    MechanisticHypothesis,
    PetriArc,
    PetriModel,
    PetriPlace,
    PetriTransition,
    Study,
    StudyPopulation,
)


def _workspace_root() -> Path:
    configured = os.getenv("CAUSALBIO_WORKSPACE_ROOT")
    if configured:
        return Path(configured).resolve()
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError("Could not locate the CausalBio Lab workspace root")


class DomainPackRegistry:
    """Discover immediate pack directories without importing scientific domain logic."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or _workspace_root() / "data" / "demo").resolve()

    def _path(self, slug: str) -> Path:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise KeyError(f"Invalid domain pack slug: {slug}")
        path = (self.root / slug / "pack.json").resolve()
        if path.parent.parent != self.root or not path.is_file():
            raise KeyError(f"Unknown domain pack: {slug}")
        return path

    def metadata(self, slug: str) -> PackMetadata:
        return PackMetadata.model_validate(self._read(slug).get("metadata"))

    def _read(self, slug: str) -> dict[str, Any]:
        raw = json.loads(self._path(slug).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"Pack {slug}: the document must be a JSON object")
        return cast(dict[str, Any], raw)

    def slugs(self) -> tuple[str, ...]:
        discovered = [path.parent.name for path in self.root.glob("*/pack.json")]
        return tuple(sorted(discovered, key=lambda slug: (self.metadata(slug).display_order, slug)))

    def load(self, slug: str) -> DomainPack:
        raw = self._read(slug)
        try:
            return _load_pack(slug, raw)
        except KeyError as exc:
            raise ValueError(
                f"Pack {slug}: missing required field or unknown reference {exc}"
            ) from exc


def domain_pack_slugs() -> tuple[str, ...]:
    return DomainPackRegistry().slugs()


def available_domain_packs() -> tuple[dict[str, Any], ...]:
    """Return lightweight metadata without constructing scientific models."""

    result: list[dict[str, Any]] = []
    registry = DomainPackRegistry()
    for slug in registry.slugs():
        metadata = registry.metadata(slug)
        result.append(
            {
                "slug": slug,
                "title": metadata.title,
                "description": metadata.description,
                "version": metadata.version,
                "example_questions": metadata.example_questions,
                "educational_notice": metadata.educational_notice,
            }
        )
    return tuple(result)


def load_domain_pack(slug: str) -> DomainPack:
    """Validate and return one curated offline domain pack."""

    return DomainPackRegistry().load(slug)


def _load_pack(slug: str, raw: dict[str, Any]) -> DomainPack:
    from causalbio.demo.integrity import validate_domain_pack

    manifest = PackMetadata.model_validate(raw["metadata"])
    for collection in ("entities", "evidence", "assertions", "interventions", "hypotheses"):
        items = raw.get(collection)
        if not isinstance(items, list):
            raise ValueError(f"Pack {slug}: {collection} must be an array")
        if any(
            not isinstance(item, dict)
            or not isinstance(item.get("key"), str)
            or not item["key"].strip()
            for item in items
        ):
            raise ValueError(
                f"Pack {slug}: {collection} entries must be objects with nonempty string keys"
            )
        keys = [item["key"] for item in items]
        if len(set(keys)) != len(keys):
            raise ValueError(f"Pack {slug}: duplicate {collection} keys")
    if set(manifest.expected_hypothesis_keys) != {item["key"] for item in raw["hypotheses"]}:
        raise ValueError(f"Pack {slug}: expected hypothesis keys do not match the mechanisms")
    metadata = cast(dict[str, Any], raw["metadata"])
    curated_at = datetime.fromisoformat(cast(str, metadata["curated_at"]))

    entity_ids = {
        cast(str, item["key"]): stable_uuid(f"{slug}:entity", cast(str, item["key"]))
        for item in cast(list[dict[str, Any]], raw["entities"])
    }
    evidence_ids = {
        cast(str, item["key"]): stable_uuid(f"{slug}:evidence", cast(str, item["key"]))
        for item in cast(list[dict[str, Any]], raw["evidence"])
    }
    assertion_ids = {
        cast(str, item["key"]): stable_uuid(f"{slug}:assertion", cast(str, item["key"]))
        for item in cast(list[dict[str, Any]], raw["assertions"])
    }
    intervention_ids = {
        cast(str, item["key"]): stable_uuid(f"{slug}:intervention", cast(str, item["key"]))
        for item in cast(list[dict[str, Any]], raw["interventions"])
    }

    entities = tuple(
        BiologicalEntity(
            id=entity_ids[cast(str, item["key"])],
            preferred_name=cast(str, item["name"]),
            aliases=tuple(cast(list[str], item.get("aliases", []))),
            entity_type=cast(str, item["type"]),
            description=cast(str, item["description"]),
            identifiers=tuple(
                EntityIdentifier(**identifier)
                for identifier in cast(list[dict[str, Any]], item.get("identifiers", []))
            ),
            source=cast(str, item.get("source", "CausalBio Lab curated demo")),
            created_at=curated_at,
            updated_at=curated_at,
            curation_status=cast(str, item.get("curation_status", "VALIDATED")),
        )
        for item in cast(list[dict[str, Any]], raw["entities"])
    )

    evidence = tuple(
        _build_evidence(slug, item, evidence_ids[cast(str, item["key"])])
        for item in cast(list[dict[str, Any]], raw["evidence"])
    )
    assertions = tuple(
        CausalAssertion(
            id=assertion_ids[cast(str, item["key"])],
            subject_id=entity_ids[cast(str, item["subject"])],
            relation=cast(str, item["relation"]),
            object_id=entity_ids[cast(str, item["object"])],
            polarity=cast(Any, item.get("polarity", 1)),
            confidence_classification=cast(str, item["confidence"]),
            causal_status=cast(str, item["causal_status"]),
            biological_context=ExperimentalContext(**cast(dict[str, Any], item["context"])),
            supporting_evidence_ids=tuple(
                evidence_ids[key] for key in cast(list[str], item["evidence"])
            ),
            contradictory_evidence_ids=tuple(
                evidence_ids[key] for key in cast(list[str], item.get("contradictory", []))
            ),
            curator="CausalBio Lab demo curation",
            extraction_method="manual_curation",
            source=cast(str, item.get("source", "Bundled curated domain pack")),
            retrieval_date=cast(str, metadata["retrieved_at"]),
            review_status=cast(str, item.get("review_status", "VALIDATED")),
            interpretation=cast(str, item["interpretation"]),
            limitations=tuple(cast(list[str], item.get("limitations", []))),
        )
        for item in cast(list[dict[str, Any]], raw["assertions"])
    )

    hypotheses = tuple(
        _build_hypothesis(
            slug,
            item,
            entity_ids=entity_ids,
            evidence_ids=evidence_ids,
            assertion_ids=assertion_ids,
            intervention_ids=intervention_ids,
        )
        for item in cast(list[dict[str, Any]], raw["hypotheses"])
    )
    interventions = tuple(
        Intervention(
            id=intervention_ids[cast(str, item["key"])],
            name=cast(str, item["name"]),
            intervention_class=cast(str, item["class"]),
            description=cast(str, item["description"]),
            target_entity_ids=tuple(entity_ids[key] for key in cast(list[str], item["targets"])),
            downstream_assertion_ids=tuple(
                assertion_ids[key] for key in cast(list[str], item.get("assertions", []))
            ),
            evidence_ids=tuple(evidence_ids[key] for key in cast(list[str], item["evidence"])),
            maturity=cast(str, item["maturity"]),
            addresses=cast(Any, item["addresses"]),
            mechanistic_relevance=cast(float, item["mechanistic_relevance"]),
            evidence_strength=cast(float, item["evidence_strength"]),
            directness=cast(float, item["directness"]),
            translational_maturity=cast(float, item["translational_maturity"]),
            uncertainty=tuple(cast(list[str], item["uncertainty"])),
            major_safety_concerns=tuple(cast(list[str], item["major_safety_concerns"])),
            unsupported_assumptions=tuple(cast(list[str], item.get("unsupported_assumptions", []))),
        )
        for item in cast(list[dict[str, Any]], raw["interventions"])
    )
    petri_model = (
        _build_petri_model(slug, cast(dict[str, Any], raw["petri_model"]), evidence_ids)
        if raw.get("petri_model") is not None
        else None
    )
    question = question_from_metadata(slug, manifest, manifest.example_questions[0])
    pack = DomainPack(
        slug=slug,
        title=cast(str, metadata["title"]),
        version=cast(str, metadata["version"]),
        description=cast(str, metadata["description"]),
        educational_notice=cast(str, metadata["educational_notice"]),
        example_questions=tuple(cast(list[str], metadata["example_questions"])),
        question=question,
        entities=entities,
        evidence=evidence,
        assertions=assertions,
        hypotheses=hypotheses,
        interventions=interventions,
        petri_model=petri_model,
    )
    validate_domain_pack(pack)
    return pack


def _build_evidence(slug: str, item: dict[str, Any], evidence_id: Any) -> EvidenceRecord:
    population = StudyPopulation(**cast(dict[str, Any], item["population"]))
    identifiers = tuple(
        EntityIdentifier(**identifier)
        for identifier in cast(list[dict[str, Any]], item["identifiers"])
    )
    study = Study(
        id=stable_uuid(f"{slug}:study", cast(str, item["key"])),
        title=cast(str, item["title"]),
        authors=tuple(cast(list[str], item["authors"])),
        publication_year=cast(int, item["year"]),
        journal=cast(str, item["journal"]),
        identifiers=identifiers,
        study_type=cast(str, item["study_type"]),
        population=population,
        source_url=cast(str, item["source_url"]),
    )
    payload = dict(item)
    for field in (
        "key",
        "title",
        "authors",
        "year",
        "journal",
        "identifiers",
        "study_type",
        "population",
        "source_url",
        "context",
        "grade",
    ):
        payload.pop(field, None)
    return EvidenceRecord(
        id=evidence_id,
        study=study,
        experimental_context=ExperimentalContext(**cast(dict[str, Any], item["context"])),
        evidence_grade=cast(str, item["grade"]),
        **payload,
    )


def _build_hypothesis(
    slug: str,
    item: dict[str, Any],
    *,
    entity_ids: dict[str, Any],
    evidence_ids: dict[str, Any],
    assertion_ids: dict[str, Any],
    intervention_ids: dict[str, Any],
) -> MechanisticHypothesis:
    paths = tuple(
        MechanismPath(
            id=stable_uuid(f"{slug}:path", f"{item['key']}:{index}"),
            entity_ids=tuple(entity_ids[key] for key in cast(list[str], path["entities"])),
            assertion_ids=tuple(assertion_ids[key] for key in cast(list[str], path["assertions"])),
        )
        for index, path in enumerate(cast(list[dict[str, Any]], item["paths"]))
    )
    return MechanisticHypothesis(
        id=stable_uuid(f"{slug}:hypothesis", cast(str, item["key"])),
        title=cast(str, item["title"]),
        plain_language_summary=cast(str, item["summary"]),
        outcome_id=entity_ids[cast(str, item["outcome"])],
        trigger_id=entity_ids[cast(str, item["trigger"])],
        mechanism_paths=paths,
        mediator_ids=tuple(entity_ids[key] for key in cast(list[str], item["mediators"])),
        tissue_ids=tuple(entity_ids[key] for key in cast(list[str], item.get("tissues", []))),
        cell_ids=tuple(entity_ids[key] for key in cast(list[str], item.get("cells", []))),
        pathway_ids=tuple(entity_ids[key] for key in cast(list[str], item.get("pathways", []))),
        evidence_ids=tuple(evidence_ids[key] for key in cast(list[str], item["evidence"])),
        contradictory_evidence_ids=tuple(
            evidence_ids[key] for key in cast(list[str], item.get("contradictory", []))
        ),
        context_requirements=tuple(cast(list[str], item.get("context_requirements", []))),
        missing_links=tuple(cast(list[str], item.get("missing_links", []))),
        uncertainty=tuple(cast(list[str], item["uncertainty"])),
        intervention_ids=tuple(
            intervention_ids[key] for key in cast(list[str], item.get("interventions", []))
        ),
        evidence_label=cast(str, item["evidence_label"]),
    )


def _build_petri_model(slug: str, item: dict[str, Any], evidence_ids: dict[str, Any]) -> PetriModel:
    for collection in ("places", "transitions"):
        keys = [entry["key"] for entry in item[collection]]
        if len(set(keys)) != len(keys):
            raise ValueError(f"Pack {slug}: duplicate model {collection} keys")
    model_id = stable_uuid(f"{slug}:petri-model", cast(str, item["key"]))
    place_ids = {
        cast(str, place["key"]): stable_uuid(f"{slug}:petri-place", cast(str, place["key"]))
        for place in cast(list[dict[str, Any]], item["places"])
    }
    transition_ids = {
        cast(str, transition["key"]): stable_uuid(
            f"{slug}:petri-transition", cast(str, transition["key"])
        )
        for transition in cast(list[dict[str, Any]], item["transitions"])
    }
    places = tuple(
        PetriPlace(
            id=place_ids[cast(str, place["key"])],
            **{key: value for key, value in place.items() if key != "key"},
        )
        for place in cast(list[dict[str, Any]], item["places"])
    )
    transitions = tuple(
        PetriTransition(
            id=transition_ids[cast(str, transition["key"])],
            name=cast(str, transition["name"]),
            biological_event=cast(str, transition["biological_event"]),
            rate_law=cast(str, transition["rate_law"]),
            parameters=cast(dict[str, float], transition["parameters"]),
            evidence_ids=tuple(
                evidence_ids[key] for key in cast(list[str], transition.get("evidence", []))
            ),
            assumptions=tuple(cast(list[str], transition["assumptions"])),
        )
        for transition in cast(list[dict[str, Any]], item["transitions"])
    )
    arcs = tuple(
        PetriArc(
            id=stable_uuid(f"{slug}:petri-arc", f"{item['key']}:{index}"),
            place_id=place_ids[cast(str, arc["place"])],
            transition_id=transition_ids[cast(str, arc["transition"])],
            arc_type=cast(str, arc["type"]),
            weight=cast(float, arc.get("weight", 1.0)),
            threshold=cast(float, arc.get("threshold", 0.0)),
        )
        for index, arc in enumerate(cast(list[dict[str, Any]], item["arcs"]))
    )
    return PetriModel(
        id=model_id,
        slug=cast(str, item["key"]),
        name=cast(str, item["name"]),
        description=cast(str, item["description"]),
        model_version=cast(str, item["model_version"]),
        places=places,
        transitions=transitions,
        arcs=arcs,
        scenarios=tuple(item.get("scenarios", [])),
        output_place_id=place_ids[cast(str, item["output_place"])]
        if item.get("output_place")
        else None,
        assumptions=tuple(cast(list[str], item["assumptions"])),
    )
