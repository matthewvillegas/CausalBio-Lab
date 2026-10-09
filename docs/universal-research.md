# General biological research

The original unknown-topic failure came from `questions/interpreter.py`: every investigation had to match an installed curated pack. The UI now starts with `/api/v1/research/interpret`, whose router preserves the curated path and selects an evidence-research fallback for other recognizable biological subjects. Legacy curated endpoints remain available for reproducible pack workflows.

## Processing and trust boundaries

1. Validate the question and edited context, then classify safety before any source request.
2. Match installed pack metadata and named-entity coverage. A familiar outcome does not make an unrepresented compound part of a curated pack.
3. Use lexical entity aliases and a bounded query plan for new topics. These hints are not biological evidence. Show the interpretation and queries for correction.
4. Retrieve Europe PMC abstracts/metadata, PubMed citation metadata, and relevant UniProt protein annotations through the shared typed source interface. Quick requests up to four main-search records per literature provider; Research requests eight Europe PMC and six PubMed records; Deep requests twelve and six. Research and Deep add separate Europe PMC searches for up to three limiting/opposing-findings records and three overview-review records. A recognized gene/protein/receptor query can add up to three UniProt entries. Provider overlap is deduplicated by PMID/DOI.
5. Preserve original context and retrieval time. Unavailable metadata remains unknown: publication type alone does not establish species, study population, effect size, or independent replication.
6. Extract exact source sentences, exclude operational passages, prioritize relevant biological statements over procedure descriptions, and cluster shared biological vocabulary into at most six topics (three for Quick). Fewer topics are shown when evidence cannot support more. Sentence ordering is a presentation heuristic, not an evidence-strength grade.
7. Link every displayed claim to a retrieved record. Titles without abstracts cannot support detailed mechanism claims. Schema validation checks source passages, citation references, graph endpoints, claim identity, and timestamps.
8. Return a provisional evidence map, uncertainty, available modifiers, partial-source notices, and immutable local reports. A limiting sentence does not automatically become a contradiction edge. No provisional edge is written to the trusted curated graph.

The router has explicit modes for curated, live, general cached/local summary, explanation, clarification, restricted-with-alternative, out-of-domain, and error handling. User-facing labels describe what is available rather than exposing enum names. Explanatory questions lead with retrieved protein function annotations when available; otherwise they use source excerpts. UniProt functions preserve the source's molecule/form scope, species, and annotation evidence, so a precursor's role is not silently assigned to its mature product. Multiple annotations from one entry remain one database source. These are extractive introductions, not unrestricted generated explanations.

## Scope of the map and models

Live maps currently connect mechanism topics to cited studies or annotations using source relationships. They do not infer molecular causal triples from association language. Grouping uses shared terminology and source context; no semantic embedding model, pathway database enrichment, or causal-discovery algorithm is implemented. Reports state this explicitly.

Every provisional group is currently `GRAPH_ONLY`. Curated models retain their separately declared availability. Literature retrieval does not supply a likelihood, identify parameters, or authorize a Petri/ODE simulation. The synthetic HMC teaching demonstration remains separate from biological inference.

Known drugs and peptides can be researched through literature. Sequence calculations remain limited to the validated Substance P and Neurokinin A registry; arbitrary peptide design, synthesis, dosing, and procurement are absent. Reactome, ChEMBL, Open Targets, clinical-trial, expression, and structural databases are not yet integrated.

## Failures, offline use, and privacy

Each provider failure is isolated. The coordinator returns available results after a 22-second source deadline; adapters have a 14-second cooperative budget and bounded retry/pacing/response sizes. Existing synchronous network calls cannot be forcibly killed, so a provider worker may finish after the response. The shared pool limits active provider workers to six. This local implementation is not a distributed job service or a hard real-time execution boundary.

Disabling live research uses validated cached responses and relevant local curated records without network access. Cached dates are never replaced with the current date. With insufficient evidence, the app shows the gap and supports query editing, retry, or curated examples; it does not invent an explanation. The status label reports configuration, not guaranteed external connectivity.

Scientific search terms are sent to the selected public providers when live research is enabled. Search planning reduces question phrasing but is not a personal-information redaction guarantee; do not include sensitive personal information. There is no LLM or telemetry. Original questions and results are saved in a separate local SQLite database, with immutable evidence and report snapshots. See [persistence](research-persistence.md) and [source contracts](data-sources.md).

## Safety behavior

The router separates operational intent from an identifiable research subject. A restricted acquisition, dosing, or synthesis question can offer a new mechanism/evidence question, preserving a recognized outcome where possible. Source retrieval starts only when the user selects that alternative. Unknown placeholders require a real subject; urgent symptom descriptions do not trigger automatic research. Normal questions about drugs, endogenous synthesis, dose-response concepts, receptors, hormones, and published peptides remain researchable.

Safety classification is deterministic and lexical. Tests cover the documented examples and edited-context boundary; they do not establish comprehensive adversarial safety, diagnostic performance, or reliable intent recognition for every paraphrase.

## Verification

Tests use injected source transports and synthetic explicitly labeled fixtures for deterministic failures and UI contracts. Live smoke checks and manually inspected question-matrix outputs are recorded separately in [validation](validation.md). Automated passing checks are evidence of software behavior, not biological correctness, full-text review, systematic coverage, clinical validity, or novice comprehension.
