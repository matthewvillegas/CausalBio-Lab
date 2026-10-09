"""Scientific checks for the bounded synthetic HMC demonstration."""

from __future__ import annotations

import numpy as np
import pytest
from causalbio.domain.enums import InferenceState
from causalbio.domain.models import HMCConfiguration, HMCInferenceRun
from causalbio.inference import load_hmc_demo_dataset, run_hmc_demo
from pydantic import ValidationError


@pytest.fixture(scope="module")
def completed_run() -> HMCInferenceRun:
    return run_hmc_demo()


def test_dataset_is_explicitly_synthetic_and_balanced() -> None:
    dataset = load_hmc_demo_dataset()
    assert dataset.synthetic is True
    assert len(dataset.outcome) == 40
    assert dataset.predictor.count(0.0) == 20
    assert dataset.predictor.count(1.0) == 20
    assert "not derived" in dataset.provenance
    assert dataset.true_parameters == {"baseline": 0.25, "condition_effect": 0.55}


def test_hmc_recovers_parameters_with_clean_diagnostics(completed_run: HMCInferenceRun) -> None:
    run = completed_run
    assert run.state is InferenceState.COMPLETE
    assert run.diagnostics.divergences == 0
    assert run.diagnostics.r_hat_max is not None and run.diagnostics.r_hat_max < 1.01
    assert run.diagnostics.ess_bulk_min is not None and run.diagnostics.ess_bulk_min >= 400
    assert run.diagnostics.energy_bfmi_min is not None and run.diagnostics.energy_bfmi_min > 0.3
    assert run.diagnostics.acceptance_rate is not None
    assert 0.6 <= run.diagnostics.acceptance_rate <= 0.99
    assert run.diagnostics.warnings == ()
    assert run.recovery == {"baseline": True, "condition_effect": True}


def test_sampled_means_match_conjugate_linear_gaussian_solution(
    completed_run: HMCInferenceRun,
) -> None:
    run = completed_run
    dataset = run.dataset
    x = np.asarray(dataset.predictor)
    design = np.column_stack((np.ones_like(x), x))
    y = np.asarray(dataset.outcome)
    precision = np.eye(2) + design.T @ design / dataset.known_sigma**2
    expected = np.linalg.solve(precision, design.T @ y / dataset.known_sigma**2)
    observed = np.asarray([summary.mean for summary in run.posterior_summaries])
    assert observed == pytest.approx(expected, abs=0.01)


def test_draws_diagnostics_predictive_checks_and_sensitivity_are_exposed(
    completed_run: HMCInferenceRun,
) -> None:
    run = completed_run
    for parameter in ("baseline", "condition_effect"):
        assert len(run.posterior_draws[parameter]) == run.configuration.chains
        assert all(
            len(chain) == run.configuration.draws for chain in run.posterior_draws[parameter]
        )
    assert len(run.chain_diagnostics) == run.configuration.chains
    assert set(run.posterior_correlation) == {"baseline", "condition_effect"}
    check = run.posterior_predictive
    assert check.interval_low < check.observed_group_difference < check.interval_high
    assert 0.05 < check.bayesian_p_value < 0.95
    assert {item.scenario for item in run.scenario_predictions} == {
        "baseline (x=0)",
        "condition (x=1)",
    }
    assert len(run.sensitivity) == 4
    assert max(abs(item.outcome_change) for item in run.sensitivity) < 0.02


def test_posterior_predictive_and_latent_scenarios_match_conjugate_distribution(
    completed_run: HMCInferenceRun,
) -> None:
    run = completed_run
    x = np.asarray(run.dataset.predictor)
    design = np.column_stack((np.ones_like(x), x))
    sigma = run.dataset.known_sigma
    covariance = np.linalg.inv(np.eye(2) + design.T @ design / sigma**2)
    mean = covariance @ (design.T @ np.asarray(run.dataset.outcome) / sigma**2)
    predictive_sd = np.sqrt(covariance[1, 1] + sigma**2 * (1 / (x == 0).sum() + 1 / (x == 1).sum()))
    check = run.posterior_predictive
    assert check.replicated_mean == pytest.approx(mean[1], abs=0.01)
    assert check.interval_low == pytest.approx(mean[1] - 1.959964 * predictive_sd, abs=0.015)
    assert check.interval_high == pytest.approx(mean[1] + 1.959964 * predictive_sd, abs=0.015)
    for scenario, weights in zip(
        run.scenario_predictions, (np.array([1, 0]), np.array([1, 1])), strict=True
    ):
        latent_mean = weights @ mean
        latent_sd = np.sqrt(weights @ covariance @ weights)
        assert scenario.includes_observation_noise is False
        assert scenario.mean == pytest.approx(latent_mean, abs=0.01)
        assert scenario.interval_low == pytest.approx(latent_mean - 1.959964 * latent_sd, abs=0.015)
        assert scenario.interval_high == pytest.approx(
            latent_mean + 1.959964 * latent_sd, abs=0.015
        )


def test_hmc_is_reproducible_for_a_fixed_seed() -> None:
    configuration = HMCConfiguration(chains=2, warmup=100, draws=100, seed=91)
    first = run_hmc_demo(configuration)
    second = run_hmc_demo(configuration)
    assert first.id == second.id
    assert first.posterior_draws == second.posterior_draws
    assert first.diagnostics == second.diagnostics


def test_hmc_configuration_rejects_short_or_unsafe_runs() -> None:
    with pytest.raises(ValidationError):
        HMCConfiguration(chains=1)
    with pytest.raises(ValidationError):
        HMCConfiguration(warmup=20)
    with pytest.raises(ValidationError):
        HMCConfiguration(step_size=2.0)
