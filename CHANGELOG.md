# Changelog

## Unreleased — planned v1.0.0: Public Research MVP

These are prepared release notes for the current implementation. No tag, GitHub release, or earlier public version is claimed. Package version `1.0.0` identifies the prepared source; publication remains an [owner action](docs/github-publishing-checklist.md).

### Investigation

- Two curated teaching packs: long-term memory and activity-related knee loading.
- Broader biological research and direct entity explanations through bounded literature/database retrieval, alongside clarification and explicit scientific alternatives for restricted requests.
- Editable interpretation and context, with curated and provisional results kept separate.

### Evidence

- PubMed, Europe PMC, and UniProt adapters with bounded requests, source identity checks, timeout handling, validated caches, and visible partial/offline results.
- Source-linked extracts and mechanism groups with publication identifiers, original retrieval dates, unknown context, uncertainty, and conflicting findings preserved.
- Typed contextual assertions and validated NetworkX graphs for curated packs; provisional source maps do not establish causation.

### Modeling

- Discrete Petri-net execution and bounded analysis, plus continuous constant/mass-action ODE simulation through SciPy.
- Fixed-step Hamiltonian Monte Carlo on an explicit synthetic linear-Gaussian model, including numerical recovery, posterior predictions, and diagnostics.
- Read-only analysis of two known peptides with calculated properties distinguished from measured biological effects.

### Product and reproducibility

- Research-notebook interface with focused pathways, numbered citations, source drawers, references, and optional graph/numerical workbenches.
- Saved general investigations and immutable report snapshots, plus curated graph/model exports and reproducibility records.
- Responsive and dark layouts, keyboard controls, focus restoration, graph text alternatives, and reduced-motion support.

### Release preparation and validation

- Public-file and documentation checks, reproducible setup instructions, release materials, and owner-review contribution/portfolio drafts.
- Python, component, production browser, numerical, offline-evaluation, and graph-integrity checks. Exact commands, current counts, coverage, and clean-copy results belong to the [validation record](docs/validation.md) and [reproducibility record](docs/reproducibility.md), not an assumed hosted CI result.

### Known limitations

Live retrieval is bounded rather than systematic. Evidence context and grouping can be incomplete. Curated packs are small educational examples; pathway models depend on declared assumptions. Bayesian inference is limited to the synthetic demonstration. The local application has no authentication or multi-user isolation and does not diagnose, prescribe, or establish clinical validity. See [scientific limitations](docs/limitations.md) and the [roadmap](docs/roadmap.md).
