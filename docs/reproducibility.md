# Reproducible local setup

The public source includes both curated packs and deterministic test fixtures. It does not include a private environment file, a saved-investigation database, source-response caches, installed dependencies, or generated reports.

## Requirements

- Python **3.11–3.13** is declared in `pyproject.toml`. The release check uses **3.11.9**.
- Node **22.19 or later, below 25** is declared in `package.json`. The release check uses **24.16.0**. The lower bound includes the patched development HTTP client used by jsdom.
- **pnpm 11.2.2**, matching the `packageManager` field and CI.
- Internet access for installing packages, downloading Chromium, and the first production build's `next/font` font download. Live source research also requires internet access. Curated workflows and fixture-based tests do not require source-provider credentials.

Windows is the locally tested platform for this release. Linux commands are represented in CI, but hosted CI has not yet run. macOS is not part of the current validation record.

## Install on Windows PowerShell

Run from the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip uninstall -y setuptools
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
pnpm install --frozen-lockfile
pnpm --filter @causalbio/web exec playwright install chromium
pnpm seed
pnpm dev
```

Python 3.11's `venv` can include an old `setuptools` bootstrap package. This project builds with Hatchling and does not use it; the uninstall removes that unnecessary dependency rather than carrying its advisories. Pip's isolated build environment installs the declared build backend automatically.

`pnpm dev` starts both services and stops the sibling if either exits. Open the web app at <http://localhost:3000>, the API health endpoint at <http://127.0.0.1:8000/api/v1/health>, or the API documentation at <http://127.0.0.1:8000/api/docs>. Leave this terminal running; use Ctrl+C to stop it.

No `.env` file is required. [`.env.example`](../.env.example) documents optional settings. Never put credentials in `NEXT_PUBLIC_` variables; those values reach the browser.

## Linux setup represented in CI

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip uninstall -y setuptools
.venv/bin/python -m pip install -e '.[dev]'
pnpm install --frozen-lockfile
pnpm --filter @causalbio/web exec playwright install --with-deps chromium
pnpm seed
pnpm dev
```

These are the platform equivalents, not a claim that a local Linux or macOS run was performed. If using a Python environment outside `.venv`, set `CAUSALBIO_PYTHON` to its interpreter. Dockerfiles and Compose configuration remain available, but Docker was unavailable for this local release pass; successful container execution is not claimed.

## Verification

Stop development servers before the production browser checks so the suite owns ports 3000 and 8000.

```powershell
$env:CI = "1"
pnpm verify
pnpm graph:validate
pnpm python:coverage
pnpm docs:check
pnpm public:check
```

`pnpm verify` includes Python formatting, lint, strict typing, tests and offline evaluations; frontend formatting, lint, TypeScript and component tests; a production build; and Chromium workflows. Browser tests use production servers by default. Explicitly set `CAUSALBIO_E2E_PRODUCTION=0` only when intentionally debugging against a development server.

Coverage and test counts describe exercised software behavior. They do not validate biological claims or clinical usefulness.

## Fresh-source release check

`pnpm release:copy` lists the current Git publication candidates, rejects private/local-only paths, and copies only regular source files to a new temporary directory outside the checkout. It does not copy `.git`, dependencies, `.venv`, `.env`, SQLite files, caches, or build outputs. The generated local manifest allows the public-file checker to run without `.git`.

This is a fresh source-copy check, not a remote clone: the repository has no published commit to clone yet. After publication, the owner should repeat these commands from an actual Git clone.

The check uses `pip --no-cache-dir`, a new isolated pnpm store (`pnpm install --frozen-lockfile --store-dir .pnpm-store`), and a new browser-download directory. Python resolves dependencies from the declared requirements; JavaScript uses the frozen lockfile. Python dependency ranges are not a complete transitive lock, so future resolver results may differ. Local installation records retain the resolved versions without publishing machine paths.

For this isolated check, keep the store setting in the shell for **all** subsequent pnpm commands. pnpm 11 checks installation state before running scripts; a one-command `--store-dir` flag does not configure later invocations. In PowerShell, use `$env:pnpm_config_store_dir = Join-Path (Get-Location) '.pnpm-store'`; in bash, use `export pnpm_config_store_dir="$PWD/.pnpm-store"`. Set `PLAYWRIGHT_BROWSERS_PATH` to the fresh copy's `.cache/browsers` directory before installing and running Chromium. Ordinary setup above uses the default store and does not need these isolation settings.

### Executed release result

The public-source copy passed on **Windows, October 8, 2026**, with Python **3.11.9**, Node **24.16.0**, pnpm **11.2.2**, and independently downloaded Chromium **151.0.7922.34**. Only candidate source files were copied; the environment began without installed packages, build outputs, provider caches, saved sessions, or private `.env` files.

| Step                                                | Result                                                                                                                                    |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Python install from `.[dev]`, with `--no-cache-dir` | Passed; `pip check` found no broken requirements                                                                                          |
| Frozen JavaScript install into isolated store       | Passed; installed Next.js 16.3.8                                                                                                          |
| `pnpm seed`                                         | Both public curated packs seeded successfully                                                                                             |
| `pnpm dev`                                          | Web, API health, and `/api/docs` returned HTTP 200; browser landing-page smoke had no page errors                                         |
| `CI=1 pnpm verify`                                  | Passed in 136s: 384 Python / 54 frontend / 9 production browser tests and 11 offline evaluations, plus formatting, lint, typing and build |
| `pnpm graph:validate`                               | Both curated graphs valid                                                                                                                 |
| `pnpm python:coverage`                              | 94.65% (4,598 / 4,858 statements), measured October 7 before final verification; scientific source unchanged                              |

After the full verification, a startup-only change explicitly bound the web development service to loopback and narrowed Compose's published host ports. The final `pnpm dev` command was smoke-tested again in the same independent environment: both services listened on `127.0.0.1`, and all three HTTP checks passed. No test expectation or scientific behavior changed. The services were then stopped. Docker port mapping and notice/bootstrap changes were inspected but cannot be reported as container-tested.

The first pnpm update attempt mixed store settings across concurrent commands. It was discarded as verification evidence, and a sequential frozen install with the persistent setting above restored the isolated store before the successful full run. A formatting failure in the portable browser config was fixed before the complete verification was rerun. No private local state was copied to resolve either issue.

Final documentation and reviewed media were synchronized after execution; public-file and link checks were repeated against the final manifest. The successful run's implementation files match the publication candidates. Local logs and installation records stay ignored under `artifacts/`; [validation](validation.md) records the exact commands and scientific limits without exposing machine paths.

See [validation](validation.md), [dependency audit](dependency-audit.md), and [public-release audit](public-release-audit.md) for the release evidence and remaining constraints.
