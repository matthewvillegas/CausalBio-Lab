"""System posture, demo registry, and question-interpretation API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from helpers import assert_problem, json_list, json_object


def test_health_declares_local_offline_private_posture(client: TestClient) -> None:
    response = client.get(
        "/api/v1/health",
        headers={"x-correlation-id": "health-contract-1"},
    )

    assert response.status_code == 200
    payload = json_object(response)
    assert payload == {
        "status": "ok",
        "version": "1.0.0",
        "mode": "local-demo",
        "no_llm": True,
        "no_telemetry": True,
        "demo_pack_count": 2,
    }
    assert response.headers["x-correlation-id"] == "health-contract-1"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "camera=()" in response.headers["permissions-policy"]


def test_openapi_lists_every_public_v1_route(client: TestClient) -> None:
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    paths = json_object(response)["paths"]
    assert isinstance(paths, dict)
    expected = {
        "/api/v1/health",
        "/api/v1/demo-cases",
        "/api/v1/questions/interpret",
        "/api/v1/investigations",
        "/api/v1/investigations/{investigation_id}",
        "/api/v1/investigations/{investigation_id}/hypotheses",
        "/api/v1/investigations/{investigation_id}/graph",
        "/api/v1/assertions/{assertion_id}",
        "/api/v1/assertions/{assertion_id}/evidence",
        "/api/v1/paths/search",
        "/api/v1/petri/models",
        "/api/v1/petri/simulate",
        "/api/v1/bayes/infer",
        "/api/v1/literature/search",
        "/api/v1/graph-exports/{investigation_id}/{export_format}",
        "/api/v1/reports",
        "/api/v1/reports/{report_id}/artifacts/{filename}",
    }
    assert expected.issubset(paths)


def test_demo_case_list_is_curated_and_offline(client: TestClient) -> None:
    response = client.get("/api/v1/demo-cases")

    assert response.status_code == 200
    cases = json_list(response)
    assert [item["slug"] for item in cases] == ["memory", "knee-pain"]
    assert all(item["version"] and item["example_questions"] for item in cases)
    assert all("educational" in str(item["educational_notice"]).casefold() for item in cases)


@pytest.mark.parametrize(
    ("question", "expected_pack", "expected_safety"),
    [
        (
            "How could memory persist after learning?",
            "memory",
            "general_biological_research",
        ),
        (
            "What mechanisms contribute to knee pain after repeated jumping?",
            "knee-pain",
            "symptom_education",
        ),
    ],
)
def test_question_interpretation_succeeds_for_both_curated_domains(
    client: TestClient,
    question: str,
    expected_pack: str,
    expected_safety: str,
) -> None:
    response = client.post(
        "/api/v1/questions/interpret",
        json={"question": question, "context": {"duration": "two weeks"}},
    )

    assert response.status_code == 200
    payload = json_object(response)
    assert payload["domain_pack"] == expected_pack
    assert payload["question"]["context"]["duration"] == "two weeks"
    assert payload["safety_notice"]["query_class"] == expected_safety
    assert payload["safety_notice"]["restricted"] is False


@pytest.mark.parametrize(
    ("question", "problem_suffix"),
    [
        ("   ", "/empty-question"),
        ("retention", "/ambiguous-question"),
        ("How does liver metabolism regulate glucose?", "/unsupported-offline-domain"),
        ("How many mg should I take to improve memory?", "/restricted-request"),
    ],
)
def test_question_interpretation_returns_safe_structured_failures(
    client: TestClient, question: str, problem_suffix: str
) -> None:
    response = client.post(
        "/api/v1/questions/interpret",
        json={"question": question},
        headers={"x-correlation-id": "question-error-1"},
    )

    problem = assert_problem(response, status=422, problem_suffix=problem_suffix)
    assert problem["detail"]
    if problem_suffix == "/ambiguous-question":
        assert "long-term memory retention" in problem["alternatives"]


def test_question_interpretation_rejects_unknown_context_fields(client: TestClient) -> None:
    response = client.post(
        "/api/v1/questions/interpret",
        json={
            "question": "How could memory persist after learning?",
            "context": {"unvalidated_field": "hidden"},
        },
    )

    problem = assert_problem(
        response,
        status=422,
        problem_suffix="/invalid-scientific-input",
    )
    assert "Unknown context fields" in problem["detail"]
