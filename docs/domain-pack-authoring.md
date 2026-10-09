# Authoring a domain pack

CausalBio Lab discovers reviewed offline packs from `data/demo/<slug>/pack.json`. A new pack supplies data and metadata to the existing question, mechanism, graph, intervention, and report components. It does not require a new interpreter branch, route, React component, or domain allowlist. Discovery is limited to immediate child directories; a slug uses lowercase letters, digits, and separating hyphens. Paths outside the registry root are rejected.

The included third-pack contract fixture is in `packages/causalbio-core/tests/fixtures/third-pack/pack.json`. It uses explicitly synthetic records, is loaded only by tests through an injected registry, and must never be copied into production as biological evidence. The two production examples remain memory retention and activity-related knee pain.

## 1. Define the interpretation contract

Create a directory such as `data/demo/tendon-recovery` only after curating its scientific content. Its `pack.json` contains `metadata`, `entities`, `evidence`, `assertions`, `hypotheses`, `interventions`, and an optional `petri_model`. Use the existing packs for the detailed record shapes and `causalbio.domain.models` for their validated enums and fields.

`metadata` is validated by `PackMetadata` in `causalbio/demo/metadata.py`:

| Field | Contract |
| --- | --- |
| `title`, `description`, `educational_notice` | Human-readable domain and scope; do not imply comprehensive coverage. |
| `version` | Version of the curated content. Bump it when claims, evidence, context, or model assumptions change. |
| `curated_at`, `retrieved_at` | An ISO timestamp with timezone and an ISO date. These record curation/retrieval, not publication date. |
| `display_order` | Optional integer; library order breaks ties by slug. |
| `example_questions` | At least one canonical question; the first provides the pack's default interpretation and recovery example. |
| `recognition_terms` | Nonempty, unique terms matched as case-insensitive phrases with word boundaries. Broad terms can overlap another pack and should be tested. |
| `ambiguous_terms` | Optional exact normalized query → clarification alternatives mapping. An ambiguous term never silently chooses a pack. |
| `clarification_label` | Short domain label used when multiple packs match a query. |
| `context_defaults` | A valid `QuestionContext`, described below. |
| `interpreted_summary` | Explain the selected research scope and the distinctions the question may obscure. |
| `question_classes` | Valid `QuestionClass` values. |
| `expected_hypothesis_keys` | Unique keys that must exactly match the supplied mechanism families. |
| `numerical_data` | Availability declarations and an explanation; see numerical gating below. |

`QuestionContext` is a shared schema. Required text fields are `requested_outcome` and `symptom_or_process`; `population` has a general research default. Optional fields are `anatomical_region`, `tissue`, `activity`, `exposure`, `timing`, `duration`, `condition`, and `candidate_intervention`. `wants_mechanisms` and `wants_interventions` accept actual JSON booleans. `important_uncertainty` is a tuple/list of text. Text is trimmed, must be nonempty when present, and is limited to 2,000 characters. Unknown fields, missing required values, and type coercions such as `"false"` for a boolean are rejected. Optional unknown values use `null`.

Interpretation is conservative phrase matching, not entity extraction or arbitrary literature synthesis. More than one matching pack produces clarification. An unsupported question receives the installed packs' canonical alternatives. Context edits are validated again, and normalized text plus the complete normalized context contribute to the question ID. Investigation identity also includes pack version, rubric version, and seed, preventing two context variants from overwriting one result.

## 2. Curate the scientific objects

Each collection uses stable, unique `key` strings. References use these keys; the loader derives UUIDs from the pack slug and object kind. Renaming a key changes that object's identity.

| Collection | Required scientific content |
| --- | --- |
| `entities` | Canonical name, type, description, aliases/identifiers when known, source and curation status. Same-type canonical names must be unique ignoring case and whitespace. |
| `evidence` | Real study title, authors, year, journal, identifiers and source URL; study type and population; experimental context; actual result direction; grade, limitations, retrieval date, adapter attribution, review status. Preserve reported effect estimates and uncertainty when available; use `null` when absent. |
| `assertions` | Directed subject/relation/object, polarity, causal status, confidence grade, biological context, supporting and contradictory evidence keys, interpretation, limitations and review status. Association, computational prediction, and a proposed mechanistic bridge remain distinct from experimentally supported causation. |
| `hypotheses` | Competing mechanism families with trigger, outcome, ordered paths, mediators and optional tissue/cell/pathway references; supporting/conflicting evidence, missing links, uncertainty, intervention references, and a conservative evidence label. |
| `interventions` | Research objects with target entities, affected assertions, supporting evidence, class, maturity, relevance/directness, uncertainty and safety limitations. These are not personal treatment recommendations. An empty list is valid. |

A path contains ordered `entities` and `assertions`; every assertion must connect the adjacent entities in that direction. Its first and last entities must match the hypothesis trigger and outcome. A path cannot repeat an entity. Feedback loops can exist in the overall graph and are reported; they are not flattened into repeated-node evidence paths.

`VALIDATED` and `CURATED` are the only trusted graph states. Proposed/extracted/rejected/outdated material belongs in the candidate review workflow, outside the trusted mechanism projection. Trusted assertions require trusted endpoint entities and trusted supporting/counterevidence. Every mechanism and intervention reference must resolve to the pack's trusted projection; contextual tissue/cell metadata may refer to other pack entities. Never promote source-adapter output just because retrieval succeeded. Review each claim's context and directness; a real paper is not evidence for every proposed edge.

## 3. Supply optional numerical models honestly

Omit `petri_model` or use `null` when no reviewed executable model exists. Mechanism cards, evidence, interventions, reports, persistence, and graph exports still work. The simulation UI explains the missing model instead of creating an illustrative fallback.

A supplied Petri model declares its places, initial values, units, bounds, compartments, transitions/rate laws/parameters, arcs, evidence references, and explicit assumptions. Optional `output_place` selects a declared place. Optional `scenarios` define named parameter/initial-value changes, with declared baseline and full-strength values. Transition evidence links must resolve, and the Petri engine validates topology and supported rate laws. A toy model must visibly say that its states and parameters are illustrative. A citation does not calibrate a model parameter by itself.

`metadata.numerical_data` requires `explanation` and has five boolean declarations, all defaulting to `false`: `observations_available`, `unknown_parameters_defined`, `priors_defined`, `likelihood_defined`, and `identifiability_reviewed`. Set these only after that material has actually been supplied and reviewed. These fields describe readiness; they are not a dataset ingestion format or permission to execute inference. This release has no pack-specific likelihood/backend binding, so biological Bayesian inference remains ineligible even if every declaration is true. The standalone synthetic HMC demonstration is separate from pack evidence. Adding real numerical observations will require a versioned observation schema, provenance and units, a validated likelihood/backend binding, and recovery/identifiability tests before eligibility can change.

## 4. Validate expected behavior

From the repository root:

```sh
pnpm graph:validate
pnpm eval
pnpm python:test
pnpm test
pnpm test:e2e
```

For a separate fixture directory without installing a production pack:

```sh
pnpm graph:validate --pack-root packages/causalbio-core/tests/fixtures --as-of 2026-10-02
```

The validator exits nonzero on invalid metadata, duplicate object IDs/keys/names, missing references or provenance, untrusted dependencies, malformed paths, or invalid model structure. Its JSON output also reports feedback components, counterevidence coverage, and source retrieval age. Age is a review cue, not proof of retraction or invalidity. Use `--as-of YYYY-MM-DD` for repeatable freshness checks; the default stale threshold is 365 days.

Add a pack fixture and tests for canonical/ambiguous/unsupported queries; context validation and identity; expected hypotheses and evidence links; path direction and known context limitations; no-model/no-data behavior; report citations; and the relevant browser flow. Model-bearing packs also need conservation/bounds and qualitative scenario tests. Do not assert a desired mechanism ranking by inflating evidence grades. Document why the curated evidence should support the expected relative ordering, and test sensitivity to the rubric.

For dependency injection, construct `DomainPackRegistry(Path("fixture-root"))`, pass it to `InvestigationService(registry)`, or pass `registry=` to `interpret_question`. The loader constructs its default research question directly from validated metadata; it never calls the interpreter or creates a circular registry dependency.

## Review before release

Run the checks above, read the generated report, and inspect the new pack in the normal workflow at desktop and narrow widths. Verify claim-to-source links and contradictory evidence manually. Record what was checked at abstract versus full-text level, preserve unknowns, and bump the version when content changes. The synthetic third-pack tests establish software extensibility; they do not establish scientific coverage of another biological domain.
