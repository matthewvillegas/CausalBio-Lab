# Data sources and provenance

## Current data boundary

Curated investigations remain available offline through checked-in, manually curated files. The general research workflow can additionally retrieve provisional evidence from public scientific sources:

- `data/demo/memory/pack.json` — memory pack version `memory-1.1.0`;
- `data/demo/knee-pain/pack.json` — knee-pain pack version `knee-pain-1.1.0`;
- `data/demo/peptides/known-peptides.json` — two curated known human tachykinin sequences and annotations;
- `data/demo/inference/linear-response.json` — explicitly synthetic HMC parameter-recovery data;
- `data/evals/offline-evals.json` — deterministic software evaluation cases.

Each biological pack currently contains six evidence records. The memory pack contains 18 entities, 15 assertions, three hypotheses, and three interventions; the knee-pain pack contains 19 entities, 18 assertions, three hypotheses, and four interventions. These are small educational slices, not systematic reviews or complete pathway databases.

## Biological literature records

The biological evidence records contain manually verified PubMed or PubMed Central metadata and direct source URLs. Their `source_adapter` values identify manual PubMed or PubMed/PMC verification; the label is provenance metadata, not an executable live adapter.

Each record includes study title, authors, year, journal, study design, population, identifiers, experimental context, source URL, result direction, limitations, evidence note, retrieval date, curation state, and grade. A short supporting excerpt may be included within the schema's 500-character limit. Full articles are not bundled.

The repository does not claim that a source's presence endorses every graph interpretation. Assertions keep supporting and contradictory record UUIDs separate, and curator interpretation and limitations are stored alongside the original metadata.

## Source discovery versus source curation

The older `/api/v1/literature/search` API retains two explicit modes:

- **bundled:** searches normalized records already present in the selected local pack;
- **live:** returns a structured 503 response because external retrieval is not enabled on this legacy route.

The general `/api/v1/research` workflow uses bounded Europe PMC core search, PubMed ESearch/ESummary, and relevant UniProtKB searches. It preserves retrieved evidence as provisional research records and builds a separate temporary evidence map. It does not insert records into the curated graph or grant executable biological-model eligibility. Every displayed source extract retains its supporting passage and evidence citation. A citation and a matching extract do not establish causal entailment or clinical applicability.

Live research is enabled by default in the local application and can be disabled through configuration or the request's `online` flag. Offline requests use validated fresh/stale caches and relevant local curated records, retaining their original retrieval dates; no external network transport is used. Scientific search terms are sent to these public services when live retrieval is enabled. Crossref, Reactome, Open Targets, ChEMBL, ClinicalTrials.gov, Gene Ontology, Human Protein Atlas, and RCSB adapters are not implemented.

## Core source-adapter behavior

The three core adapters share a typed `SourceSearchRequest`: normalized queries are 2–500 characters and result limits are 1–50. They use adapter-controlled HTTPS endpoints rather than caller-supplied URLs, disable HTTP redirects, and cap decoded response bodies at five megabytes while streaming, closing an oversized response immediately. Injected transports are also size-checked. Non-200 responses, invalid UTF-8/JSON, missing required fields, and invalid counts raise explicit typed errors rather than producing records.

Europe PMC retrieves bounded `resultType=core` results, normalizing publication identifiers, title, authors, year, journal, publication types, source-supplied abstract, and license metadata when present. The echoed query, result type, and page size must match the request. Abstract HTML is converted to plain text; script/style elements are discarded. Species, population, tissue, cell type, effect size, and sample size are not invented from a publication title. The adapter does not fetch full text or classify clinical applicability.

PubMed returns normalized citation metadata from ESearch and ESummary; it does not retrieve or invent abstracts. UniProt returns normalized accession, name, genes, organism, review status, sequence length, function text when present, identifiers, and canonical URL. Function annotations preserve the source's optional `molecule` scope and its evidence codes/source identifiers. The legacy flattened `functions` tuple remains for compatibility, but explanations must use scoped `function_annotations`: a precursor's annotation does not establish the activity or sequence of a mature peptide. Missing optional metadata remains absent. Adapter version `uniprotkb-json-search-3` uses a new cache key so earlier flattened records are not silently reused as scoped annotations.

Validated results use a content-addressed filesystem cache under `data/cache/sources` by default. Cache keys include adapter version, query, and limit but not PubMed email or API key. The default time-to-live is 24 hours. A fresh entry avoids a network call; an expired validated entry may be returned with an explicit stale warning only when retrieval fails and the request permits it. Corrupt, identity-mismatched, oversized, or schema-invalid entries are ignored or rejected and never treated as trusted source data.

Adapter tests inject checked-in PubMed, Europe PMC, and UniProt response fixtures and remain offline. Transient transport failures and HTTP 408/425/429/5xx receive at most three attempts by default, with 0.25-second exponential backoff capped at two seconds. Retry-After seconds/date values are honored; if the requested delay exceeds the cap or remaining search budget, retrieval stops. Requests are paced at least 0.34 seconds apart per source across adapters in one process; waiting for the pacing lock and the next request slot is also bounded by the remaining budget. Multi-worker deployments still need a shared upstream rate limiter. Redirects, other status errors, and malformed data are not retried. Duplicate IDs, result counts above the requested limit, inconsistent totals, changed citation identity, and missing/unknown UniProt review classifications fail closed.

Default per-request timeouts are ten seconds for PubMed/UniProt and eight seconds for Europe PMC. Default adapter search budgets are thirty and twenty seconds respectively. The research workflow configures five-second request timeouts, fourteen-second adapter budgets, and at most two attempts online; offline cache fallback permits one failed transport attempt. The research service waits at most twenty-two seconds for provider futures and returns completed providers while marking overdue providers unavailable. Already-running synchronous provider calls cannot be force-cancelled by that future deadline.

These are cooperative bounds, not a hard operating-system wall-clock kill. The transport checks elapsed time after each decoded transport chunk and at completion, and closes on detected expiry. HTTPX phase timeouts bound a stalled socket operation, but DNS, connection phases, decoding, or one active read can finish after the deadline. A deadline does not guarantee that every worker has stopped when the partial investigation is returned. Deployment isolation and admission limits remain necessary for adversarial or persistently unhealthy upstreams.

The opt-in `scripts/check_sources_live.py` smoke passed with fresh temporary caches on **2026-10-03 UTC** (October 2 in America/Chicago): PubMed `2869411[uid]` returned PMID 2869411 at 02:49:15 UTC, UniProt `accession:P01303` returned P01303 at 02:49:17 UTC, and Europe PMC `EXT_ID:41303871 AND SRC:MED` returned MED:41303871 at 02:49:19 UTC. These three contract checks do not establish comprehensive availability or scientific validity. The Europe PMC fixture includes an attributed CC BY 4.0 abstract; see its [fixture provenance](../packages/causalbio-core/tests/fixtures/source_adapters/README.md). Candidate assertions still require licensing review, evidence modeling, and human curation before entering the curated graph.

## Known-peptide registry

The peptide registry contains Substance P and Neurokinin A, their declared human precursor, source URLs, known-target annotations, biological contexts, terminal amidation, and selected structure annotations. The API exposes read-only catalog, analysis, and comparison routes by registry slug. It provides no arbitrary-sequence POST endpoint.

For a registered sequence, the implementation calculates composition, approximate molecular weight, charge at a declared pH, a Brent-root isoelectric point when a finite zero exists, Kyte–Doolittle hydrophobicity, idealized alpha/beta hydrophobic moments, charge density, and normalized sequence entropy. Pairwise comparison uses a documented global alignment to report literal identity and conserved positions.

These are calculations or database annotations, not measurements, structure predictions, binding predictions, efficacy estimates, or safety claims. The current `measured_properties` mappings are empty. The registry explicitly excludes novel sequence generation, synthesis instructions, and personal-use guidance.

## Pack loading and stable identifiers

The human-reviewable JSON packs use short local keys. The domain registry converts those keys into deterministic UUIDs scoped by pack and object type, constructs strict Pydantic models, and validates cross-references. It discovers immediate `<slug>/pack.json` directories under an injectable root instead of registering domains in code. The production root currently contains the two biological packs; the synthetic third-pack contract fixture lives under tests. [Domain-pack authoring](domain-pack-authoring.md) documents the validated interpretation metadata and required checks.

The loader creates typed:

- biological entities and external identifiers;
- studies and evidence records;
- causal assertions;
- competing hypotheses and mechanism paths;
- intervention research objects;
- Petri places, transitions, arcs, and models.

Constructed domain objects and metadata use closed Pydantic models that reject unknown fields. The compact object-key format is mapped by the registry rather than a published JSON Schema, so raw-format changes still require loader tests and review. Duplicate raw keys are rejected before UUID mapping. Trusted assertions require trusted entities and supporting/counterevidence; graph and pack validation check duplicate IDs/names, provenance, references, and the direction and endpoints of every mechanism path. Petri models may be absent. Numerical-readiness metadata is validated but cannot enable biological inference without a reviewed backend/model/data contract.

## SQLite snapshot

`scripts/seed_demo_data.py` loads every registered pack, revalidates it, and atomically replaces that pack's rows in a local SQLite database. The snapshot stores normalized lookup columns plus complete JSON payloads. Pack metadata records:

- pack, graph, schema, software, evidence-rubric, and Petri-model versions;
- retrieval dates;
- entity, evidence, assertion, hypothesis, intervention, and model counts;
- a SHA-256 digest of canonical, sorted JSON content.

Loading from SQLite reconstructs and revalidates a complete `DomainPack`. The checked-in JSON is the present curation source; SQLite is a materialized runtime and reproducibility snapshot, not an independent scientific source.

## Synthetic inference data

The HMC fixture contains 40 generated values from a two-group linear Gaussian equation with known parameters and noise. It is labeled `synthetic: true` and records the generating seed and equation. It is not derived from people, animals, publications, patient records, or the biological packs.

Synthetic data are appropriate for parameter recovery and sampler diagnostics. They provide no evidence for a biological mechanism or intervention.

## Evaluation fixtures

The offline evaluation fixture covers representative question routing, relation and causal-status preservation, species context, contradictions, intervention-versus-outcome distinctions, safety boundaries, and source grounding. `scripts/run_evals.py` performs deterministic pass/fail checks.

These cases are regression fixtures, not a statistically representative benchmark. The project does not publish accuracy, precision, citation-entailment, or clinical-safety performance metrics from them.

## Licensing and responsible reuse

The project code is Apache-2.0. Third-party publication metadata, abstracts, excerpts, identifiers, and linked full text remain subject to their source terms. Contributors must verify that any new stored content is permitted for redistribution, retain attribution, keep excerpts minimal, and avoid checking in copyrighted full text without an appropriate license.

Never fabricate a source, identifier, quote, effect estimate, sample size, retrieval date, or verification status. If a value cannot be verified, omit it or mark the uncertainty explicitly.

## Remaining adapter integration requirements

The core supplies normalized source identity checks, bounded retries/pacing, streamed size caps, deterministic cache fixtures, provisional live research, and the local auditable candidate workflow described in [evidence-model.md](evidence-model.md). Before a public deployment, add deployment egress controls, admission controls, shared rate limiting across processes, monitoring and credential operations, source-specific redistribution/license review, authenticated curator access, and independent source-entailment review. Do not treat the provider protocol or local queue as a production review service.
