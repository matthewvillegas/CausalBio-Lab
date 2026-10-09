# Local research sessions and reports

`causalbio.research.storage.SQLiteResearchStore` preserves complete `UniversalResearchResult` snapshots in a separate SQLite database, `data/research.sqlite3` by default. It does not insert evidence, entities, or assertions into the trusted domain-pack database. The API can inject a different database path for local configuration or isolated tests.

A save validates the entire result again, including claim-to-source references, temporary graph references, and timezone-aware retrieval timestamps. It then atomically stores:

- the original question and complete interpreted context;
- result mode, direct answer, mechanism groups, complications and modifiers;
- the exact evidence records, source IDs, available source metadata, retrieval dates, cache status and provisional/curated labels;
- the temporary evidence graph and any included reviewed-pack result;
- source searches, partial failures and unavailable sources;
- limitations, synthesis method, creation time and saved status;
- standalone HTML, Markdown and JSON reports, with renderer, software and snapshot-schema versions.

The stored payload and each rendered artifact have SHA-256 content digests. Reads reject corrupted content instead of silently regenerating it. These checks detect accidental corruption; they are not signatures against an attacker who can rewrite the local database. Reports are rendered from the completed snapshot without network retrieval or new biological synthesis.

Snapshots are immutable through this interface. Saving exactly the same ID and payload is idempotent, after normalizing `saved_locally` to `true`. Saving different evidence or context under an existing ID is rejected. A refreshed investigation needs a new result ID, so old reports retain the evidence and retrieval date that supported them. Recent-session summaries are bounded to 1–100 entries, defaulting to 20, and ordered by creation time.

## Python interface

```python
from pathlib import Path
from causalbio.research.storage import SQLiteResearchStore

store = SQLiteResearchStore(Path("data/research.sqlite3"))
saved = store.save(completed_result)
same_snapshot = store.load(saved.id)
recent = store.list_recent(limit=20)
html_report = store.report(saved.id, "html")
markdown_report = store.report(saved.id, "md")  # "markdown" also works
json_report = store.report(saved.id, "json")
```

Unknown IDs raise `KeyError`. Invalid formats, conflicting snapshots and integrity failures raise `ValueError` subclasses. Generated artifacts live in the same transaction and table as the result; a failed save cannot leave a partially populated session. Each database operation opens and closes its own connection, and writes use an immediate transaction to serialize conflicting writers.

## Report interpretation

Every report starts with its investigation type and evidence status. Live or general research remains provisional; a source being retrieved successfully does not make its assertions curated. Source-extract claims link to the evidence entries they cite. Supporting passages and uncertainty remain visible. A curated result retains the existing reviewed report in an appendix.

Reports list searched and unavailable sources, original retrieval timestamps, and cache status. A cached date is never changed to the report creation date. Missing organism, population, tissue, cell type, sample size, effect estimate, identifiers and study-design details are explicitly “Not reported.” Lack of an extracted contradiction is described as an incomplete assessment, not consensus. The temporary map retains association/source-membership relations and explicitly disclaims causal-effect interpretation.

HTML escapes user and source text, uses a restrictive Content Security Policy, and needs no remote assets or scripts. Markdown escapes source-authored HTML and link/image syntax while retaining renderer-created citation links. JSON contains the complete frozen result, including available abstracts and all supplied metadata, plus export version information. Missing provider version information is not inferred from the retrieval date or reported as known.

## Verification and current limits

`packages/causalbio-core/tests/test_research_storage_reports.py` exercises reopened-database round trips, complete metadata retention, report citations and escaping, provisional labels, failed providers and stale sources, immutable IDs, revalidation, corruption rejection, recent ordering/limits, and reviewed-report preservation. The store is local persistence, not a multi-user account system, shared workspace, cloud backup, source monitoring service, or automatic curation pathway.
