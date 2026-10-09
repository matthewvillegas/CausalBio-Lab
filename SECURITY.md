# Security policy

## Reporting a vulnerability

Do not post suspected vulnerabilities, secrets, personal research queries, or private logs in public issues or pull requests. Use the repository's **Security → Report a vulnerability** option if the owner has enabled GitHub private vulnerability reporting. If it is unavailable, use an established private channel with the maintainer; this repository does not invent a contact address.

Include the affected commit or version, a minimal reproduction, impact, and redacted logs. Reports are handled on a best-effort basis; no response-time guarantee is offered. Fixes target the current development branch. A `v1.0.0` release is being prepared; this policy does not claim that it has been published or that older versions have a maintenance commitment.

## Local service boundary

CausalBio Lab is designed for a local research demonstration. It has no accounts, authorization, tenant isolation, or confidential research workspace. Saved questions, results, and report snapshots are stored locally; anyone with access to the service or its files may be able to read them. Keep it bound to loopback. A public GitHub repository is not authorization to expose the running API publicly.

The API validates typed inputs, bounds actual request-body bytes before parsing (including chunked requests), checks report paths, escapes report content, applies response security headers and configured CORS, and uses a process-local request limiter. These measures do not replace authentication or a deployment security review. The limiter is neither shared across workers nor durable.

## Scientific sources and content

The general research workflow can contact PubMed, Europe PMC, and UniProt. Live searches send scientific search terms to those services. Disable live retrieval with `CAUSALBIO_LIVE_RESEARCH_ENABLED=false` for cached/curated operation. The application has no LLM or telemetry integration.

Adapters control the HTTPS destinations, disable redirects, bound response sizes and result counts, apply cooperative timeouts/retries, and validate source identity and cached schemas. These are application controls, not an operating-system egress sandbox or a hard deadline for every upstream worker. A shared deployment would also need admission controls, shared upstream rate limiting, and an explicit network policy.

Treat abstracts, metadata, identifiers, and any imported research text as untrusted content. A source response cannot automatically become trusted curated evidence. Preserve citations and licensing information; do not commit private questions, patient records, unrestricted response dumps, or unlicensed full text. See [source boundaries](docs/data-sources.md) and [third-party notices](THIRD_PARTY_NOTICES.md).

## Secrets and dependencies

- No credentials are required for the documented local demo. `.env.example` contains only safe configuration examples. Keep real `.env` files, caches, SQLite databases, logs, and browser artifacts out of Git.
- Values prefixed `NEXT_PUBLIC_` are sent to the browser and must never contain secrets.
- If a credential is accidentally committed or otherwise exposed, revoke or rotate it. Deleting the current file does not remove previous exposure or Git history.
- Review security advisories for declared dependencies and apply focused updates with the existing tests. Do not assume a passing test suite or a one-time dependency scan proves security.
- The dated [dependency review](docs/dependency-audit.md) records the current scan results and the unresolved development-only `braces` advisory. It does not claim the full dependency audit is clean.
- Before distributing a hosted build or container, retain dependency and font notices and review that deployment's authentication, TLS, logging, backups, deletion policy, and access controls.

Scientific disagreements can use the evidence issue template; provenance corruption or routing flaws that turn unsupported content into trusted claims may also be security-integrity issues. The project is not a medical device, diagnosis service, or prescribing system.
