"""Literature fallback, graph export, and safe report artifact route tests."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest
from causalbio.domain.models import InvestigationResult
from causalbio_api.state import store
from fastapi.testclient import TestClient
from helpers import (
    MEMORY_QUESTION,
    assert_problem,
    create_investigation,
    json_object,
)


def test_whitespace_search_is_rejected_instead_of_matching_every_record(client: TestClient) -> None:
    response = client.post("/api/v1/literature/search", json={"query": "    "})
    assert_problem(response, status=422, problem_suffix="/validation-error")


def test_report_can_be_generated_without_creating_artifacts(
    client: TestClient, artifact_dir: Path
) -> None:
    investigation = create_investigation(client, MEMORY_QUESTION)
    response = client.post(
        "/api/v1/reports",
        json={"investigation_id": investigation["id"], "persist_artifacts": False},
    )
    assert response.status_code == 200
    assert json_object(response)["artifacts"] == []
    assert not artifact_dir.exists()


def test_export_and_report_use_the_investigation_snapshot(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    investigation = create_investigation(client, MEMORY_QUESTION)

    def unavailable_pack(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("An existing investigation must not reload mutable pack data")

    monkeypatch.setattr("causalbio_api.routers.v1.load_domain_pack", unavailable_pack)
    response = client.get(f"/api/v1/graph-exports/{investigation['id']}/nodes-csv")
    assert response.status_code == 200
    assert len(list(csv.DictReader(io.StringIO(response.text)))) == len(
        investigation["graph"]["entities"]
    )
    report = client.post("/api/v1/reports", json={"investigation_id": investigation["id"]})
    assert report.status_code == 200


def test_bundled_literature_search_returns_curated_cached_records(client: TestClient) -> None:
    response = client.post(
        "/api/v1/literature/search",
        json={"query": "slow oscillations", "mode": "bundled"},
    )

    assert response.status_code == 200, response.text
    payload = json_object(response)
    assert payload["mode"] == "bundled"
    assert payload["cached"] is True
    assert "not a real-time systematic search" in payload["notice"]
    assert payload["records"]
    assert all(record["curation_status"] == "VALIDATED" for record in payload["records"])
    assert all(record["study"]["source_url"] for record in payload["records"])

    empty = client.post(
        "/api/v1/literature/search",
        json={"query": "nonexistent-fixture-term", "mode": "bundled"},
    )
    assert empty.status_code == 200
    assert json_object(empty)["records"] == []


def test_live_literature_search_fails_closed_without_network_fabrication(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/literature/search",
        json={"query": "memory", "mode": "live"},
        headers={"x-correlation-id": "live-literature-1"},
    )

    problem = assert_problem(
        response,
        status=503,
        problem_suffix="/external-source-unavailable",
    )
    assert response.headers["content-type"].startswith("application/problem+json")
    assert problem["alternatives"] == ["bundled"]
    assert "offline mode" in problem["title"]


def test_every_graph_export_is_downloadable_and_provenance_bearing(
    client: TestClient,
) -> None:
    investigation = create_investigation(client, MEMORY_QUESTION)
    investigation_id = investigation["id"]

    json_ld = client.get(f"/api/v1/graph-exports/{investigation_id}/json-ld")
    graphml = client.get(f"/api/v1/graph-exports/{investigation_id}/graphml")
    nodes_csv = client.get(f"/api/v1/graph-exports/{investigation_id}/nodes-csv")
    edges_csv = client.get(f"/api/v1/graph-exports/{investigation_id}/edges-csv")

    assert all(response.status_code == 200 for response in (json_ld, graphml, nodes_csv, edges_csv))
    assert json_ld.headers["content-type"].startswith("application/ld+json")
    assert graphml.headers["content-type"].startswith("application/graphml+xml")
    assert nodes_csv.headers["content-type"].startswith("text/csv")
    assert edges_csv.headers["content-type"].startswith("text/csv")
    assert all(
        "attachment; filename=" in response.headers["content-disposition"]
        for response in (json_ld, graphml, nodes_csv, edges_csv)
    )

    graph_payload = json.loads(json_ld.text)
    assert graph_payload["@graph"]
    assert "<graphml" in graphml.text
    node_rows = list(csv.DictReader(io.StringIO(nodes_csv.text)))
    edge_rows = list(csv.DictReader(io.StringIO(edges_csv.text)))
    assert node_rows and edge_rows
    assert all(row["supporting_evidence_ids"] for row in edge_rows)


def test_graph_exports_reject_unknown_investigations_and_formats(client: TestClient) -> None:
    unknown = client.get(f"/api/v1/graph-exports/{UUID(int=995)}/json-ld")
    assert_problem(unknown, status=404, problem_suffix="/not-found")

    investigation = create_investigation(client, MEMORY_QUESTION)
    invalid = client.get(f"/api/v1/graph-exports/{investigation['id']}/unsafe-format")
    problem = assert_problem(
        invalid,
        status=422,
        problem_suffix="/invalid-scientific-input",
    )
    assert "Supported graph exports" in problem["detail"]


def test_report_generation_writes_complete_confined_artifacts(
    client: TestClient, artifact_dir: Path
) -> None:
    investigation = create_investigation(client, MEMORY_QUESTION)
    response = client.post(
        "/api/v1/reports",
        json={"investigation_id": investigation["id"], "persist_artifacts": True},
    )

    assert response.status_code == 200, response.text
    report = json_object(response)
    assert report["citation_coverage"] == 1.0
    artifacts = cast(list[dict[str, Any]], report["artifacts"])
    expected_names = {
        "report.md",
        "report.html",
        "report.json",
        "investigation.json",
        "graph.jsonld",
        "graph.graphml",
        "nodes.csv",
        "edges.csv",
        "petri-model.json",
    }
    assert {artifact["filename"] for artifact in artifacts} == expected_names

    report_dir = (artifact_dir / report["report_id"]).resolve()
    assert report_dir.parent == artifact_dir.resolve()
    assert {path.name for path in report_dir.iterdir()} == expected_names
    assert all(path.resolve().parent == report_dir for path in report_dir.iterdir())

    downloads = {
        artifact["filename"]: client.get(artifact["download_url"]) for artifact in artifacts
    }
    assert all(download.status_code == 200 for download in downloads.values())
    assert all(
        "attachment; filename=" in download.headers["content-disposition"]
        for name, download in downloads.items()
        if name != "report.html"
    )
    assert downloads["report.html"].headers["content-disposition"].startswith("inline;")
    assert "default-src 'none'" in downloads["report.html"].headers["content-security-policy"]
    assert "frame-ancestors 'none'" in downloads["report.html"].headers["content-security-policy"]
    assert "frame-ancestors" not in downloads["report.html"].text
    assert downloads["report.html"].headers["x-content-type-options"] == "nosniff"
    assert "not a diagnosis" in downloads["report.md"].text
    assert "Content-Security-Policy" in downloads["report.html"].text
    assert "<script" not in downloads["report.html"].text.casefold()

    report_json = json.loads(downloads["report.json"].text)
    assert report_json["investigation_id"] == investigation["id"]
    assert report_json["citation_coverage"] == 1.0
    assert report_json["claims"]
    assert all(claim["evidence_ids"] for claim in report_json["claims"])


def test_report_without_a_pathway_model_omits_the_model_artifact(client: TestClient) -> None:
    investigation = InvestigationResult.model_validate(
        create_investigation(client, MEMORY_QUESTION)
    )
    store.put(investigation.model_copy(update={"petri_model": None}))

    response = client.post("/api/v1/reports", json={"investigation_id": str(investigation.id)})
    assert response.status_code == 200, response.text
    report = json_object(response)
    artifacts = {item["filename"]: item for item in report["artifacts"]}
    assert "petri-model.json" not in artifacts
    html = client.get(artifacts["report.html"]["download_url"])
    assert html.status_code == 200
    assert "does not include an executable pathway model" in html.text
    assert '<details class="appendix">' in html.text
    missing_model = client.get(f"/api/v1/reports/{report['report_id']}/artifacts/petri-model.json")
    assert_problem(missing_model, status=404, problem_suffix="/not-found")


def test_report_download_rejects_unknown_and_path_like_filenames(
    client: TestClient,
) -> None:
    investigation = create_investigation(client, MEMORY_QUESTION)
    report = json_object(
        client.post(
            "/api/v1/reports",
            json={"investigation_id": investigation["id"]},
        )
    )
    report_id = report["report_id"]

    unknown = client.get(f"/api/v1/reports/{report_id}/artifacts/not-listed.txt")
    assert_problem(unknown, status=404, problem_suffix="/not-found")

    unknown_report = client.get(f"/api/v1/reports/{UUID(int=994)}/artifacts/report.md")
    assert_problem(unknown_report, status=404, problem_suffix="/not-found")

    traversal = client.get(f"/api/v1/reports/{report_id}/artifacts/..%2Freport.md")
    assert traversal.status_code == 404
    assert "# CausalBio Lab" not in traversal.text
