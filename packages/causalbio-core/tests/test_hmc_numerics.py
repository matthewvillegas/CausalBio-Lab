"""Independent numerical identities and adverse cases for the educational HMC."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from causalbio.domain.enums import InferenceState
from causalbio.domain.models import HMCConfiguration
from causalbio.inference import hmc
from causalbio.inference.hmc import FloatArray


def gaussian_problem(prior_scale: float = 1.0) -> dict[str, Any]:
    dataset = hmc.load_hmc_demo_dataset()
    design = hmc._design_matrix(dataset)
    prior_sd = np.full(2, prior_scale)
    precision = design.T @ design / dataset.known_sigma**2 + np.diag(1 / prior_sd**2)
    return {
        "design": design,
        "outcome": np.asarray(dataset.outcome),
        "sigma": dataset.known_sigma,
        "prior_mean": np.zeros(2),
        "prior_sd": prior_sd,
        "mass_inverse": np.linalg.inv(precision),
    }


def test_potential_gradient_matches_central_finite_differences() -> None:
    problem = gaussian_problem(0.15)
    problem.pop("mass_inverse")
    problem["prior_mean"] = np.array([-0.2, 0.1])
    problem["prior_sd"] = np.array([0.15, 2.5])
    position = np.array([0.6, -0.1])
    _, gradient = hmc._potential_and_gradient(position, **problem)
    numerical = []
    for dimension in range(2):
        displacement = np.eye(2)[dimension] * 1e-6
        upper, _ = hmc._potential_and_gradient(position + displacement, **problem)
        lower, _ = hmc._potential_and_gradient(position - displacement, **problem)
        numerical.append((upper - lower) / 2e-6)
    np.testing.assert_allclose(gradient, numerical, rtol=1e-8, atol=1e-7)


def test_momentum_flipped_leapfrog_is_reversible_and_does_not_mutate_inputs() -> None:
    problem = gaussian_problem()
    position = np.array([0.1, 0.7])
    momentum = np.array([2.0, -1.5])
    proposal, flipped = hmc._leapfrog(position, momentum, steps=8, step_size=0.2, **problem)
    recovered, recovered_momentum = hmc._leapfrog(
        proposal, flipped, steps=8, step_size=0.2, **problem
    )
    np.testing.assert_allclose(recovered, position, atol=1e-13)
    np.testing.assert_allclose(recovered_momentum, momentum, atol=1e-12)
    np.testing.assert_array_equal(position, [0.1, 0.7])
    np.testing.assert_array_equal(momentum, [2.0, -1.5])


def test_leapfrog_energy_error_converges_quadratically_at_fixed_duration() -> None:
    problem = gaussian_problem()
    position = np.array([0.1, 0.7])
    momentum = np.array([2.0, -1.5])
    initial = hmc._hamiltonian(position, momentum, **problem)
    errors = []
    for steps, step_size in ((4, 0.3), (8, 0.15), (16, 0.075)):
        proposal, flipped = hmc._leapfrog(
            position, momentum, steps=steps, step_size=step_size, **problem
        )
        errors.append(abs(hmc._hamiltonian(proposal, flipped, **problem) - initial))
    assert errors[0] / errors[1] == pytest.approx(4.0, rel=0.08)
    assert errors[1] / errors[2] == pytest.approx(4.0, rel=0.08)


def test_metropolis_rejects_large_energy_error_and_keeps_the_previous_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unstable_proposal(
        position: FloatArray, momentum: FloatArray, **_: Any
    ) -> tuple[FloatArray, FloatArray]:
        return position + 1_000.0, momentum

    monkeypatch.setattr(hmc, "_leapfrog", unstable_proposal)
    problem = gaussian_problem()
    mass = np.linalg.inv(problem.pop("mass_inverse"))
    initial = np.array([0.25, 0.55])
    config = HMCConfiguration(chains=2, warmup=100, draws=100)
    result = hmc._sample_chain(
        rng=np.random.default_rng(12), initial_position=initial, config=config, mass=mass, **problem
    )
    assert result.acceptance_rate == 0.0
    assert result.divergences == config.draws
    np.testing.assert_allclose(result.draws, np.tile(initial, (config.draws, 1)))


@pytest.mark.parametrize(
    "prior_scale,step_size,leapfrog_steps", [(0.05, 0.3, 5), (10.0, 0.55, 8), (1.0, 0.15, 12)]
)
def test_sampling_recovers_gaussian_covariance_from_dispersed_starts_and_prior_scales(
    prior_scale: float, step_size: float, leapfrog_steps: int
) -> None:
    problem = gaussian_problem(prior_scale)
    covariance = problem.pop("mass_inverse")
    precision = np.linalg.inv(covariance)
    expected_mean = covariance @ (problem["design"].T @ problem["outcome"] / problem["sigma"] ** 2)
    config = HMCConfiguration(
        chains=4, warmup=250, draws=700, step_size=step_size, leapfrog_steps=leapfrog_steps
    )
    chains = [
        hmc._sample_chain(
            rng=np.random.default_rng(seed),
            initial_position=np.array([sign * 8.0, -sign * 8.0]),
            config=config,
            mass=precision,
            **problem,
        ).draws
        for seed, sign in ((21, -1), (22, 1), (23, -2), (24, 2))
    ]
    draws = np.concatenate(chains)
    np.testing.assert_allclose(draws.mean(axis=0), expected_mean, atol=0.012)
    np.testing.assert_allclose(np.cov(draws, rowvar=False), covariance, rtol=0.18, atol=0.0002)
    expected_correlation = covariance[0, 1] / np.sqrt(covariance[0, 0] * covariance[1, 1])
    correlation = np.asarray(np.corrcoef(draws, rowvar=False), dtype=np.float64)
    assert correlation[0, 1] == pytest.approx(expected_correlation, abs=0.065)
    assert not np.array_equal(chains[0], chains[1])


def test_rank_bulk_ess_matches_independent_stan_posterior_reference() -> None:
    with np.load(Path(__file__).parent / "fixtures" / "stan_bernoulli_diagnostics.npz") as fixture:
        assert hmc._bulk_ess(fixture["lp"]) == pytest.approx(1512.7684, abs=1e-4)
        assert hmc._bulk_ess(fixture["theta"]) == pytest.approx(1407.5124, abs=1e-4)


def test_rank_folded_rhat_matches_independent_stan_posterior_reference() -> None:
    with np.load(Path(__file__).parent / "fixtures" / "stan_bernoulli_diagnostics.npz") as fixture:
        assert hmc._split_r_hat(fixture["lp"]) == pytest.approx(1.00073, abs=1e-5)
        assert hmc._split_r_hat(fixture["theta"]) == pytest.approx(1.006789, abs=1e-5)


def test_bulk_ess_handles_autocorrelation_antithetic_draws_and_monotone_transforms() -> None:
    rng = np.random.default_rng(189)
    draws = rng.normal(size=(4, 4000))
    for coefficient in (0.8, -0.6):
        samples = draws.copy()
        for index in range(1, samples.shape[1]):
            samples[:, index] += coefficient * samples[:, index - 1]
        ess = hmc._bulk_ess(samples)
        theoretical = samples.size * (1 - coefficient) / (1 + coefficient)
        assert ess == pytest.approx(theoretical, rel=0.22)
        assert hmc._bulk_ess(np.exp(samples)) == pytest.approx(ess, rel=1e-12)
    assert hmc._bulk_ess(draws) == pytest.approx(draws.size, rel=0.15)


def test_rank_rhat_detects_scale_mismatch_and_split_nonstationarity() -> None:
    rng = np.random.default_rng(12)
    samples = rng.normal(size=(4, 2000))
    assert hmc._split_r_hat(samples) < 1.01
    scale_mismatch = samples * np.array([1, 1, 5, 5])[:, None]
    assert hmc._split_r_hat(scale_mismatch) > 1.1
    drifting = samples.copy()
    drifting[:, 1000:] += 5
    assert hmc._split_r_hat(drifting) > 1.2
    assert hmc._bulk_ess(drifting) < 100


def test_diagnostics_handle_ties_odd_lengths_and_reject_nonfinite_or_constant_chains() -> None:
    rng = np.random.default_rng(321)
    odd = np.round(rng.normal(size=(4, 1001)), 1)
    omitted_middle = np.concatenate((odd[:, :500], odd[:, 501:]), axis=1)
    assert hmc._bulk_ess(odd) == pytest.approx(hmc._bulk_ess(omitted_middle))
    assert hmc._split_r_hat(odd) == pytest.approx(hmc._split_r_hat(omitted_middle))
    for bad in (
        np.ones((4, 100)),
        np.full((4, 100), np.nan),
        np.full((4, 100), np.inf),
        np.zeros((1, 4)),
    ):
        assert np.isnan(hmc._bulk_ess(bad))
        assert np.isnan(hmc._split_r_hat(bad))


def test_energy_bfmi_matches_squared_increment_estimator_and_detects_slow_energy_motion() -> None:
    energy = np.array([1.0, 2.0, 1.0, 4.0])
    assert hmc._energy_bfmi(energy) == pytest.approx((11 / 3) / 2)
    assert hmc._energy_bfmi(np.linspace(0, 1, 100)) < 0.01
    assert hmc._energy_bfmi(np.ones(100)) == 0


def test_tiny_steps_warn_and_resonant_nonmoving_chains_fail_honestly() -> None:
    poor = hmc.run_hmc_demo(
        HMCConfiguration(chains=2, warmup=100, draws=100, step_size=0.0001, leapfrog_steps=1)
    )
    assert poor.state is InferenceState.DIAGNOSTIC_WARNING
    assert poor.diagnostics.r_hat_max is not None and poor.diagnostics.r_hat_max > 1.01
    assert poor.diagnostics.ess_bulk_min is not None and poor.diagnostics.ess_bulk_min < 400
    with pytest.raises(hmc.HMCInferenceError, match="constant chains"):
        hmc.run_hmc_demo(
            HMCConfiguration(chains=2, warmup=100, draws=100, step_size=1, leapfrog_steps=6)
        )


def test_run_identity_includes_dataset_content_and_each_chain_uses_an_independent_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = HMCConfiguration(chains=2, warmup=100, draws=100, seed=567)
    original = hmc.run_hmc_demo(config)
    draws = original.posterior_draws["baseline"]
    assert draws[0] != draws[1]
    dataset = original.dataset
    modified = dataset.model_copy(
        update={"outcome": tuple(value + 0.1 for value in dataset.outcome)}
    )
    monkeypatch.setattr(hmc, "load_hmc_demo_dataset", lambda: modified)
    changed = hmc.run_hmc_demo(config)
    assert changed.dataset.id == original.dataset.id
    assert changed.id != original.id
    assert changed.posterior_summaries[0].mean > original.posterior_summaries[0].mean
