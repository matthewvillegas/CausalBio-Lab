# Architecture decision records

## ADR-001: Python 3.11 is the supported baseline

**Status:** accepted

Python 3.11 is the locally validated baseline for the scientific stack. The project declares `>=3.11,<3.14`; this compatibility range is broader than the versions actually exercised locally. Additional interpreter versions need their own test results rather than an assumed pass. See [validation](validation.md) for the tested environment.

## ADR-002: Scientific logic is framework-independent

**Status:** accepted

The `causalbio` package must not import FastAPI, SQLAlchemy web models, or frontend concepts. The API composes core services. This makes scientific tests runnable offline and prevents UI state from changing results.

## ADR-003: Assertions, not bare triples, are the graph primitive

**Status:** accepted

A NetworkX `MultiDiGraph` stores assertion IDs as edge keys and keeps full typed assertion payloads. This preserves provenance, contradiction, species, tissue, causal status, and curation state across projections and exports.

## ADR-004: Curated fixtures are canonical for the demo

**Status:** accepted

Versioned JSON files are reviewable in source control and work without infrastructure. SQLite is a materialized local repository created by the seed script. This is more reproducible than treating a generated database as the only source of truth.

## ADR-005: Deterministic interpretation precedes optional LLM support

**Status:** accepted

Synonym maps and explicit rules support bundled examples and common variants. Ambiguous inputs produce alternatives rather than a silent choice. An LLM provider can later implement the same validated interface but is not required and cannot insert trusted claims.

## ADR-006: Evidence scoring is transparent and non-probabilistic

**Status:** accepted

Evidence grades and mechanism ranking expose their components. The displayed plausibility index is a normalized heuristic used for ordering; it is not a causal effect, clinical confidence, or Bayesian probability.

## ADR-007: Petri execution is restricted to curated models

**Status:** accepted

The MVP provides schema-validated, educational memory and knee-load models with synthetic parameters. It supports discrete firing plus continuous ODE simulation for explicit supported rate laws. Known-system numerical tests do not validate these biological abstractions. Knowledge-graph edges are not automatically converted into executable biology.

## ADR-008: Bayesian inference is eligibility-gated

**Status:** accepted

No inference result is produced without observations, unknown parameters, explicit priors, an explicit likelihood, identifiability review, a supported HMC/NUTS backend, and diagnostics. The initial vertical slice returns a structured ineligibility explanation rather than fake samples.

## ADR-009: Next.js client UI consumes a typed API contract

**Status:** accepted

The web app uses strict TypeScript models mirroring versioned response schemas. Cytoscape is loaded client-side. Scientific analysis is fetched once per question/context change; theme, tabs, filters, and simple/advanced mode remain local display state.

## ADR-010: Local setup cannot depend on Docker or uv

**Status:** accepted

The documented baseline uses `py -3.11 -m venv`, pip, and pnpm because those tools exist in the workspace environment. Docker Compose and uv-compatible metadata may be added, but are optional.
