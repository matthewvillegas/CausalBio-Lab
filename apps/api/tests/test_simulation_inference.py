"""Petri simulation and inference-gating route tests."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from fastapi.testclient import TestClient
from helpers import assert_problem, json_list, json_object


def _modified_place(place: dict[str, Any]) -> float:
    initial = float(place["initial_value"])
    minimum = float(place["valid_min"])
    maximum = float(place["valid_max"])
    if initial != minimum:
        return minimum
    return minimum + (maximum - minimum) / 2.0


def test_petri_models_list_contains_both_curated_offline_models(client: TestClient) -> None:
    response = client.get("/api/v1/petri/models")

    assert response.status_code == 200
    models = json_list(response)
    assert len(models) == 2
    assert {model["slug"] for model in models} == {
        "memory-plasticity",
        "knee-load",
    }
    assert all(model["curated"] is True for model in models)
    assert all(
        "not a personalized biological prediction" in model["safety_label"] for model in models
    )


def test_modified_petri_scenario_is_executed_and_reproducible(client: TestClient) -> None:
    model = json_list(client.get("/api/v1/petri/models"))[0]
    place = cast(dict[str, Any], model["places"][0])
    modified_initial = _modified_place(place)
    base_payload = {
        "model_id": model["id"],
        "duration": 2.0,
        "steps": 9,
        "seed": 42,
    }
    baseline_response = client.post(
        "/api/v1/petri/simulate",
        json={**base_payload, "scenario": "baseline"},
    )
    modified_payload = {
        **base_payload,
        "scenario": "modified initial state",
        "initial_overrides": {place["id"]: modified_initial},
    }
    modified_response = client.post("/api/v1/petri/simulate", json=modified_payload)
    repeated_response = client.post("/api/v1/petri/simulate", json=modified_payload)

    assert baseline_response.status_code == 200, baseline_response.text
    assert modified_response.status_code == repeated_response.status_code == 200
    baseline = json_object(baseline_response)
    modified = json_object(modified_response)
    repeated = json_object(repeated_response)
    assert baseline["state"] == modified["state"] == "COMPLETE"
    assert modified == repeated
    assert baseline["id"] != modified["id"]
    assert modified["parameters"]["scenario"] == "modified initial state"
    assert modified["parameters"]["initial_overrides"] == {place["id"]: modified_initial}
    assert modified["trajectories"][place["id"]][0] == modified_initial
    assert len(modified["times"]) == 9
    assert modified["transition_activity"]
    assert "not a personalized biological prediction" in modified["summary"][0]


def test_petri_simulation_rejects_unknown_model_and_invalid_override(client: TestClient) -> None:
    unknown = client.post(
        "/api/v1/petri/simulate",
        json={"model_id": str(UUID(int=996)), "duration": 1, "steps": 3},
    )
    assert_problem(unknown, status=404, problem_suffix="/not-found")

    model = json_list(client.get("/api/v1/petri/models"))[0]
    place = cast(dict[str, Any], model["places"][0])
    invalid = client.post(
        "/api/v1/petri/simulate",
        json={
            "model_id": model["id"],
            "duration": 1,
            "steps": 3,
            "initial_overrides": {place["id"]: float(place["valid_max"]) + 1.0},
        },
    )
    problem = assert_problem(
        invalid,
        status=422,
        problem_suffix="/invalid-scientific-input",
    )
    assert "valid maximum" in problem["detail"]


def test_bayesian_route_fails_closed_when_inference_requirements_are_absent(
    client: TestClient,
) -> None:
    response = client.post("/api/v1/bayes/infer")

    assert response.status_code == 200
    eligibility = json_object(response)
    assert eligibility["state"] == "INELIGIBLE"
    assert eligibility["eligible"] is False
    assert eligibility["no_fake_fallback"] is True
    assert eligibility["requirements"]["defined_numerical_model"] is True
    assert eligibility["requirements"]["explicit_priors"] is False
    assert eligibility["requirements"]["explicit_likelihood"] is False
    assert eligibility["requirements"]["hmc_backend_and_diagnostics"] is False
    assert "unavailable" in eligibility["explanation"]


def test_bundled_hmc_demo_runs_real_sampling_with_diagnostics(client: TestClient) -> None:
    response = client.post("/api/v1/bayes/demo/run", json={})

    assert response.status_code == 200, response.text
    run = json_object(response)
    assert run["state"] == "COMPLETE"
    assert run["dataset"]["synthetic"] is True
    assert "not derived" in run["dataset"]["provenance"]
    assert run["diagnostics"]["divergences"] == 0
    assert run["diagnostics"]["r_hat_max"] < 1.01
    assert run["diagnostics"]["ess_bulk_min"] >= 400
    assert run["diagnostics"]["energy_bfmi_min"] >= 0.3
    assert run["recovery"] == {"baseline": True, "condition_effect": True}
    assert len(run["posterior_draws"]["baseline"]) == 4
    assert len(run["posterior_draws"]["baseline"][0]) == 750
    assert run["priors"] and run["likelihood"]
    assert run["posterior_predictive"]
    assert run["sensitivity"]

    invalid = client.post("/api/v1/bayes/demo/run", json={"chains": 1})
    assert_problem(invalid, status=422, problem_suffix="/validation-error")
