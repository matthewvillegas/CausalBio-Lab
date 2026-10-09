"""Durable local research snapshots, isolated from trusted domain-pack storage."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal, cast
from uuid import UUID

from causalbio.research.models import UniversalResearchResult
from causalbio.research.reporting import RESEARCH_SNAPSHOT_VERSION, generate_research_report

ReportFormat = Literal["html", "md", "markdown", "json"]


class ResearchSnapshotError(ValueError):
    """A persisted research result does not match its recorded immutable snapshot."""


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SQLiteResearchStore:
    """Append-only complete result and report storage; no scientific graph writes."""

    def __init__(self, database_path: str | Path = Path("data/research.sqlite3")) -> None:
        self.database_path = Path(database_path).expanduser().resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS research_sessions (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                mode TEXT NOT NULL,
                created_at TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                payload TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL,
                report_html TEXT NOT NULL,
                report_html_sha256 TEXT NOT NULL,
                report_markdown TEXT NOT NULL,
                report_markdown_sha256 TEXT NOT NULL,
                report_json TEXT NOT NULL,
                report_json_sha256 TEXT NOT NULL
            )""")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS research_sessions_recent ON research_sessions(created_at DESC, id)"
            )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def save(self, result: UniversalResearchResult) -> UniversalResearchResult:
        """Validate then atomically save the result and its standalone report formats."""
        payload = result.model_dump(mode="json")
        payload["saved_locally"] = True
        saved = UniversalResearchResult.model_validate(payload)
        serialized = json.dumps(
            saved.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        digest = _digest(serialized)
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT payload, payload_sha256 FROM research_sessions WHERE id = ?",
                (str(saved.id),),
            ).fetchone()
            if existing is not None:
                if existing["payload_sha256"] != digest or _digest(existing["payload"]) != digest:
                    raise ResearchSnapshotError(
                        "A different snapshot already uses this research ID; create a new investigation to refresh evidence"
                    )
                return UniversalResearchResult.model_validate_json(existing["payload"])
            reports = generate_research_report(saved)
            connection.execute(
                "INSERT INTO research_sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(saved.id),
                    saved.interpretation.question.original_text,
                    saved.mode.value,
                    saved.created_at.isoformat(),
                    RESEARCH_SNAPSHOT_VERSION,
                    serialized,
                    digest,
                    reports.html,
                    _digest(reports.html),
                    reports.markdown,
                    _digest(reports.markdown),
                    reports.json,
                    _digest(reports.json),
                ),
            )
        return saved

    def _row(self, investigation_id: UUID) -> sqlite3.Row:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM research_sessions WHERE id = ?", (str(investigation_id),)
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown saved research investigation: {investigation_id}")
        if row["schema_version"] != RESEARCH_SNAPSHOT_VERSION:
            raise ResearchSnapshotError("Saved research schema is unsupported")
        if _digest(row["payload"]) != row["payload_sha256"]:
            raise ResearchSnapshotError("Saved research payload failed its content integrity check")
        result = UniversalResearchResult.model_validate_json(row["payload"])
        if (
            str(result.id) != str(investigation_id)
            or result.interpretation.question.original_text != row["question"]
            or result.mode.value != row["mode"]
            or result.created_at.isoformat() != row["created_at"]
        ):
            raise ResearchSnapshotError("Saved research metadata does not match its payload")
        return cast(sqlite3.Row, row)

    def load(self, investigation_id: UUID) -> UniversalResearchResult:
        return UniversalResearchResult.model_validate_json(self._row(investigation_id)["payload"])

    def list_recent(self, limit: int = 20) -> list[dict[str, str]]:
        if not 1 <= limit <= 100:
            raise ValueError("Recent research limit must be between 1 and 100")
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT id, question, mode, created_at FROM research_sessions ORDER BY julianday(created_at) DESC, id LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {name: str(row[name]) for name in ("id", "question", "mode", "created_at")}
            for row in rows
        ]

    def report(self, investigation_id: UUID, format: ReportFormat) -> str:
        columns = {
            "html": "report_html",
            "md": "report_markdown",
            "markdown": "report_markdown",
            "json": "report_json",
        }
        if format not in columns:
            raise ValueError("Research report format must be html, md, markdown, or json")
        row = self._row(investigation_id)
        column = columns[format]
        content = str(row[column])
        if _digest(content) != row[f"{column}_sha256"]:
            raise ResearchSnapshotError("Saved research report failed its content integrity check")
        return content
