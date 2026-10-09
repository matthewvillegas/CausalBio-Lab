"""Focused tests for transactional SQLite domain-pack snapshots."""

from __future__ import annotations

from pathlib import Path

import pytest
from causalbio import __version__
from causalbio.demo.registry import domain_pack_slugs, load_domain_pack
from causalbio.evidence.scoring import PathScorer
from causalbio.storage import SNAPSHOT_SCHEMA_VERSION, SnapshotCounts, SQLiteSnapshotStore
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError


def expected_counts(slug: str) -> SnapshotCounts:
    pack = load_domain_pack(slug)
    return SnapshotCounts(
        entities=len(pack.entities),
        evidence=len(pack.evidence),
        assertions=len(pack.assertions),
        hypotheses=len(pack.hypotheses),
        interventions=len(pack.interventions),
        petri_models=1,
    )


def test_schema_and_summaries_cover_both_registry_packs(tmp_path: Path) -> None:
    store = SQLiteSnapshotStore(tmp_path / "causalbio.sqlite3")
    try:
        summaries = store.replace_packs(load_domain_pack(slug) for slug in domain_pack_slugs())

        assert {summary.slug for summary in summaries} == set(domain_pack_slugs())
        assert set(inspect(store.engine).get_table_names()) == {
            "assertions",
            "entities",
            "evidence",
            "interventions",
            "pack_metadata",
            "petri_models",
        }
        for summary in summaries:
            pack = load_domain_pack(summary.slug)
            assert summary.counts == expected_counts(summary.slug)
            assert summary.provenance.pack_version == pack.version
            assert summary.provenance.graph_version == pack.version
            assert summary.provenance.schema_version == SNAPSHOT_SCHEMA_VERSION
            assert summary.provenance.software_version == __version__
            assert summary.provenance.evidence_rubric_version == PathScorer.rubric_version
            assert pack.petri_model is not None
            assert summary.provenance.petri_model_version == pack.petri_model.model_version
            assert len(summary.provenance.content_sha256) == 64
    finally:
        store.dispose()


@pytest.mark.parametrize("slug", domain_pack_slugs())
def test_replace_is_idempotent_and_json_round_trips(slug: str, tmp_path: Path) -> None:
    pack = load_domain_pack(slug)
    store = SQLiteSnapshotStore(tmp_path / "causalbio.sqlite3")
    try:
        first = store.replace_pack(pack)
        second = store.replace_pack(pack)

        assert first == second
        assert second.counts == expected_counts(slug)
        assert store.list_packs() == (second,)
        assert store.load_pack(slug) == pack
    finally:
        store.dispose()


def test_failed_replacement_rolls_back_the_existing_pack(tmp_path: Path) -> None:
    pack = load_domain_pack("memory")
    store = SQLiteSnapshotStore(tmp_path / "causalbio.sqlite3")
    try:
        original = store.replace_pack(pack)
        duplicate_entity_pack = pack.model_copy(
            update={"entities": (*pack.entities, pack.entities[0])}
        )

        with pytest.raises(IntegrityError):
            store.replace_pack(duplicate_entity_pack)

        assert store.summary(pack.slug) == original
        assert store.load_pack(pack.slug) == pack
    finally:
        store.dispose()


def test_empty_optional_collection_does_not_emit_a_default_insert(tmp_path: Path) -> None:
    pack = load_domain_pack("memory").model_copy(update={"interventions": ()})
    store = SQLiteSnapshotStore(tmp_path / "causalbio.sqlite3")
    try:
        summary = store.replace_pack(pack)

        assert summary.counts.interventions == 0
        assert store.load_pack(pack.slug).interventions == ()
    finally:
        store.dispose()


def test_unknown_pack_read_has_clear_error(tmp_path: Path) -> None:
    store = SQLiteSnapshotStore(tmp_path / "causalbio.sqlite3")
    try:
        with pytest.raises(KeyError, match="Unknown SQLite domain pack"):
            store.load_pack("not-present")
    finally:
        store.dispose()


def test_pack_without_model_round_trips(tmp_path: Path) -> None:
    pack = load_domain_pack("memory").model_copy(update={"petri_model": None})
    store = SQLiteSnapshotStore(tmp_path / "no-model.sqlite3")
    try:
        summaries = store.replace_packs([pack])
        assert summaries[0].counts.petri_models == 0
        assert store.load_pack(pack.slug).petri_model is None
    finally:
        store.dispose()
