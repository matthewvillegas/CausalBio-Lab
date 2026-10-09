"""Frozen research sessions preserve provenance and never become trusted graph records."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest
from causalbio.domain.models import QuestionContext, ResearchQuestion
from causalbio.investigations.service import InvestigationService
from causalbio.research.models import (
    ResearchClaim,
    ResearchEdge,
    ResearchEvidence,
    ResearchInterpretation,
    ResearchMechanism,
    ResearchMode,
    ResearchNode,
    SourceRun,
    TemporaryGraph,
    UniversalResearchResult,
)
from causalbio.research.reporting import generate_research_report
from causalbio.research.storage import ReportFormat, ResearchSnapshotError, SQLiteResearchStore
from causalbio.safety.classifier import classify_query
from factories import uid
from pydantic import ValidationError

STAMP = datetime(2026, 10, 2, 12, 30, tzinfo=UTC)
EXTRACT = (
    "Fixture association only; ![remote](https://example.org/image). <svg onload='x'>fixture</svg>"
)
COUNTEREVIDENCE = "Fixture counterevidence is mixed."
MODIFIER = "Fixture modifier is only a research object."


@pytest.fixture
def research_result() -> UniversalResearchResult:
    """All claims and identifiers are explicit software fixtures, not scientific sources."""
    question = ResearchQuestion(
        id=uid(100),
        original_text="How does fixture tendon recovery work?",
        normalized_text="how does fixture tendon recovery work?",
        question_classes=(),
        interpreted_summary="Synthetic research-session fixture for tendon recovery.",
        context=QuestionContext(
            requested_outcome="fixture tendon recovery",
            symptom_or_process="synthetic repair",
            tissue="tendon",
            population="software fixture",
        ),
    )
    record = ResearchEvidence(
        id=uid(101),
        source="software-fixture",
        source_record_id="fixture-study",
        title="Synthetic record <script>alert('source')</script>",
        abstract=" ".join((EXTRACT, COUNTEREVIDENCE, MODIFIER)),
        authors=("Fixture author",),
        year=2025,
        source_url="https://example.org/fixture-study",
        organism="mouse",
        population="synthetic software objects",
        tissue="fixture tendon",
        cell_type="fixture cell",
        study_type="synthetic animal experiment",
        primary_or_review="primary",
        experimental_context="Synthetic reduced-load condition",
        result_direction="mixed",
        effect_estimate="Synthetic estimate; not a biological measurement",
        sample_size=12,
        annotation_evidence=(
            {"evidence_code": "ECO:0000250", "source": "PubMed", "identifier": "12345678"},
        ),
        limitations=("This is a test fixture with no real scientific claims.",),
        retrieved_at=STAMP - timedelta(days=2),
        cache_status="stale_cache",
    )
    claim = ResearchClaim(
        id=uid(102),
        text=EXTRACT,
        evidence_ids=(record.id,),
        kind="source_extract",
        source_passage=EXTRACT,
        relation="ASSOCIATED_WITH",
        uncertainty="Software fixture; not causation.",
    )
    nodes = (
        ResearchNode(id=uid(104), name="Synthetic repair", entity_type="process"),
        ResearchNode(id=uid(105), name="Fixture study", entity_type="study"),
    )
    return UniversalResearchResult(
        id=uid(110),
        mode=ResearchMode.GENERAL_EVIDENCE_SUMMARY,
        interpretation=ResearchInterpretation(
            mode=ResearchMode.GENERAL_EVIDENCE_SUMMARY,
            question=question,
            search_queries=("fixture tendon recovery",),
            notice="Using cached fixture evidence.",
            safety_notice=classify_query(question.original_text),
        ),
        direct_answer=(claim,),
        mechanisms=(
            ResearchMechanism(
                id=uid(103),
                title="Fixture repair",
                description="Software-only grouping",
                claims=(claim,),
                evidence_dimensions={"Context match": "Unclear"},
            ),
        ),
        evidence=(record,),
        graph=TemporaryGraph(
            nodes=nodes,
            edges=(
                ResearchEdge(
                    id=uid(106),
                    subject_id=nodes[0].id,
                    object_id=nodes[1].id,
                    relation="ASSOCIATED_WITH",
                    claim_id=claim.id,
                    evidence_ids=(record.id,),
                ),
            ),
        ),
        complications=(
            claim.model_copy(
                update={
                    "id": uid(107),
                    "relation": "CONTRADICTED_BY",
                    "text": COUNTEREVIDENCE,
                    "source_passage": COUNTEREVIDENCE,
                }
            ),
        ),
        modifiers=(
            claim.model_copy(update={"id": uid(108), "text": MODIFIER, "source_passage": MODIFIER}),
        ),
        source_runs=(
            SourceRun(
                source="software-fixture",
                provider_version="fixture-adapter-1.2.3",
                query="fixture tendon recovery",
                status="cached",
                record_count=1,
                retrieved_at=record.retrieved_at,
            ),
            SourceRun(
                source="other-fixture",
                query="fixture repair",
                status="unavailable",
                record_count=0,
                detail="Simulated timeout",
            ),
        ),
        limitations=("A software-test investigation only.",),
        notices=("Cached fixture evidence is not current.",),
        created_at=STAMP,
    )


def test_reopened_store_preserves_full_snapshot_and_reports(
    tmp_path: Path, research_result: UniversalResearchResult
) -> None:
    path = tmp_path / "research.sqlite3"
    saved = SQLiteResearchStore(path).save(research_result)
    reopened = SQLiteResearchStore(path)
    assert saved.saved_locally
    assert reopened.load(saved.id) == saved
    assert reopened.list_recent() == [
        {
            "id": str(saved.id),
            "question": saved.interpretation.question.original_text,
            "mode": saved.mode.value,
            "created_at": STAMP.isoformat(),
        }
    ]
    exported = json.loads(reopened.report(saved.id, "json"))
    assert exported["investigation"] == saved.model_dump(mode="json")
    assert exported["evidence_status"] == "Provisional; not independently curated"
    assert exported["report_generator_version"]
    assert reopened.report(saved.id, "md") == reopened.report(saved.id, "markdown")
    with sqlite3.connect(path) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert tables == {"research_sessions"}


def test_report_links_claims_preserves_unknowns_cache_and_failure_and_escapes_content(
    research_result: UniversalResearchResult,
) -> None:
    report = generate_research_report(research_result)
    assert f'href="#evidence-{research_result.evidence[0].id}"' in report.html
    assert 'href="https://example.org/fixture-study"' in report.html
    assert "<script>" not in report.html and "<svg onload" not in report.html
    assert "&lt;script&gt;" in report.html and "&lt;svg" in report.html
    assert "Content-Security-Policy" in report.html
    assert "frame-ancestors" not in report.html
    assert "![remote]" not in report.markdown
    for detail in (
        "Organism: mouse",
        "Tissue: fixture tendon",
        "DOI: Not reported",
        "PMID: Not reported",
        "Sample size: 12",
        "Primary research or review: primary",
        "Result direction: mixed",
        "stale cache",
        "Simulated timeout",
        "provider version: fixture-adapter-1.2.3",
        "2026-09-30",
        "ASSOCIATED_WITH",
        "Source links and topic membership are not causal effects",
        "Annotation evidence: ECO:0000250; source: PubMed; identifier: 12345678",
        "have not been independently retrieved or adjudicated",
    ):
        assert detail in report.html
    assert research_result.complications[0].text in report.html
    assert research_result.modifiers[0].text in report.html


def test_report_uses_readable_summary_and_utc_time_without_changing_snapshot(
    research_result: UniversalResearchResult,
) -> None:
    result = research_result.model_copy(
        update={
            "mode": ResearchMode.GENERAL_EVIDENCE_SUMMARY,
            "created_at": datetime.fromisoformat("2026-10-03T23:45:07-05:00"),
        }
    )
    original = result.model_dump(mode="json")
    report = generate_research_report(result)

    assert "Investigation type: Research summary." in report.html
    assert "<h2>Research summary</h2>" in report.html
    assert "Overview" not in report.html
    assert "General evidence summary" not in report.html
    assert "Investigation created: October 04, 2026 at 04:45:07 UTC." in report.html
    assert f"Created at: {result.created_at.isoformat()}" in report.html
    assert result.evidence[0].retrieved_at.isoformat() in report.html
    assert "## Research summary" in report.markdown
    assert json.loads(report.json)["investigation"] == original
    assert result.model_dump(mode="json") == original


def test_same_id_is_idempotent_but_cannot_replace_evidence(
    tmp_path: Path, research_result: UniversalResearchResult
) -> None:
    store = SQLiteResearchStore(tmp_path / "research.sqlite3")
    saved = store.save(research_result)
    assert store.save(research_result) == store.save(saved) == saved
    changed = research_result.model_copy(
        update={"evidence": (research_result.evidence[0].model_copy(update={"organism": "human"}),)}
    )
    with pytest.raises(ResearchSnapshotError, match="different snapshot"):
        store.save(changed)
    assert store.load(saved.id).evidence[0].organism == "mouse"
    assert len(store.list_recent()) == 1


def test_modified_models_are_revalidated_before_persistence(
    tmp_path: Path, research_result: UniversalResearchResult
) -> None:
    store = SQLiteResearchStore(tmp_path / "research.sqlite3")
    invalid = research_result.model_copy(update={"evidence": ()})
    with pytest.raises(ValidationError, match="same result"):
        store.save(invalid)
    assert store.list_recent() == []


@pytest.mark.parametrize("column", ["payload", "report_html", "report_markdown", "report_json"])
def test_corrupted_snapshots_or_artifacts_are_not_silently_returned(
    tmp_path: Path, research_result: UniversalResearchResult, column: str
) -> None:
    path = tmp_path / "research.sqlite3"
    store = SQLiteResearchStore(path)
    store.save(research_result)
    with sqlite3.connect(path) as connection:
        # The column is selected only from this fixed parameterized test list.
        connection.execute(f"UPDATE research_sessions SET {column} = ?", ("corrupted",))
    with pytest.raises(ResearchSnapshotError, match="integrity"):
        if column == "payload":
            store.load(research_result.id)
        else:
            format = {"report_html": "html", "report_markdown": "md", "report_json": "json"}[column]
            store.report(research_result.id, cast(ReportFormat, format))


def test_recent_order_missing_sessions_and_bounded_limits(
    tmp_path: Path, research_result: UniversalResearchResult
) -> None:
    store = SQLiteResearchStore(tmp_path / "research.sqlite3")
    store.save(research_result)
    newer = research_result.model_copy(
        update={"id": uid(111), "created_at": STAMP + timedelta(hours=1)}
    )
    store.save(newer)
    assert [item["id"] for item in store.list_recent(limit=1)] == [str(newer.id)]
    with pytest.raises(ValueError, match="limit"):
        store.list_recent(0)
    with pytest.raises(KeyError, match="Unknown saved"):
        store.load(uid(999))
    with pytest.raises(ValueError, match="format"):
        store.report(research_result.id, cast(ReportFormat, "../../report.html"))


def test_curated_reports_keep_existing_reviewed_report_appendix(
    research_result: UniversalResearchResult,
) -> None:
    curated = InvestigationService().investigate(
        "What mechanisms support long-term memory retention?"
    )
    result = research_result.model_copy(
        update={"mode": ResearchMode.CURATED, "curated_result": curated}
    )
    report = generate_research_report(result)
    assert "Investigation type: Curated evidence pack. Evidence status: Curated." in report.html
    assert "Curated investigation appendix" in report.html
    assert "plausibility index" in report.html
    assert "4727084" in report.html
