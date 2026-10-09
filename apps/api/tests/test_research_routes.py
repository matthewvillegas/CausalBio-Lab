"""Universal research endpoints keep provisional snapshots outside trusted graph state."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from causalbio.research.models import ResearchMode
from causalbio.research.service import ResearchService
from causalbio.research.storage import SQLiteResearchStore
from causalbio_api.config import get_settings
from causalbio_api.routers import research
from fastapi.testclient import TestClient


@pytest.fixture
def research_client(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> TestClient:
    store = SQLiteResearchStore(tmp_path / "research.sqlite3")
    monkeypatch.setattr(research, "research_store", lambda: store)
    monkeypatch.setattr(
        research, "research_service", lambda online: ResearchService(providers={}, online=False)
    )
    return client


def test_interpretation_of_new_topic_succeeds_without_creating_a_session(
    research_client: TestClient,
) -> None:
    response = research_client.post(
        "/api/v1/research/interpret",
        json={"question": "What mechanisms influence tendon recovery?", "depth": "deep"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["mode"] == ResearchMode.LIVE_RESEARCH
    assert result["depth"] == "deep"
    assert result["domain_pack"] is None
    assert result["search_queries"]
    assert research_client.get("/api/v1/research/sessions").json() == []


def test_offline_result_is_saved_reopened_exported_and_separate_from_trusted_graph(
    research_client: TestClient,
) -> None:
    response = research_client.post(
        "/api/v1/research", json={"question": "What is dopamine?", "online": False}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["saved_locally"] is True
    assert result["mode"] == ResearchMode.EXPLANATORY
    assert any("Offline mode" in item for item in result["notices"])
    assert all(record["cache_status"] == "local_curated" for record in result["evidence"])
    assert result["evidence"]
    investigation_id = result["id"]
    assert research_client.get(f"/api/v1/research/{investigation_id}").json() == result
    recent = research_client.get("/api/v1/research/sessions?limit=1").json()
    assert recent[0]["id"] == investigation_id
    assert (
        research_client.get(f"/api/v1/investigations/{investigation_id}/graph").status_code == 404
    )
    html = research_client.get(f"/api/v1/research/{investigation_id}/report/html")
    assert html.status_code == 200
    assert html.headers["content-type"].startswith("text/html")
    assert html.headers["content-disposition"].startswith("inline;")
    assert "default-src 'none'" in html.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in html.headers["content-security-policy"]
    assert "frame-ancestors" not in html.text
    assert "What is dopamine?" in html.text
    assert "local curated" in html.text
    markdown = research_client.get(f"/api/v1/research/{investigation_id}/report/markdown")
    assert markdown.status_code == 200
    assert markdown.headers["content-disposition"].startswith("attachment;")
    assert (
        markdown.text == research_client.get(f"/api/v1/research/{investigation_id}/report/md").text
    )
    exported = research_client.get(f"/api/v1/research/{investigation_id}/report/json")
    assert exported.status_code == 200
    assert json.loads(exported.text)["investigation"] == result


@pytest.mark.parametrize(
    ("question", "mode"),
    [
        ("How much metformin should I take?", ResearchMode.RESTRICTED_WITH_SAFE_ALTERNATIVE),
        ("retention", ResearchMode.CLARIFICATION_REQUIRED),
        ("Explain computer memory", ResearchMode.OUT_OF_DOMAIN),
    ],
)
def test_nonresearch_responses_are_useful_and_not_persisted(
    research_client: TestClient,
    question: str,
    mode: ResearchMode,
) -> None:
    response = research_client.post("/api/v1/research", json={"question": question})
    assert response.status_code == 200
    result = response.json()
    assert result["mode"] == mode
    assert not result["saved_locally"]
    assert not result["evidence"] and not result["source_runs"]
    if mode is ResearchMode.RESTRICTED_WITH_SAFE_ALTERNATIVE:
        assert result["interpretation"]["safe_research_question"]
    assert research_client.get("/api/v1/research/sessions").json() == []


def test_safe_alternative_requires_a_second_explicit_request(research_client: TestClient) -> None:
    denied = research_client.post(
        "/api/v1/research", json={"question": "Where can I buy BPC-157?"}
    ).json()
    assert denied["source_runs"] == []
    alternative = denied["interpretation"]["safe_research_question"]
    assert alternative
    accepted = research_client.post(
        "/api/v1/research", json={"question": alternative, "online": False}
    )
    assert accepted.status_code == 200
    assert accepted.json()["mode"] == ResearchMode.GENERAL_EVIDENCE_SUMMARY
    assert accepted.json()["saved_locally"]
    assert len(research_client.get("/api/v1/research/sessions").json()) == 1


@pytest.mark.parametrize(
    "body",
    [
        {"question": "x"},
        {"question": "How does tendon repair work?", "depth": "unbounded"},
        {"question": "How does tendon repair work?", "online": "false"},
        {"question": "How does tendon repair work?", "context": {"tissue": 15}},
        {"question": "How does tendon repair work?", "context": {"tissue": True}},
        {"question": "How does tendon repair work?", "unexpected": "field"},
    ],
)
def test_invalid_request_bodies_are_structured_errors_without_saved_results(
    research_client: TestClient,
    body: dict[str, object],
) -> None:
    response = research_client.post("/api/v1/research", json=body)
    assert response.status_code == 422
    assert response.json()["correlation_id"]
    assert research_client.get("/api/v1/research/sessions").json() == []


def test_missing_sessions_and_invalid_report_formats_are_structured_errors(
    research_client: TestClient,
) -> None:
    absent_id = uuid4()
    for path in (f"/api/v1/research/{absent_id}", f"/api/v1/research/{absent_id}/report/html"):
        response = research_client.get(path)
        assert response.status_code == 404
        assert response.json()["correlation_id"]
    assert research_client.get(f"/api/v1/research/{absent_id}/report/exe").status_code == 422
    assert research_client.get("/api/v1/research/not-a-uuid").status_code == 422
    assert research_client.get("/api/v1/research/sessions?limit=101").status_code == 422


def test_status_distinguishes_enabled_capability_from_source_availability(
    research_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CAUSALBIO_LIVE_RESEARCH_ENABLED", "false")
    get_settings.cache_clear()
    response = research_client.get("/api/v1/research/status")
    assert response.status_code == 200
    assert response.json()["live_enabled"] is False
    assert "Offline" in response.json()["status_label"]
    monkeypatch.setenv("CAUSALBIO_LIVE_RESEARCH_ENABLED", "true")
    get_settings.cache_clear()
    enabled = research_client.get("/api/v1/research/status").json()
    assert enabled["live_enabled"] is True
    assert "checked during each bounded search" in enabled["notice"]


def test_openapi_documents_universal_research_routes(research_client: TestClient) -> None:
    paths = research_client.get("/api/openapi.json").json()["paths"]
    assert {
        "/api/v1/research/status",
        "/api/v1/research/interpret",
        "/api/v1/research",
        "/api/v1/research/sessions",
        "/api/v1/research/{research_id}",
        "/api/v1/research/{research_id}/report/{report_format}",
    }.issubset(paths)


@pytest.mark.parametrize(
    ("server_enabled", "requested_online", "expected_online"),
    [(False, True, False), (True, False, False), (True, True, True)],
)
def test_service_factory_combines_server_capability_with_explicit_offline_choice(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    server_enabled: bool,
    requested_online: bool,
    expected_online: bool,
) -> None:
    calls: list[bool] = []

    def capture_service(*, online: bool, cache_root: Path) -> ResearchService:
        calls.append(online)
        assert cache_root.is_absolute()
        return ResearchService(providers={}, online=online)

    monkeypatch.setattr(research, "ResearchService", capture_service)
    monkeypatch.setenv("CAUSALBIO_LIVE_RESEARCH_ENABLED", str(server_enabled).lower())
    get_settings.cache_clear()
    service = research.research_service(requested_online)
    assert calls == [expected_online]
    assert service.online is expected_online
