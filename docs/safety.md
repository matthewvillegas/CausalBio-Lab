# Safety, privacy, and product boundaries

## Product boundary

> CausalBio Lab provides research-oriented mechanism analysis. It does not diagnose conditions or tell individuals what treatment or substance to use.

CausalBio Lab is research software for inspecting biological mechanism hypotheses and evidence. It is not a physician, emergency service, medical device, diagnostic engine, treatment planner, prescribing system, dosing calculator, procurement assistant, synthesis assistant, or predictor of an individual's outcome.

The bundled content is educational and incomplete. A graph path, intervention card, evidence grade, plausibility index, Petri trajectory, or synthetic posterior must not be presented as clinical validation or personalized advice.

## Query classification

Before an investigation is constructed, a deterministic classifier assigns one of these classes:

- general biological research;
- symptom education;
- intervention-mechanism research;
- diagnostic request;
- personalized prescribing request;
- dosing request;
- substance-acquisition request;
- synthesis request;
- dangerous self-experimentation request;
- urgent symptom description.

The classifier uses transparent regular-expression rules. Urgent patterns are checked first, followed by restricted self-experimentation, synthesis, acquisition, dosing, prescribing, and diagnostic patterns. Symptom and intervention education remain allowed with a boundary notice. Restricted classifications stop the investigation rather than quietly generating a mechanism report.

## Allowed use

For general biological and symptom research, the application may:

- map curated mechanisms and competing hypotheses;
- distinguish experimental, associative, mechanistic, genetic, computational, and hypothetical claims;
- summarize supporting and contradictory evidence;
- show species, tissue, population, and temporal context;
- compare intervention classes by mechanism, evidence, maturity, uncertainty, and broad safety concerns;
- execute explicitly curated educational pathway models;
- report limitations, unknowns, and translation barriers.

Existing drugs, peptides, therapies, behaviors, experimental compounds, and devices may appear as research objects. Their model fixes `personal_recommendation` to `false`.

The known-peptide surface is additionally closed to arbitrary sequences: it lists two curated published human peptides and accepts their registry slugs for read-only property analysis or comparison. Calculated mass, charge, isoelectric point, hydrophobicity, hydrophobic moment, sequence entropy, alignment, and identity are descriptive calculations. They do not establish receptor binding, activity, delivery, efficacy, or safety. There is no sequence-generation, synthesis, dosing, or arbitrary-sequence endpoint.

## Restricted use

The application does not provide:

- individual diagnosis or reassurance that excludes a condition;
- a choice of drug, substance, device, exercise, or treatment for a particular person;
- doses, schedules, routes, titration, cycling, formulation, or administration optimization;
- purchasing, sourcing, prescription-evasion, or access instructions;
- chemical or peptide synthesis procedures;
- novel sequences claimed to have biological effects;
- protocols for injection, home infusion, or other self-experimentation;
- claims that an animal, cell, computational, or synthetic result proves a human effect;
- claims that a simulation predicts what will happen to an individual.

Restricted requests receive an explicit explanation and may be redirected only to general published mechanism, evidence, limitations, and major safety concerns.

## Urgent descriptions

The current rules flag a small set of warning phrases such as inability to breathe, chest pain, unconsciousness, severe bleeding, suicidality, major trauma or deformity, inability to bear weight, or a hot swollen joint. The response directs the user to immediate real-world emergency or urgent medical help.

This is not clinical triage. The list is incomplete, wording-dependent, English-centric, and unable to assess severity or circumstances. Failure to trigger an urgent notice does not mean a situation is safe. The application should never delay real-world care.

## Symptom and intervention language

Symptom investigations present mechanism families, not diagnoses. For example, activity-related knee pain keeps mechanical loading, tissue adaptation, pain sensitivity, and alternative anatomical contexts distinct. Memory investigations distinguish encoding, consolidation, retrieval, attention, and motivation.

Interventions are not ranked as personal recommendations. Any comparison is research-oriented and must retain maturity, uncertainty, translational limits, and major safety concerns. No output should use imperative treatment language.

## Scientific safety controls

Implemented controls include:

- typed, closed schemas that reject unknown fields;
- first-class evidence and assertion provenance;
- trusted-only graph projections by default;
- explicit causal-status labels;
- separate contradictory-evidence links;
- species and context visibility plus extrapolation penalties;
- a plausibility index labeled as a heuristic, not a probability;
- inference gating with no fake fallback;
- simulation safety labels and bounded numerical inputs;
- deterministic report generation from structured records.

These controls reduce overclaiming but do not replace expert review. Manual curation can be wrong, evidence packs can be incomplete, and heuristic ranking can encode value judgments.

## Source and prompt-injection boundary

Paper text, abstracts, metadata, URLs, and future adapter responses are untrusted content. They may provide data to a validated extraction and curation process, but they must never alter application instructions, bypass the safety classifier, execute code, reveal secrets, or create trusted claims automatically.

Curated investigations use bundled records. The legacy literature route's `live` mode remains disabled, while the general research route uses bounded Europe PMC, PubMed and UniProt retrieval. These adapters use fixed HTTPS endpoints, disabled redirects, bounded inputs, timeouts, streamed response-size limits, closed output schemas, and validated caching. Retrieved evidence remains provisional and is never inserted into the trusted graph automatically. Deployment still requires egress controls, licensing review, access control and audit policies.

## Privacy

Local mode does not require a legal name, address, insurance information, medical record, or exact date of birth. `CAUSALBIO_NO_LLM` and `CAUSALBIO_NO_TELEMETRY` default to true. Interpretation is local, but live research sends scientific query terms to public source providers. Disable live retrieval to use only cached or bundled evidence; avoid identifying information in every mode.

The legacy curated API keeps runtime investigation indexes in process memory. General research sessions and immutable reports persist in a separate local SQLite database; generated artifacts can contain submitted questions and context. The bundled SQLite snapshot stores curated packs. There is no authenticated multi-user isolation or user-facing deletion API. Users should avoid sensitive health information and manage local databases and artifacts according to their own retention needs.

The project has not established HIPAA, GDPR, medical-device, or other healthcare-regulatory compliance and must not be described as compliant.

## Security boundary

Local API controls include schema validation, a request-size check, process-local rate limiting, correlation IDs, safe problem responses, restricted response headers, configured CORS, environment-backed configuration, and report-artifact path containment. These are local-demo safeguards, not a production security architecture. See `SECURITY.md` for deployment limitations.

## Classifier limitations and review

Regex classification can miss paraphrases and can also flag benign text. Safety precedence is deterministic but does not understand intent, language variety, negation, or clinical context. Tests cover representative allowed and restricted inputs, not every possible phrase.

Safety rules, demo content, and user-visible language should be reviewed whenever new domains, interventions, source adapters, generation models, or storage modes are added. A feature that broadens actionability requires an explicit safety review before release.
