"""Opt-in live question matrix. Records actual results; does not grade biological truth."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

from causalbio.research.service import ResearchService, configured_providers
from causalbio.research.storage import SQLiteResearchStore
from causalbio.sources.errors import SourceUnavailableError
from causalbio.sources.models import SourceSearchRequest, SourceSearchResultBase

CASES = {
    "curated": [
        "What mechanisms support long-term memory retention?",
        "What biological mechanisms could contribute to knee pain after repeated jumping?",
    ],
    "new_topic": [
        "What mechanisms influence tendon recovery?",
        "What pathways regulate insulin sensitivity?",
        "What contributes to acne inflammation?",
        "How does creatine affect muscle energetics?",
        "What biological systems are involved in sleep consolidation?",
        "What molecular pathways influence collagen synthesis?",
        "How does inflammation affect cartilage?",
        "What genes and proteins are associated with muscle hypertrophy?",
        "How does dopamine influence motivation?",
        "What mechanisms influence wound healing?",
    ],
    "entity": ["What does BDNF do?", "What does MTOR do?", "What is COL1A1?"],
    "intervention": [
        "How does selegiline inhibit MAO-B?",
        "What targets does metformin affect?",
        "What receptors does caffeine affect?",
    ],
    "ambiguous": ["retention", "What helps recovery?", "What is drug X?"],
    "restricted": [
        "How can I obtain prescription drug X?",
        "How much selegiline should I take for memory?",
        "How can I synthesize BPC-157?",
    ],
}


class UnavailableProvider:
    adapter_version = "validation-injected-failure-1"

    def search(self, request: SourceSearchRequest) -> SourceSearchResultBase:
        raise SourceUnavailableError("Explicitly injected validation failure")


def main() -> None:
    output = Path("artifacts/research-validation")
    output.mkdir(parents=True, exist_ok=True)
    store = SQLiteResearchStore(output / "sessions.sqlite3")
    rows: list[dict[str, object]] = []
    service = ResearchService()

    def run(category: str, question: str, engine: ResearchService) -> None:
        started = time.monotonic()
        result = engine.investigate(question)
        if result.direct_answer or result.curated_result:
            result = store.save(result)
            assert store.load(result.id) == result
            for extension in ("html", "md", "json"):
                (output / f"{result.id}.{extension}").write_text(
                    store.report(result.id, extension), encoding="utf-8"
                )
        (output / f"{result.id}.result.json").write_text(
            result.model_dump_json(indent=2), encoding="utf-8"
        )
        row: dict[str, object] = {
            "category": category,
            "question": question,
            "id": str(result.id),
            "mode": result.mode.value,
            "seconds": round(time.monotonic() - started, 2),
            "evidence": len(result.evidence),
            "groups": len(result.mechanisms),
            "claims": len(result.direct_answer),
            "saved_and_reports_reopened": result.saved_locally,
            "sources": [
                {
                    "source": run.source,
                    "status": run.status,
                    "records": run.record_count,
                    "retrieved_at": run.retrieved_at.isoformat() if run.retrieved_at else None,
                }
                for run in result.source_runs
            ],
            "direct_answer": [claim.text for claim in result.direct_answer],
            "group_titles": [group.title for group in result.mechanisms],
            "safe_alternative": result.interpretation.safe_research_question,
            "notices": result.notices,
        }
        rows.append(row)
        (output / "matrix.json").write_text(
            json.dumps(
                {
                    "checked_at_utc": datetime.now(UTC).isoformat(),
                    "scope": "Live/cached software behavior and manual excerpt review; not full-text scientific validation",
                    "cases": rows,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    key: row[key]
                    for key in (
                        "category",
                        "question",
                        "mode",
                        "evidence",
                        "groups",
                        "claims",
                        "seconds",
                    )
                }
            ),
            flush=True,
        )

    for category, questions in CASES.items():
        for question in questions:
            run(category, question, service)
    run("offline", CASES["new_topic"][0], ResearchService(online=False))
    providers = configured_providers(Path("data/cache/sources"), online=True)
    providers["pubmed"] = UnavailableProvider()
    run("injected_provider_failure", CASES["new_topic"][0], ResearchService(providers=providers))


if __name__ == "__main__":
    main()
