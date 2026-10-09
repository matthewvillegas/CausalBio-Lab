# Petri nets

## Scope and implementation status

CausalBio Lab includes an executable engine for curated discrete and continuous Petri nets. Both bundled domain packs contain one model. The engine supports transition enabling and firing, deadlock checks, bounded breadth-first reachability, and deterministic continuous ODE simulations for constant and mass-action rate laws.

Stochastic simulation, automatic mechanism-graph-to-Petri conversion, delays, and executable Hill rate laws are not implemented. The bundled parameters are synthetic educational values and are not fitted biological or clinical predictions.

## Places, tokens, and state

The default UI calls this **Pathway simulation**. Controls come from each model's declared scenarios and output place rather than pack-specific frontend branches. A model may omit scenarios or the pack may omit the model entirely; both states have an explanation instead of an unusable run button. Comparisons retain their submitted settings, cache the baseline for those settings, and mark results stale when controls change. **What changed?** is derived from returned trajectories; the model definition remains available under **View Petri-net model**. An accessible values table accompanies the chart.

A `PetriPlace` represents a modeled state quantity such as an input, activated process, accumulated signal, or recovery state. Each place declares:

- a stable UUID and name;
- a biological description and representation;
- units and compartment;
- valid minimum and maximum;
- an initial value within that range.

In a discrete interpretation, the marking assigns token values to places. The implementation uses nonnegative floating-point values rather than enforcing integer-only tokens. In the continuous interpretation, the same values are state variables integrated over time.

Places are abstractions. A value labeled “normalized activity” is not automatically a molecule count, concentration, or clinical scale. Units and interpretation must be stated by each curated model.

## Transitions

A `PetriTransition` represents a biological event. It declares a UUID, event description, rate law, nonnegative parameters, evidence UUIDs, and assumptions. Every transition must have at least one state-changing input or output arc.

Transitions do not inherit causality or kinetics from a knowledge-graph edge. A curator must explicitly define the executable model, stoichiometry, rate law, parameters, and assumptions.

## Arc semantics

Four arc types are implemented:

- **Input:** requires at least `max(weight, threshold)` in discrete mode and subtracts its weight when the transition fires. In a continuous mass-action law, its weight is also the kinetic order.
- **Output:** adds its weight to the connected place.
- **Read:** requires the place value to reach a threshold but does not consume it.
- **Inhibitory:** disables the transition when the place reaches or exceeds a threshold and does not consume the place.

For read and inhibitory arcs, a positive explicit `threshold` takes precedence; otherwise the arc weight is the threshold. Input and output weights form the stoichiometric vector. Model validation rejects unknown references, duplicate arc/type combinations, nonfinite values, negative place minima, invalid bounds, missing state-changing arcs, and unsupported rate laws.

## Discrete execution

A transition is enabled only when:

- every input requirement is met;
- every read threshold is met;
- no inhibitory threshold is met;
- firing would keep every affected place within its declared range.

Firing returns a new marking and does not mutate the caller's mapping. Attempting to fire a disabled transition raises a typed error. Enabled transitions are returned in stable UUID order, and a marking with no enabled transition is reported as deadlocked.

## Reachability

The engine explores a small discrete state space using deterministic breadth-first search. Callers set `max_depth` and `max_states`; discovered markings, transition edges, and deadlocks are returned in stable order.

The `truncated` flag is essential. It becomes true when depth or state limits prevent exhaustive exploration. A truncated result is not a proof that the model is bounded, live, safe, or complete. Even an exhaustive result for one finite initial marking does not validate the biological abstraction.

## Continuous execution

Continuous models are translated to an ODE system:

```text
d state / dt = stoichiometric matrix × transition-rate vector
```

The system is integrated with SciPy `solve_ivp` using RK45, fixed output times, relative tolerance `1e-8`, absolute tolerance `1e-10`, and a maximum step based on the requested duration and output count. Simulation duration is limited to 1,000 model-time units and output to 5,000 steps by schema validation.

Supported rates are:

- **constant:** `rate`;
- **mass action:** `rate_constant × product(input_value ** input_weight)`.

Read and inhibitory arcs act as hard gates in continuous mode. Rates are stopped at declared state boundaries so a transition does not push a bounded place farther outside its range. Final numerical trajectories are checked for success, shape, and finite values and constrained to declared bounds when necessary; a warning is emitted if constraint was required.

An input arc still requires a positive substrate when matching input and output arcs cancel its net stoichiometry. This prevents a constant-rate catalytic self-loop from producing output from an empty prerequisite state. Continuous input weights are kinetic orders and stoichiometric coefficients, rather than the discrete token availability threshold.

The solver stops with a typed error after 100,000 derivative evaluations. Discontinuous hard gates can chatter, and stiff kinetics can exhaust this budget; no partial trajectory is returned as complete. Boundary clipping can introduce small conservation error near hard limits, and RK45 does not implement exact event-driven constraint handling. These are documented limitations, not fitted biological effects.

Simulation IDs are derived deterministically from the complete model content and parameter configuration, so a changed rate cannot reuse an old run identity even if a curator forgets to bump the model version. Results record software version, model version, scenario, seed, time points, trajectories, transition activities, summaries, and warnings. The current ODE solver is deterministic, so the seed is recorded for reproducibility and future stochastic extensions but does not introduce randomness into continuous execution.

## Numerical validation

`test_petri.py` compares execution with independent analytic solutions and conservation laws:

- constant production and first-order exponential decay;
- reversible `A ⇌ B` mass action, conserved `A + B`, equilibrium ratio, and balanced equilibrium flux;
- weighted `2A → B`, conserved `A + 2B` in continuous trajectories and exhaustive discrete reachable states, and its rational decay solution;
- an open production–degradation system approaching its analytic equilibrium;
- read and inhibitory gates switching when a decaying modifier crosses a known threshold;
- upper and lower bounds, an empty catalytic self-loop, and an explicit solver-budget failure.

Existing tests also cover disabled firing, deadlocks, reachability truncation, unsupported kinetics, invalid references, explicit overrides, and fixed-input reproducibility. These checks establish behavior for small synthetic systems; they do not validate the bundled biological abstractions or guarantee performance for stiff or discontinuous models.

## Rate-law boundary

The controlled vocabulary includes Hill activation and Hill inhibition so future models can use stable schema terms. The current engine deliberately rejects both because their numerical semantics are not implemented. It does not silently substitute mass action.

## Stochastic models

No Gillespie, tau-leaping, stochastic Petri-net, or probabilistic transition scheduler is present. Discrete reachability enumerates enabled firings; it does not sample waiting times or estimate event probabilities. Stochastic reproducibility and uncertainty propagation therefore remain roadmap work.

## Biological assumptions and interpretation

The bundled memory and knee-load models are curated, simplified pathway demonstrations. They assume that selected states, interactions, thresholds, and normalized rates are adequate for qualitative scenario comparison. They omit many cell types, feedback loops, time scales, spatial effects, compensatory mechanisms, and person-level determinants.

Changing a parameter answers “what does this mathematical model do under this change?” It does not answer “what will happen in a person?” Every `PetriModel` and `SimulationRun` carries the label:

> Model-based simulation, not a personalized biological prediction.

Model output must not be interpreted as a dose recommendation, treatment ranking, clinical trajectory, or experimentally validated kinetic estimate.
