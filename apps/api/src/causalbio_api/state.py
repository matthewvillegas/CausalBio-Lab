"""Thread-safe local-mode runtime state."""

from __future__ import annotations

from pathlib import Path
from threading import RLock
from uuid import UUID

from causalbio.domain.models import InvestigationResult


class InvestigationStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._items: dict[UUID, InvestigationResult] = {}

    def put(self, result: InvestigationResult) -> None:
        with self._lock:
            self._items[result.id] = result

    def get(self, investigation_id: UUID) -> InvestigationResult:
        with self._lock:
            try:
                return self._items[investigation_id]
            except KeyError as exc:
                raise KeyError(f"Unknown investigation: {investigation_id}") from exc

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


store = InvestigationStore()


class ReportArtifactStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._items: dict[UUID, dict[str, Path]] = {}

    def put(self, report_id: UUID, artifacts: dict[str, Path]) -> None:
        with self._lock:
            self._items[report_id] = dict(artifacts)

    def get(self, report_id: UUID, filename: str) -> Path:
        if Path(filename).name != filename:
            raise KeyError("Invalid artifact filename")
        with self._lock:
            try:
                return self._items[report_id][filename]
            except KeyError as exc:
                raise KeyError(f"Unknown report artifact: {report_id}/{filename}") from exc

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


report_artifacts = ReportArtifactStore()
