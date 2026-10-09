# CausalBio Lab

An evidence-grounded computational biology workbench connecting questions, sources, mechanism graphs, and selected mathematical models.

> **OWNER REVIEW REQUIRED:** This is a factual case-study draft. Confirm your contribution before adapting “What was built” into first-person portfolio copy. Implementation used coding assistants; the repository alone cannot establish which lines, algorithms, or reviews you personally completed.

## Problem

Biological evidence is distributed across papers, protein databases, tissues, organisms, and experimental settings. A list of search results leaves the reader to reconstruct the proposed mechanism and determine whether the sources actually address the same question. CausalBio makes that structure inspectable while retaining uncertainty and source context.

## What was built

A local research application supports two curated teaching investigations and bounded research into broader biological topics. It presents cited extracts, possible mechanisms, a focused pathway or source map, and saved research reports. Optional tools explore curated graphs, educational Petri/ODE models, known peptide properties, and a separate synthetic Bayesian demonstration.

## Technical approach

Next.js consumes a typed FastAPI contract. A framework-independent Python core uses Pydantic records, a NetworkX directed multigraph, bounded public-source adapters, and immutable SQLite research snapshots. Curated assertions carry context and supporting or conflicting evidence; provisional extracts remain separate and cannot silently become trusted graph relationships. SciPy integrates explicitly authored pathway models. Fixed-step HMC is checked on a two-parameter synthetic Gaussian problem with an analytic reference.

**Key technologies:** Python, TypeScript, Next.js/React, FastAPI, Pydantic, NetworkX, SciPy, SQLite, Cytoscape, pytest, Vitest, and Playwright.

## Hardest problem

Generalizing beyond two curated questions required separating the ability to retrieve related literature from the ability to claim a reviewed mechanism. Metadata-driven packs preserve deeper curated examples, while broader results expose provisional source links and explicit gaps. No numerical model is invented merely because a new question produced a graph.

## What failed

An earlier extraction rule prioritized review publications and sometimes selected literature-search methods or neighboring topics instead of biological findings. The rule was revised to require closer topic overlap, and regression cases were added. The [question review](live-research-validation.md) still documents incomplete and context-mismatched answers; fixing selection did not establish scientific completeness.

## What I learned — owner-review draft

“I learned to separate finding a source, representing its claim, and validating a model. I also learned that revealing every technical tool at once makes a research interface harder to use. The redesign starts with mechanisms and sources, then exposes the graph and numerical tools when they are useful.”

Use this paragraph only if it accurately describes your own learning. Prepare a concrete code or design change you can explain for each sentence.

## Validation

Python, frontend, production browser, and offline-evaluation suites protect the workflow. Tests include source provenance, failure/offline behavior, graph integrity, report persistence, analytic Petri checks, HMC gradients and reversibility, and browser focus restoration. The [release validation record](validation.md) reports current counts and measured coverage; the [reproducibility record](reproducibility.md) documents installation and execution from a fresh public-source copy.

## Limitations and result

The system now provides a reproducible route from a question to inspectable evidence and selected computational analysis. Live research is bounded and can miss or misgroup relevant studies. Curated coverage is small, models are educational, and HMC results concern synthetic data. The application does not diagnose, prescribe, or establish causation from retrieved literature.

## Links

- GitHub: **Owner to add the real public repository URL.**
- Demo: **Owner to add the reviewed recording URL.** See the [recording script](demo-script.md).
- [Architecture](architecture.md), [methods](petri-nets.md), [Bayesian demonstration](bayesian-inference.md), and [limitations](limitations.md).
