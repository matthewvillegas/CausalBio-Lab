"""SQLAlchemy-backed materialized snapshots of curated domain packs.

The reviewable JSON fixtures remain canonical. This adapter validates a complete
``DomainPack`` before replacing the corresponding SQLite rows in one transaction.
It intentionally stores JSON payloads alongside a few indexed provenance columns:
the payloads retain the complete typed scientific record, while the columns make
the generated database straightforward to inspect.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Final, cast

from sqlalchemy import (
    JSON,
    URL,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    delete,
    event,
    insert,
    select,
)
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql.schema import MetaData

from causalbio import __version__
from causalbio.domain.models import DomainPack
from causalbio.evidence.scoring import PathScorer

DEFAULT_DATABASE_PATH: Final = Path("data") / "causalbio.sqlite3"
SNAPSHOT_SCHEMA_VERSION: Final = "causalbio-sqlite-snapshot-1.0"


class SnapshotBase(DeclarativeBase):
    """Declarative base with deterministic table naming exposed for inspection."""


class PackMetadataRow(SnapshotBase):
    __tablename__ = "pack_metadata"

    slug: Mapped[str] = mapped_column(String(120), primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    pack_version: Mapped[str] = mapped_column(String(120), nullable=False)
    graph_version: Mapped[str] = mapped_column(String(120), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(120), nullable=False)
    software_version: Mapped[str] = mapped_column(String(120), nullable=False)
    evidence_rubric_version: Mapped[str] = mapped_column(String(160), nullable=False)
    petri_model_version: Mapped[str] = mapped_column(String(120), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    seeded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retrieval_dates: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    entity_count: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    assertion_count: Mapped[int] = mapped_column(Integer, nullable=False)
    hypothesis_count: Mapped[int] = mapped_column(Integer, nullable=False)
    intervention_count: Mapped[int] = mapped_column(Integer, nullable=False)
    petri_model_count: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class EntityRow(SnapshotBase):
    __tablename__ = "entities"

    pack_slug: Mapped[str] = mapped_column(
        String(120), ForeignKey("pack_metadata.slug", ondelete="CASCADE"), primary_key=True
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    preferred_name: Mapped[str] = mapped_column(String(300), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class EvidenceRow(SnapshotBase):
    __tablename__ = "evidence"

    pack_slug: Mapped[str] = mapped_column(
        String(120), ForeignKey("pack_metadata.slug", ondelete="CASCADE"), primary_key=True
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    study_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    publication_year: Mapped[int] = mapped_column(Integer, nullable=False)
    source_adapter: Mapped[str] = mapped_column(String(160), nullable=False)
    evidence_grade: Mapped[str] = mapped_column(String(20), nullable=False)
    retrieved_at: Mapped[date] = mapped_column(Date, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class AssertionRow(SnapshotBase):
    __tablename__ = "assertions"

    pack_slug: Mapped[str] = mapped_column(
        String(120), ForeignKey("pack_metadata.slug", ondelete="CASCADE"), primary_key=True
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False)
    relation: Mapped[str] = mapped_column(String(80), nullable=False)
    object_id: Mapped[str] = mapped_column(String(36), nullable=False)
    causal_status: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class InterventionRow(SnapshotBase):
    __tablename__ = "interventions"

    pack_slug: Mapped[str] = mapped_column(
        String(120), ForeignKey("pack_metadata.slug", ondelete="CASCADE"), primary_key=True
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    intervention_class: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class PetriModelRow(SnapshotBase):
    __tablename__ = "petri_models"

    pack_slug: Mapped[str] = mapped_column(
        String(120), ForeignKey("pack_metadata.slug", ondelete="CASCADE"), primary_key=True
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), nullable=False)
    model_version: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


@dataclass(frozen=True, slots=True)
class SnapshotCounts:
    """Stable record counts for one materialized domain pack."""

    entities: int
    evidence: int
    assertions: int
    hypotheses: int
    interventions: int
    petri_models: int

    @property
    def stored_records(self) -> int:
        """Return the number of rows excluding the single metadata row."""

        return (
            self.entities + self.evidence + self.assertions + self.interventions + self.petri_models
        )


@dataclass(frozen=True, slots=True)
class SnapshotProvenance:
    """Versions and digest needed to identify an exact generated snapshot."""

    pack_version: str
    graph_version: str
    schema_version: str
    software_version: str
    evidence_rubric_version: str
    petri_model_version: str
    content_sha256: str


@dataclass(frozen=True, slots=True)
class PackSnapshotSummary:
    """Human-readable result returned after materialization or inspection."""

    slug: str
    title: str
    counts: SnapshotCounts
    provenance: SnapshotProvenance


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _: Any) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def _enum_value(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw)


def _json_payload(value: Any) -> dict[str, Any]:
    return cast(dict[str, Any], value.model_dump(mode="json"))


def _content_digest(pack: DomainPack) -> str:
    canonical = json.dumps(
        pack.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class SQLiteSnapshotStore:
    """Materialize and validate versioned ``DomainPack`` snapshots in SQLite."""

    def __init__(
        self,
        database_path: str | Path = DEFAULT_DATABASE_PATH,
        *,
        software_version: str = __version__,
        evidence_rubric_version: str = PathScorer.rubric_version,
        create_schema: bool = True,
    ) -> None:
        path = Path(database_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._database_path = path
        self._software_version = software_version
        self._evidence_rubric_version = evidence_rubric_version
        url = URL.create("sqlite+pysqlite", database=str(path))
        self._engine = create_engine(url)
        event.listen(self._engine, "connect", _enable_sqlite_foreign_keys)
        if create_schema:
            self.create_schema()

    @property
    def database_path(self) -> Path:
        return self._database_path

    @property
    def engine(self) -> Engine:
        """Expose the engine for read-only inspection and application composition."""

        return self._engine

    @property
    def metadata(self) -> MetaData:
        return SnapshotBase.metadata

    def create_schema(self) -> None:
        """Create missing snapshot tables without modifying existing rows."""

        SnapshotBase.metadata.create_all(self._engine)

    def dispose(self) -> None:
        """Release pooled database connections."""

        self._engine.dispose()

    def replace_pack(self, pack: DomainPack) -> PackSnapshotSummary:
        """Atomically replace all rows belonging to one validated pack."""

        validated = DomainPack.model_validate(pack.model_dump(mode="json"))
        with self._engine.begin() as connection:
            self._delete_pack(connection, validated.slug)
            self._insert_pack(connection, validated)
        return self.summary(validated.slug)

    def replace_packs(self, packs: Iterable[DomainPack]) -> tuple[PackSnapshotSummary, ...]:
        """Replace each supplied pack independently and return stable summaries."""

        return tuple(self.replace_pack(pack) for pack in packs)

    def list_packs(self) -> tuple[PackSnapshotSummary, ...]:
        """List materialized packs in deterministic slug order."""

        with self._engine.connect() as connection:
            rows = connection.execute(
                select(
                    PackMetadataRow.slug,
                    PackMetadataRow.title,
                    PackMetadataRow.pack_version,
                    PackMetadataRow.graph_version,
                    PackMetadataRow.schema_version,
                    PackMetadataRow.software_version,
                    PackMetadataRow.evidence_rubric_version,
                    PackMetadataRow.petri_model_version,
                    PackMetadataRow.content_sha256,
                    PackMetadataRow.entity_count,
                    PackMetadataRow.evidence_count,
                    PackMetadataRow.assertion_count,
                    PackMetadataRow.hypothesis_count,
                    PackMetadataRow.intervention_count,
                    PackMetadataRow.petri_model_count,
                ).order_by(PackMetadataRow.slug)
            ).mappings()
            return tuple(self._summary_from_mapping(dict(row)) for row in rows)

    def summary(self, slug: str) -> PackSnapshotSummary:
        """Return counts and provenance for one materialized pack."""

        summaries = {summary.slug: summary for summary in self.list_packs()}
        try:
            return summaries[slug]
        except KeyError as error:
            raise KeyError(f"Unknown SQLite domain pack: {slug}") from error

    def load_pack(self, slug: str) -> DomainPack:
        """Revalidate and reconstruct a complete pack from stored JSON payloads."""

        with self._engine.connect() as connection:
            metadata_payload = connection.execute(
                select(PackMetadataRow.payload).where(PackMetadataRow.slug == slug)
            ).scalar_one_or_none()
            if metadata_payload is None:
                raise KeyError(f"Unknown SQLite domain pack: {slug}")

            entity_payloads = list(
                connection.execute(
                    select(EntityRow.payload)
                    .where(EntityRow.pack_slug == slug)
                    .order_by(EntityRow.ordinal)
                ).scalars()
            )
            evidence_payloads = list(
                connection.execute(
                    select(EvidenceRow.payload)
                    .where(EvidenceRow.pack_slug == slug)
                    .order_by(EvidenceRow.ordinal)
                ).scalars()
            )
            assertion_payloads = list(
                connection.execute(
                    select(AssertionRow.payload)
                    .where(AssertionRow.pack_slug == slug)
                    .order_by(AssertionRow.ordinal)
                ).scalars()
            )
            intervention_payloads = list(
                connection.execute(
                    select(InterventionRow.payload)
                    .where(InterventionRow.pack_slug == slug)
                    .order_by(InterventionRow.ordinal)
                ).scalars()
            )
            petri_payload = connection.execute(
                select(PetriModelRow.payload).where(PetriModelRow.pack_slug == slug)
            ).scalar_one_or_none()

        complete_payload = {
            **cast(dict[str, Any], metadata_payload),
            "entities": entity_payloads,
            "evidence": evidence_payloads,
            "assertions": assertion_payloads,
            "interventions": intervention_payloads,
            "petri_model": petri_payload,
        }
        return DomainPack.model_validate(complete_payload)

    @staticmethod
    def _delete_pack(connection: Connection, slug: str) -> None:
        for row_type in (
            PetriModelRow,
            InterventionRow,
            AssertionRow,
            EvidenceRow,
            EntityRow,
        ):
            connection.execute(delete(row_type).where(row_type.pack_slug == slug))
        connection.execute(delete(PackMetadataRow).where(PackMetadataRow.slug == slug))

    def _insert_pack(self, connection: Connection, pack: DomainPack) -> None:
        counts = SnapshotCounts(
            entities=len(pack.entities),
            evidence=len(pack.evidence),
            assertions=len(pack.assertions),
            hypotheses=len(pack.hypotheses),
            interventions=len(pack.interventions),
            petri_models=int(pack.petri_model is not None),
        )
        metadata_payload = pack.model_dump(
            mode="json",
            exclude={"entities", "evidence", "assertions", "interventions", "petri_model"},
        )
        retrieval_dates = sorted({record.retrieved_at.isoformat() for record in pack.evidence})
        connection.execute(
            insert(PackMetadataRow),
            {
                "slug": pack.slug,
                "title": pack.title,
                "pack_version": pack.version,
                "graph_version": pack.version,
                "schema_version": SNAPSHOT_SCHEMA_VERSION,
                "software_version": self._software_version,
                "evidence_rubric_version": self._evidence_rubric_version,
                "petri_model_version": pack.petri_model.model_version
                if pack.petri_model
                else "unavailable",
                "content_sha256": _content_digest(pack),
                "seeded_at": datetime.now(UTC),
                "retrieval_dates": retrieval_dates,
                "entity_count": counts.entities,
                "evidence_count": counts.evidence,
                "assertion_count": counts.assertions,
                "hypothesis_count": counts.hypotheses,
                "intervention_count": counts.interventions,
                "petri_model_count": counts.petri_models,
                "payload": metadata_payload,
            },
        )
        entity_rows = [
            {
                "pack_slug": pack.slug,
                "id": str(entity.id),
                "ordinal": ordinal,
                "preferred_name": entity.preferred_name,
                "entity_type": _enum_value(entity.entity_type),
                "payload": _json_payload(entity),
            }
            for ordinal, entity in enumerate(pack.entities)
        ]
        if entity_rows:
            connection.execute(insert(EntityRow), entity_rows)

        evidence_rows = [
            {
                "pack_slug": pack.slug,
                "id": str(record.id),
                "ordinal": ordinal,
                "study_id": str(record.study.id),
                "title": record.study.title,
                "publication_year": record.study.publication_year,
                "source_adapter": record.source_adapter,
                "evidence_grade": _enum_value(record.evidence_grade),
                "retrieved_at": record.retrieved_at,
                "payload": _json_payload(record),
            }
            for ordinal, record in enumerate(pack.evidence)
        ]
        if evidence_rows:
            connection.execute(insert(EvidenceRow), evidence_rows)

        assertion_rows = [
            {
                "pack_slug": pack.slug,
                "id": str(assertion.id),
                "ordinal": ordinal,
                "subject_id": str(assertion.subject_id),
                "relation": _enum_value(assertion.relation),
                "object_id": str(assertion.object_id),
                "causal_status": _enum_value(assertion.causal_status),
                "payload": _json_payload(assertion),
            }
            for ordinal, assertion in enumerate(pack.assertions)
        ]
        if assertion_rows:
            connection.execute(insert(AssertionRow), assertion_rows)

        intervention_rows = [
            {
                "pack_slug": pack.slug,
                "id": str(intervention.id),
                "ordinal": ordinal,
                "name": intervention.name,
                "intervention_class": _enum_value(intervention.intervention_class),
                "payload": _json_payload(intervention),
            }
            for ordinal, intervention in enumerate(pack.interventions)
        ]
        if intervention_rows:
            connection.execute(insert(InterventionRow), intervention_rows)
        if pack.petri_model is not None:
            connection.execute(
                insert(PetriModelRow),
                {
                    "pack_slug": pack.slug,
                    "id": str(pack.petri_model.id),
                    "slug": pack.petri_model.slug,
                    "model_version": pack.petri_model.model_version,
                    "payload": _json_payload(pack.petri_model),
                },
            )

    @staticmethod
    def _summary_from_mapping(row: dict[str, Any]) -> PackSnapshotSummary:
        return PackSnapshotSummary(
            slug=cast(str, row["slug"]),
            title=cast(str, row["title"]),
            counts=SnapshotCounts(
                entities=cast(int, row["entity_count"]),
                evidence=cast(int, row["evidence_count"]),
                assertions=cast(int, row["assertion_count"]),
                hypotheses=cast(int, row["hypothesis_count"]),
                interventions=cast(int, row["intervention_count"]),
                petri_models=cast(int, row["petri_model_count"]),
            ),
            provenance=SnapshotProvenance(
                pack_version=cast(str, row["pack_version"]),
                graph_version=cast(str, row["graph_version"]),
                schema_version=cast(str, row["schema_version"]),
                software_version=cast(str, row["software_version"]),
                evidence_rubric_version=cast(str, row["evidence_rubric_version"]),
                petri_model_version=cast(str, row["petri_model_version"]),
                content_sha256=cast(str, row["content_sha256"]),
            ),
        )
