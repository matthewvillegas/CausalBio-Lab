"""Shared typed helpers for API route tests."""

from __future__ import annotations

from typing import Any, cast

from fastapi.testclient import TestClient
from httpx import Response

MEMORY_QUESTION = "How could long-term memory persist after learning?"
KNEE_QUESTION = "What mechanisms contribute to knee pain after repeated jumping?"


def json_object(response: Response) -> dict[str, Any]:
    payload = response.json()
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


def json_list(response: Response) -> list[dict[str, Any]]:
    payload = response.json()
    assert isinstance(payload, list)
    assert all(isinstance(item, dict) for item in payload)
    return cast(list[dict[str, Any]], payload)


def create_investigation(client: TestClient, question: str) -> dict[str, Any]:
    response = client.post("/api/v1/investigations", json={"question": question})
    assert response.status_code == 201, response.text
    return json_object(response)


def assert_problem(
    response: Response,
    *,
    status: int,
    problem_suffix: str,
) -> dict[str, Any]:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith(
        "application/problem+json"
    ) or response.headers["content-type"].startswith("application/json")
    problem = json_object(response)
    assert problem["status"] == status
    assert str(problem["type"]).endswith(problem_suffix)
    assert problem["correlation_id"] == response.headers["x-correlation-id"]
    assert "traceback" not in str(problem).casefold()
    return problem
