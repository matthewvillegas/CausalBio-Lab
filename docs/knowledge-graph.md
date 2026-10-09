# Knowledge graph

## Scope and implementation status

CausalBio Lab uses a local NetworkX `MultiDiGraph`. Biological entities are nodes, and provenance-bearing `CausalAssertion` objects are directed edge keys. Parallel edges are allowed so the same entity pair can carry different relations, evidence, contexts, or causal statuses.

The current implementation supports validated local packs, trusted projections, filters, path search, and deterministic exports. It does not yet provide an RDF triple store, SPARQL, Neo4j, ontology ingestion, automated entity resolution, live source expansion, or a curation user interface.

## Entity model

Every `BiologicalEntity` has a UUID, preferred name, aliases, type, description, optional external identifiers, source, timestamps, and curation status. Supported types are:

- outcomes and observations: cognitive outcome, symptom, phenotype, disease or condition;
- anatomy: anatomical region, organ, tissue, cell type, cellular component;
- molecular biology: gene, RNA, protein, receptor, enzyme, ion channel, pathway, biological process, metabolite, neurotransmitter, hormone, immune mediator;
- exposures and actions: biomechanical force, behavior, environmental exposure;
- research interventions: drug, peptide, experimental compound, therapy, device;
- provenance objects: study and dataset.

External identifiers are namespace/value pairs with an optional URL. They are preserved when present, but no single ontology is mandatory. Within a loaded graph, two entities with the same case- and whitespace-normalized preferred name and entity type are rejected as duplicate canonical entities. Duplicate object IDs are rejected before dictionary construction can overwrite a record.

## Relation ontology

The controlled relation vocabulary is:

```text
ACTIVATES              INHIBITS                BINDS_TO
PHOSPHORYLATES         EXPRESSED_IN            LOCATED_IN
PARTICIPATES_IN        PRODUCES                CONSUMES
REQUIRES               UPREGULATES             DOWNREGULATES
INCREASES              DECREASES               CAUSES
CONTRIBUTES_TO         MEDIATES                MODERATES
PRECEDES               ASSOCIATED_WITH         PREDICTED_TO_AFFECT
TREATS                 REDUCES_SYMPTOM         AFFECTS_RISK
METABOLIZED_BY         TRANSPORTED_BY          SUPPORTED_BY
CONTRADICTED_BY        DERIVED_FROM
```

The relation must be interpreted together with `causal_status`. For example, an `INCREASES` assertion based on cross-sectional association is not promoted to experimental causality by its relation label.

## Assertion schema and provenance

An assertion records subject, relation, object, polarity, direction, evidence grade, causal status, experimental context, supporting and contradictory evidence IDs, curator, extraction method, source, retrieval date, review status, interpretation, and limitations.

Validation rejects:

- self-edges and undirected assertions;
- duplicate entity, assertion, or evidence IDs;
- missing subject or object entities;
- missing supporting or contradictory evidence references;
- trusted assertions without supporting evidence;
- trusted assertions that depend on untrusted endpoints, supporting records, or counterevidence;
- missing curator/source provenance;
- duplicate canonical entities or duplicate contextual assertions within one graph;
- missing hypothesis/intervention references, untrusted mechanism paths, or paths with disconnected/reversed edges, repeated entities, or inconsistent trigger/outcome endpoints.

Parallel assertions with a different context or polarity are retained. Identical contextual claims should merge provenance rather than masquerade as independent support. The validator does not infer contradictions from text; explicit counterevidence links and opposing assertions preserve what curators have recorded.

The graph is therefore more than a display network: the scientific claim and its provenance remain first-class data throughout query and export.

## Projections and filters

The default investigation view is an accessible HTML pathway of up to twelve nodes from the selected mechanism's highest-ranked path. Selecting a connection opens its evidence beside the pathway. The optional Cytoscape explorer begins with that path and bounded neighboring nodes, then offers upstream/downstream expansion, intervention and entity-class views, conflicting pathways, and the full graph. Direction, line style, arrow type, and labels supplement color. Advanced client filters include node type, tissue, organism, evidence grade, causal status, intervention class, and relation type. The relationship selector offers a keyboard alternative to canvas interaction. Display changes do not rerun scientific API requests.

The default projection is trusted-only, meaning assertions must be `VALIDATED` or `CURATED`. Callers can request all assertions or filter by:

- relation type;
- evidence grade;
- organism text;
- tissue text.

A projection contains only entities and evidence referenced by the selected assertions and records the filters applied. Filtering changes the view, not the underlying curated pack.

## Directed path search

Path search operates in the assertion direction and requires known source and target entity UUIDs. It uses simple node paths, so an entity is not repeated within a result. The maximum path length must be between one and ten edges, and the result limit between one and one hundred.

For entity pairs with parallel assertions, the implementation selects the assertion with the strongest current edge-support heuristic. Traversal and score ties use stable identifiers so input insertion order does not choose a different result. Complete paths are ranked by the evidence plausibility index and include UUIDs of weak links whose edge support is below 0.50. Search examines up to four times the requested result limit before sorting; this bounded navigation search does not guarantee the globally best path in a large graph.

This search is mechanism navigation, not causal-effect identification. A returned path can be indirect, context-mismatched, associative, or translationally uncertain; those properties remain visible in its assertions and score components.

## Pack validation command

Run `pnpm graph:validate` to load and validate every discovered pack. `--pack-root <directory>` selects an isolated registry and `--as-of YYYY-MM-DD` fixes the date for repeatable retrieval-age checks. Invalid structure exits nonzero. Valid output includes entity/assertion/evidence counts, strongly connected feedback components, assertions with counterevidence, and evidence retrieved more than 365 days earlier. Feedback and age are review cues, not automatic scientific failures. See [domain-pack-authoring.md](domain-pack-authoring.md) for metadata, optional-model, and third-fixture requirements.

## Exports

The graph repository currently emits:

- JSON-LD with entity and assertion UUID URNs, types, relation, causal status, grade, and evidence links;
- GraphML with entity attributes and provenance-bearing edge attributes;
- a CSV node table;
- a CSV edge table.

The API exposes these artifacts as report downloads and graph-export routes. The JSON-LD context currently uses a project placeholder schema namespace (`https://causalbio.example/schema/`), not a published ontology. CSV and GraphML are exchange formats, not lossless replacements for every nested field in the source pack. A graph-import API is not implemented.

## Current curation workflow

The installed biological packs are still manually curated and review-oriented:

1. Add or update studies and evidence records in a versioned local pack.
2. Add typed assertions that reference those evidence UUIDs.
3. Record biological context, causal status, interpretation, limitations, and curation state.
4. Load the pack through Pydantic schema validation and graph-integrity checks.
5. Run graph, scoring, reporting, and pack-storage tests.
6. Materialize the validated pack into SQLite with version metadata and a canonical-content SHA-256 digest.
7. Review graph and report output before changing a record to a trusted state.

For proposed additions, `causalbio.evidence.curation` supplies `CandidateDraft`, `CandidateProvenance`, and a SQLite `CandidateReviewStore`. Submit, edit, accept, reject, and uncertain-review events retain revisions and hash-linked audit history. Acceptance requires an explicit human review; curated bundle export does not mutate a pack. `scripts/curate_candidate.py` exposes this review workflow as a CLI, not a browser curation interface.

The optional `CandidateExtractionProvider` protocol and `extract_candidate` boundary validate a generated candidate's source/provenance identity, generated-content flag, and suggested/extracted state. No live model provider or API retrieval-to-review integration is installed. Source text and metadata remain untrusted input, and no source or model response automatically inserts a trusted edge.

## Planned extensions

Roadmap work includes ontology-assisted entity resolution, an operator UI and explicit source-adapter integration for the existing candidate review store, richer context queries, production relational and graph adapters, and an RDF vocabulary with a stable namespace. Those capabilities should not be inferred from the current local NetworkX implementation.
