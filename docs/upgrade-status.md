# Upgrade work record

This record describes the implemented upgrade. [Validation](validation.md) is the consolidated record of commands, observed results, and remaining verification limits; [live research validation](live-research-validation.md) records actual provider behavior and question review. Implementation completion does not establish scientific correctness or user comprehension.

## Scope and order

1. UX 2.0: simplify the existing two curated examples before adding domains.
2. Domain-pack architecture: metadata-driven interpretation/registration, optional models, third-pack fixture, graph integrity and context validation.
3. Evidence engine: source robustness, auditable candidate review, conservative claim correction.
4. Scientific validation: ranking sensitivity, Petri conservation/gates, Bayesian recovery and diagnostics.
5. General research: preserve curated investigations while adding bounded source retrieval, explanatory answers, safe alternatives, provisional evidence maps, and saved research sessions.

## Saved implementation

- `docs/ux-audit.md`: ten primary UX findings, original test baseline, honest startup failures.
- `docs/scientific-audit.md`: 33 assertion dispositions and twelve source checks, with full-text verification limits.
- New question → interpretation → mechanism cards → focused pathway/evidence/intervention flow. Advanced tools lazily load and stay mounted after first use. Library consumes existing API metadata.
- Focused graph expansion and semantic edge styles; selected mechanism is carried into graph exploration. No scientific API calls on display filters.
- Evidence intervals and uncertainty retained. Backend returns actual per-edge support for strongest/weakest-link explanations.
- Petri scenario schema is model-driven; simulation handles missing models and stale controls. All three labs and summary-first reports are implemented and covered by interaction tests.
- ChartFrame mounts charts only at positive measured dimensions while preserving lab state. Hidden panels no longer emit Recharts warnings.
- Metadata-driven pack registry, strict context/identity, graph integrity, third-pack fixture and CLI are implemented. Packs can omit numerical models; readiness metadata alone does not enable inference.
- Bounded source transport/retries/pacing and a separate append-only candidate curation store are implemented. Candidate decisions retain provenance and never directly mutate the trusted graph.
- Validated ranking weights and local sensitivity are recorded with results. API exports use the investigation snapshot; report persistence=false performs no disk write; streamed request bodies are bounded.
- Rank-normalized HMC diagnostics and numerical fixtures are implemented, including an independent pinned diagnostic reference, recovery, gradient, reversibility and sensitivity checks. Petri fixtures exercise conservation, equilibria, gates and bounds.
- A tiered question router preserves installed curated coverage and supports new biological subjects through Europe PMC, PubMed and UniProt. Safety classification runs before retrieval; restricted operational requests can offer a separate scientific question for the user to select.
- Quick, Research and Deep retrieval are bounded. Research and Deep include limiting-findings and overview-review searches. Provider failures return partial results, validated caches retain original timestamps, and offline mode uses cached or relevant local evidence without source requests.
- Provisional claims retain exact source passages and citations, with unknown context left unknown. Grouping and evidence maps use shared terminology rather than inferred molecular causality. UniProt functions retain molecule/form scope and annotation evidence. New groups remain graph-only.
- General research has its own results view, explanatory answers, status and depth controls, evidence metadata, local history, and immutable cited HTML/Markdown/JSON reports. These sessions are stored separately from curated graph data.

## Verification record

The original audit and intermediate UX checks are preserved in [the UX audit](ux-audit.md). Their test counts and startup failures describe earlier revisions, not current acceptance. Next's webpack mode was selected after reproducible Turbopack React Client Manifest failures in this Windows checkout.

Current automated checks cover the Python core and API, deterministic evaluation fixtures, graph integrity, frontend formatting/lint/types/unit tests, production build, and browser workflows. Source-failure and UI contract tests use injected or explicitly synthetic fixtures; actual external retrieval is assessed separately. Consult [validation](validation.md) for the commands that were run and their results rather than inferring a pass from this implementation list.

Production screenshots and browser review are part of the final verification record. An older screenshot is not proof that the final revision was inspected. Neither scripted timing nor an automated browser pass establishes novice comprehension; no independent human usability study is claimed.

## Remaining product limits

Broad research currently produces bounded, extractive introductions and topic/source maps. Some questions receive narrow, incomplete, or insufficient source coverage. The system does not perform systematic review, infer a validated causal pathway from abstracts, or create a justified numerical model for arbitrary questions. Exact source matching verifies traceability rather than independent scientific correctness. See [general research](universal-research.md), [limitations](limitations.md), and the live question-review record for practical boundaries.

Authentication, multi-user isolation, production curator tooling, additional biological databases, and broader validated numerical models remain future work. These are separate from the implemented local upgrade.

The repository was entirely untracked at the start, so `git diff` alone cannot show the upgrade relative to a committed baseline. Do not create a commit or erase existing files merely to manufacture a diff.
