"""CausalBio Lab v1 API routes."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from causalbio import __version__ as core_version
from causalbio.demo.registry import available_domain_packs, domain_pack_slugs, load_domain_pack
from causalbio.domain.enums import InferenceState
from causalbio.domain.models import (
    CausalAssertion,
    EvidenceRecord,
    GraphProjection,
    HMCConfiguration,
    HMCInferenceRun,
    InferenceEligibility,
    InvestigationResult,
    MechanismPath,
    MechanisticHypothesis,
    PetriModel,
    SimulationParameters,
    SimulationRun,
)
from causalbio.graph.repository import LocalKnowledgeGraph
from causalbio.inference import run_hmc_demo
from causalbio.investigations.service import InvestigationService
from causalbio.peptides import KnownPeptideRegistry, analyze_known_peptide, compare_known_peptides
from causalbio.peptides.analysis import (
    KnownPeptide,
    KnownPeptideAnalysis,
    PeptideSequenceComparison,
)
from causalbio.petri import PetriEngine
from causalbio.questions.interpreter import interpret_question
from causalbio.reporting import ReportGenerator
from causalbio.safety.classifier import classify_query
from fastapi import APIRouter, Query, Request, Response, status
from fastapi.responses import FileResponse

from causalbio_api.config import get_settings
from causalbio_api.exceptions import openapi_error_responses
from causalbio_api.schemas import (
    HealthResponse,
    HMCDemoRequest,
    InterpretationResponse,
    LiteratureSearchRequest,
    LiteratureSearchResponse,
    PathSearchRequest,
    QuestionRequest,
    ReportArtifact,
    ReportRequest,
    ReportResponse,
    SimulationRequest,
)
from causalbio_api.state import report_artifacts, store

router = APIRouter(prefix="/api/v1", responses=openapi_error_responses())
service = InvestigationService()


def _graph_for(result: InvestigationResult) -> LocalKnowledgeGraph:
    return LocalKnowledgeGraph(
        result.graph.entities,
        result.graph.assertions,
        result.graph.evidence,
        graph_id=result.graph.graph_id,
        version=result.graph_version,
    )


def _model(model_id: UUID) -> PetriModel:
    for slug in domain_pack_slugs():
        model = load_domain_pack(slug).petri_model
        if model is not None and model.id == model_id:
            return model
    raise KeyError(f"Unknown Petri model: {model_id}")


def _assertion(assertion_id: UUID) -> tuple[CausalAssertion, tuple[EvidenceRecord, ...]]:
    for slug in domain_pack_slugs():
        pack = load_domain_pack(slug)
        lookup = {record.id: record for record in pack.evidence}
        for assertion in pack.assertions:
            if assertion.id == assertion_id:
                ids = (*assertion.supporting_evidence_ids, *assertion.contradictory_evidence_ids)
                return assertion, tuple(lookup[item] for item in ids)
    raise KeyError(f"Unknown assertion: {assertion_id}")


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        version=core_version,
        no_llm=settings.no_llm,
        no_telemetry=settings.no_telemetry,
        demo_pack_count=len(domain_pack_slugs()),
    )


@router.get("/demo-cases", tags=["investigations"])
def demo_cases() -> tuple[dict[str, object], ...]:
    return available_domain_packs()


@router.post(
    "/questions/interpret",
    response_model=InterpretationResponse,
    tags=["investigations"],
)
def interpret(payload: QuestionRequest) -> InterpretationResponse:
    safety = classify_query(payload.question)
    if safety.restricted:
        # Use the same exception path as full investigations.
        from causalbio.investigations.service import RestrictedQueryError

        raise RestrictedQueryError(safety.message)
    domain, question = interpret_question(payload.question, context_updates=payload.context)
    return InterpretationResponse(domain_pack=domain, question=question, safety_notice=safety)


@router.post(
    "/investigations",
    response_model=InvestigationResult,
    status_code=status.HTTP_201_CREATED,
    tags=["investigations"],
)
def create_investigation(payload: QuestionRequest) -> InvestigationResult:
    result = service.investigate(payload.question, context_updates=payload.context)
    store.put(result)
    return result


@router.get(
    "/investigations/{investigation_id}",
    response_model=InvestigationResult,
    tags=["investigations"],
)
def get_investigation(investigation_id: UUID) -> InvestigationResult:
    return store.get(investigation_id)


@router.get(
    "/investigations/{investigation_id}/hypotheses",
    response_model=tuple[MechanisticHypothesis, ...],
    tags=["investigations"],
)
def hypotheses(investigation_id: UUID) -> tuple[MechanisticHypothesis, ...]:
    return store.get(investigation_id).hypotheses


@router.get(
    "/investigations/{investigation_id}/graph",
    response_model=GraphProjection,
    tags=["graph"],
)
def investigation_graph(investigation_id: UUID) -> GraphProjection:
    return store.get(investigation_id).graph


@router.get(
    "/assertions/{assertion_id}",
    response_model=CausalAssertion,
    tags=["graph"],
)
def assertion(assertion_id: UUID) -> CausalAssertion:
    return _assertion(assertion_id)[0]


@router.get(
    "/assertions/{assertion_id}/evidence",
    response_model=tuple[EvidenceRecord, ...],
    tags=["evidence"],
)
def assertion_evidence(assertion_id: UUID) -> tuple[EvidenceRecord, ...]:
    return _assertion(assertion_id)[1]


@router.post("/paths/search", response_model=tuple[MechanismPath, ...], tags=["graph"])
def search_paths(payload: PathSearchRequest) -> tuple[MechanismPath, ...]:
    result = store.get(payload.investigation_id)
    graph = _graph_for(result)
    return graph.search_paths(
        payload.source_id,
        payload.target_id,
        max_length=payload.max_length,
        requested_context=result.question.context.tissue,
    )


@router.get("/petri/models", response_model=tuple[PetriModel, ...], tags=["simulation"])
def petri_models() -> tuple[PetriModel, ...]:
    return tuple(
        model
        for slug in domain_pack_slugs()
        if (model := load_domain_pack(slug).petri_model) is not None
    )


@router.post("/petri/simulate", response_model=SimulationRun, tags=["simulation"])
def simulate(payload: SimulationRequest) -> SimulationRun:
    model = _model(payload.model_id)
    parameters = SimulationParameters(**payload.model_dump())
    return PetriEngine(model).simulate_continuous(parameters)


@router.post("/bayes/infer", response_model=InferenceEligibility, tags=["inference"])
def infer() -> InferenceEligibility:
    return InferenceEligibility(
        state=InferenceState.INELIGIBLE,
        eligible=False,
        requirements={
            "defined_numerical_model": True,
            "observed_or_curated_numerical_data": False,
            "unknown_parameters": False,
            "explicit_priors": False,
            "explicit_likelihood": False,
            "identifiability_review": False,
            "hmc_backend_and_diagnostics": False,
        },
        explanation=(
            "Bayesian parameter inference is unavailable because the bundled pathways lack an "
            "approved observation model, identified unknowns, priors, likelihood, and diagnostics."
        ),
    )


@router.post("/bayes/demo/run", response_model=HMCInferenceRun, tags=["inference"])
def run_bayesian_demo(payload: HMCDemoRequest) -> HMCInferenceRun:
    """Run real HMC only for the bundled, fully specified synthetic model."""

    return run_hmc_demo(HMCConfiguration(**payload.model_dump()))


@router.get("/peptides/known", response_model=tuple[KnownPeptide, ...], tags=["peptides"])
def known_peptides() -> tuple[KnownPeptide, ...]:
    """List only the reviewed sequences in the bundled known-peptide registry."""

    return KnownPeptideRegistry().list()


@router.get(
    "/peptides/known/{slug}/analysis",
    response_model=KnownPeptideAnalysis,
    tags=["peptides"],
)
def known_peptide_analysis(
    slug: str,
    ph: float = Query(default=7.4, alias="pH", ge=0, le=14),
) -> KnownPeptideAnalysis:
    return analyze_known_peptide(slug, pH=ph)


@router.get(
    "/peptides/compare/{slug_a}/{slug_b}",
    response_model=PeptideSequenceComparison,
    tags=["peptides"],
)
def known_peptide_comparison(slug_a: str, slug_b: str) -> PeptideSequenceComparison:
    return compare_known_peptides(slug_a, slug_b)


@router.post(
    "/literature/search",
    response_model=LiteratureSearchResponse,
    tags=["evidence"],
)
def literature_search(
    payload: LiteratureSearchRequest, request: Request
) -> LiteratureSearchResponse:
    if payload.mode == "live":
        correlation_id = str(getattr(request.state, "correlation_id", "unavailable"))
        return Response(
            status_code=503,
            media_type="application/problem+json",
            content=json.dumps(
                {
                    "type": "https://causalbio.example/problems/external-source-unavailable",
                    "title": "Live literature source is unavailable in offline mode",
                    "status": 503,
                    "detail": "Use bundled mode or configure a validated source adapter.",
                    "correlation_id": correlation_id,
                    "alternatives": ["bundled"],
                }
            ),
        )  # type: ignore[return-value]
    query = payload.query.casefold()
    records: list[dict[str, object]] = []
    for slug in domain_pack_slugs():
        for record in load_domain_pack(slug).evidence:
            haystack = f"{record.study.title} {record.evidence_note}".casefold()
            if all(term in haystack for term in query.split()):
                records.append(record.model_dump(mode="json"))
    return LiteratureSearchResponse(mode="bundled", records=tuple(records))


@router.get("/graph-exports/{investigation_id}/{export_format}", tags=["exports"])
def graph_export(investigation_id: UUID, export_format: str) -> Response:
    result = store.get(investigation_id)
    if export_format not in {"json-ld", "graphml", "nodes-csv", "edges-csv"}:
        raise ValueError("Supported graph exports: json-ld, graphml, nodes-csv, edges-csv")
    exports = _graph_for(result).exports()
    options = {
        "json-ld": (exports.json_ld, "application/ld+json", "jsonld"),
        "graphml": (exports.graphml, "application/graphml+xml", "graphml"),
        "nodes-csv": (exports.nodes_csv, "text/csv", "nodes.csv"),
        "edges-csv": (exports.edges_csv, "text/csv", "edges.csv"),
    }
    try:
        content, media_type, extension = options[export_format]
    except KeyError as exc:
        raise ValueError("Supported graph exports: json-ld, graphml, nodes-csv, edges-csv") from exc
    filename = f"causalbio-{investigation_id}-{extension}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"content-disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/reports", response_model=ReportResponse, tags=["reports"])
def create_report(payload: ReportRequest) -> ReportResponse:
    investigation = store.get(payload.investigation_id)
    generator = ReportGenerator()
    report = generator.generate(investigation)
    if not payload.persist_artifacts:
        return ReportResponse(
            report_id=report.id,
            citation_coverage=report.citation_coverage,
            artifacts=(),
        )
    graph_exports = _graph_for(investigation).exports()
    settings = get_settings()
    root = settings.artifact_dir.resolve()
    report_dir = (root / str(report.id)).resolve()
    if root != report_dir.parent:
        raise ValueError("Resolved report directory escaped the configured artifact root")
    report_dir.mkdir(parents=True, exist_ok=True)

    contents: dict[str, tuple[str, str, str]] = {
        "report.md": (generator.render_markdown(report), "text/markdown", "Markdown"),
        "report.html": (generator.render_html(report), "text/html", "HTML"),
        "report.json": (
            report.model_dump_json(indent=2),
            "application/json",
            "Complete report JSON",
        ),
        "investigation.json": (
            investigation.model_dump_json(indent=2),
            "application/json",
            "Investigation JSON",
        ),
        "graph.jsonld": (graph_exports.json_ld, "application/ld+json", "JSON-LD"),
        "graph.graphml": (graph_exports.graphml, "application/graphml+xml", "GraphML"),
        "nodes.csv": (graph_exports.nodes_csv, "text/csv", "Node table CSV"),
        "edges.csv": (graph_exports.edges_csv, "text/csv", "Edge table CSV"),
    }
    if investigation.petri_model is not None:
        contents["petri-model.json"] = (
            json.dumps(investigation.petri_model.model_dump(mode="json"), indent=2),
            "application/json",
            "Petri model JSON",
        )
    paths: dict[str, Path] = {}
    artifacts: list[ReportArtifact] = []
    for filename, (content, media_type, label) in contents.items():
        path = report_dir / filename
        path.write_text(content, encoding="utf-8", newline="\n")
        paths[filename] = path
        artifacts.append(
            ReportArtifact(
                format=label,
                filename=filename,
                media_type=media_type,
                download_url=f"/api/v1/reports/{report.id}/artifacts/{filename}",
            )
        )
    report_artifacts.put(report.id, paths)
    return ReportResponse(
        report_id=report.id,
        citation_coverage=report.citation_coverage,
        artifacts=tuple(artifacts),
    )


@router.get("/reports/{report_id}/artifacts/{filename}", tags=["reports"])
def report_artifact(report_id: UUID, filename: str) -> FileResponse:
    """Open the script-free HTML report in a browser; download its data artifacts."""
    path = report_artifacts.get(report_id, filename)
    media_types = {
        ".md": "text/markdown",
        ".html": "text/html",
        ".json": "application/json",
        ".jsonld": "application/ld+json",
        ".graphml": "application/graphml+xml",
        ".csv": "text/csv",
    }
    return FileResponse(
        path,
        media_type=media_types.get(path.suffix, "application/octet-stream"),
        filename=path.name,
        content_disposition_type="inline" if path.suffix == ".html" else "attachment",
        headers={
            "Content-Security-Policy": (
                "default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; "
                "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
            ),
            "X-Content-Type-Options": "nosniff",
        },
    )
