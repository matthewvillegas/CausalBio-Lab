# Bayesian inference

## Scope and implementation status

CausalBio Lab has two deliberately separate inference paths:

1. Arbitrary biological investigations return a structured `INELIGIBLE` result. Their literature records and Petri parameters do not provide an approved observation model, identified unknown parameters, priors, likelihood, or diagnostic plan.
2. A narrow, checked-in **synthetic parameter-recovery demonstration** runs real fixed-step Hamiltonian Monte Carlo (HMC) for a fully specified two-parameter linear Gaussian model.

The demonstration is mathematical validation of the inference plumbing. It is not biological evidence, does not infer parameters for the memory or knee-pain packs, and does not make clinical or intervention predictions. NUTS and a production Bayesian framework are not implemented.

## Demonstration model and data

The optional UI starts with the unknown parameters, prior, synthetic observations, posterior estimates, and interval interpretation. It also states why the selected biological investigation is ineligible. Diagnostic warnings are visible with the result; R-hat, ESS, energy diagnostics, traces, sensitivity, and predictive checks are available under **Advanced mathematical details**. Running the demonstration never makes the biological investigation eligible.

The fixture contains 40 synthetic observations: 20 with a binary condition indicator of zero and 20 with a value of one. It was generated once from:

```text
y_i = baseline + condition_effect × x_i + Normal(0, 0.25)
```

The checked-in generating values are `baseline = 0.25` and `condition_effect = 0.55`; the observation standard deviation is treated as known at `0.25`. The provenance explicitly states that the data are not derived from people, animals, publications, or article prose.

The balanced design identifies the intercept and condition coefficient within this model. It does not give either parameter a biological meaning.

## Priors

A prior describes uncertainty about a parameter before conditioning on the modeled observations. The demo uses independent `Normal(0, 1)` priors for both parameters. These are weakly regularizing demonstration priors, not literature-derived or biological priors.

The run returns typed `PriorSpecification` objects with distribution, parameters, and provenance. Sensitivity output also calculates conjugate analytic posterior means under `Normal(0, 0.5)` and `Normal(0, 2)` alternatives and reports each change from the default-prior posterior mean.

A future biological inference model would need prior provenance, unit checks, prior predictive simulation, and sensitivity analyses appropriate to its actual parameterization.

## Likelihood

The likelihood connects parameters to observed data. The implemented likelihood is:

```text
y_i ~ Normal(baseline + condition_effect × x_i, 0.25)
```

It assumes a correct linear mean, independent Gaussian errors, constant known variance, and a balanced binary design. The typed likelihood specification exposes the outcome, distribution, mean expression, known standard deviation, and observation description.

Literature evidence grades are not observations in this likelihood. No prose, citation count, plausibility index, Petri trajectory, or qualitative claim is converted into a pseudo-likelihood.

## Hamiltonian Monte Carlo

HMC augments the parameter vector with simulated momentum and uses Hamiltonian dynamics to propose distant states with less random-walk behavior than a simple random-walk Metropolis algorithm. The implementation uses:

- independent momentum refreshment;
- a fixed Euclidean mass matrix based on the model's posterior precision;
- symplectic leapfrog integration;
- a Metropolis energy correction;
- deterministic, separately spawned random streams per chain.

The default configuration is four chains, 500 warmup iterations, 750 retained draws, eight leapfrog steps, step size `0.55`, and seed `1729`. Configuration bounds prevent one chain, fewer than 100 warmup or retained draws, excessive step sizes, and unbounded requests.

This is genuine HMC, but it is intentionally small and model-specific. It has no adaptive step-size or mass-matrix warmup and is not intended as a replacement for mature samplers.

## NUTS

The No-U-Turn Sampler (NUTS) adaptively chooses trajectory length and is usually preferable to hand-tuned fixed-step HMC for general models. NUTS is **not implemented** in the current repository. Production biological inference should use a maintained backend such as PyMC, NumPyro, or Stan after installation reliability and model needs are reviewed.

## Diagnostics

The HMC run reports:

- rank-normalized split R-hat, taking the maximum of ordinary and median-folded ranks for each parameter;
- rank-normalized split bulk effective sample size (ESS) per parameter and the minimum;
- divergent-transition count using a large energy-error threshold;
- mean acceptance rate;
- per-chain acceptance rate and energy Bayesian fraction of missing information (E-BFMI);
- diagnostic warnings and an overall `COMPLETE` or `DIAGNOSTIC_WARNING` state.

Current warning thresholds are R-hat above 1.01, bulk ESS below 400, any divergence, E-BFMI below 0.3, or mean acceptance outside 0.60–0.99. Passing these checks does not prove that the model is correct; it only removes several common sampling warnings for this run.

Pooled average ranks are transformed with Blom normal scores. ESS uses autocovariances divided by the half-chain length and Geyer's initial positive and monotone paired sequence beginning at lags `(0, 1)`. Antithetic chains can have ESS above their retained draw count; the estimator caps it at `draws × log10(draws)`. Odd-length chains discard the central draw before splitting. These choices follow [Vehtari et al. (2021)](https://doi.org/10.1214/20-BA1221) and are checked against the [Stan diagnostic reference](https://github.com/stan-dev/stan/blob/develop/src/stan/analyze/mcmc/ess.hpp).

Nonfinite or effectively constant chains have undefined convergence diagnostics. The demonstration raises a typed error and the API returns `422`; it never presents those chains as a successful posterior. Small but moving trajectories instead return diagnostic warnings. Tail ESS and quantile Monte Carlo errors are not implemented, so a clean bulk diagnostic is not a claim of reliable tail estimates. E-BFMI is the mean squared successive energy difference divided by sample energy variance, evaluated separately within each retained chain.

### Numerical validation

`test_hmc.py` and `test_hmc_numerics.py` check:

- central finite-difference gradients with unequal prior scales and nonzero prior means;
- momentum-flipped leapfrog reversibility, input immutability, and quadratic energy-error convergence at fixed trajectory duration;
- rejection of deliberately large energy errors, and truthful warnings or failure for poor and resonant tuning;
- analytic Gaussian posterior means, covariance, and correlation under tight and wide priors, multiple trajectory settings, and widely dispersed chain starts;
- sampled predictive intervals and latent scenario intervals against their conjugate Gaussian distributions;
- fixed-seed reproducibility, distinct chain streams, and identity changes when fixture content changes;
- tied ranks, odd lengths, autocorrelation, antithetic draws, split nonstationarity, scale disagreement, and invalid diagnostics;
- independent numerical values from Stan's checked-in Bernoulli draws: bulk ESS `1512.7684` / `1407.5124` and R-hat `1.00073` / `1.006789` for `lp__` / `theta` (see the [fixture provenance](../packages/causalbio-core/tests/fixtures/README.md)).

The default fixture also checks whether its two known generating parameters fall inside the sampled 95% intervals. This is one seeded recovery example, not a repeated-simulation calibration or coverage study. The sampler is tested on an analytically tractable Gaussian with a known precision matrix, not on funnels, multimodal distributions, unknown noise, or biological models.

## Posterior predictive checks

The demo draws replicated differences between the two synthetic groups from the posterior plus the known observation noise. It reports the observed difference, replicated mean, 95% interval, and a Bayesian tail-area value.

This check asks whether the specified model can reproduce one chosen summary of its own synthetic data. It does not validate biology, clinical transportability, the selected discrepancy measure, or all model assumptions.

## Scenario propagation and sensitivity

Posterior draws are propagated to the model's expected response for `x=0` and `x=1`, without observation noise. These are mathematical scenario summaries, not intervention forecasts. The output also includes posterior parameter correlation and prior-scale sensitivity results.

## Identifiability

Identifiability asks whether distinct parameter values imply distinguishable data distributions under the design. The demo's two balanced groups and known noise identify its two regression coefficients. More realistic dynamic models may have weak, practical, or structural non-identifiability even with many observations.

Before enabling inference for a biological investigation, the project requires:

- approved numerical observations with units and provenance;
- explicitly unknown parameters;
- an identifiable model and documented review;
- priors with defensible provenance;
- an explicit likelihood and observation process;
- a supported sampling backend;
- convergence and energy diagnostics;
- prior and posterior predictive checks;
- synthetic recovery, sensitivity, and failure tests.

If these requirements are absent, the correct output is `INELIGIBLE`; there is no random-number or literature-score fallback.

## Why evidence scores are not posterior probabilities

The evidence plausibility index is a deterministic weighted rubric for comparing graph paths. It has no generative data model, likelihood, calibrated prior, or posterior normalization. Therefore an index of 80 does not mean an 80% chance that a mechanism is true, that an intervention will work, or that an outcome will occur.

Only the bounded synthetic model produces posterior distributions, and those distributions answer only the question defined by that synthetic likelihood and prior.
