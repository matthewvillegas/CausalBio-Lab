# Scientific and source audit

Audit date: 2026-09-12. Scope: every assertion in the two bundled packs (15 memory, 18 knee-pain), their 12 literature records, core source adapters, ranking, and numerical implementations. This is an engineering and claim-to-source audit, not a systematic review, clinical validation, or independent replication.

## Method and verification boundary

The audit compared subject, relation, object, confidence, causal status, supporting/contradictory IDs, species, tissue, population, and limitations against available original-publication metadata and abstracts. All 12 PMIDs resolved through one successful batched NCBI EFetch request. Direct PubMed browsing worked for most records; empty pages and a PMC browser challenge prevented uniform browser access. EFetch supplied the missing abstracts. An earlier EFetch display failed on the Windows console encoding; the corrected ASCII-escaped output completed. No retrieved abstract or full article was added to the repository.

The Breda article's accessible PMC text was also inspected. Other full texts and supplements were not comprehensively re-reviewed. Consequently, missing full-text details, risk of bias, laboratory independence, unreported exclusions, and exact sample sizes absent from an abstract are not newly certified by this audit. Existing retrieval dates remain historical; this audit does not relabel all records as freshly curated.

The most important distinction is between a source being real and a graph edge being established by that source. Several records correctly carry grade U and explicitly describe model bridges. Those edges must remain visibly uncertain; attaching a source to a modeling assumption is not evidential entailment.

## Citation checks

| Pack / source key | Verified source and scope | Assessment |
| --- | --- | --- |
| memory / `bliss_lomo_1973` | [PMID 4727084](https://pubmed.ncbi.nlm.nih.gov/4727084/): rabbit dentate recordings after patterned stimulation; abstract reports 15 of 18 animals with potentiation. | Metadata and narrow experimental endpoint match. Natural learning and behavioral retention were not tested. |
| memory / `morris_1986` | [PMID 2869411](https://pubmed.ncbi.nlm.nih.gov/2869411/): AP5, hippocampal potentiation, and selective place-learning impairment. | Abstract and rat indexing match; does not isolate potentiation as the mediator of learning effects. Sample size remains unavailable in inspected abstract. |
| memory / `tsien_1996` | [PMID 8980238](https://pubmed.ncbi.nlm.nih.gov/8980238/): CA1-restricted receptor deletion in mice, altered physiology, spatial-memory impairment. | Species and anatomical specificity match. Does not establish general human memory retention; sample size not verified here. |
| memory / `marshall_2006` | [PMID 17086200](https://pubmed.ncbi.nlm.nih.gov/17086200/): controlled human sleep stimulation, physiological changes, declarative retention. | Direction and healthy-human context match. The bundled sample size of 13 is not independently recoverable from the inspected abstract and still needs full-text confirmation. |
| memory / `bueno_lopez_2019` | [PMID 30842037](https://pubmed.ncbi.nlm.nih.gov/30842037/): randomized crossover, 23 participants, no significant memory or sleep-physiology effect. | Sample, design, and null result match. A boundary to stimulation generalization; absent target engagement limits inference against all slow-oscillation mechanisms. |
| memory / `westbrook_2020` | [PMID 32193325](https://pubmed.ncbi.nlm.nih.gov/32193325/): human cognitive-effort choices and dopamine-related measurements/perturbations. | Endpoint is effort valuation, not retention. Full-text sample and exact correlation were not independently rechecked here. |
| knee-pain / `janssen_2013` | [PMID 23247704](https://pubmed.ncbi.nlm.nih.gov/23247704/): 50 volleyball players, regression estimates of tendon loading. | 52% and 70% variance figures match. These are prediction-model statistics, not pain effects. |
| knee-pain / `bohm_2015` | [PMID 27747846](https://pubmed.ncbi.nlm.nih.gov/27747846/): 27 studies, 264 healthy adults, chronic exercise and tendon properties. | Stiffness estimate and interval match. Healthy-tendon adaptation cannot establish pain relief or mediation through an acute force estimate. |
| knee-pain / `visnes_2013` | [PMID 22260424](https://pubmed.ncbi.nlm.nih.gov/22260424/): youth volleyball cohort, 141 participants, 28 incident cases. | Exposure odds ratios and population match; longitudinal association remains correctly distinguished from causation. |
| knee-pain / `clifford_2020` | [PMID 32818059](https://pubmed.ncbi.nlm.nih.gov/32818059/): 10 randomized studies across tendon sites; variable exercise responses. | Mixed result and quality limitation match. Does not measure latent stress or peripheral nociceptive states. |
| knee-pain / `breda_2021` | [PMID 33219115](https://pubmed.ncbi.nlm.nih.gov/33219115/), [original PMC article](https://pmc.ncbi.nlm.nih.gov/articles/PMC8070614/): 76 patients, clinical-score comparison at 24 weeks. | Estimate and interval match. Comparator, shared cointerventions, adherence, clinical population, and endpoint limitations must accompany the edge. |
| knee-pain / `rathleff_2015` | [PMID 25388552](https://pubmed.ncbi.nlm.nih.gov/25388552/): cluster trial in 121 adolescents with patellofemoral pain. | Added-exercise comparison and recovery odds ratio match. Separate population and outcome from patellar tendinopathy. |

## Every memory assertion

Source keys below link to the publication checks above. “Retain” means the restricted representation is defensible under the inspected material; it does not imply clinical certainty. “Flag” means no direct claim-to-source entailment was established.

| Assertion key | Source / context | Relation check and disposition |
| --- | --- | --- |
| `learning_precedes_activity` | Bliss; general hippocampal abstraction, species unspecified | Natural learning was not studied. Flag as a model bridge; retain U and the explicit limitation. |
| `activity_activates_nmda` | Morris, Tsien; rat/mouse hippocampus | Mechanistic interpretation consistent with receptor-dependent preparations; activity-pattern specificity must remain. Retain D, not a general human activation claim. |
| `activity_increases_ltp` | Bliss; rabbit dentate gyrus | Experimental stimulation-to-population-potentiation relationship matches. Retain animal context and D; do not rename endpoint memory. |
| `nmda_contributes_ltp` | Morris, Tsien; rat/mouse hippocampus | Perturbations support receptor dependence for tested potentiation paradigms. Retain restriction to tested forms. |
| `nmda_contributes_spatial_learning` | Morris, Tsien; rat/mouse hippocampus | Restricted experimental learning claim matches. Perturbations affect multiple receptor functions; retain mediation caveat. |
| `ltp_contributes_memory` | Morris, Tsien; cross-species projection | No direct long-term human-retention mediation result. Retain predicted relation, hypothesis-only status, and U. |
| `sleep_precedes_slow` | Marshall, Bueno-Lopez; healthy humans, NREM | Descriptive temporal/context relation, not an isolated causal effect. Retain expert-curation qualification. |
| `slow_contributes_consolidation` | Marshall with Bueno-Lopez conflict; healthy humans | Mixed intervention evidence with co-changing physiology. Retain qualification and contradiction; do not imply isolated mediation. |
| `consolidation_contributes_persistence` | Marshall with Bueno-Lopez conflict; sleep-period retention | Conceptual connection overlaps the measured outcome. Retain curated/contextual interpretation; do not count as an independent experimental replication. |
| `stimulation_affects_slow` | Marshall with Bueno-Lopez conflict; laboratory NREM protocols | Protocol-dependent target engagement. Retain predicted relation and visible null result. |
| `dopamine_associated_effort` | Westbrook; human striatal measurements, rewarded choices | Associative wording matches the selected placebo measurement. Retain; no direct retention effect. |
| `effort_contributes_engagement` | Westbrook; general learning extrapolation | Learning engagement was not the measured endpoint. Flag, retain U/hypothesis-only. |
| `engagement_increases_exposure` | Westbrook; general learning abstraction | Conceptual bridge outside source. U is appropriate; causal-sounding verb must be accompanied by model-assumption wording. |
| `exposure_contributes_memory` | Westbrook; general learning extrapolation | Retention not measured. Flag and preserve U/predicted status. |
| `antagonism_inhibits_nmda` | Morris; experimental rat hippocampal perturbation | Restricted inhibitory relationship is supported; preserve laboratory-only research scope. |

## Every knee-pain assertion

| Assertion key | Source / context | Relation check and disposition |
| --- | --- | --- |
| `jumping_increases_exposure` | Visnes; youth volleyball, weekly exposure | Exposure is an activity proxy, not measured jump count. Retain expert-curation/proxy limitation. |
| `exposure_affects_tendinopathy_risk` | Visnes; prospective youth cohort | Longitudinal risk association matches. Preserve causal-status label beside the potentially causal-sounding relation. |
| `tendinopathy_associated_pain` | Breda; selected symptomatic tendon population | Clinical-population association is reasonable. Cannot identify the cause of an undifferentiated symptom query. |
| `jumping_precedes_landing` | Janssen; laboratory stop-jump | Descriptive ordering fits the task. Not pathological mechanics evidence. |
| `landing_predicts_force` | Janssen; estimated tendon load | Predictive relation and E/computational label are appropriate. No direct pain endpoint. |
| `force_contributes_stress` | Janssen, Bohm; cross-study tendon model | Latent tissue stress not directly measured. Retain U/hypothesis-only and no damage inference. |
| `stress_contributes_pain` | Breda; symptom-model projection | Trial does not identify stress mediation. Retain U/predicted, with clinical-context caveat. |
| `loading_increases_adaptation` | Bohm; healthy adult chronic-loading interventions | **Flag endpoint substitution:** current subject is a single-jump estimated-force entity, whereas evidence is chronic exercise. Grade A on that exact edge overstates support. Downgrade/mark the cross-study bridge or author a distinct, correctly scoped chronic-loading entity. |
| `adaptation_moderates_stress` | Bohm; abstract tendon model | Stress moderation was not directly tested. Preserve U/hypothesis-only. |
| `recovery_moderates_stress` | Bohm, Visnes; unspecified species, latent model | Neither measures a unified recovery-capacity quantity. Preserve U; no validated threshold. |
| `stress_contributes_nociception` | Clifford; educational tendon model | Pain review does not establish this molecular/peripheral connection. Flag, retain U/predicted. |
| `nociception_contributes_pain` | Clifford; general symptom model | Broad conceptual contribution; attached review lacks direct signaling evidence. Keep U and explicit source gap. |
| `force_distribution_affects_pf_load` | Janssen; patellofemoral projection | Tendon-force study does not establish joint-load endpoint. Retain U and anatomical-extrapolation warning. |
| `pf_load_affects_pf_pain` | Rathleff; adolescent patellofemoral population | Trial does not identify joint load as causal mediator. Retain U/predicted. |
| `pf_pain_associated_activity_pain` | Rathleff; adolescent patellofemoral region | Distinct symptomatic population, reasonable association. No diagnosis implication. |
| `progressive_loading_improves_outcome` | Breda; confirmed tendinopathy, 24 weeks | Valid restricted comparator result. **Flag outcome compression:** shared `reported_recovery` entity combines a clinical score with another trial's self-reported recovery. Show the exact outcome in evidence and distinguish outcomes during later authoring. |
| `isometric_variable_pain` | Clifford; multiple tendon populations | Variable response and no consistent superiority are correctly retained. No uniform analgesic or healing claim. |
| `education_exercise_increases_recovery` | Rathleff; adolescent patellofemoral pain | Added-exercise effect fits the endpoint. Keep population and education-only comparator; do not generalize to tendinopathy. |

## Cross-cutting findings and corrections

1. **High: trusted curation is not direct source support.** A curated U/hypothesis-only bridge may remain in a research graph, but explanations must clearly identify it as an assumption. Review state alone is insufficient to label evidence strong.
2. **High: acute-to-chronic endpoint substitution.** The adaptation edge identified above should be conservatively downgraded if the endpoint is retained; do not fabricate new literature to fill the gap.
3. **Moderate: endpoint compression.** `reported_recovery` is shared across non-equivalent clinical outcomes and populations. Comparative displays must use the assertion context and study-specific outcome.
4. **Moderate: source count is not independent replication.** Multiple evidence rows or repeated source usage along one path do not establish independent replications or independent edge evidence.
5. **Moderate: “human relevance” is lexical.** The scorer currently checks species strings. This is not tissue match, clinical transportability, or mechanistic directness.
6. **Moderate: evidence-grade meanings need restraint.** An A-grade review does not make every derived edge strong, and D-grade animal evidence can be mechanistically informative while remaining indirect for humans.
7. **Unresolved external review:** full-text verification of all stored details, systematic contradiction searching, stale/retracted-publication surveillance, source-license metadata, and independent domain-expert review remain outside this completed audit.

## Source adapter review and live checks

Official [NCBI introduction and usage policy](https://www.ncbi.nlm.nih.gov/books/NBK25497/) and [E-utilities parameter documentation](https://www.ncbi.nlm.nih.gov/books/NBK25499/) confirm ESearch/ESummary and the existing authoritative host. NCBI specifies at most three requests per second without an API key. Existing code has fixed HTTPS endpoints, disabled redirects, ten-second timeout, typed normalization, and cache timestamps, but no pacing or retry loop.

The [UniProt API help](https://www.uniprot.org/help/api_queries) page returned a JavaScript fallback through the browsing tool; its detailed policy text was not readable and no numeric UniProt quota is claimed here. A real bounded query nevertheless verified the configured `https://rest.uniprot.org/uniprotkb/search` endpoint and requested fields.

| Live check | Actual result |
| --- | --- |
| PubMed adapter, `2869411[uid]`, limit 1 | Passed at 2026-09-12 23:57:58 UTC; one normalized Morris citation with matching PMID/DOI. |
| UniProt adapter, `accession:P01303`, limit 1 | Passed at 2026-09-12 23:58:00 UTC; one reviewed human protein record, taxon 9606. |
| Bundled citation audit | One successful batched EFetch XML response returned all 12 expected PMIDs and abstracts. |

The live adapter calls used fresh temporary caches and no secret credentials. They do not enable public live mode or make offline tests network-dependent.

| Concern | Existing behavior | Bounded correction |
| --- | --- | --- |
| Retries / rate limits | Immediate typed failure, stale fallback | Add bounded transient retry with injectable wait, Retry-After handling, and per-source pacing. Keep offline fixtures deterministic. |
| Response-size limit | Five-megabyte check after fully buffering HTTP content | Enforce during streaming in production transport, still check injected responses. |
| Malformed or oversized result arrays | Required fields checked; upstream cardinality is trusted | Reject more records than requested and duplicate/malformed identifiers. |
| Schema exceptions | Pydantic errors may escape normalized source-error boundary | Wrap invalid normalized records as `SourceResponseError`. |
| Cache | Version/query/limit key, 24-hour TTL, validated stale fallback, corruption checks | Preserve; tests should also check response identity and schema mismatch. |
| Provenance | Canonical source URL, normalized identifiers, retrieval time | Preserve; candidate extraction must not auto-promote to graph evidence. |
| Common interface | `SourceAdapter` protocol already exists | Extend incrementally; do not introduce empty integrations for ten sources. |

## Numerical review and next validation gate

The core implements actual discrete enabling/firing and SciPy integration; the HMC code implements momentum refresh, half/full/half leapfrog, kinetic plus potential energy, log Metropolis correction, and separately spawned chain RNG streams. Biological simulations use synthetic, uncalibrated model rates; HMC uses a separate synthetic Gaussian dataset.

Existing Petri tests cover consumption, output, read/inhibitory gates, deadlock, bounded reachability, constant growth, and irreversible mass action. Add a reversible two-state system with analytic equilibrium and conserved total, continuous upper-bound behavior, and an explicit inhibition-removal comparison.

Existing HMC tests compare posterior means to a conjugate solution and test recovery/reproducibility. Add finite-difference gradients, leapfrog reversibility, energy-error convergence, analytic covariance/correlation, dispersed starts, narrow/wide valid priors, trajectory-length/step-size sensitivity, and bad-tuning diagnostics. Current `_bulk_ess` uses raw-scale autocorrelations and pairs lags starting at 1; it should not claim modern rank-normalized bulk ESS without a corresponding implementation and tests. Split R-hat is ordinary split R-hat, not rank-normalized folded R-hat. Document limitations even if the current Gaussian fixture passes.

Ranking already exposes its component formula but embeds weights in code. A validated weight configuration and local one-at-a-time sensitivity test can expose unstable ranks without pretending to calibrate probabilities. Mathematical tests establish behavior for tested systems and tolerances; they do not validate biological pathways.

Implementation corrections and their actual checks will be recorded after the ordered UX and domain-pack milestone gates. No implementation change was made during this initial audit.


## Implemented evidence corrections, 2026-10-02

- The `loading_increases_adaptation` edge now explicitly represents a model bridge from a single-jump force estimate to chronic adaptation. Its relation is `PREDICTED_TO_AFFECT`, grade U, and causal status hypothesis-only, with the endpoint mismatch and healthy-adult restrictions recorded. The Bohm study's evidence grade is preserved; source quality does not establish this substituted endpoint. Knee pack version is `knee-pain-1.1.0`.
- Source requests now stream with a decoded byte cap, reject excess/duplicate/malformed identities, preserve normalized provenance, wrap schema failures, and use bounded retries, Retry-After handling and process-local pacing. Invalid cached identity is rejected before fresh/stale use. Offline tests cover these paths.
- The local candidate queue retains hash-linked immutable review events and explicit human acceptance; provider suggestions cannot write trusted graph data. Citation identity and copied excerpts are validated, but this does not automate scientific entailment.
- Fresh-cache production-adapter smoke: PubMed query `2869411[uid]`, limit one, returned PMID 2869411 at **2026-10-02 21:05:46 UTC**; UniProt query `accession:P01303`, limit one, returned P01303 at **2026-10-02 21:05:48 UTC**. No credentials, stored full articles, or public API live-mode changes were involved.
- Current official [NLM endpoint guidance](https://dataguide.nlm.nih.gov/eutilities/utilities.html) and [NLM rate-limit guidance](https://support.nlm.nih.gov/kbArticle/?fromlegacy=true&pn=KA-05317) retain the E-utilities host and three requests/second unauthenticated limit. The Bookshelf pages hit a browser challenge in this follow-up, and UniProt help returned its JavaScript fallback. The [UniProt API primary publication](https://academic.oup.com/nar/article/53/W1/W547/8126256) describes its search endpoint; the actual successful adapter request independently checked the configured endpoint. No unverified numeric UniProt quota is asserted.
