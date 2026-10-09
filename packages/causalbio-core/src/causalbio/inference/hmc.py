"""A narrow, auditable Hamiltonian Monte Carlo parameter-recovery demo.

This module intentionally does not turn literature prose or arbitrary investigation
graphs into numerical data.  It samples a fully specified two-parameter linear
Gaussian model against a checked-in synthetic fixture whose generating values are
known.  The implementation is conventional Euclidean-metric HMC: independent
momentum refreshment, symplectic leapfrog integration, and a Metropolis correction.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray
from scipy.special import ndtri
from scipy.stats import rankdata

from causalbio import __version__
from causalbio.domain.enums import InferenceState
from causalbio.domain.identifiers import stable_uuid
from causalbio.domain.models import (
    BayesianParameter,
    HMCChainDiagnostics,
    HMCConfiguration,
    HMCDemoDataset,
    HMCInferenceRun,
    InferenceDiagnostics,
    LikelihoodSpecification,
    PosteriorPredictiveCheck,
    PosteriorSummary,
    PriorSpecification,
    ScenarioPrediction,
    SensitivityResult,
)

FloatArray = NDArray[np.float64]
_PARAMETER_NAMES = ("baseline", "condition_effect")
_MODEL_VERSION = "linear-gaussian-hmc-v3"


class HMCInferenceError(RuntimeError):
    """Raised when the bounded HMC demonstration cannot run faithfully."""


@dataclass(frozen=True, slots=True)
class _ChainResult:
    draws: FloatArray
    acceptance_rate: float
    divergences: int
    energies: FloatArray


def _workspace_root() -> Path:
    configured = os.getenv("CAUSALBIO_WORKSPACE_ROOT")
    if configured:
        return Path(configured).resolve()
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise HMCInferenceError("Could not locate the CausalBio Lab workspace root")


def load_hmc_demo_dataset(path: Path | None = None) -> HMCDemoDataset:
    """Load and validate the explicit synthetic inference fixture."""

    source = path or _workspace_root() / "data" / "demo" / "inference" / "linear-response.json"
    try:
        payload = cast(dict[str, Any], json.loads(source.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise HMCInferenceError(f"Could not load HMC demo data from {source}") from exc
    return HMCDemoDataset.model_validate(payload)


def _design_matrix(dataset: HMCDemoDataset) -> FloatArray:
    predictor = np.asarray(dataset.predictor, dtype=np.float64)
    return np.column_stack((np.ones_like(predictor), predictor))


def _potential_and_gradient(
    position: FloatArray,
    design: FloatArray,
    outcome: FloatArray,
    sigma: float,
    prior_mean: FloatArray,
    prior_sd: FloatArray,
) -> tuple[float, FloatArray]:
    prior_residual = (position - prior_mean) / prior_sd
    observation_residual = (outcome - design @ position) / sigma
    potential = 0.5 * float(prior_residual @ prior_residual)
    potential += 0.5 * float(observation_residual @ observation_residual)
    gradient = (position - prior_mean) / np.square(prior_sd)
    gradient += design.T @ (design @ position - outcome) / (sigma * sigma)
    return potential, np.asarray(gradient, dtype=np.float64)


def _hamiltonian(
    position: FloatArray,
    momentum: FloatArray,
    *,
    mass_inverse: FloatArray,
    design: FloatArray,
    outcome: FloatArray,
    sigma: float,
    prior_mean: FloatArray,
    prior_sd: FloatArray,
) -> float:
    potential, _ = _potential_and_gradient(position, design, outcome, sigma, prior_mean, prior_sd)
    kinetic = 0.5 * float(momentum @ mass_inverse @ momentum)
    return potential + kinetic


def _leapfrog(
    position: FloatArray,
    momentum: FloatArray,
    *,
    steps: int,
    step_size: float,
    mass_inverse: FloatArray,
    design: FloatArray,
    outcome: FloatArray,
    sigma: float,
    prior_mean: FloatArray,
    prior_sd: FloatArray,
) -> tuple[FloatArray, FloatArray]:
    proposed_position = position.copy()
    proposed_momentum = momentum.copy()
    _, gradient = _potential_and_gradient(
        proposed_position, design, outcome, sigma, prior_mean, prior_sd
    )
    proposed_momentum -= 0.5 * step_size * gradient
    for step in range(steps):
        proposed_position += step_size * (mass_inverse @ proposed_momentum)
        _, gradient = _potential_and_gradient(
            proposed_position, design, outcome, sigma, prior_mean, prior_sd
        )
        if step < steps - 1:
            proposed_momentum -= step_size * gradient
    proposed_momentum -= 0.5 * step_size * gradient
    return proposed_position, -proposed_momentum


def _sample_chain(
    *,
    rng: np.random.Generator,
    initial_position: FloatArray,
    config: HMCConfiguration,
    mass: FloatArray,
    design: FloatArray,
    outcome: FloatArray,
    sigma: float,
    prior_mean: FloatArray,
    prior_sd: FloatArray,
) -> _ChainResult:
    mass_inverse = np.asarray(np.linalg.inv(mass), dtype=np.float64)
    mass_cholesky = np.asarray(np.linalg.cholesky(mass), dtype=np.float64)
    position = initial_position.copy()
    kept = np.empty((config.draws, position.size), dtype=np.float64)
    energies = np.empty(config.draws, dtype=np.float64)
    accepted = 0
    divergences = 0
    total_iterations = config.warmup + config.draws

    for iteration in range(total_iterations):
        momentum = mass_cholesky @ rng.normal(size=position.size)
        current_energy = _hamiltonian(
            position,
            momentum,
            mass_inverse=mass_inverse,
            design=design,
            outcome=outcome,
            sigma=sigma,
            prior_mean=prior_mean,
            prior_sd=prior_sd,
        )
        proposed_position, proposed_momentum = _leapfrog(
            position,
            momentum,
            steps=config.leapfrog_steps,
            step_size=config.step_size,
            mass_inverse=mass_inverse,
            design=design,
            outcome=outcome,
            sigma=sigma,
            prior_mean=prior_mean,
            prior_sd=prior_sd,
        )
        proposed_energy = _hamiltonian(
            proposed_position,
            proposed_momentum,
            mass_inverse=mass_inverse,
            design=design,
            outcome=outcome,
            sigma=sigma,
            prior_mean=prior_mean,
            prior_sd=prior_sd,
        )
        energy_error = proposed_energy - current_energy
        divergent = not np.isfinite(energy_error) or abs(energy_error) > 100.0
        if divergent:
            divergences += int(iteration >= config.warmup)
        log_acceptance = min(0.0, -energy_error) if np.isfinite(energy_error) else -np.inf
        was_accepted = np.log(rng.uniform()) < log_acceptance
        if was_accepted:
            position = proposed_position
        if iteration >= config.warmup:
            draw_index = iteration - config.warmup
            kept[draw_index] = position
            energies[draw_index] = current_energy
            accepted += int(was_accepted)

    return _ChainResult(
        draws=kept,
        acceptance_rate=accepted / config.draws,
        divergences=divergences,
        energies=energies,
    )


def _split_chains(samples: FloatArray) -> FloatArray:
    half = samples.shape[1] // 2
    # Discard the middle draw for odd chain lengths, preserving equal half lengths.
    return np.concatenate((samples[:, :half], samples[:, -half:]), axis=0)


def _valid_diagnostic_draws(samples: FloatArray) -> bool:
    if samples.ndim != 2 or samples.shape[0] < 2 or samples.shape[1] < 8:
        return False
    if not np.all(np.isfinite(samples)):
        return False
    # Roundoff-sized jitter in a stuck chain is not posterior exploration.
    tolerance = 100 * np.finfo(np.float64).eps * np.maximum(1.0, np.max(np.abs(samples), axis=1))
    return bool(np.all(np.ptp(samples, axis=1) > tolerance))


def _rank_normalize(samples: FloatArray) -> FloatArray:
    """Pooled average ranks and Blom normal scores (Vehtari et al., 2021)."""

    ranks = rankdata(samples, method="average").reshape(samples.shape)
    return np.asarray(ndtri((ranks - 0.375) / (samples.size + 0.25)), dtype=np.float64)


def _r_hat(split: FloatArray) -> float:
    draws = split.shape[1]
    within = float(np.mean(np.var(split, axis=1, ddof=1)))
    if within <= 0:
        return float("nan")
    between = draws * float(np.var(np.mean(split, axis=1), ddof=1))
    variance = ((draws - 1) / draws) * within + between / draws
    return float(np.sqrt(variance / within))


def _split_r_hat(samples: FloatArray) -> float:
    """Maximum rank-normalized and folded rank-normalized split R-hat."""

    if not _valid_diagnostic_draws(samples):
        return float("nan")
    split = _split_chains(samples)
    bulk = _r_hat(_rank_normalize(split))
    folded = _r_hat(_rank_normalize(np.abs(split - np.median(split))))
    return max(bulk, folded)


def _bulk_ess(samples: FloatArray) -> float:
    """Rank-normalized split bulk ESS with Geyer positive/monotone lag pairs.

    See Vehtari et al. (2021), doi:10.1214/20-BA1221, and Stan's ess.hpp.
    Lag pairs start at (0, 1), not (1, 2). Biased autocovariances divide by
    the entire half-chain length, avoiding unstable large-lag estimates.
    """

    if not _valid_diagnostic_draws(samples):
        return float("nan")
    ranked = _rank_normalize(_split_chains(samples))
    chains, draws = ranked.shape
    chain_means = np.mean(ranked, axis=1)
    centered = ranked - chain_means[:, None]
    fft_length = 1 << (2 * draws - 1).bit_length()
    transformed = np.fft.rfft(centered, n=fft_length, axis=1)
    autocovariance = np.fft.irfft(transformed * np.conjugate(transformed), n=fft_length, axis=1)
    mean_autocovariance = np.mean(autocovariance[:, :draws] / draws, axis=0)
    within = float(mean_autocovariance[0] * draws / (draws - 1))
    variance_plus = within * (draws - 1) / draws + float(np.var(chain_means, ddof=1))
    correlations = 1.0 - (within - mean_autocovariance) / variance_plus
    correlations[0] = 1.0

    paired_sum = 0.0
    previous_pair = float("inf")
    antithetic_tail = 0.0
    for lag in range(0, draws - 1, 2):
        pair = float(correlations[lag] + correlations[lag + 1])
        if pair <= 0:
            # Retain the final positive even lag for antithetic chains.
            antithetic_tail = max(0.0, float(correlations[lag]))
            break
        pair = min(pair, previous_pair)
        paired_sum += pair
        previous_pair = pair
    total = chains * draws
    autocorrelation_time = max(1.0 / np.log10(total), -1.0 + 2.0 * paired_sum + antithetic_tail)
    return float(total / autocorrelation_time)


def _energy_bfmi(energies: FloatArray) -> float:
    variance = float(np.var(energies, ddof=1))
    if variance <= 0:
        return 0.0
    return float(np.mean(np.square(np.diff(energies))) / variance)


def _posterior_summary(name: str, values: FloatArray) -> PosteriorSummary:
    low, median, high = np.quantile(values, (0.025, 0.5, 0.975))
    return PosteriorSummary(
        parameter=name,
        mean=float(np.mean(values)),
        median=float(median),
        interval_low=float(low),
        interval_high=float(high),
        interval_level=0.95,
    )


def _analytic_posterior_mean(
    design: FloatArray,
    outcome: FloatArray,
    sigma: float,
    prior_sd: float,
) -> FloatArray:
    precision = np.eye(design.shape[1]) / (prior_sd * prior_sd)
    precision += design.T @ design / (sigma * sigma)
    return np.asarray(
        np.linalg.solve(precision, design.T @ outcome / (sigma * sigma)), dtype=np.float64
    )


def run_hmc_demo(configuration: HMCConfiguration | None = None) -> HMCInferenceRun:
    """Run the reproducible synthetic HMC example and calculate diagnostics."""

    config = configuration or HMCConfiguration()
    dataset = load_hmc_demo_dataset()
    design = _design_matrix(dataset)
    outcome = np.asarray(dataset.outcome, dtype=np.float64)
    prior_mean = np.zeros(2, dtype=np.float64)
    prior_sd = np.ones(2, dtype=np.float64)
    sigma = dataset.known_sigma
    posterior_precision = np.diag(1.0 / np.square(prior_sd))
    posterior_precision += design.T @ design / (sigma * sigma)

    chains: list[_ChainResult] = []
    seed_sequence = np.random.SeedSequence(config.seed)
    for chain_index, child_seed in enumerate(seed_sequence.spawn(config.chains)):
        rng = np.random.default_rng(child_seed)
        initial = rng.normal(loc=0.0, scale=0.75, size=2)
        # A deterministic offset keeps starts overdispersed even for an unusually similar seed draw.
        initial += (chain_index - (config.chains - 1) / 2) * np.array([0.15, -0.15])
        chains.append(
            _sample_chain(
                rng=rng,
                initial_position=initial,
                config=config,
                mass=posterior_precision,
                design=design,
                outcome=outcome,
                sigma=sigma,
                prior_mean=prior_mean,
                prior_sd=prior_sd,
            )
        )

    stacked = np.stack([chain.draws for chain in chains])
    r_hats = {
        name: _split_r_hat(stacked[:, :, index]) for index, name in enumerate(_PARAMETER_NAMES)
    }
    effective_sizes = {
        name: _bulk_ess(stacked[:, :, index]) for index, name in enumerate(_PARAMETER_NAMES)
    }
    if not all(np.isfinite(value) for value in (*r_hats.values(), *effective_sizes.values())):
        raise HMCInferenceError(
            "Sampling produced nonfinite or effectively constant chains; convergence diagnostics "
            "are undefined. No posterior result is available for this tuning configuration."
        )
    flattened = stacked.reshape(-1, stacked.shape[-1])
    summaries = tuple(
        _posterior_summary(name, flattened[:, index]) for index, name in enumerate(_PARAMETER_NAMES)
    )

    chain_diagnostics = tuple(
        HMCChainDiagnostics(
            chain=index + 1,
            acceptance_rate=chain.acceptance_rate,
            divergences=chain.divergences,
            energy_bfmi=_energy_bfmi(chain.energies),
        )
        for index, chain in enumerate(chains)
    )
    divergences = sum(item.divergences for item in chain_diagnostics)
    acceptance_rate = float(np.mean([item.acceptance_rate for item in chain_diagnostics]))
    energy_bfmi_min = min(item.energy_bfmi for item in chain_diagnostics)
    warnings: list[str] = []
    if max(r_hats.values()) > 1.01:
        warnings.append("At least one rank-normalized folded split R-hat exceeds 1.01.")
    if min(effective_sizes.values()) < 400:
        warnings.append("At least one bulk effective sample size is below 400.")
    if divergences:
        warnings.append("Divergent transitions were detected.")
    if energy_bfmi_min < 0.3:
        warnings.append("At least one chain has E-BFMI below 0.3.")
    if not 0.6 <= acceptance_rate <= 0.99:
        warnings.append("The mean acceptance rate falls outside the expected 0.60-0.99 range.")
    state = InferenceState.COMPLETE if not warnings else InferenceState.DIAGNOSTIC_WARNING
    diagnostics = InferenceDiagnostics(
        r_hat_max=max(r_hats.values()),
        ess_bulk_min=min(effective_sizes.values()),
        divergences=divergences,
        acceptance_rate=acceptance_rate,
        energy_bfmi_min=energy_bfmi_min,
        parameter_r_hat=r_hats,
        parameter_ess_bulk=effective_sizes,
        warnings=tuple(warnings),
    )

    predictive_rng = np.random.default_rng(config.seed + 100_003)
    group_counts = np.bincount(np.asarray(dataset.predictor, dtype=np.int64), minlength=2)
    observed_difference = float(
        outcome[np.asarray(dataset.predictor) == 1].mean()
        - outcome[np.asarray(dataset.predictor) == 0].mean()
    )
    difference_noise_sd = sigma * np.sqrt(1 / group_counts[0] + 1 / group_counts[1])
    replicated_differences = flattened[:, 1] + predictive_rng.normal(
        0.0, difference_noise_sd, flattened.shape[0]
    )
    predictive_low, predictive_high = np.quantile(replicated_differences, (0.025, 0.975))
    posterior_predictive = PosteriorPredictiveCheck(
        observed_group_difference=observed_difference,
        replicated_mean=float(np.mean(replicated_differences)),
        interval_low=float(predictive_low),
        interval_high=float(predictive_high),
        interval_level=0.95,
        bayesian_p_value=float(np.mean(replicated_differences >= observed_difference)),
        interpretation=(
            "The observed group difference is compared with replicated differences from the "
            "specified linear-Gaussian model; this is a model check, not evidence from biology."
        ),
    )

    baseline = flattened[:, 0]
    condition = flattened[:, 0] + flattened[:, 1]
    scenario_predictions = tuple(
        ScenarioPrediction(
            scenario=name,
            mean=float(np.mean(values)),
            interval_low=float(np.quantile(values, 0.025)),
            interval_high=float(np.quantile(values, 0.975)),
            interval_level=0.95,
            includes_observation_noise=False,
        )
        for name, values in (("baseline (x=0)", baseline), ("condition (x=1)", condition))
    )

    default_mean = _analytic_posterior_mean(design, outcome, sigma, 1.0)
    sensitivity: list[SensitivityResult] = []
    for prior_scale in (0.5, 2.0):
        alternate_mean = _analytic_posterior_mean(design, outcome, sigma, prior_scale)
        for index, name in enumerate(_PARAMETER_NAMES):
            change = float(alternate_mean[index] - default_mean[index])
            sensitivity.append(
                SensitivityResult(
                    parameter=name,
                    perturbation=f"Normal(0, {prior_scale:g}) prior; conjugate analytic refit",
                    outcome_change=change,
                    interpretation=(
                        "Change in posterior mean relative to the sampling model's Normal(0, 1) "
                        "prior; small shifts indicate limited prior sensitivity in this fixture."
                    ),
                )
            )

    recovery = {
        summary.parameter: summary.interval_low
        <= dataset.true_parameters[summary.parameter]
        <= summary.interval_high
        for summary in summaries
    }
    correlation_matrix = np.asarray(
        np.atleast_2d(np.corrcoef(flattened, rowvar=False)), dtype=np.float64
    )
    correlation = {
        row_name: {
            column_name: float(correlation_matrix[row, column])
            for column, column_name in enumerate(_PARAMETER_NAMES)
        }
        for row, row_name in enumerate(_PARAMETER_NAMES)
    }
    posterior_draws = {
        name: tuple(tuple(float(value) for value in chain[:, index]) for chain in stacked)
        for index, name in enumerate(_PARAMETER_NAMES)
    }
    run_key = json.dumps(
        {
            "configuration": config.model_dump(mode="json"),
            "dataset": dataset.model_dump(mode="json"),
        },
        sort_keys=True,
    )
    return HMCInferenceRun(
        id=stable_uuid("hmc-demo-run", f"{_MODEL_VERSION}:{dataset.id}:{run_key}"),
        state=state,
        model_name="Two-group linear Gaussian parameter-recovery model",
        model_version=_MODEL_VERSION,
        dataset=dataset,
        parameters=(
            BayesianParameter(
                name="baseline",
                description="Expected normalized outcome when the condition indicator is zero.",
                units="normalized outcome units",
            ),
            BayesianParameter(
                name="condition_effect",
                description="Additive change in expected outcome when the condition indicator is one.",
                units="normalized outcome units",
            ),
        ),
        priors=tuple(
            PriorSpecification(
                parameter=name,
                distribution="Normal",
                parameters={"mean": 0.0, "standard_deviation": 1.0},
                provenance=(
                    "Weakly regularizing demonstration prior chosen before observing this fixed "
                    "fixture; not a biological prior."
                ),
            )
            for name in _PARAMETER_NAMES
        ),
        likelihood=LikelihoodSpecification(
            distribution="Normal",
            outcome="normalized_response",
            parameters={
                "mean": "baseline + condition_effect * condition",
                "standard_deviation": f"{sigma:g} (known)",
            },
            observations_description=(
                "Forty synthetic observations: 20 at condition=0 and 20 at condition=1."
            ),
        ),
        configuration=config,
        posterior_summaries=summaries,
        diagnostics=diagnostics,
        chain_diagnostics=chain_diagnostics,
        posterior_draws=posterior_draws,
        posterior_correlation=correlation,
        posterior_predictive=posterior_predictive,
        scenario_predictions=scenario_predictions,
        sensitivity=tuple(sensitivity),
        recovery=recovery,
        assumptions=(
            "The linear mean structure is correctly specified for the generated fixture.",
            "Observation errors are independent, Gaussian, homoscedastic, and have known sigma=0.25.",
            "Both parameters are identifiable under the balanced two-group design.",
            "The full posterior precision matrix is used as a fixed Euclidean HMC mass matrix.",
        ),
        limitations=(
            "All observations are synthetic and carry no empirical biological or clinical meaning.",
            "Known observation noise avoids estimating a third parameter and narrows the demonstration.",
            "Fixed-step HMC is educational; production work should use a mature NUTS implementation.",
            "Bulk ESS and rank-normalized folded split R-hat do not certify tail accuracy; tail ESS is not reported.",
            "Scenario propagation shows the mathematical model only and is not an intervention forecast.",
        ),
        software_version=__version__,
    )
