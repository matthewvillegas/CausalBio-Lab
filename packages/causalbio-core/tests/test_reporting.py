"""Focused tests for evidence-linked, honest, and safe report generation."""

from __future__ import annotations

from uuid import UUID

import pytest
from causalbio.domain.models import InvestigationResult, ReportClaim
from causalbio.investigations.service import InvestigationService
from causalbio.reporting import (
    REQUIRED_REPORT_SECTIONS,
    ReportGenerator,
    ReportValidationError,
    generate_report,
    render_html,
    render_markdown,
    validate_claim_evidence,
    validate_report,
)


@pytest.fixture(scope="module")
def memory_investigation() -> InvestigationResult:
    return InvestigationService().investigate("What mechanisms support long-term memory retention?")


def test_complete_report_has_graph_local_citations_and_unavailable_analyses(
    memory_investigation: InvestigationResult,
) -> None:
    report = generate_report(memory_investigation)
    graph_evidence_ids = {record.id for record in memory_investigation.graph.evidence}

    assert tuple(report.sections) == REQUIRED_REPORT_SECTIONS
    assert report.investigation_id == memory_investigation.id
    assert report.citation_coverage == 1.0
    assert validate_claim_evidence(report.claims, memory_investigation) == 1.0
    assert validate_report(report, memory_investigation) == 1.0
    assert set(report.reference_evidence_ids) == graph_evidence_ids
    assert report.claims
    assert all(
        claim.evidence_ids and set(claim.evidence_ids) <= graph_evidence_ids
        for claim in report.claims
        if claim.is_scientific_claim
    )

    assert "Unavailable" in report.sections["Bayesian model"]
    assert "No priors, likelihood" in report.sections["Bayesian model"]
    assert "Unavailable" in report.sections["Posterior diagnostics"]
    assert "Unavailable" in report.sections["Sensitivity analysis"]
    assert "contains no SimulationRun" in report.sections["Simulation results"]
    assert (
        "no explicitly curated contradictory"
        not in report.sections["Contradictory evidence"].casefold()
    )
    assert "has no effects on declarative memory" in report.sections["Contradictory evidence"]
    assert "Evidence ranking:" in report.sections["Sensitivity analysis"]
    assert "Policy weights:" in report.sections["Evidence-plausibility scoring"]
    assert memory_investigation.ranking_sensitivity is not None
    assert report.reproduction[
        "ranking_sensitivity"
    ] == memory_investigation.ranking_sensitivity.model_dump(mode="json")


def test_validator_rejects_uncited_or_unknown_scientific_claims(
    memory_investigation: InvestigationResult,
) -> None:
    report = generate_report(memory_investigation)
    uncited = ReportClaim(
        id=UUID(int=2**128 - 2),
        text="An unsupported scientific statement.",
        evidence_ids=(),
    )
    uncited_report = report.model_copy(update={"claims": (*report.claims, uncited)})

    with pytest.raises(ReportValidationError, match="has no evidence IDs"):
        validate_report(uncited_report, memory_investigation)

    unknown_evidence_id = UUID(int=2**128 - 1)
    unknown = report.claims[0].model_copy(update={"evidence_ids": (unknown_evidence_id,)})
    unknown_report = report.model_copy(update={"claims": (unknown, *report.claims[1:])})
    with pytest.raises(ReportValidationError, match="absent from the graph"):
        validate_report(unknown_report, memory_investigation)


def test_validator_allows_uncited_non_scientific_metadata_claim(
    memory_investigation: InvestigationResult,
) -> None:
    report = generate_report(memory_investigation)
    metadata_claim = ReportClaim(
        id=UUID(int=2**128 - 3),
        text="The report was generated offline.",
        evidence_ids=(),
        is_scientific_claim=False,
    )
    augmented = report.model_copy(update={"claims": (*report.claims, metadata_claim)})

    assert validate_report(augmented, memory_investigation) == 1.0


def test_validator_requires_every_citation_in_the_reference_index(
    memory_investigation: InvestigationResult,
) -> None:
    report = generate_report(memory_investigation)
    shortened = report.model_copy(
        update={"reference_evidence_ids": report.reference_evidence_ids[1:]}
    )

    with pytest.raises(ReportValidationError, match="missing from the reference index"):
        validate_report(shortened, memory_investigation)


def test_renderers_are_complete_deterministic_and_escape_untrusted_text(
    memory_investigation: InvestigationResult,
) -> None:
    malicious_question = memory_investigation.question.model_copy(
        update={
            "original_text": (
                '<script>alert("report")</script> What mechanisms support memory retention?'
            )
        }
    )
    malicious_result = memory_investigation.model_copy(update={"question": malicious_question})
    generator = ReportGenerator()
    first = generator.generate(malicious_result)
    second = generator.generate(malicious_result)
    markdown = render_markdown(first)
    html = render_html(first)

    assert first.id == second.id
    assert tuple(claim.id for claim in first.claims) == tuple(claim.id for claim in second.claims)
    assert first.reference_evidence_ids == second.reference_evidence_ids

    assert markdown.startswith("# Research summary\n\n## Question")
    assert "### Bayesian model" in markdown
    assert '&lt;script&gt;alert("report")&lt;/script&gt;' in markdown
    assert "<script>" not in markdown

    assert html.startswith("<!doctype html>")
    assert "Content-Security-Policy" in html
    assert "default-src 'none'" in html
    assert "frame-ancestors" not in html
    assert "<script>" not in html
    assert "&lt;script&gt;alert(&quot;report&quot;)&lt;/script&gt;" in html
    assert "<h2>Bayesian model</h2>" in html
    assert html.rstrip().endswith("</html>")


@pytest.mark.parametrize(
    "question",
    (
        "What mechanisms support long-term memory retention?",
        "What could contribute to knee pain after repeated jumping?",
    ),
)
def test_summary_precedes_collapsed_technical_appendix(question: str) -> None:
    report = generate_report(InvestigationService().investigate(question))
    html = render_html(report)
    markdown = render_markdown(report)
    summary_html, appendix_html = html.split('<details class="appendix">')
    summary_markdown, appendix_markdown = markdown.split("## Research and reproducibility appendix")
    expected_summary = (
        "Question",
        "Top mechanisms",
        "Strongest evidence",
        "Biggest uncertainties",
        "Intervention research",
        "Key limitations",
    )
    assert tuple(report.sections)[:6] == expected_summary
    for section in expected_summary:
        assert f"<h2>{section}</h2>" in summary_html
        assert f"## {section}" in summary_markdown
    assert "What argues against this?" in summary_html
    assert "[E" in summary_html
    assert "R-hat" not in summary_html
    assert "random seed" not in summary_html
    assert "graph version" not in summary_markdown
    assert "Reproduction information" in appendix_html
    assert "random seed" in appendix_markdown
    assert "<details open" not in html


def test_report_honestly_handles_an_evidence_pack_without_a_model(
    memory_investigation: InvestigationResult,
) -> None:
    result = memory_investigation.model_copy(update={"petri_model": None})
    report = generate_report(result)
    assert "does not include an executable pathway model" in report.sections["Petri-net model"]
    assert "no executable pathway model" in report.sections["Limitations"]
    assert validate_report(report, result) == 1.0
