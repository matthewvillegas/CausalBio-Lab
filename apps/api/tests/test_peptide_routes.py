"""Known-peptide API tests keep analysis bounded and transparent."""

from fastapi.testclient import TestClient
from helpers import assert_problem, json_list, json_object


def test_known_peptide_catalog_and_analysis(client: TestClient) -> None:
    catalog_response = client.get("/api/v1/peptides/known")
    assert catalog_response.status_code == 200
    catalog = json_list(catalog_response)
    assert {item["slug"] for item in catalog} == {"substance-p", "neurokinin-a"}

    response = client.get("/api/v1/peptides/known/substance-p/analysis", params={"pH": 7.4})
    assert response.status_code == 200, response.text
    analysis = json_object(response)
    assert analysis["peptide"]["sequence"] == "RPKPQQFFGLM"
    assert analysis["measured_properties"] == {}
    assert analysis["calculated_properties"]["sequence_length"] == 11
    assert analysis["calculated_properties"]["approximate_molecular_weight_da"] > 1300
    assert analysis["database_annotations"]["known_targets"]
    assert analysis["model_predictions"]["unsupported_activity_prediction"] is False
    assert "No novel sequence generation" in analysis["safety_notice"]


def test_known_peptide_comparison_and_closed_input_surface(client: TestClient) -> None:
    response = client.get("/api/v1/peptides/compare/substance-p/neurokinin-a")
    assert response.status_code == 200
    comparison = json_object(response)
    assert comparison["sequence_identity"] > 0
    assert [item["residue"] for item in comparison["conserved_positions"]] == list("KFGLM")

    missing = client.get("/api/v1/peptides/known/invented/analysis")
    assert_problem(missing, status=404, problem_suffix="/not-found")
    invalid_ph = client.get("/api/v1/peptides/known/substance-p/analysis", params={"pH": 15})
    assert_problem(invalid_ph, status=422, problem_suffix="/validation-error")

    # There is intentionally no POST endpoint that accepts or designs an arbitrary sequence.
    openapi = json_object(client.get("/api/openapi.json"))
    peptide_paths = {
        path: methods for path, methods in openapi["paths"].items() if "/peptides/" in path
    }
    assert peptide_paths
    assert all(
        set(methods).isdisjoint({"post", "put", "patch"}) for methods in peptide_paths.values()
    )
