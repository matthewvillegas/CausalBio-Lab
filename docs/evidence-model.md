# Evidence model

## Scope and implementation status

The implemented evidence layer records where a claim came from, the study and experimental context, how the result was interpreted, and how it was curated. It also supplies transparent components for ranking mechanism paths.

The model does **not** automatically assess risk of bias from full text, perform a systematic review, pool effects, or turn literature grades into probabilities. Current records are manually curated in two bundled demonstration packs.

## Evidence records

The primary interface uses qualitative evidence strength and explicitly separates human, animal, cellular, and computational source context. Counts are source records, not independent replications. Mechanism views keep supporting and conflicting records separate, identify the weakest and strongest connections using the returned edge-support values, and disclose extrapolation and missing evidence. Opening a connection exposes its underlying records, study design, context, limitations, effect intervals where present, and provenance. Numerical path scores remain in advanced analysis.

An `EvidenceRecord` contains:

- a UUID;
- a nested `Study` with title, authors, year, journal, study type, identifiers, population, and source URL;
- an `ExperimentalContext` for species, population, tissue, cell type, condition, and temporal context;
- result direction: `supports`, `contradicts`, `mixed`, `null`, or `contextualizes`;
- an optional effect estimate with measure, value, unit, interval, interval level, and source note;
- an uncertainty measure when available;
- limitations and a curated evidence note;
- an optional short supporting excerpt;
- retrieval date and source-adapter label;
- curation status and ordinal evidence grade.

Unknown values should remain unknown. An effect estimate is optional precisely because many mechanism claims in the bundled literature cannot support a commensurable quantitative estimate.

## Provenance chain

The user-visible trace is:

```text
mechanism path
→ causal assertion UUID
→ supporting and contradictory evidence UUIDs
→ study metadata and source URL
→ curator interpretation, context, limitations, and retrieval date
```

Assertions also record their curator, extraction method, source, retrieval date, and review status. Only `manual_curation` and `validated_structured_extraction` are accepted extraction-method values. Retrieved text is not an instruction source and must not create trusted assertions automatically.

The SQLite materialization stores validated JSON payloads and pack-level versions, retrieval dates, an evidence-rubric version, and a SHA-256 digest of canonical pack content. The versioned JSON pack remains the current authoring source; SQLite is a reproducible local snapshot.

## Curation and trust

Curation states are `SUGGESTED`, `EXTRACTED`, `VALIDATED`, `CURATED`, `REJECTED`, and `OUTDATED`. Trusted graph projections use only `VALIDATED` and `CURATED` assertions. A trusted assertion must have supporting evidence, and every supporting record on that assertion must also be trusted.

This is a workflow integrity rule, not independent scientific validation. `CURATED` means a record passed the project's curation process; it does not mean that the original result is unbiased, replicated, clinically validated, or universally applicable.

### Candidate review architecture

`causalbio.evidence.curation.CandidateReviewStore` is a local SQLite review queue. Candidates contain a proposed assertion, entities, evidence, separate supporting/counterevidence references, source records, aware retrieval timestamps, optional short source excerpts and their locators. Submitted assertions, entities, and evidence must remain `SUGGESTED` or `EXTRACTED`; citation URLs/identifiers, available titles, dates, excerpt text, and graph references are validated. A citation match is not a check of scientific entailment.

Every submit, edit, accept, reject, or mark-uncertain action appends an actor, rationale, timestamp, draft snapshot, revision, previous hash, and SHA-256 event hash. SQLite triggers prohibit ordinary updates/deletes and reads verify the hash chain. Actor names are local attribution, not authenticated identities; a database owner can replace a whole log. This is an auditable local workflow, not a tamper-proof service.

Acceptance requires explicit human confirmation of source entailment and context. Mark uncertain downgrades the assertion to grade U/hypothesis-only while retaining the source record's grade. Editing or rejecting an accepted candidate prevents further curated export until it is accepted again. `accepted_bundle()` produces a reviewable curated bundle; it never edits the checked-in pack or the application's graph.

Use `node scripts/python-run.mjs scripts/curate_candidate.py --database artifacts/curation.sqlite submit --file candidate.json --actor "Curator name" --reason "Source ready for review"`. The CLI also supports `history --id UUID`, `edit --file candidate.json --revision N`, and `accept|reject|uncertain --id UUID --revision N`; review actions require an actor/reason, and acceptance additionally requires `--confirm-human-review`. `export --id UUID` prints the accepted bundle for a separate, reviewed pack change.

The optional `CandidateExtractionProvider` protocol in `causalbio.evidence.providers` receives at most twelve explicit source records and returns bounded JSON. `extract_candidate()` enforces schema, generated attribution, untrusted state, and unchanged supplied provenance. No live LLM provider is configured. Source text is data, not instructions. This boundary validates citation identity and supplied excerpts; human scientific review remains necessary for relation, study design, population, and context. It has no graph mutation or acceptance operation.


## Evidence grades

Grades `A`, `B`, `C`, `D`, `E`, and `U` are ordinal curated inputs. For path ranking, the implementation maps assertion confidence grades to support values:

| Grade | Ranking value |
| --- | ---: |
| A | 0.95 |
| B | 0.82 |
| C | 0.68 |
| D | 0.50 |
| E | 0.32 |
| U | 0.15 |

These numbers are rubric weights, not calibrated probabilities. The current code does not infer a grade from study design alone and does not claim that all studies of one design share a grade. Curators must consider the actual source, context, limitations, directness, and relevance.

## Causal directness

The scorer also uses a documented mapping from assertion causal status:

| Causal status | Ranking value |
| --- | ---: |
| Causal experimental | 0.95 |
| Quasi-experimental | 0.82 |
| Mechanistic biochemical | 0.80 |
| Genetic evidence | 0.76 |
| Longitudinal association | 0.58 |
| Expert curation | 0.55 |
| Cross-sectional association | 0.38 |
| Computational prediction | 0.28 |
| Hypothesis only | 0.12 |

Again, this is an inspectable ranking policy, not a universal hierarchy or posterior model.

## Human relevance and translation

For a requested species, the current scorer counts supporting records whose species text contains the requested term. With supporting records, the human-relevance component ranges from 0.35 to 1.00 according to that fraction; without records it is 0.10. Nonmatching records produce an extrapolation penalty of up to 0.35. Computational predictions and hypothesis-only assertions receive an additional 0.30 extrapolation penalty.

This is deliberately simple. It makes animal or computational extrapolation visible, but it does not model phylogenetic distance, construct equivalence, dose scaling, tissue exposure, age, sex, disease state, experimental validity, or clinical transportability. Users must read the underlying context and limitations.

## Replication and context matching

The current replication component is based on the number of supporting records: 0.45 for one record, increasing by 0.18 for each additional record up to 1.00. It does not test whether studies are independent laboratories, preregistered replications, or affected by publication bias.

Context matching compares requested terms longer than three characters with assertion context text. A lexical match receives 0.95, a nonmatch 0.62, and an unspecified requested context 0.80. This is a deterministic convenience heuristic, not semantic entailment.

## Contradictions

Assertions keep contradictory evidence IDs separate from supporting IDs. Each contradictory record adds 0.22 to a contradiction component, capped at 0.85. The final edge-support calculation subtracts a weighted contradiction penalty; contradictory records are also exposed in the graph and report rather than silently averaged away.

A contradiction can reflect a true opposing result, a different population or endpoint, study limitations, or a boundary condition. The current formula does not adjudicate those possibilities automatically. Curated interpretation is required.

## Plausibility index

For an edge, positive components are weighted as follows:

```text
0.28 × evidence quality
+ 0.24 × causal directness
+ 0.18 × human relevance
+ 0.12 × replication
+ 0.18 × context match
```

The scorer subtracts `0.28 × contradiction penalty` and `0.24 × extrapolation penalty`, then constrains edge support to 0.03–0.99. A path uses geometric support across edges, with a 0.10 penalty for each edge beyond two and a 0.32 penalty for every `E`, `U`, or hypothesis-only link. The displayed score is the constrained value multiplied by 100.

Every score includes its component values, ordered edge supports, weakest-link explanation, path-length penalty, unsupported-link penalty, and exact policy weights. Investigations record rubric version `causalbio-evidence-rubric-1.1`. The defaults preserve the previous formula.

`ScoringWeights` in `domain/scoring_policy.py` validates finite coefficients in [0, 1] and requires at least one positive component. Pass a policy to `PathScorer(evidence, weights=...)`. Positive coefficients are divided by their sum; penalty coefficients are applied separately. The default values are those printed above. Grade/directness mappings, support bounds, lexical context matching, and source-count components remain documented heuristic choices.

Each investigation checks eighteen local configurations: each of the nine weights individually decreased and increased by 20%, renormalizing positive terms. Mechanism scores use their highest-scoring declared path; tied displayed indices share a rank. Results record the baseline and observed rank range for each mechanism and how many configurations changed ranks. An unstable result is visible before advanced tools and in the report; the exact counts and policy are available in advanced analysis. This is a local sensitivity check, not calibration, joint perturbation analysis, an exhaustive path search, or proof that omitted evidence cannot change the order.

The plausibility index exists only to compare paths under this rubric. It must never be reported as a probability, effect estimate, treatment benefit, or individual forecast.

## Known limitations

- Investigation evidence retrieval is bundled and offline. PubMed and UniProt candidate-source adapters exist in the core, but are not connected to evidence records, the public live-search route, or a systematic-review workflow.
- Grades and interpretations are manual and may be revised.
- Citation coverage does not establish citation entailment.
- Record count is not a meta-analysis or quality-adjusted replication estimate.
- The scorer does not correct for bias, multiplicity, dependence, selective reporting, or conflicting outcome definitions.
- Animal, cell, genetic, and computational evidence remains explicitly distinct from demonstrated human effects.
