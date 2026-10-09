# CausalBio Lab implementation plan

This plan is intentionally staged around a working, offline vertical slice. A phase is marked complete only after its checks have run successfully.

## Scope and constraints discovered

- The workspace was empty on 2026-08-03 and was not a Git repository.
- Python 3.11, 3.13, and 3.14 are installed. Python 3.11 is the project baseline because the scientific stack is mature on that interpreter.
- Node.js 24 and pnpm 11 are installed. `uv` and Docker are not installed, so neither is required for the local path.
- Demo investigations must work with no network, API key, or LLM.
- Scientific claims in the trusted graph must be curated and traceable to real sources.
- Scores derived from the evidence rubric are plausibility indices, never probabilities.

## Delivery phases

### Phase 0 — foundation

- [x] Inspect workspace and toolchains.
- [x] Record architecture and decisions.
- [x] Establish root Python and pnpm workspaces.
- [x] Install locked dependencies and initialize Git.

### Phase 1 — typed core and curated data

- [x] Typed entities, assertions, evidence, hypotheses, interventions, reports, and simulation models.
- [x] NetworkX-backed knowledge graph with validation, filtering, path search, and exports.
- [x] SQLite snapshot repository and idempotent seed command.
- [x] Curated memory-retention and activity-related knee-pain domain packs.
- [x] Scientific-core unit tests.

### Phase 2 — interpretation, ranking, safety, and reports

- [x] Deterministic question interpretation and ambiguity handling.
- [x] Competing-hypothesis construction and transparent component scoring.
- [x] Restricted-action classification and visible safety boundaries.
- [x] Evidence-linked Markdown, HTML, JSON, JSON-LD, GraphML, and CSV exports.
- [x] Citation-coverage validation.

### Phase 3 — API

- [x] Versioned FastAPI routes and OpenAPI schemas.
- [x] Correlation IDs, request-size checks, CORS configuration, safe errors, and local rate limiting.
- [x] Investigation, assertion, evidence, simulation, report, inference, and known-peptide routes.
- [x] API integration and failure-path tests.

### Phase 4 — frontend MVP

- [x] Direct question-first landing experience and curated examples.
- [x] Interpreted context, problem map, competing hypotheses, and intervention comparison.
- [x] Cytoscape graph with filtering, path focus, and edge-level provenance.
- [x] Simple/advanced display modes that do not recompute analysis.
- [x] Curated Petri simulation controls and baseline comparison.
- [x] Evidence-linked report and download actions.
- [x] Accessible responsive UI, dark mode, unit tests, and production build.

### Phase 5 — bounded advanced modules

- [x] Add an explicit synthetic linear-response fixture with known ground truth.
- [x] Implement real fixed-metric Hamiltonian Monte Carlo with convergence diagnostics and eligibility gates.
- [x] Add a closed, provenance-aware known-peptide registry, analysis, comparison, API, and UI.
- [x] Add bounded PubMed and UniProt core adapters with deterministic cache and offline fixtures.
- [x] Add discrete and continuous Petri-net execution with reachability and deadlock checks.

### Phase 6 — verification and documentation

- [x] Run Python tests, Ruff, and mypy.
- [x] Run frontend lint, type checking, tests, and production build.
- [x] Seed SQLite, start API, and verify health plus both end-to-end demo workflows.
- [x] Exercise simulation, exports, ambiguity, no-LLM, restricted-action, and external-source failure paths.
- [x] Run three browser workflows and capture production screenshots.
- [x] Record only actual results in `docs/validation.md`.

## Explicitly deferred advanced work

- Arbitrary graph-to-Petri translation.
- Live literature insertion without curator validation.
- Production PostgreSQL/Neo4j/object-storage adapters.
- Optional LLM extraction.
- General-purpose HMC/NUTS for arbitrary investigations. The shipped HMC path is deliberately limited to the checked-in synthetic linear-response fixture; other investigations return an explicit ineligibility result.
- Stochastic and Hill-kinetic Petri-net execution.
- PDF export and a curation administration interface.
