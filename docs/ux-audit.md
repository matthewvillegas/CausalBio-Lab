# UX audit before the 2.0 redesign

Date: 2026-09-12. Existing implementation inspected before product code changes. Scope: complete repository inventory, README, architecture, evidence, Petri, Bayesian, validation and safety documentation; frontend state, API orchestration, graph/evidence/report paths, simulation and inference implementations.

## Baseline evidence

- Python: 117 tests passed (9.38 s), one existing Starlette TestClient deprecation warning.
- Frontend: 7 Vitest tests passed (65.54 s). Offline evaluations: 11/11 fixtures passed.
- Started the actual API and Next.js application. Initial browser workflows failed: Next selected an unrelated parent lockfile as its workspace root and emitted React Client Manifest errors. Both loopback origins are already allowed by the API; the reported cross-origin warning came from Next development resources. These are baseline environment failures, not successful demonstrations. Fix development configuration before repeating UI inspection.
- Captured actual landing screenshot at `artifacts/ux-baseline/landing-desktop.png`; no fabricated captures. Desktop/narrow/dark results inspection will be repeated after startup recovery.
- Backend trace completed for memory: interpreter -> pack loader -> LocalKnowledgeGraph trusted projection -> PathScorer -> ranked hypotheses -> ReportGenerator. Context-only edits currently reuse investigation IDs, and `model_copy` bypasses context validation.
- Petri trace: model registry -> validated SimulationParameters -> stoichiometric rates -> SciPy solve_ivp -> trajectories/transition activity -> comparison. A memory run completed with 121 points and no warnings.
- HMC trace: approved synthetic fixture -> two-group Gaussian model -> independent-chain leapfrog proposals and Metropolis correction -> posterior diagnostics/predictive checks. Default run completed, both known values inside intervals, zero divergences; R-hat 1.000487, reported ESS 3000, acceptance 0.964667, E-BFMI 0.977476. The current ESS label deserves mathematical review.

## Ten largest usability problems

| Priority / severity | Problem and root cause | Proposed correction | Affected files |
|---|---|---|---|
| 1 / Critical | Nine result tabs give every technical subsystem equal prominence; overview precedes the useful mechanism decision. | Start with 3–5 mechanism cards and one Explore action; single collapsed Advanced analysis. | `apps/web/components/ResultsView.tsx` |
| 2 / High | Mechanism cards lead with an arbitrary /100 index and show full paths without selection. | Qualitative evidence, context, one uncertainty, structured ranking explanation; inspect one pathway at a time. | `ResultsView.tsx`, new mechanism components |
| 3 / High | Graph path selection only highlights; it still renders the entire 18/19-node pack with filters and raw relations. | Focused accessible pathway, explicit expansion; graph filters only advanced; non-color edge semantics. | `components/graph/CausalGraph.tsx` |
| 4 / High | Confirmation requires reading six input fields plus three side panels. | Plain outcome/process/context summary; edits behind disclosure, obvious Continue. | `InvestigationApp.tsx` |
| 5 / High | Evidence and contradictions require leaving the selected mechanism; grades imply more certainty than their rubric supports. | Evidence grouped by study context, visible counterargument section, source notes and limitations beside claims. | `ResultsView.tsx`, graph evidence panels |
| 6 / High | Simulation exposes ODE machinery and hard-coded domain controls. Editing scenario relabels old curves; baseline recomputes every run. | Supported model-provided controls, submitted settings snapshot, stale notice, cached baseline, numeric model explanation and collapsed Petri definition. | `components/simulation/SimulationLab.tsx`, model schema/pack metadata |
| 7 / High | Bayesian module leads with diagnostics and feels attached to the biological investigation. | Separate synthetic teaching demonstration, observations/prior/parameter estimates first, diagnostics nested. | `components/inference/BayesianLab.tsx` |
| 8 / Medium | Intervention table leads with multiple numerical metrics; peptide panel leads with sequence properties. | Target/pathway position, maturity, uncertainty and mechanism-vs-symptom role; properties on request. | `ResultsView.tsx`, `components/peptides/KnownPeptideLab.tsx` |
| 9 / Medium | Reports lead with 21 technical sections and expose reproducibility before useful findings; repeated generation performs avoidable work. | Research summary first, readable downloads, technical appendix and retained artifacts. | `reporting/generator.py`, `components/report/ReportPanel.tsx` |
| 10 / High | Beginner landing mentions Petri nets and a global Advanced switch; errors show IDs; graph dark labels use fixed dark colors; tab semantics lack arrow-key handling. | Quiet landing/about/library, nested technical errors, theme-aware graph, native controls, focus management and screen-reader pathway alternative. | `InvestigationApp.tsx`, `globals.css`, `CausalGraph.tsx` |

## Architecture, accessibility and performance findings

Existing discriminated state unions are a useful foundation; retain them and protect asynchronous transitions from obsolete responses. Results should be invalidated by question/context changes, not by selecting a node, chart variable, theme or display filter. Graph calculation is client-only; changing filters does not call the scientific API, but recreates Cytoscape. Advanced modules are eagerly imported and remounting loses expensive runs. Use lazy loading and preserve mounted advanced panels after first access.

The graph already has a relationship select and line/arrow distinctions; retain and strengthen these rather than replace them. Focus indicators and reduced-motion CSS exist. Critical explanations must also work as semantic HTML, without canvas hover or color. Tables and horizontal chains need narrow-screen containment.

Future-domain blockers: registry and interpreter hard-code two packs, model is mandatory, frontend defaults every unknown domain to knee pain, and scenario constants live in React. Generalize only after the UX milestone is working. Trust states already exist; do not build a second evidence system. Duplicate graph IDs are currently overwritten before validation; path direction and referenced IDs need stronger checks. Source adapters already have a shared normalized/cache architecture, but transport buffering, retry/rate bounds and metadata entailment need review.

## Completion evidence

Post-change browser captures, viewport checks, network observations and exact test outcomes are recorded in `validation.md`. A scripted fast path is a regression check, not proof that an unbriefed human understands the product in 30 seconds; that requires an observed usability session.
