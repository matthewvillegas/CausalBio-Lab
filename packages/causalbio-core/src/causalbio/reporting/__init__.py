"""Evidence-linked research report generation and in-memory rendering."""

from causalbio.reporting.generator import (
    REPORT_GENERATOR_VERSION,
    REQUIRED_REPORT_SECTIONS,
    ReportGenerator,
    ReportValidationError,
    generate_html,
    generate_markdown,
    generate_report,
    render_html,
    render_markdown,
    validate_claim_evidence,
    validate_report,
)

__all__ = [
    "REPORT_GENERATOR_VERSION",
    "REQUIRED_REPORT_SECTIONS",
    "ReportGenerator",
    "ReportValidationError",
    "generate_html",
    "generate_markdown",
    "generate_report",
    "render_html",
    "render_markdown",
    "validate_claim_evidence",
    "validate_report",
]
