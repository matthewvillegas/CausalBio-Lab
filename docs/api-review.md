# API and architecture review

The current resolution record below supersedes the historical findings retained later in this file. See `validation.md` for the final combined verification record and `scientific-audit.md` for the citation audit.

## Current resolution record — 2026-10-02

Source inspection confirms these corrections are implemented:

- `CorrelationAndSecurityMiddleware` now counts actual ASGI request chunks before JSON parsing, including absent or understated `Content-Length`; excessive bodies return 413. Malformed lengths return 400 with a correlation ID. The process-local rate limiter and local-only deployment limitations still apply.
- Curated and universal context edits are revalidated against `QuestionContext`; unknown keys and invalid text/boolean values are rejected. Validated context participates in the deterministic question and curated-investigation identities. Universal routing also classifies operational language introduced through an edited context.
- Legacy graph exports and reports construct the graph from the stored investigation projection. Later pack-file changes do not silently change that snapshot. `persist_artifacts=false` returns an empty artifact manifest without creating report files. Curated runtime lookup indexes remain process-local.
- Invalid HMC diagnostics raise `HMCInferenceError` and return a structured 422. Biological inference remains ineligible unless an approved model exists; the separate sampler demonstration remains synthetic. Accepted HMC settings still permit relatively expensive synchronous work.
- Source adapters enforce decoded response size during streaming, bounded transient retries and pacing, request/result identity, record cardinality and duplicate identifiers, timezone-aware retrieval dates, and validated stale-cache fallback. Europe PMC extends the existing shared adapter boundary with abstract metadata. Search deadlines preserve partial results; a running synchronous HTTP request is bounded by its transport timeouts rather than forcibly terminated when the investigation deadline returns.
- Graph construction rejects duplicate IDs before indexing, duplicate canonical names and contextual assertions, untrusted dependencies of trusted assertions, missing path references, invalid ordered edge direction, and trigger/outcome mismatches. Registry metadata and optional numerical models support additional packs without hardcoded domain branches.
- The acute-force-to-chronic-adaptation knee bridge is now `PREDICTED_TO_AFFECT`, grade U, `hypothesis_only`, with its cross-context limitation visible. The underlying source study retains its own study grade.

The new universal endpoints are separate from the trusted curated graph. Their provisional source records and evidence maps cannot be queried as legacy curated investigations. Successful research snapshots and HTML/Markdown/JSON reports are saved atomically in a local SQLite database, survive store reopening, and are checked against saved content hashes. An existing research ID cannot be overwritten with changed evidence. Reopening or exporting a session does not refresh its sources. This storage does not add authentication or multi-user isolation.

### Universal research route inventory

All suffixes below are under `/api/v1`. Research bodies accept a question of 3–2,000 characters, `depth` (`quick`, `research`, or `deep`), validated context edits, and a strict boolean `online` choice. The server's live-source setting and the request's online choice must both permit external retrieval. Status describes enabled capability; it does not assert provider availability.

| Method and suffix | Successful output and behavior | Expected failures or boundaries |
| --- | --- | --- |
| `GET /research/status` | Live-source capability, provider names, and disclosure that scientific search terms go to the public sources. | Makes no external availability probe; no LLM or telemetry is used. |
| `POST /research/interpret` | `ResearchInterpretation`: curated/live/explanatory/clarification/restricted/out-of-domain routing, context, bounded search queries, and a separate safe alternative where available. | Invalid request/context: 422. Does not retrieve evidence or save a research session. |
| `POST /research` | `UniversalResearchResult`: cited source extracts, provisional topic groups, evidence map, source attempts/freshness, limitations, or the curated result. Successful research modes save a local snapshot. | Provider failure retains other available records. Empty/offline results explicitly state the evidence gap. Restricted/clarification/out-of-domain responses return 200 with their explicit mode and are not saved; no sources are called for these routes. A safe alternative requires another explicit request. |
| `GET /research/sessions` | Recent local session metadata, with `limit` default 20 and bounds 1–100. | Invalid limit: 422. This list is local to the configured database, not an account-scoped history. |
| `GET /research/{research_id}` | Complete validated frozen `UniversalResearchResult`. | Invalid UUID: 422; unknown ID: 404; unsupported or altered snapshot: structured 422. |
| `GET /research/{research_id}/report/{report_format}` | Saved `html`, `md`/`markdown`, or `json`. HTML opens inline under a restrictive content-security policy; Markdown/JSON download as attachments. Reports retain citations, provider versions, original retrieval dates, missing-context labels, partial failures, model limits, and temporary-map status. | Invalid format or UUID: 422; missing session: 404; report or payload integrity failure: structured 422. No retrieval, rescoring, or graph promotion occurs. |

Focused executed checks for this addition: **86 tests passed** across `test_research_router.py`, `test_research_pipeline.py`, `test_research_storage_reports.py`, and `test_research_routes.py`. These use explicitly labeled software fixtures and injected providers for repeatable routing, deadline, failure, cache, provenance, storage, safety, and HTTP contracts; they are not live scientific validation. Scoped Ruff and strict mypy checks passed. One installed FastAPI/Starlette test-client deprecation warning was observed. Final broad checks and live evidence review are recorded separately in `validation.md`.

Known remaining architectural limits include process-local legacy state and rate limiting, synchronous numerical work, bounded rather than globally optimal path search, incomplete OpenAPI declarations for middleware/server errors, and no server-side reuse of legacy report generation. Provisional terminology groups are not validated molecular pathways, contradiction review is incomplete, and no executable biological model is automatically inferred from an abstract.

## Historical review — 2026-10-01

The remainder records the implementation inspected during the UX milestone, **before** the corrections above. Its present-tense statements describe that older snapshot, not the current API. The original source review did not itself establish that every listed failure was exercised against a running server.

## Boundary and shared behavior

All application routes use `/api/v1`. OpenAPI is served at `/api/openapi.json`, with an interactive client at `/api/docs`. The API is synchronous, local-first, and has no user authentication. Investigations and artifact indexes are process-local dictionaries protected by locks; report files persist on disk, but restarting the API loses their lookup indexes. Do not describe this as durable multi-user storage.

Request schemas reject extra top-level fields. UUID path and body fields, scalar limits, and domain-model validation are enforced where described below. Errors handled by the application have `type`, `title`, `status`, `detail`, `correlation_id`, and `alternatives`; ordinary handlers currently use `application/json`, while the explicit live-literature refusal uses `application/problem+json`. Invalid request shapes return 422; unknown research identifiers return 404; unexpected failures return a safe 500 message without a stack trace. OpenAPI declares shared 404 and 422 models but omits the implemented 413, 429, 500, and route-specific 503 cases. Unmatched framework routes do not use the same problem envelope.

The outer middleware validates or creates an `x-correlation-id`, adds basic security headers, and rejects declared request bodies over the configured limit (default 1,000,000 bytes). This is presently a **Content-Length check, not a streaming body limit**; absent or dishonest lengths are not bounded and malformed lengths are not explicitly handled. The process-local limiter permits 180 requests per minute per client by default and returns 429 with `Retry-After: 60`. It is not a shared production limiter. CORS accepts the configured web origin and the two local port-3000 origins, without credentials.

## Route inventory

“UI” means a current frontend call or download link. “API” means available to external/local clients and tests, with no current direct frontend caller. Response names refer to the Pydantic types rather than undocumented JSON shapes.

| Method and suffix | Caller and input | Successful output | Validation and expected errors |
| --- | --- | --- | --- |
| `GET /health` | Browser test startup / API; no body | `HealthResponse`: version, local-demo mode, no-LLM/no-telemetry flags, pack count | No source or model computation; does not verify external connectivity or durable storage. |
| `GET /demo-cases` | UI landing library | Tuple of metadata objects: slug, title, description, version, examples, educational notice | Loads each bundled JSON file; malformed packs can fail. No explicit typed response model. |
| `POST /questions/interpret` | UI first step; `QuestionRequest` | `InterpretationResponse`: selected pack, structured question/context, safety notice | Question length 1–2,000 at request boundary; normalized length at least 3 in interpreter. Safety refusal, ambiguous question, unsupported domain, or unknown context field: 422. Context values are loosely typed and currently copied into the domain model without revalidation. |
| `POST /investigations` | UI confirmation; same request | 201 `InvestigationResult`, including graph/evidence, ranked hypotheses, interventions, optional Petri model, limitations and reproducibility | Same question errors. Runs pack loading, graph validation, scoring and projection. Stores result in memory. Deterministic identity currently omits context edits, so equal question/version/seed requests can overwrite different contexts under one ID. |
| `GET /investigations/{investigation_id}` | API; UUID | Full stored `InvestigationResult` | Invalid UUID: 422; absent/restarted-store entry: 404. |
| `GET /investigations/{investigation_id}/hypotheses` | API; UUID | Tuple of stored `MechanisticHypothesis` | 422/404 as above. Does not rescore. |
| `GET /investigations/{investigation_id}/graph` | API; UUID | Stored `GraphProjection`, including assertion provenance | 422/404 as above. Does not rebuild or filter the graph. |
| `GET /assertions/{assertion_id}` | API; UUID | `CausalAssertion` | 422 for invalid UUID; 404 for absent assertion. Scans validated packs. |
| `GET /assertions/{assertion_id}/evidence` | API; UUID | Tuple of supporting and contradictory `EvidenceRecord` objects | 422/404 as above. Evidence roles remain on the assertion; the returned tuple itself is ungrouped. |
| `POST /paths/search` | API; investigation/source/target UUIDs, `max_length` default 6, range 1–10 | Tuple of at most 10 scored directed `MechanismPath` objects | Unknown investigation/endpoints: 404; invalid bound: 422; valid endpoints without a path: empty tuple. Uses trusted assertions, tissue text as requested context, and a bounded candidate prefix, not an exhaustive global optimum. |
| `GET /petri/models` | API; no body | Tuple of bundled `PetriModel` objects | Skips packs without a model. Loads every pack. |
| `POST /petri/simulate` | UI simulation; model UUID, scenario label, duration, steps, seed and override maps | `SimulationRun`: submitted settings, trajectories, transition activity, summary/warnings, model/software versions | Duration `(0, 1000]`; steps 3–5,000; scenario max 120 characters. Unknown model: 404. Engine checks override keys, finite nonnegative values, and place ranges; invalid scientific inputs: 422. Scenario is a run label; overrides determine the actual calculation. The UI builds them from validated model metadata. |
| `POST /bayes/infer` | API; no request schema | `InferenceEligibility` with `eligible=false` | No parameter fitting occurs. The fixed explanation describes missing approved biological observations, priors, likelihood and identifiability review. Does not inspect a particular investigation or accept its ID. |
| `POST /bayes/demo/run` | UI separate teaching lab; `HMCDemoRequest` | `HMCInferenceRun` for the approved synthetic two-group Gaussian model | Chains 2–8; warmup/draws each 100–5,000; leapfrog steps 1–50; step size `(0,1]`; seed integer. No biological inference. Worst-case accepted settings are computationally expensive and execute synchronously. |
| `GET /peptides/known` | API; no input | Tuple of reviewed registry `KnownPeptide` records | Bundled catalog only; no arbitrary sequence design. |
| `GET /peptides/known/{slug}/analysis` | UI peptide inspection; slug and `pH` query default 7.4 | `KnownPeptideAnalysis`, with descriptor limitations | pH 0–14; invalid range: 422; unknown catalog slug: 404. |
| `GET /peptides/compare/{slug_a}/{slug_b}` | UI peptide comparison; two catalog slugs | `PeptideSequenceComparison` | Unknown slug: 404. Comparison is descriptive and does not establish biological equivalence. |
| `POST /literature/search` | API; query length 2–500, mode `bundled` or `live` | Bundled `LiteratureSearchResponse`, records, cache flag and explicit limited-search notice | All whitespace-separated query terms must match title/evidence note. No match: empty list. `live` returns 503 with `alternatives=["bundled"]`; adapters are not silently enabled. Whitespace-only query currently passes schema and matches all bundled records. |
| `GET /graph-exports/{investigation_id}/{export_format}` | UI advanced graph links | Attachment: `json-ld`, `graphml`, `nodes-csv`, or `edges-csv`, correct media type | Unknown investigation: 404; unsupported format: 422. Rebuilds graph and computes all formats before selecting one. |
| `POST /reports` | UI report disclosure; investigation UUID and `persist_artifacts` default true | `ReportResponse`: ID, citation coverage and downloadable artifact manifest | Unknown investigation: 404. Writes Markdown, HTML, report/investigation JSON, four graph exports, and Petri JSON when present. Path confined to configured artifact root. **The `persist_artifacts` option is currently ignored; false still writes artifacts.** |
| `GET /reports/{report_id}/artifacts/{filename}` | UI report download links | Registered `FileResponse` with filename/media type | Invalid UUID: 422; unknown report/filename or path-like filename: 404. Only indexed artifacts are selectable. Externally deleted files are not proactively checked by the store. |

## Recomputation and state

1. `load_domain_pack` parses and reconstructs every typed object on each call. Model/assertion lookup, bundled literature search, path search, exports, reports, and model listing repeat work. A validated immutable pack registry with explicit version/content invalidation can centralize parsing and ID indexes. Avoid a cache that silently hides edited authoring files.
2. Investigation creation always repeats interpretation, graph construction and scoring. Context must first become part of validated identity; caching before fixing identity would preserve incorrect results. Display changes in the frontend must not trigger investigation creation.
3. Graph exports reconstruct the graph from the current pack rather than exclusively from the investigation snapshot. If a pack changes between creation and download, artifact content can drift from the stored investigation/version. Generate from the stored projection or retain a pinned pack revision. Validate the requested format before serialization and serialize only that format for individual downloads.
4. Path search considers at most `limit * 4` node paths and picks the strongest parallel assertion for each hop. Results depend on candidate enumeration order; this is a bounded exploratory search, not a guaranteed top-k path algorithm. Full graph search also becomes expensive on larger dense packs despite the short path limit.
5. Every report request regenerates sections/exports and writes files. The current UI caches report requests by investigation ID and keeps completed advanced panels mounted, reducing repeated user-triggered work. Server callers still repeat generation. Server reuse should key all scientific content/version inputs and check artifact existence.
6. Simulation and HMC routes are synchronous CPU work. Existing validation bounds dimensions but allows costly HMC combinations. Introduce a total-computation budget before adding larger datasets or shared access. The UI simulation baseline cache and submitted-settings snapshot are the appropriate immediate UX correction; do not rerun models for chart filtering or theme changes.
7. The UI receives the full graph/evidence/hypothesis bundle once and uses it locally for mechanism selection, evidence expansion and graph display. Preserve this useful separation. Avoid adding per-selection scientific requests solely to support visual changes.

## Source adapter design

The existing `SourceAdapter` protocol, typed PubMed/UniProt normalization, transport injection and content-addressed filesystem cache are a useful shared boundary. Preserve them rather than add parallel integration abstractions. Production URLs are adapter-controlled HTTPS endpoints with redirects disabled, a ten-second default timeout, and a five-megabyte response allowance. Cache keys include source namespace, cache schema, adapter version, query and limit; stored envelopes check namespace/key/schema identity, size and timezone-aware timestamps. TTL is 24 hours by default; stale fallback is explicit and warned, and no adapter result is automatically promoted to curated evidence.

Required bounded corrections after the UX gate:

- Enforce response size while reading HTTP chunks; the current `response.content` buffering precedes the size check.
- Retry only transient failures with a small attempt budget, bounded backoff/`Retry-After`, injectable sleep/clock, and per-source pacing. Permanent 4xx, malformed JSON, normalization failures, and oversized responses should fail without repeated downloads.
- Check upstream record cardinality against the requested limit and reject malformed/duplicate IDs. Ensure PubMed summaries correspond to the IDs requested.
- Translate normalization/schema failures into `SourceResponseError` so stale fallback and callers share a predictable error boundary.
- Validate cached payload identity against the requested query/source endpoint and normalized schema; a valid envelope alone does not prove the payload is for that request.
- Keep tests deterministic with fixture transports and temporary caches. The prior 12-publication audit and successful live adapter smoke checks are documented in `scientific-audit.md`; repeating them is unnecessary for this implementation review.

## Graph and curation integrity

`LocalKnowledgeGraph` validates assertion endpoints, all referenced evidence IDs, duplicate canonical names, and trusted supporting evidence. It retains typed causal status, confidence, context, source IDs and contradictions in projections/exports. Unreviewed assertions are excluded from the default trusted projection. However, trusted curation describes review state, not direct causal support; curated grade-U assumptions must stay visible as assumptions.

Integrity gaps to close in the domain/graph milestone:

- Dictionaries currently overwrite duplicate entity/assertion/evidence IDs before validation. Reject duplicates before constructing indexes, including duplicate raw authoring keys that collapse to deterministic UUIDs.
- Validate every declared hypothesis/path reference, ordered edge direction against consecutive entities, trigger/outcome alignment, evidence links and intervention references. Length alone is not connectivity.
- Apply review-state checks consistently to graph entities and contradictory evidence as well as supporting evidence; define whether unreviewed evidence is excluded or explicitly displayed as a candidate. Do not silently discard contradictions or promote candidates.
- Validate Petri place/transition/arc uniqueness, bindings and supported scenario metadata while allowing packs with no numerical model. Scenario baselines must match declared parameters/initial values, and full-strength initial values must remain in declared bounds.
- Correct the knee `loading_increases_adaptation` edge: the subject is an acute single-jump force estimate, while its source concerns chronic loading in healthy adults. Conservatively label the bridge as hypothetical/grade U unless separately authored with a matching chronic-exercise endpoint. Keep the source study's own evidence grade unchanged.
- Explain outcome differences and source reuse. A clinical score and self-reported recovery are not interchangeable; multiple graph edges citing one publication are not independent replications.

No additional citation is invented to fill these model gaps. Evidence changes, numerical corrections, and their actual verification must be recorded as completed work only after the ordered milestone gates pass.
