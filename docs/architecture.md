# Architecture

CausalBio Lab is a local-first monorepo with three runtime layers:

```text
Next.js web application
        │ typed JSON over /api/v1
        ▼
FastAPI application
        │ orchestration only
        ▼
causalbio scientific core
  ├─ curated JSON domain packs
  ├─ NetworkX assertion graph
  ├─ deterministic routing and curated path ranking
  ├─ bounded public-source retrieval and cache
  ├─ provisional source extracts and evidence maps
  ├─ Petri and continuous simulation
  ├─ synthetic HMC demonstration
  ├─ evidence-linked reporting
  └─ separate SQLite research sessions and curated snapshots
```

## Scientific core

`packages/causalbio-core` contains all scientific semantics and is independent of HTTP and React. Pydantic models provide validated, serializable boundaries. Assertions are first-class objects: a displayed edge retains direction, polarity, causal status, context, supporting and contradictory evidence IDs, curation state, retrieval date, and source.

The local graph adapter uses a NetworkX `MultiDiGraph`. This permits multiple contextual assertions between the same pair of entities without flattening their semantics. Path search filters untrusted assertions by default and applies a documented plausibility calculation with separate evidence-quality, directness, human-relevance, replication, context-match, contradiction, extrapolation, path-length, and unsupported-link components.

Curated domain packs are immutable versioned JSON fixtures discovered from immediate `<slug>/pack.json` directories. `PackMetadata` defines canonical questions, recognition/clarification terms, context defaults, expected mechanisms, and numerical-readiness declarations. The registry root is injectable for isolated fixtures; interpretation and loading share metadata without circular calls or a two-domain allowlist. See [domain-pack-authoring.md](domain-pack-authoring.md) for the contract. A seed command validates the packs and materializes a normalized SQLite snapshot for inspection and reproducibility. Runtime demonstrations can load the fixtures directly, so a missing database never blocks offline use.

The graph boundary rejects duplicate identifiers and canonical names, missing references/provenance, untrusted dependencies, and invalid ordered mechanism paths. Contextual parallel edges and biological feedback remain supported. `pnpm graph:validate` reports integrity plus retrieval-age review cues. A third synthetic fixture exercises discovery, interpretation, investigation, and reporting without adding a production scientific domain.

Ranking weights are validated and recorded with each score. A local sensitivity calculation varies one weight at a time, retains ties, and reports mechanism rank ranges; it measures dependence on this heuristic rather than biological uncertainty. Petri conservation, gating and bounds, plus the synthetic HMC sampler's recovery, reversibility, and diagnostics have dedicated numerical fixtures. These checks do not make arbitrary literature graphs eligible for numerical inference.

## General research

`research/router.py` applies the safety boundary before selecting a curated investigation, live research, an explanatory answer, a cached/local evidence summary, clarification, a restricted request with a safe alternative, or an out-of-domain response. A compound mentioned beside a familiar outcome does not inherit that outcome's curated coverage. Interpretation and queries remain editable; source retrieval for a restricted request starts only after the user chooses the offered research alternative.

`research/service.py` coordinates Europe PMC abstracts, PubMed citation metadata, and relevant UniProt function annotations. Quick retrieves up to four main-search records from each literature provider. Research uses up to eight Europe PMC and six PubMed records; Deep uses twelve and six. Both add separate Europe PMC searches for up to three limiting-findings records and three overview-review records. A recognized gene, protein, or receptor can add up to three UniProt entries. PMID/DOI overlap is deduplicated. UniProt function records preserve molecule/form scope, species, and annotation evidence; multiple annotations from one entry are not independent replication.

The coordinator returns partial results after its source deadline. Each adapter validates response identity and size, bounds retries and pacing, and uses a validated cache with original retrieval timestamps. Offline operation makes no source requests and can use cached responses or relevant local curated records. Provider status distinguishes fresh retrieval, cache use, unavailable sources, and offline gaps. See [general research](universal-research.md) and [data sources](data-sources.md) for the exact execution and source contracts.

Extraction selects exact cited passages and groups shared biological terms. A provisional map connects these groups to their supporting source records; it does not infer molecular causal triples or promote claims into the trusted graph. Source metadata that cannot establish species, population, effect size, or study context remains unknown. Title-only citations cannot support detailed mechanism claims. A separate append-only candidate-review store records curator decisions and provenance for explicit review/export, without automatic graph insertion.

## API

`apps/api` is a thin FastAPI orchestration layer. It owns request validation, investigation lifecycle, response projection, correlation IDs, safe failures, size limits, local rate limiting, and report artifacts. It does not implement scientific rules.

Curated investigations are deterministic and use stable IDs derived from normalized input, the complete validated context, data-pack version, scoring rubric, and seed. Context edits therefore create a distinct result when their meaning changes. General research uses a new session ID for each run and stores an immutable result/report snapshot in `SQLiteResearchStore`. Reopening a saved session does not silently refresh its evidence. Long-running-job interfaces are represented in schemas, while the local simulation executes synchronously because its curated ODE systems finish quickly.

`/api/v1/research/interpret` exposes routing and interpretation; `/api/v1/research` runs retrieval, and `/sessions`, `/{id}`, and `/{id}/report/{format}` support local history and reports. `/status` describes whether live retrieval is enabled, not whether providers are currently reachable. General research is enabled by default and can be disabled per request or through `CAUSALBIO_LIVE_RESEARCH_ENABLED`. The legacy literature route's disabled live mode is a separate API boundary.

## Web application

`apps/web` is a Next.js App Router application. Its explicit workflow is question → interpretation → mechanism cards → selected pathway. Evidence, counterevidence, intervention targets, and comparison belong to that selected mechanism. Numerical scores, Cytoscape, simulation, the synthetic Bayesian demonstration, peptide properties, and raw provenance sit behind disclosure controls.

New topics use a provisional-results view with a cited answer, grouped evidence, context and uncertainty, an optional evidence map, and local reports. Explanatory questions can proceed directly to an answer; Quick, Research, and Deep control bounded retrieval. The library distinguishes installed curated investigations from general research and exposes saved sessions. No numerical control is offered as though a model had been generated for a new topic.

The workflow rejects obsolete asynchronous replies when a question is edited. Display filters operate on the returned investigation and do not recompute scientific results. Advanced modules load on demand and retain submitted results across tool changes. Simulation separates edited controls from the settings used for the displayed run, reuses baseline calculations, and handles absent models. Reports cache successful and pending requests with retry after failures.

Development and production scripts explicitly use Next's webpack mode. This followed reproducible Turbopack React Client Manifest failures in this Windows checkout; the configured repository root and allowed local origins remain explicit.

## Trust boundaries

- Bundled scientific text is curated data, not executable instruction.
- Only `VALIDATED` and `CURATED` assertions enter trusted views by default.
- External-source responses are normalized into untrusted records and never mutate the graph automatically.
- Scientific claims carry evidence IDs. Provisional extract claims additionally validate exact source-passage membership; this proves traceability, not full-text entailment or biological correctness.
- Safety classification occurs before interpretation; restricted requests receive research-level boundaries and no operational instructions.
- Petri models may be absent; no numerical model is synthesized to fill that gap. Pack-specific Bayesian inference remains disabled because no validated likelihood/backend binding is supplied, regardless of numerical-readiness metadata. The synthetic HMC demonstration is a separate numerical-validation tool.

## Reproducibility record

Each curated investigation records the software version, domain-pack and graph versions, evidence-rubric version, ranking weights and sensitivity, retrieval dates, random seed, simulation parameters, and display-independent scientific result. Export filenames include the stable investigation ID. Exports use the saved investigation projection instead of reloading a mutable pack.

General research snapshots record the interpretation, query plan and actual source runs, provider versions, source/cache dates, extract method, provisional graph, unavailable analyses, and complete evidence references. Result and HTML/Markdown/JSON report snapshots are saved atomically with checksums. Refreshing creates a new session. See [research persistence](research-persistence.md).

This is a local service without user accounts or multi-user access isolation. Scientific query terms reach public providers when live research is enabled; original questions and results remain in local storage. The query planner is not a personal-information redactor. No LLM or telemetry is required.
