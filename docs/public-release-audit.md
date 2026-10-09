# Public release audit

Audit started October 5 and completed October 8, 2026. Local release preparation and verification are complete. **Publication status: NOT READY until the owner confirms personal contribution language and performs the publishing checklist.** No repository, commit, tag, remote CI result, or public release was fabricated. One development-only dependency advisory remains documented.

## Initial repository inspection

Git is on an unborn `master` branch: no commits, tracked files, or remotes exist. All project files are untracked. There is no development history to reconstruct or publish as historical commits. A clean public-source copy, rather than a Git clone, is the appropriate local reproducibility test.

The initial Git candidate set contains 328 files, 11.7 MB. The established `apps/web`, `apps/api`, and `packages/causalbio-core` boundaries are sound. Tests live beside their applications/packages; moving them to a root folder would add churn. The bulk of candidate binary content is 99 design-review images, rather than required program data.

| Material                                                                                        | Decision                  | Reason / required action                                                                  |
| ----------------------------------------------------------------------------------------------- | ------------------------- | ----------------------------------------------------------------------------------------- |
| Applications, scientific core, tests, licensed numerical/source fixtures                        | KEEP                      | Production behavior, provenance, and meaningful regression coverage                       |
| Public curated packs, synthetic data, evaluations                                               | KEEP                      | Offline demo and numerical reproducibility                                                |
| Manifests, lockfile, setup/validation/capture scripts                                           | KEEP / FIX                | Correct Node prerequisites, production CI, and absent local-baseline handling             |
| `.venv`, dependencies, build outputs, tool caches                                               | IGNORE                    | Installed or generated; fresh setup must recreate them                                    |
| SQLite stores and sidecars, retrieval caches, generated reports, logs, coverage, browser traces | IGNORE                    | Local state; strengthen patterns to cover future variants                                 |
| `.env` variants and editor/OS metadata                                                          | IGNORE                    | Private or machine-specific; retain a safe, accurate `.env.example`                       |
| Six current README images and intentional social/demo assets                                    | KEEP                      | Explain the actual application; review visible content and source attribution             |
| Bulk design-validation images and duplicate captures                                            | IGNORE                    | Preserve local review evidence without publishing a screenshot dump                       |
| Technical/method/scientific audit documents                                                     | KEEP / FIX                | Preserve evidence; replace public links to ignored files with clearly labeled local paths |
| Historical implementation plan                                                                  | KEEP, move only if useful | Describes earlier scope; must not be mistaken for current release status                  |
| Changelog, security and contribution instructions                                               | FIX                       | Stale two-topic/live-source claims and unsupported dated release framing                  |
| `LICENSE`                                                                                       | FIX                       | Existing file is only the short Apache notice; provide the complete Apache-2.0 license    |

No credential, private email, or user-specific absolute path was detected in the initial candidate scan. Explicit dummy test values are not real credentials. No private `.env` exists. This is a scoped inspection, not a guarantee that no secret can exist. Final publication candidates will be scanned again after cleanup.

## Changes made

- **Kept** the existing monorepo boundaries, scientific implementation, substantive tests, licensed fixtures, public curated packs, and historical review documents. No scientific feature or invented mathematical claim was added.
- **Ignored** local databases and sidecars, retrieval caches, coverage/logs, browser traces, private environment variants, editor files, and bulk screenshots. Six README screenshots, one social preview, and the reviewed video remain public. Local review images and user data were preserved.
- **Removed** the redundant browser CI config, unused `python-multipart`, and the deprecated Cytoscape type stub. No folder reshuffle or manufactured historical commits were needed.
- **Fixed** declared Node prerequisites, portable Python/browser startup, production browser defaults, font-notice packaging, loopback startup/Compose bindings, missing-baseline handling in the optional design capture, and narrowly scoped dependency advisories. Container changes were inspected, not executed locally.
- **Added** reproducible-copy, public-file, and documentation checks; a concise docs index; practical issue/PR templates; updated contribution/security policies; complete Apache-2.0 text and third-party notices; unreleased v1.0.0 notes; conservative portfolio/application drafts; and the 28-topic defense guide.

## Verification and integrity

| Release check             | Observed result                                                                                                                                                                                     |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Fresh public-source setup | Independent Python environment, pnpm store, Chromium and production build; no private `.env`, dependencies, cache or database copied                                                                |
| `CI=1 pnpm verify`        | Passed October 8 in 136s: **384 Python / 54 frontend / 9 browser tests; 11/11 offline evaluations**, formatting, lint, strict typing and build                                                      |
| `pnpm graph:validate`     | Both curated graphs valid                                                                                                                                                                           |
| `pnpm python:coverage`    | **94.65%**, 4,598 / 4,858 statements, measured October 7 in the fresh copy; scientific source unchanged afterward                                                                                   |
| Startup                   | Seed and `pnpm dev` passed without private configuration; web, API health and API docs returned HTTP 200                                                                                            |
| Assets                    | Six current design screenshots selected; 1280×640 social preview rendered; 71.92s real production recording and transcript reviewed                                                                 |
| Security                  | No credential, private email, user-specific path, or private local artifact detected in final publication candidates; pattern scan supplemented by manual review                                    |
| Dependency scans          | Production JavaScript: zero known findings; Python: zero known findings, local unpublished distribution skipped; full JavaScript: one high development-only `braces` finding with no published fix  |
| Links and public files    | 200 local links/anchors/images and 248 public candidates checked with zero findings; 58 external references inventoried, including 17 selected official links checked successfully during this pass |
| Git                       | Unborn `master`, no tracked files, commits or remote; `git diff --check` clean, with untracked files reviewed separately                                                                            |

Exact commands, dated coverage, warnings and verification failures repaired before acceptance are in [validation](validation.md), [reproducibility](reproducibility.md), and the [dependency audit](dependency-audit.md). No test was weakened. No hosted CI, independent scientific review, complete accessibility certification, Linux/macOS execution, or container success is claimed. Software checks do not establish biological or clinical truth.

No actual credential was found that would require rotation. Dummy test strings are intentional. Scanners cannot prove absence of every secret. The one high advisory remains visible; it is not suppressed or misreported as a clean full audit.

Apache-2.0 is retained for project code. Font OFL notices and numerical/source-fixture licenses are present. The video includes one CC BY-NC 4.0 passage whose noncommercial restriction remains separate from Apache-2.0; see [the attribution](../THIRD_PARTY_NOTICES.md#additional-demo-video-source-material). The source repository does not redistribute full papers or raw research caches.

## Public tree

The final candidate set contains **248 files, approximately 8.1 MB**, including the 5.30 MB video. No individual file exceeds the 10 MB review threshold. The initial set was 328 files / 11.7 MB; selected publication material replaced the bulk screenshot dump. The tree below is condensed, not a claim that generated local directories were deleted.

```text
CausalBio Lab/
├── apps/
│   ├── api/                 # HTTP boundary and API tests
│   └── web/                 # UI, component/browser tests, capture scripts, font notices
├── packages/causalbio-core/ # Scientific code, tests and attributed fixtures
├── data/
│   ├── demo/               # Public curated packs and synthetic data
│   ├── evals/              # Deterministic question cases
│   └── cache/.gitkeep
├── docs/
│   ├── README.md           # Methods, architecture, validation and design index
│   ├── assets/             # Six screenshots, preview, video and review records
│   ├── project-defense-guide.md
│   ├── portfolio-case-study.md
│   ├── college-application-summary.md
│   ├── portfolio-positioning.md
│   ├── demo-script.md
│   ├── demo-transcript.md
│   ├── github-publishing-checklist.md
│   └── ...                 # Scientific methods and dated review documents
├── scripts/                # Seed, graph/evaluation, live checks and release checks
├── .github/                # CI, two issue templates, short PR template
├── docker/                 # API/web Dockerfiles; execution remains unverified
├── artifacts/.gitkeep
├── README.md
├── LICENSE / NOTICE / THIRD_PARTY_NOTICES.md
├── CONTRIBUTING.md / SECURITY.md / CODE_OF_CONDUCT.md
├── CHANGELOG.md / CITATION.cff / IMPLEMENTATION_PLAN.md
├── .env.example / .gitignore / .dockerignore
├── .editorconfig / .pre-commit-config.yaml
└── package.json / pnpm-lock.yaml / pnpm-workspace.yaml / pyproject.toml / docker-compose.yml
```

## Presentation review

This was a content inspection, not a timed user study or rendered public GitHub test:

- **15 seconds:** the opening sentence, three bullets, workspace image and real demo link explain the purpose and appearance without setup instructions or badge clutter.
- **60 seconds:** the workflow, architecture boundaries, concrete methods and current test/coverage summary explain how it works and what was checked.
- **10 minutes:** linked graph, Petri/ODE, Bayesian, evidence, safety, validation and reproducibility documents expose assumptions and implementation references. The defense guide covers all 28 requested questions and gives owner practice tasks.

The README remains a summary; detailed methodology stays in `docs/`. Personal claims are explicitly marked **OWNER REVIEW REQUIRED**. No claim is made that the repository establishes the creator's independent understanding.

## Review rubric

Editorial self-assessment, 0–5 per dimension, not an admissions score, independent evaluation, or prediction. Scores identify the next useful work rather than justify more features.

| Dimension                | Score | Evidence and remaining gap                                                                                                                       |
| ------------------------ | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Original problem framing | 4     | Inspectable mechanisms address fragmented evidence; novelty relative to other research tools has not been independently established              |
| Technical depth          | 4     | Typed evidence graphs, ODE execution and synthetic HMC with analytic/numerical checks; models remain deliberately bounded                        |
| Engineering complexity   | 4     | UI/API/core, providers, persistence, exports and multiple test layers integrate coherently; shared deployment is outside scope                   |
| Scientific maturity      | 4     | Context, counterevidence, provenance and inference boundaries are explicit; no expert adjudication or broad biological validation                |
| Validation               | 4     | Meaningful failure, numerical, persistence and production-browser tests plus current coverage; Chromium/Windows and bounded fixtures limit scope |
| Reproducibility          | 4     | Independent public-source installation, seed/startup/full checks passed; actual remote clone and hosted platform execution remain owner steps    |
| User experience          | 4     | Mechanism-first notebook layout, citations, text alternatives and responsive review; dense graphs and lengthy extracts still need refinement     |
| Ownership                | 2     | Decisions and defense material are documented; personal contribution and ability to explain/modify code require owner confirmation               |
| Presentation             | 4     | Scannable README, six selected screenshots, real captioned demo and concise case study; public repository card and hosted demo not yet live      |
| Growth / iteration       | 4     | Dated reviews document two-topic routing, extraction and UI failures and revisions; no fabricated Git chronology or measured user study          |

## Remaining actions

The owner must confirm contribution/assistant-use wording, inspect the candidate tree, create the intended repository, commit/push the real source, confirm hosted CI, set metadata/social preview, host the reviewed video, and publish the real v1.0.0 tag/release. Exact steps and a truthful initial-import command sequence are in the [publishing checklist](github-publishing-checklist.md).

Technical limitations remain: the unfixed development advisory; Python dependency ranges rather than a full transitive lock; internet access for initial installs/fonts; unvalidated container/OS/browser combinations; two small curated packs; bounded and sometimes context-mismatched live research; dense full graphs; and educational numerical models. The roadmap prioritizes those concrete gaps. No further scientific feature was added for presentation value.
