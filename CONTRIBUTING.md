# Contributing to CausalBio Lab

Thank you for helping improve CausalBio Lab. Contributions are welcome across scientific curation, Python, TypeScript, documentation, accessibility, testing, and research-software quality.

The project is research software, not a clinical decision system. A smaller, traceable contribution is preferable to an impressive-looking claim that cannot be reproduced.

## Development setup

Use Python `>=3.11,<3.14`, Node `>=22.19,<25`, and pnpm `11.2.2`. See the [README setup](README.md#run-it-locally) and [reproducibility record](docs/reproducibility.md) for the combinations actually tested. A declared version range is not a tested-platform matrix.

From the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip uninstall -y setuptools
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
pnpm install --frozen-lockfile
pnpm seed
pnpm dev
```

On macOS or Linux, use `.venv/bin/python` in place of `.venv\Scripts\python.exe` for the installation command. Root pnpm scripts select the platform-appropriate interpreter from `.venv`; set `CAUSALBIO_PYTHON` only when an explicit alternative interpreter is needed. Installation and font compilation require internet access. The curated demonstrations work offline without a cloud account, API key, Docker, or an LLM. Live research contacts public scientific providers; disabling it permits cached or local evidence where available, not new uncached retrieval.

## Before submitting a change

Run the checks relevant to your work. The complete local verification command is:

```powershell
pnpm --filter @causalbio/web exec playwright install chromium
pnpm verify
pnpm graph:validate
pnpm docs:check
pnpm public:check
```

`pnpm verify` runs Python formatting, lint, strict typing, tests and offline evaluations, then frontend formatting, lint, typing, component tests, a production build and production browser workflows. Stop development servers first and set `CI=1` to require fresh test servers. Use the individual scripts in `package.json` for a focused local check; report what actually ran. Coverage is available through `pnpm python:coverage`.

Add or update tests whenever behavior changes. Do not rewrite unrelated files or silently weaken validation to make a test pass.

## Scientific contributions

Scientific claims require more than a graph triple. New or changed assertions should include:

- a typed relation and explicit causal status;
- biological and population context;
- supporting and, where present, contradictory evidence IDs;
- source identifiers, source URL, retrieval date, and curation status;
- a plain-language interpretation and important limitations;
- a defensible evidence grade that follows the documented rubric.

Curated demo data live in `data/demo/<pack>/pack.json`. Keep packs deterministic and schema-valid. Do not fabricate references, excerpts, effect estimates, sample sizes, identifiers, model parameters, or validation results. Clearly label synthetic values and animal-to-human extrapolation.

A grade, heuristic plausibility index, mechanism path, or Petri simulation must never be described as a posterior probability, causal effect estimate, diagnosis, treatment recommendation, or personalized prediction.

## Adding a domain pack

1. Define stable UUIDs and typed entities.
2. Add full evidence records before trusted assertions that reference them.
3. Add assertions, competing hypotheses, interventions, and a curated Petri model.
4. Validate the pack by loading it through the domain registry.
5. Seed a temporary SQLite snapshot and verify a round trip.
6. Add tests for graph integrity, contradictions, paths, safety language, and reporting.
7. Document the pack's scope, provenance, synthetic fields, and omissions.

Two production packs are bundled: memory and activity-related knee pain. Pack discovery and interpretation use metadata rather than a hard-coded two-topic allowlist. Supply recognition terms, context defaults and readiness metadata through the [domain-pack contract](docs/domain-pack-authoring.md); verify discovery and interpretation without adding unnecessary frontend branches. General biological questions use the separate provisional-research route.

Curated evidence is explicitly reviewed and packaged with assertions. Provisional evidence consists of normalized source records and traceable extracts; it does not become curated because a source is reputable or a test passes. Keep unknown context unknown and preserve conflicting findings. Changes to extraction or grouping need fixtures that demonstrate the intended scientific distinction, including a case that must remain unsupported.

Source adapters must use adapter-controlled HTTPS endpoints, bounded requests, strict normalized schemas, explicit timeout and unavailable-source errors, fixture transports, cache-integrity checks, and an untrusted review boundary. Never connect adapter output directly to a trusted assertion.

The peptide module accepts only slugs from the curated known-peptide registry. Do not add an arbitrary-sequence analysis, generation, synthesis, procurement, dosing, or activity-prediction endpoint. Keep calculated properties, measured values, database annotations, and heuristic labels visibly separate.

## Safety and security

Do not add dosing, procurement, synthesis, evasion-of-oversight, or individualized treatment functionality. Retrieved abstracts and metadata are untrusted input and must never be allowed to alter application instructions or create trusted assertions without review.

Never commit secrets, personal health information, proprietary source text, or data without a compatible license. Report security issues as described in [SECURITY.md](SECURITY.md), not in a public issue.

## Pull requests

Keep pull requests focused. Describe:

- what changed and why;
- scientific assumptions and provenance impacts;
- tests and commands actually run;
- user-visible safety implications;
- known limitations or follow-up work.

Before submitting, check that provenance and safety boundaries remain intact, public files contain no credentials or local artifacts, and tests assert the intended behavior rather than mirror implementation details. Explain new dependencies and remove unrelated generated output.

Use clear commit messages and update documentation or `CHANGELOG.md` when behavior, schemas, data, or public interfaces change. Never invent prior commits, dates, citations, contributors, or validation. Describe coding-assistant use honestly when discussing personal authorship. By contributing, you agree that your contribution is licensed under Apache-2.0.
