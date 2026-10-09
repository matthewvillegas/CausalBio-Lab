# Causal model

## Scope and implementation status

CausalBio Lab currently implements a **provenance-rich mechanism graph**, not a causal-effect identification engine. The graph can represent whether a curated claim is experimental, associative, mechanistic, genetic, computational, expert-curated, or hypothetical. It can compare evidence-backed paths. It does not estimate an intervention effect from observational data, discover an adjustment set, run do-calculus, or answer an individual counterfactual.

That distinction is intentional: a typed causal claim is more informative than an untyped connection, but typing a claim does not make its underlying study design causally sufficient.

## Mechanism graph versus causal DAG

A mechanism graph is a scientific representation assembled from heterogeneous evidence. Its nodes may span biomechanical forces, tissues, cell types, proteins, processes, symptoms, and interventions. Its edges are first-class assertions with context and provenance. Multiple parallel assertions may connect the same entities because studies can differ by species, tissue, design, direction, or interpretation.

A causal directed acyclic graph (DAG), by contrast, is normally defined for a particular population, time ordering, causal question, and set of variables. It encodes assumptions about common causes and supports identification analysis under additional assumptions. The local CausalBio graph is a directed multigraph and may contain cycles, feedback, repeated biological levels, and literature-derived associations. It is therefore not automatically a valid DAG for an estimand.

| Question | Mechanism graph in this repository | Causal DAG analysis |
| --- | --- | --- |
| Primary purpose | Organize mechanisms and evidence | Identify an estimand under explicit assumptions |
| Edge meaning | Typed, contextual scientific assertion | Direct causal dependence for a defined analysis |
| Cycles | Allowed | Usually excluded in a conventional static DAG |
| Evidence | Heterogeneous study records | Data plus a specified identification model |
| Output | Paths and a comparison heuristic | Identified or non-identified causal quantity |

## Assertion semantics

Every implemented `CausalAssertion` contains:

- subject and object UUIDs;
- a controlled relation and polarity;
- a directed orientation;
- an ordinal confidence classification;
- a causal-status label;
- species, population, tissue, cell, condition, and temporal context where available;
- supporting and contradictory evidence UUIDs;
- curator, extraction method, source, retrieval date, and review status;
- a human-readable interpretation and limitations.

Self-edges are rejected. Assertions marked `VALIDATED` or `CURATED` require supporting evidence, and the graph rejects a trusted assertion whose supporting record is not itself trusted.

The causal-status vocabulary is:

- causal experimental evidence;
- quasi-experimental evidence;
- longitudinal association;
- cross-sectional association;
- mechanistic biochemical evidence;
- genetic evidence;
- computational prediction;
- expert curation;
- hypothesis only.

These labels communicate the basis of a claim. They are not interchangeable evidence designs and they do not certify that every relevant bias has been controlled.

## Association and causation

Relations such as `ASSOCIATED_WITH` and causal statuses such as `cross_sectional_association` remain associative. Temporal ordering can strengthen an argument but does not by itself eliminate confounding, selection bias, measurement error, reverse causation, or model misspecification. Computational predictions and expert curation remain explicit even when biologically coherent.

Relations such as `CAUSES`, `CONTRIBUTES_TO`, `MEDIATES`, `ACTIVATES`, or `INHIBITS` should be read together with their causal status, evidence design, context, and limitations. The relation name alone is never sufficient evidence of causality.

## Confounding

A confounder is a cause of both an exposure and an outcome that can induce or distort an association. The current graph can represent candidate common causes and competing mechanism branches, but it does not:

- assert that all confounders have been measured;
- calculate back-door or front-door adjustment sets;
- fit propensity, regression, weighting, instrumental-variable, or g-method estimators;
- certify exchangeability after adjustment.

Consequently, a path from an exposure to an outcome is a possible evidence-backed mechanism, not proof that the exposure has an identified causal effect.

## Mediation and moderation

`MEDIATES` represents a curated mechanistic claim that an intermediate process may lie on a pathway. `MODERATES` represents context-dependent modification. Neither relation currently defines natural, controlled, interventional, or separable direct and indirect effects. The application does not estimate mediation quantities or test the cross-world assumptions required by some counterfactual mediation analyses.

Paths may also mix molecular mechanisms and person-level outcomes. That is useful for research navigation, but every cross-level link carries translational assumptions that must be inspected separately.

## Interventions

Interventions are modeled as research objects with class, targets, evidence, maturity, relevance, uncertainty, safety concerns, and whether they address a cause, mediator, symptom, or multiple levels. They are compared descriptively; `personal_recommendation` is fixed to `false`.

An intervention edge does not mean that the system has simulated `do(X=x)`. The current application does not recommend treatment, calculate dose, or predict an individual's response.

## Counterfactual assumptions

A counterfactual statement such as “the outcome would have differed if this intervention had been applied” requires a well-defined intervention and assumptions such as consistency, positivity, exchangeability, correct temporal ordering, and limited interference. Those assumptions are not established by the current literature graph. No individual treatment effect, potential outcome, or counterfactual probability is produced.

## Path scoring

The path scorer combines curated evidence grade, causal directness, a simple species-relevance heuristic, replication count, context matching, contradictions, extrapolation, path length, and weak-link penalties. The displayed 0–100 value is labeled **plausibility index**.

It is a deterministic ranking heuristic. It is not:

- a posterior probability that a mechanism is true;
- a causal effect size;
- a confidence interval or frequentist test result;
- a clinical risk score;
- a substitute for reading the linked evidence.

## Limits of graph-based reasoning

Graph traversal can surface missing links, alternative branches, indirectness, and contradictory evidence. It cannot repair biased source studies, resolve inconsistent constructs, infer missing temporal information, guarantee biological transportability, or distinguish all causal structures that fit the same observations. Feedback represented in the mechanism graph also needs a separately specified dynamic model before it can be simulated.

The bundled packs are curated educational slices, not comprehensive systematic reviews. Results should be interpreted as transparent research hypotheses subject to source review, external validation, and revision.
