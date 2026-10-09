"""Escaped, evidence-linked reports from an already completed research snapshot."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC
from html import escape
from typing import Final

from causalbio import __version__
from causalbio.reporting import ReportGenerator
from causalbio.research.models import (
    ResearchClaim,
    ResearchEvidence,
    ResearchMode,
    UniversalResearchResult,
)

RESEARCH_REPORT_VERSION: Final = "1.0.0"
RESEARCH_SNAPSHOT_VERSION: Final = "causalbio-research-snapshot-1.0"


@dataclass(frozen=True, slots=True)
class ResearchReportArtifacts:
    html: str
    markdown: str
    json: str


def _markdown_text(value: object) -> str:
    """Quote user/source text without allowing HTML, images, or Markdown links."""
    text = escape(str(value), quote=False)
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", text)


def _known(value: object | None) -> str:
    return str(value) if value is not None and value != "" else "Not reported"


def _mode_label(result: UniversalResearchResult) -> str:
    return {
        ResearchMode.CURATED: "Curated evidence pack",
        ResearchMode.LIVE_RESEARCH: "Live evidence research",
        ResearchMode.GENERAL_EVIDENCE_SUMMARY: "Research summary",
        ResearchMode.EXPLANATORY: "Evidence-linked explanation",
        ResearchMode.CLARIFICATION_REQUIRED: "Question awaiting clarification",
        ResearchMode.RESTRICTED_WITH_SAFE_ALTERNATIVE: "Safe research alternative",
        ResearchMode.OUT_OF_DOMAIN: "Question outside biological research",
        ResearchMode.ERROR: "Incomplete investigation",
    }[result.mode]


class _ReportBuilder:
    def __init__(self, evidence: tuple[ResearchEvidence, ...]) -> None:
        self.html: list[str] = []
        self.markdown: list[str] = []
        self.evidence = {record.id: record for record in evidence}
        self.labels = {record.id: index for index, record in enumerate(evidence, start=1)}

    def heading(self, title: str, level: int = 2) -> None:
        self.html.append(f"<h{level}>{escape(title)}</h{level}>")
        self.markdown.extend(("", f"{'#' * level} {_markdown_text(title)}", ""))

    def paragraph(self, text: str) -> None:
        self.html.append(f"<p>{escape(text)}</p>")
        self.markdown.extend((_markdown_text(text), ""))

    def bullets(self, items: tuple[str, ...]) -> None:
        self.html.append("<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>")
        self.markdown.extend(f"- {_markdown_text(item)}" for item in items)
        self.markdown.append("")

    def claim(self, claim: ResearchClaim) -> None:
        html_citations: list[str] = []
        markdown_citations: list[str] = []
        for evidence_id in dict.fromkeys(claim.evidence_ids):
            record = self.evidence[evidence_id]
            label = self.labels[evidence_id]
            html_citations.append(f'<a href="#evidence-{evidence_id}">[{label}]</a>')
            markdown_citations.append(f"[{label}](<{record.source_url}>)")
        self.html.append(f"<p>{escape(claim.text)} {' '.join(html_citations)}</p>")
        self.markdown.extend((f"{_markdown_text(claim.text)} {' '.join(markdown_citations)}", ""))
        self.paragraph(
            f"Evidence interpretation: {claim.kind.replace('_', ' ')}. {claim.uncertainty}"
        )
        if claim.source_passage:
            self.html.append(
                f"<details><summary>Source passage</summary><blockquote>{escape(claim.source_passage)}</blockquote></details>"
            )
            self.markdown.extend((f"> {_markdown_text(claim.source_passage)}", ""))

    def claims(self, claims: tuple[ResearchClaim, ...], *, empty: str) -> None:
        if not claims:
            self.paragraph(empty)
        for claim in claims:
            self.claim(claim)

    def evidence_record(self, record: ResearchEvidence) -> None:
        self.html.append(f'<section id="evidence-{record.id}">')
        self.heading(f"[{self.labels[record.id]}] {record.title}", 3)
        url = str(record.source_url)
        self.html.append(
            f'<p><a href="{escape(url, quote=True)}" rel="noopener noreferrer">Open source record</a></p>'
        )
        self.markdown.extend((f"[Open source record](<{url}>)", ""))
        metadata = (
            ("Source", f"{record.source}: {record.source_record_id}"),
            ("Authors", "; ".join(record.authors) or None),
            ("Publication year", record.year),
            ("DOI", record.doi),
            ("PMID", record.pmid),
            ("Organism", record.organism),
            ("Population", record.population),
            ("Tissue", record.tissue),
            ("Cell type", record.cell_type),
            ("Study type", record.study_type),
            ("Primary research or review", record.primary_or_review),
            ("Experimental context", record.experimental_context),
            ("Result direction", record.result_direction),
            ("Effect estimate", record.effect_estimate),
            ("Sample size", record.sample_size),
            ("Evidence status", record.evidence_status),
            ("Retrieved at", record.retrieved_at.isoformat()),
            ("Retrieval status", record.cache_status.replace("_", " ")),
        )
        self.bullets(tuple(f"{name}: {_known(value)}" for name, value in metadata))
        if record.annotation_evidence:
            self.paragraph(
                "Annotation references are supplied by the source database; they have not been independently retrieved or adjudicated for this investigation."
            )
            self.bullets(
                tuple(
                    f"Annotation evidence: {_known(item.get('evidence_code'))}; source: {_known(item.get('source'))}; identifier: {_known(item.get('identifier'))}"
                    for item in record.annotation_evidence
                )
            )
        self.paragraph(
            "Limitations: "
            + (
                " ".join(record.limitations)
                or "No source limitations were extracted; this is not evidence that none exist."
            )
        )
        self.html.append("</section>")


def generate_research_report(result: UniversalResearchResult) -> ResearchReportArtifacts:
    """Render validated claims without retrieval, synthesis, or trusted graph insertion."""
    result = UniversalResearchResult.model_validate(result.model_dump(mode="json"))
    builder = _ReportBuilder(result.evidence)
    title = result.interpretation.question.original_text
    status = (
        "Curated"
        if result.mode is ResearchMode.CURATED
        else "Provisional; not independently curated"
    )
    builder.heading(title, 1)
    builder.paragraph(f"Investigation type: {_mode_label(result)}. Evidence status: {status}.")
    created = result.created_at.astimezone(UTC).strftime("%B %d, %Y at %H:%M:%S UTC")
    builder.paragraph(
        f"Investigation created: {created}. This report preserves the saved investigation; it does not refresh its sources."
    )
    builder.heading("Research summary")
    builder.claims(
        result.direct_answer,
        empty="No citation-backed direct answer was produced in this snapshot.",
    )
    builder.heading("Interpreted question and context")
    builder.paragraph(result.interpretation.question.interpreted_summary)
    context = result.interpretation.question.context.model_dump()
    builder.bullets(
        tuple(
            f"{key.replace('_', ' ').capitalize()}: {_known('; '.join(value) if isinstance(value, tuple | list) else value)}"
            for key, value in context.items()
        )
    )
    builder.paragraph(result.interpretation.notice)
    builder.heading("Possible mechanisms")
    if not result.mechanisms:
        builder.paragraph(
            "No evidence-backed mechanism families were constructed in this snapshot."
        )
    for mechanism in result.mechanisms:
        builder.heading(mechanism.title, 3)
        builder.paragraph(mechanism.description)
        builder.claims(mechanism.claims, empty="No cited claims are available.")
        builder.bullets(mechanism.uncertainties)
        builder.bullets(
            tuple(f"{name}: {value}" for name, value in mechanism.evidence_dimensions.items())
        )
        builder.paragraph(
            f"Model availability: {mechanism.model_eligibility.replace('_', ' ').lower()}."
        )
    builder.heading("What complicates this explanation?")
    builder.claims(
        result.complications,
        empty="No explicit conflicting claim was extracted. This is not evidence of agreement or a systematic contradiction review.",
    )
    builder.heading("Interventions and modifiers as research objects")
    builder.claims(
        result.modifiers, empty="No citation-backed intervention or modifier claim was extracted."
    )
    builder.heading("Limitations and safety")
    builder.bullets((*result.limitations, *result.notices))
    builder.paragraph(result.interpretation.safety_notice.message)
    builder.heading("Sources searched and unavailable")
    if not result.source_runs:
        builder.paragraph("No live source requests are recorded for this investigation.")
    for run in result.source_runs:
        builder.paragraph(
            f"{run.source} — {run.status}; provider version: {_known(run.provider_version)}; query: {run.query}; {run.record_count} records. Retrieval date: {_known(run.retrieved_at.isoformat() if run.retrieved_at else None)}. {_known(run.detail)}"
        )
    builder.heading("Evidence and retrieval freshness")
    builder.paragraph(
        "Cached retrieval dates describe the original retrieval, not the current date. Missing organism, tissue, population, study-design, or effect information remains unknown."
    )
    if not result.evidence:
        builder.paragraph("No source evidence was retained in this snapshot.")
    for record in result.evidence:
        builder.evidence_record(record)
    builder.heading("Temporary evidence map")
    builder.paragraph(result.graph.notice)
    nodes = {node.id: node.name for node in result.graph.nodes}
    if not result.graph.edges:
        builder.paragraph("No temporary evidence-map connections were constructed.")
    for edge in result.graph.edges:
        references = ", ".join(f"[{builder.labels[item]}]" for item in edge.evidence_ids)
        builder.paragraph(
            f"{nodes[edge.subject_id]} → {edge.relation} → {nodes[edge.object_id]}. Evidence: {references}. Status: {edge.status}."
        )
    if result.curated_result is not None:
        curated = ReportGenerator().generate(result.curated_result)
        builder.heading("Curated investigation appendix")
        builder.paragraph(
            "The following reviewed-pack report preserves its existing claim-to-evidence references and numerical-model limitations."
        )
        for section, content in curated.sections.items():
            builder.heading(section, 3)
            builder.paragraph(content)
    builder.heading("Reproducibility")
    builder.paragraph(result.synthesis_method)
    builder.bullets(
        (
            f"Investigation ID: {result.id}",
            f"Created at: {result.created_at.isoformat()}",
            f"Software version: {__version__}",
            f"Report renderer: {RESEARCH_REPORT_VERSION}",
            f"Snapshot schema: {RESEARCH_SNAPSHOT_VERSION}",
            "The JSON export contains the complete frozen interpretation, source records, cited claims, source runs, temporary graph, and available curated result.",
        )
    )
    html = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">"
        f"<title>{escape(title)} — CausalBio Lab</title>"
        "<style>*{box-sizing:border-box}body{margin:0;background:#f6f4ef;color:#20201d;"
        "font:16px/1.75 'Segoe UI',Arial,sans-serif}"
        "main{max-width:900px;margin:auto;padding:3rem 2rem;overflow-wrap:anywhere}"
        "h1,h2{font-family:Georgia,serif;font-weight:400;line-height:1.2;letter-spacing:-.02em}"
        "h1{font-size:2.5rem}h2{font-size:1.75rem;margin-top:2.5rem;"
        "border-top:1px solid #d8d4cb;padding-top:1.5rem}h3{font-size:1.1rem;line-height:1.4}"
        "a{color:#24483c;text-underline-offset:3px}li{margin:.5rem 0}details{margin:1rem 0}"
        "summary{cursor:pointer;font-weight:600;padding:.5rem 0}"
        "blockquote{border-left:2px solid #a8a397;margin:1rem 0;padding-left:1rem}"
        "a:focus-visible,summary:focus-visible{outline:2px solid #24483c;outline-offset:4px}"
        "pre,code{font-family:Consolas,monospace}pre{overflow:auto}"
        "@media(max-width:600px){main{padding:2rem 1.25rem}h1{font-size:2rem}}"
        "@media(prefers-color-scheme:dark){body{background:#22231f;color:#eeeae0}"
        "h2{border-color:#484a40}a{color:#c7d8cb}blockquote{border-color:#787a6c}"
        "a:focus-visible,summary:focus-visible{outline-color:#c7d8cb}}"
        "@media print{body{background:white;color:#20201d}main{max-width:none;padding:0}"
        "h1,h2,h3{break-after:avoid}a{color:inherit}}</style>"
        "</head><body><main>" + "\n".join(builder.html) + "</main></body></html>\n"
    )
    payload = {
        "schema_version": RESEARCH_SNAPSHOT_VERSION,
        "report_generator_version": RESEARCH_REPORT_VERSION,
        "software_version": __version__,
        "investigation_type": _mode_label(result),
        "evidence_status": status,
        "investigation": result.model_dump(mode="json"),
    }
    return ResearchReportArtifacts(
        html=html,
        markdown="\n".join(builder.markdown).strip() + "\n",
        json=json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    )
