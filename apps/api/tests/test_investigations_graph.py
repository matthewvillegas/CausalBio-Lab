"""Investigation retrieval, provenance, assertion, and path route tests."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from helpers import (
    KNEE_QUESTION,
    MEMORY_QUESTION,
    assert_problem,
    create_investigation,
    json_list,
    json_object,
)


@pytest.mark.parametrize(
    ("question", "expected_pack"),
    [(MEMORY_QUESTION, "memory"), (KNEE_QUESTION, "knee-pain")],
)
def test_create_and_retrieve_complete_investigations_for_both_packs(
    client: TestClient, question: str, expected_pack: str
) -> None:
    created = create_investigation(client, question)
    investigation_id = created["id"]

    assert created["state"] == "COMPLETE"
    assert created["domain_pack"] == expected_pack
    assert len(created["hypotheses"]) >= 2
    assert created["graph"]["assertions"]
    assert created["graph"]["evidence"]
    assert created["petri_model"]["curated"] is True
    assert created["inference_eligibility"]["eligible"] is False

    fetched_response = client.get(f"/api/v1/investigations/{investigation_id}")
    assert fetched_response.status_code == 200
    fetched = json_object(fetched_response)
    assert fetched["id"] == investigation_id
    assert fetched["hypotheses"] == created["hypotheses"]

    hypotheses_response = client.get(f"/api/v1/investigations/{investigation_id}/hypotheses")
    graph_response = client.get(f"/api/v1/investigations/{investigation_id}/graph")
    assert hypotheses_response.status_code == graph_response.status_code == 200
    assert hypotheses_response.json() == created["hypotheses"]
    assert graph_response.json() == created["graph"]


def test_unknown_investigation_returns_correlation_aware_not_found(client: TestClient) -> None:
    response = client.get(f"/api/v1/investigations/{UUID(int=999)}")

    problem = assert_problem(response, status=404, problem_suffix="/not-found")
    assert "Unknown investigation" in problem["detail"]


def test_assertion_and_evidence_routes_preserve_provenance(client: TestClient) -> None:
    investigation = create_investigation(client, MEMORY_QUESTION)
    assertions = cast(list[dict[str, Any]], investigation["graph"]["assertions"])
    assertion_summary = next(item for item in assertions if item["supporting_evidence_ids"])
    assertion_id = assertion_summary["id"]

    assertion_response = client.get(f"/api/v1/assertions/{assertion_id}")
    evidence_response = client.get(f"/api/v1/assertions/{assertion_id}/evidence")
    assert assertion_response.status_code == evidence_response.status_code == 200
    assertion = json_object(assertion_response)
    records = json_list(evidence_response)

    expected_evidence_ids = [
        *assertion["supporting_evidence_ids"],
        *assertion["contradictory_evidence_ids"],
    ]
    assert assertion["id"] == assertion_id
    assert [record["id"] for record in records] == expected_evidence_ids
    assert all(record["study"]["source_url"] for record in records)
    assert all(record["evidence_note"] for record in records)


def test_unknown_assertion_and_evidence_routes_return_not_found(client: TestClient) -> None:
    unknown = UUID(int=998)
    for suffix in ("", "/evidence"):
        response = client.get(f"/api/v1/assertions/{unknown}{suffix}")
        assert_problem(response, status=404, problem_suffix="/not-found")


def test_path_search_uses_stored_investigation_and_is_deterministic(client: TestClient) -> None:
    investigation = create_investigation(client, MEMORY_QUESTION)
    hypothesis = cast(dict[str, Any], investigation["hypotheses"][0])
    seeded_path = cast(dict[str, Any], hypothesis["mechanism_paths"][0])
    entity_ids = cast(list[str], seeded_path["entity_ids"])
    request = {
        "investigation_id": investigation["id"],
        "source_id": entity_ids[0],
        "target_id": entity_ids[-1],
        "max_length": 6,
    }

    first_response = client.post("/api/v1/paths/search", json=request)
    second_response = client.post("/api/v1/paths/search", json=request)
    assert first_response.status_code == second_response.status_code == 200
    first = json_list(first_response)
    second = json_list(second_response)
    assert first == second
    assert first
    assert all(path["entity_ids"][0] == entity_ids[0] for path in first)
    assert all(path["entity_ids"][-1] == entity_ids[-1] for path in first)
    scores = [path["score"]["display_index"] for path in first]
    assert scores == sorted(scores, reverse=True)


def test_path_search_rejects_unknown_endpoints_and_invalid_limits(client: TestClient) -> None:
    investigation = create_investigation(client, MEMORY_QUESTION)
    known_entity = investigation["graph"]["entities"][0]["id"]
    base_request = {
        "investigation_id": investigation["id"],
        "source_id": known_entity,
        "target_id": str(UUID(int=997)),
        "max_length": 6,
    }

    missing = client.post("/api/v1/paths/search", json=base_request)
    assert_problem(missing, status=404, problem_suffix="/not-found")

    invalid = client.post(
        "/api/v1/paths/search",
        json={**base_request, "target_id": known_entity, "max_length": 11},
    )
    assert invalid.status_code == 422
