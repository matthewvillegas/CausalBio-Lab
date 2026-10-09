# Scientific and product limitations

The application preserves two small curated teaching packs and investigates broader biological subjects through bounded Europe PMC, PubMed and UniProt retrieval. This broader coverage is provisional and uneven: it does not establish a complete answer to every question, perform systematic review, diagnose a person, select treatment, or estimate clinical effects. A third synthetic pack fixture verifies authoring contracts only. See the per-question limitations in [live research validation](live-research-validation.md).

## Evidence and ranking

The source audit verifies publication identity and assesses assertions against retrieved metadata, abstracts, and stated context. It is not complete full-text adjudication or independent expert review. Sources can be reused by multiple edges; counts do not establish independent replication. No automated retraction surveillance or comprehensive contradiction search runs. `VALIDATED` and `CURATED` describe review state, not biological truth.

Evidence grades and weights are an explicit heuristic. Species and context matching remain lexical, and record-count replication does not adjust for dependence or bias. The ranking sensitivity check varies one weight at a time by 20%; it does not explore every joint change or compensate for missing studies. Graph path search is bounded exploratory navigation, not causal identification or guaranteed global top-k search. Weak and hypothetical bridges remain visible.

## Numerical models

Petri parameters are synthetic and uncalibrated. Continuous hard gates and state-bound clipping require care near discontinuities; the known-system tests cover stated fixtures and tolerances. Stochastic firing, Hill laws, automatic graph-to-kinetic conversion, and person-specific simulation are absent.

HMC fits one synthetic Gaussian teaching model with known noise. It uses fixed tuning and a fixed mass matrix, not NUTS or adaptive warmup. Rank-normalized bulk ESS and folded split R-hat improve diagnostics; they do not establish tail accuracy, model adequacy, biological validity, or inference readiness. A curated graph or model availability flag cannot satisfy the biological observation/likelihood/identifiability contract.

## Runtime, sources, and review

Legacy curated investigation and artifact lookup indexes remain process-local. General research uses a separate immutable SQLite session store with persisted HTML, Markdown and JSON reports that survive reopening. Neither system provides user accounts, authorization, a deletion policy, or distributed rate limits. The local service is not isolated for concurrent untrusted users.

Europe PMC, PubMed and UniProt responses are bounded, cached, and normalized, but external availability and schema stability cannot be guaranteed. General research enables live retrieval by default, with an offline choice and explicit scientific-query disclosure; the older `/literature/search` route still refuses its legacy live mode. Local candidate review has auditable events and explicit export, but no authenticated reviewer UI or automatic determination of citation entailment. Provisional research never inserts trusted graph assertions.

Exact source extracts can still be incomplete, describe a different population or tissue, or fail to answer the requested mechanism. Grouping uses shared terminology, not validated ontology inference or semantic causal discovery. Unknown structured context remains unknown even when an abstract mentions a species. A limiting sentence is not automatically an adjudicated contradiction. A provider's cooperative deadline may leave a bounded synchronous worker finishing after partial results are returned.

## Usability and verification

Automated tests verify workflow behavior, accessibility basics, responsive containment, and console failures in Chromium. Screenshots are captured from the application. These checks do not establish the user's 30-second novice-comprehension target; that needs an observed usability study with unfamiliar users. Screen-reader behavior, every browser/platform, remote CI, containers, deployment, and external security review must not be inferred from local checks. Exact observed commands and remaining exclusions are in [validation.md](validation.md).
