"""Opt-in, minimal live contract smoke; never run as part of the offline suite."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from causalbio.sources import (
    EuropePMCAdapter,
    FileSystemSourceCache,
    PubMedAdapter,
    SourceAdapterError,
    SourceSearchRequest,
    UniProtAdapter,
)


def main() -> None:
    checks: list[dict[str, object]] = []
    with TemporaryDirectory(prefix="causalbio-source-smoke-") as directory:
        cache = FileSystemSourceCache(Path(directory))
        for adapter, query, expected_id in (
            (PubMedAdapter(cache=cache), "2869411[uid]", "2869411"),
            (UniProtAdapter(cache=cache), "accession:P01303", "P01303"),
            (EuropePMCAdapter(cache=cache), "EXT_ID:41303871 AND SRC:MED", "MED:41303871"),
        ):
            check: dict[str, object] = {
                "source": adapter.name,
                "query": query,
                "limit": 1,
                "checked_at": datetime.now(UTC).isoformat(),
            }
            try:
                result = adapter.search(SourceSearchRequest(query=query, limit=1))
                check.update(
                    outcome="passed"
                    if result.record_ids() == (expected_id,)
                    else "unexpected_records",
                    record_ids=result.record_ids(),
                    retrieved_at=result.retrieved_at.isoformat(),
                    cache_status=result.cache_status.value,
                    source_endpoint=str(result.source_endpoint),
                )
            except SourceAdapterError as exc:
                check.update(outcome="failed", error_type=type(exc).__name__, error=str(exc))
            checks.append(check)
    print(json.dumps({"checks": checks}, indent=2))
    if any(check["outcome"] != "passed" for check in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
