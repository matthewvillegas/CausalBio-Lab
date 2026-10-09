# Question interpretation

## Scope and implementation status

Question interpretation is deterministic and offline. It supports two curated demonstration domains: long-term memory and activity-related knee pain after jumping or landing. It does not use an LLM, perform open-domain entity linking, infer a diagnosis, or search the internet.

The output is a typed `ResearchQuestion` with normalized text, question classes, an interpreted summary, a structured `QuestionContext`, uncertainties, and a deterministic UUID.

## Processing order

The API and investigation service use this sequence:

```text
submitted question
→ safety classification
→ stop if restricted
→ whitespace normalization
→ supported-domain routing
→ domain-specific context template
→ validated context updates
→ investigation construction
```

Safety runs before scientific interpretation. A request for diagnosis, prescribing, dosing, acquisition, synthesis, dangerous self-experimentation, or urgent-symptom handling does not proceed to a normal mechanism investigation.

## Normalization and validation

Leading and trailing whitespace is removed and internal whitespace is collapsed. Questions shorter than three characters are rejected. Original normalized capitalization is retained in `original_text`, while `normalized_text` is case-folded for stable matching. The schema caps question text at 2,000 characters.

Context updates are limited to declared `QuestionContext` fields:

- requested outcome;
- symptom or process;
- anatomical region and tissue;
- activity and exposure;
- timing and duration;
- population and condition;
- candidate intervention;
- mechanism/intervention preferences;
- important uncertainty.

Unknown context field names are rejected. Context improves relevance; it does not permit diagnosis.

## Domain routing

Memory routing recognizes terms such as memory, remember, retention, consolidation, forgetting, and learning. Knee routing recognizes terms such as knee, patellar, patellofemoral, jumper's knee, jumping, and landing.

If both families occur, the interpreter asks the caller to investigate one outcome at a time and returns alternatives. The single word `retention` is also rejected as ambiguous, with biological and nonbiological alternatives. A question matching neither domain receives a clear unsupported-domain error that names the two available packs.

This is lexical routing. It does not understand arbitrary synonyms, spelling variation, negation, multilingual input, or all legitimate questions within the two fields.

## Memory interpretation

Memory questions are mapped to long-term memory persistence after an encoding event, with a context spanning hippocampal and distributed neural systems. The interpreter explicitly keeps apart:

- encoding;
- consolidation;
- retrieval;
- attention;
- motivation;
- forgetting or persistence.

The research context is general human relevance with animal evidence labeled separately. The bundled workflow includes intervention research objects, but does not recommend one or imply that a molecular mechanism is proven to improve a person's memory.

## Knee-pain interpretation

Knee questions are mapped to pain during or after repeated jumping or landing. Patellar-tendon and patellofemoral structures remain competing contexts. The interpretation explicitly separates:

- exposure and movement mechanics;
- estimated tissue loading;
- tissue adaptation or stress constructs;
- nociceptive signaling;
- reported pain;
- a clinical diagnosis.

The question alone cannot identify patellar tendinopathy, patellofemoral pain, or another condition. The output is educational mechanism research in a general context.

## Question classes and intervention intent

Memory questions receive `biological_process` and `pathway` classes. Knee questions receive `symptom_mechanism` and `pathway` classes. Terms such as intervention, therapy, drug, exercise, or loading program—and “which” questions—are recognized as intervention interest. Both current pack templates expose intervention comparisons as research objects.

Question classes organize the workflow; they do not establish a scientific claim or safety clearance.

## Errors and client behavior

Interpretation failures are returned as structured problem details with a correlation ID and, for ambiguous cases, suggested alternatives. The client should preserve user text, explain the boundary plainly, and allow revision. It should not silently route an unsupported question to the nearest pack.

Changing display mode or graph filters does not reinterpret the question. Changing the research question or scientific context requires a new investigation so the provenance record remains coherent.

## Limitations and roadmap

The deterministic interpreter is reproducible and testable, but intentionally narrow. Future open-domain interpretation requires ontology-assisted entity linking, calibrated relation extraction, source grounding, ambiguity handling, and evaluation. An optional LLM could propose structured fields only behind a provider abstraction, schema validation, citation enforcement, prompt-injection controls, and a no-LLM fallback. It must not bypass safety or create trusted assertions directly.
