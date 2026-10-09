# Dependency review

Reviewed October 8, 2026. This is a dated check of declared/installed dependencies and known advisory services, not a security certification. The [security policy](../SECURITY.md) describes the local-service boundary. Current functional checks are recorded in [validation](validation.md).

## JavaScript

`pnpm audit --json` initially returned 33 advisory entries. Focused Next.js/ESLint-config and Vitest patches, plus compatible transitive updates, reduced the October 8 full audit to **one high-severity development dependency finding** across 610 dependency records (exit 1). `pnpm audit --prod --json` returned **zero known findings** across its 138 dependency records (exit 0). The full audit is not presented as clean.

The installed and locked Next.js and `eslint-config-next` versions are **16.3.8**. This patch replaces 16.3.6 after a renewed audit found additional production advisories; the [maintainer's release notes](https://github.com/vercel/next.js/releases/tag/v16.3.8) identify its security fixes. Vitest is **4.1.11**. The deprecated `@types/cytoscape` stub was removed because Cytoscape provides its own types.

The remaining package is `braces@3.0.3`, reached through `eslint-config-next → @next/eslint-plugin-next → fast-glob → micromatch`. Deeply nested brace patterns can exhaust the stack. The [GitHub advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) and [upstream report](https://github.com/micromatch/braces/issues/70) were checked directly. Although the audit response suggests `>=3.0.4`, that version was not published in the registry during this check, and the advisory lists no patched version.

This path is development tooling; application code does not import these pattern-processing packages or forward research questions to them. That limits this project's observed exposure, but does not resolve the dependency defect. Keep lint/build tooling away from untrusted glob patterns, review incoming configuration changes, and update the dependency when a verified upstream fix is available. No advisory suppression or unreviewed replacement package was added.

The small [workspace override list](../pnpm-workspace.yaml) raises affected `shell-quote`, `nanoid`, `js-yaml`, `undici`, `brace-expansion`, and `source-map-js` versions within their existing major versions. Remove overrides when the direct dependencies naturally resolve to patched versions. The lockfile records the actual graph; this pass did not broadly upgrade unrelated packages.

## Python

The audit tool, `pip-audit 2.10.1`, was installed in a separate ignored virtual environment. It inspected installed virtual-environment packages, including development tools, using the default PyPI advisory service. The initial result contained 16 entries representing **eight distinct advisory IDs in two tooling packages**; duplicate service records account for the larger entry count. No application-runtime package was reported affected in that scan.

- `virtualenv@21.7.1`, used by pre-commit, had four advisories involving downloaded seed wheels and generated environment configuration/activation scripts. The development dependency floor is now `>=21.7.13,<22`. The maintainer's [21.7.13 advisory](https://github.com/pypa/virtualenv/security/advisories/GHSA-p58f-9548-mpm2) identifies the last of these fixes; the [seed-wheel advisory](https://github.com/pypa/virtualenv/security/advisories/GHSA-94p9-xgh2-xp45) documents the separate integrity issue.
- `setuptools@65.5.0` came from Python's virtual-environment bootstrap, rather than the application manifest. The affected package-index and source-distribution routines are packaging tools. The project builds with Hatchling and has no setuptools imports. No installed dependency required its active extras, so the unused bootstrap package was removed; setup instructions do the same. The [setuptools release history](https://setuptools.pypa.io/en/latest/history.html#v83-0-0) records the Unicode exclusion fix, and the [package-index advisory](https://github.com/pypa/setuptools/security/advisories/GHSA-5rjg-fvgr-3xxf) describes the older traversal issue.

The October 7 audit of the fresh source copy returned **zero known vulnerabilities** across 52 distribution records, with `virtualenv@21.14.5` installed and setuptools absent. The October 8 recheck of the working environment also returned **zero known vulnerabilities**, across 53 distribution records (exit 0). It used `pip-audit --path .venv/Lib/site-packages` from the separate audit environment; no dependency was modified by the scan. The different record counts reflect separately installed environments, not identical Python lockfiles.

The unpublished local `causalbio-lab` distribution was skipped because it has no PyPI advisory entry; these results do not audit the project's own code. Fresh installation and behavior are validated separately in the [release audit](public-release-audit.md).

## Scope and maintenance

Application dependencies were retained where they support actual HTTP retrieval, typed validation, graphs, numerical computation, storage, UI, plotting, or the existing quality checks. Package-manager caches, downloaded tooling, audit JSON, and virtual environments remain local artifacts. A passing advisory scan does not inspect all application logic, every vendored component, unpublished vulnerabilities, or a future deployment.

The existing Starlette/httpx test-client deprecation warning is tracked as compatibility work; it is not itself a reported vulnerability. Recheck advisories before publishing a hosted service and after dependency updates. Do not expose the current unauthenticated local research API as a public confidential workspace.
