"""Isolated FastAPI client fixtures for local-mode route tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from causalbio_api.config import get_settings
from causalbio_api.main import create_app
from causalbio_api.state import report_artifacts, store
from fastapi.testclient import TestClient


@pytest.fixture
def artifact_dir(tmp_path: Path) -> Path:
    return tmp_path / "artifacts"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, artifact_dir: Path) -> Iterator[TestClient]:
    monkeypatch.setenv("CAUSALBIO_ARTIFACT_DIR", str(artifact_dir))
    monkeypatch.setenv("CAUSALBIO_NO_LLM", "true")
    monkeypatch.setenv("CAUSALBIO_NO_TELEMETRY", "true")
    monkeypatch.setenv("CAUSALBIO_LOCAL_RATE_LIMIT_PER_MINUTE", "1000")
    get_settings.cache_clear()
    store.clear()
    report_artifacts.clear()

    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        yield test_client

    store.clear()
    report_artifacts.clear()
    get_settings.cache_clear()
