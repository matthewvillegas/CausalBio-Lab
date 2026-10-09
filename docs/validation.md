# Validation record — 2026-10-08

This records local checks on Windows/PowerShell, Python 3.11.9, Node 24.16.0 and pnpm 11.2.2. Passing tests do not establish clinical validity, systematic scientific coverage, independent expert review, or novice comprehension.

## Public-release verification

The literal `CI=1 pnpm verify` completed successfully in a fresh public-source copy on October 8, 2026, in **136 seconds**. It used an independently installed Python environment, isolated pnpm store, separately downloaded Chromium, and new production servers. The project has no commits or remote yet, so this is a source-copy validation, not a remote clone. See [reproducibility](reproducibility.md) for the complete setup and scope.

| Check                               | Result                                                                          |
| ----------------------------------- | ------------------------------------------------------------------------------- |
| Python formatting / lint            | Ruff passed                                                                     |
| Strict Python typing                | mypy passed across 93 source/test files                                         |
| Python tests                        | **384 passed**, 15.70s; one existing Starlette test-client warning              |
| Offline evaluations                 | **11/11 passed**                                                                |
| Frontend formatting / lint / typing | Prettier, ESLint, TypeScript passed                                             |
| Frontend tests                      | **54 passed**, 9.64s                                                            |
| Production build                    | Next.js **16.3.8**, webpack, passed in the fresh environment                    |
| Production browser workflows        | **9 passed**, 31.2s, no retry required                                          |
| `pnpm graph:validate`               | Memory: 18 entities / 15 assertions / 6 evidence; knee: 19 / 18 / 6; both valid |
| Python statement coverage           | **94.65%**, 4,598 / 4,858 statements; 260 missing                               |

Coverage was measured separately with `pnpm python:coverage` on **October 7** in the same fresh environment: all 384 tests passed. Scientific source remained unchanged for the October 8 verification. This replaces the earlier 94.64% figure for current release descriptions; historical measurements remain below with their dates.

Local evidence: `artifacts/release-clean-final-verify.log`, `artifacts/release-clean-final-install.log`, `artifacts/release-clean-final-graphs.log`, and `artifacts/release-coverage.json` (ignored local files). These logs are not committed because they can include machine paths. The public record reports results without those paths.

The root production build also passed on Next.js 16.3.8. The real [72-second browser recording](demo-transcript.md) used cached provider results, no mocked responses, and completed without page errors. Seven representative video frames and the new social preview were inspected. The six README screenshots remain the October 5 production captures: this release pass changed dependencies and presentation materials, not the interface design. It did not rerun the entire 99-image design matrix or claim new performance measurements.

A final startup-only change bound `pnpm dev` explicitly to loopback and narrowed Compose's host port mappings. The updated development command was checked separately in the fresh copy: both listeners used `127.0.0.1`; web, API health and API docs returned HTTP 200. The completed full-suite result applies to the unchanged scientific/UI implementation; the invocation change has this separate smoke result. Containers remain unvalidated.

Public-file and documentation-link checks are recorded in the [release audit](public-release-audit.md). Dependency scans report zero known production JavaScript and installed Python findings; the full JavaScript audit still has one high development-only `braces` finding without a published fix. See the [dated dependency review](dependency-audit.md), including its scope and skipped local distribution.

An initial canonical run stopped at Prettier formatting of the portable browser config; formatting was corrected and the complete command rerun. A preceding pnpm store-setting mismatch was repaired with a sequential isolated install before the successful verification. Neither fix changed test expectations. Terminal color-environment notices and the existing Starlette warning remain. Hosted CI, containers, macOS, a browser-engine matrix, and independent scientific review have not been validated by this run.

## October 5 design-pass verification (historical)

The final `pnpm verify` passed after the screenshot-driven refinements, using `CAUSALBIO_E2E_PRODUCTION=1` and `CI=1` with fresh browser-test servers. The scientific core, source contracts, safety routing, and numerical expectations were preserved.

| Check                           | Final result                                                                  |
| ------------------------------- | ----------------------------------------------------------------------------- |
| Python formatting, lint, typing | Ruff clean, 132 files formatted; strict mypy clean across 93 files            |
| Python tests                    | **384 passed**, one existing Starlette test-client deprecation warning        |
| Offline evaluations             | **11/11 passed**                                                              |
| Frontend checks                 | Prettier, ESLint, TypeScript and production webpack build passed              |
| Frontend tests                  | **54 Vitest tests passed**                                                    |
| Production browser suite        | **9 passed**, first attempt, 33.3s                                            |
| Curated graph validation        | Both valid: memory 18 entities / 15 assertions / 6 evidence; knee 19 / 18 / 6 |

Evidence: `artifacts/design-verify-final.log` (local-only) and `artifacts/design-graphs.log` (local-only). Coverage was **not** remeasured in this pass; the October 3 coverage figure below is historical.

On October 5, the production review captured **99 images covering 33 states at three widths**, plus refreshed **13 README screenshots**. The [design capture manifest](assets/design/review-record.json) records viewports, actual research IDs and source statuses, controlled fixtures, keyboard checks, reduced-motion behavior, contrast samples, and resource measurements. It completed without document overflow or unexpected browser warnings/errors; the intentional 503 fixture is separately recorded. The two README workflows also passed: [curated capture record](assets/capture-record.json), [live research capture record](assets/live-capture-record.json).

The review repaired detached citations, mobile graph/table guidance, empty-result affordances, dialog focus restoration, and an invalid report meta-CSP directive while preserving HTTP frame protection. The [design and code audit](design-and-code-audit.md) gives the measured performance costs, accessibility scope, screenshots, and remaining weaknesses. These are local Chromium results, not full accessibility or field-performance certification.

## October 3 scientific-upgrade record (historical)

The following record preserves the earlier scientific upgrade's commands, coverage, and source-review evidence. Its test counts and timings are not the current design-pass counts above.

### Executed verification

The canonical `pnpm verify` sequence ran with `CAUSALBIO_E2E_PRODUCTION=1` and `CI=1`, using fresh production browser-test servers with reuse disabled. It passed with exit code 0 in **274.44 seconds**: Ruff formatting/lint, strict mypy, 379 Python tests, 11 offline evaluations, frontend Prettier/ESLint/TypeScript, 36 Vitest tests, the production webpack build, and nine Chromium workflows. Log: `artifacts/final-verify.log` (local-only).

Subsequent manual review exposed extraction-selection problems and a UI issue with shared claims. Those fixes have separate final check records below; the earlier canonical counts are not presented as the final test counts.

| Final check                | Observed result                                                                                                 |
| -------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Python formatting and lint | 130 files formatted; Ruff clean                                                                                 |
| Strict Python typing       | mypy clean across 93 source/test files                                                                          |
| Python suite and coverage  | **383 passed**, 1 dependency warning; 4,595 / 4,855 statements covered (**94.64%, displayed as 95%**)           |
| Offline evaluations        | **11/11 passed**                                                                                                |
| Curated graph validation   | Both packs valid: memory 18 entities / 15 assertions / 6 evidence records; knee 19 / 18 / 6                     |
| Final frontend checks      | Prettier, ESLint, TypeScript and production build passed; **37 Vitest tests** and **9 Playwright tests** passed |

Python commands:

```powershell
pnpm python:format
pnpm python:lint
pnpm python:typecheck
node scripts/python-run.mjs -m pytest --cov=causalbio --cov=causalbio_api --cov-report=term --cov-report=json:artifacts/final-coverage.json
pnpm eval
pnpm graph:validate
```

The final Python sequence passed in 61.96 seconds; pytest took 43.18 seconds. Evidence: `artifacts/final-python-review.log` (local-only), `artifacts/final-coverage.json` (local-only), and `artifacts/final-graph-validation.log` (local-only). One installed FastAPI/Starlette test-client deprecation warning remains. Terminal color-environment warnings in browser tooling were not browser console errors.

The final frontend sequence passed in **97.27 seconds** after the shared-claim fix. All nine Playwright workflows passed on their first attempt in **25.4 seconds**, using fresh production servers with reuse disabled. Evidence: `artifacts/final-web-review.log` (local-only).

### What the checks cover

Python tests exercise pack discovery and optional numerical models, graph identity and directed-path integrity, context validation and identity, ranking sensitivity, isolated candidate review, source identity/cache/retry/deadline boundaries, exact passage/citation grounding, source-specific molecule scope, restricted-context routing, partial retrieval, local sessions, immutable reports, exports, and API request boundaries.

Numerical tests include gradients against finite differences, leapfrog reversibility and energy behavior, Gaussian parameter/covariance recovery, independent pinned Stan diagnostic fixtures, prior/tuning/seed sensitivity, Petri conservation/equilibria, gates and bounds. They validate the stated synthetic fixtures, not biological inference. See [Bayesian methodology](bayesian-inference.md) and [Petri methodology](petri-nets.md) for exact model assumptions and boundaries.

The browser suite covers both curated journeys, narrow/dark layout, keyboard use, missing numerical models, graph/evidence inspection, Petri and HMC demonstrations, known peptides, reports and recovery, new-topic research, direct BDNF explanation and deeper interpretation, explicit safe-alternative selection, saved sessions, source failure, and offline gaps. Universal provider results in these automated browser tests use labeled fixtures. Real sources are checked separately below.

### Real sources and manual question review

[`live-research-validation.md`](live-research-validation.md) records all **26 cases**: two curated questions, ten new biological topics, three entity questions, three intervention questions, three ambiguous questions, three restricted questions, offline use, and an injected PubMed failure.

Fresh retrievals from Europe PMC, PubMed and UniProt were observed earlier on October 3 UTC. Later matrix runs intentionally reused their validated cache; they did not relabel old retrieval dates as current. The reviewed final matrix returned four to six provisional groups for new topics, with one to three direct extracts when supported. Twenty successful cases were saved, reopened, and exported in HTML, Markdown and JSON. An artifact audit found no broken references among 360 deduplicated-per-result claim instances and 276 temporary source-link edges.

These are traceability and software results. Manual review still found incomplete explanations, neighboring topics, mixed tissue/population contexts, and thin support for some requested targets. For example, sleep consolidation mixes meanings, selegiline extracts describe downstream effects rather than the full inhibition mechanism, and collagen synthesis spans disparate model systems. These cases are not reported as fully adequate biological answers.

### Production screenshots and real browser walkthroughs

Two scripts captured the production application at 1440×1000 and 390×844:

```powershell
# Run from apps/web with the local production web/API servers running.
node scripts/capture-docs-screenshots.mjs
node scripts/capture-live-research.mjs
```

The October 3 run captured eight curated-workflow and five general-research views and reported no horizontal overflow or browser console/page warnings or errors. These image paths and their manifests in [`docs/assets`](assets/) have since been refreshed on October 5; they now represent the design pass described above. The general-research walkthrough uses real provider/cache results, not mocked source payloads: tendon evidence and its HTML report, BDNF direct explanation/deeper interpretation, and a restricted selegiline question followed by an explicit scientific-alternative click. The latest tendon and BDNF runs reused validated cache; the safe-alternative run mixed cached records and available PubMed retrieval. Original retrieval dates are preserved. The safe alternative can still report an evidence gap in its direct answer while retaining related sources and mechanism groups.

Visual review exposed a loading-state screenshot selected by an inexact heading match, and a focused map that included other groups when they shared a claim. The capture now waits for the exact completed heading; the map now filters by the selected mechanism, with distinct/shared-claim regression cases.

### Failures repaired during the scientific upgrade

- Next/Turbopack client-manifest failures in this Windows checkout: switched the existing application to webpack development/build commands.
- Hidden/zero-size chart warnings and stale control displays: measured chart containers and submitted-input snapshots preserve state and accurate labels.
- Context-insensitive result identities, weak graph validation, export drift, ignored report persistence, and declared-length-only request limits: validated context and immutable projections, stronger graph contracts, honored no-write behavior, and actual streamed-body limits.
- HMC diagnostic and degenerate-chain boundaries: independent reference tests and explicit finite/degenerate failure handling.
- Source metadata/form flattening and provisional citation integrity: bounded provider validation, scoped UniProt annotations, exact passage checks, and immutable snapshots.
- Unknown-pack dead ends and operational-only safety screens: tiered research routing and explicit safe scientific alternatives.
- Review-method sentences and neighboring-topic overviews: conservative extraction filters and subject/process overlap, including a regression preventing `synthetic` from matching `synthesis`.

## Limits of this validation

No deployment, hosted CI run, container build, external security review, authenticated multi-user use, clinical dataset, full systematic review, clinical prediction, or independent scientific replication was validated. The Docker CLI was unavailable during the earlier audit; containers were not retested here. No representative adversarial safety benchmark or observed novice usability study was performed. Live source availability can change. The 11 deterministic evaluation fixtures are regressions, not a measured general accuracy rate. See [limitations](limitations.md) and [general research](universal-research.md).
