"""Tiered research API, separate from trusted curated graph mutations."""

from typing import Literal
from uuid import UUID

from causalbio.research.models import (
    ResearchDepth,
    ResearchInterpretation,
    ResearchMode,
    UniversalResearchResult,
)
from causalbio.research.router import route_question
from causalbio.research.service import ResearchService
from causalbio.research.storage import SQLiteResearchStore
from fastapi import APIRouter, Query, Response
from pydantic import Field, StrictBool

from causalbio_api.config import get_settings
from causalbio_api.exceptions import openapi_error_responses
from causalbio_api.schemas import ApiModel

router = APIRouter(
    prefix="/api/v1/research", tags=["general research"], responses=openapi_error_responses()
)


class ResearchRequest(ApiModel):
    question: str = Field(min_length=3, max_length=2000)
    depth: ResearchDepth = "research"
    context: dict[str, str | bool | None] = Field(default_factory=dict)
    online: StrictBool = True


def research_store() -> SQLiteResearchStore:
    return SQLiteResearchStore(get_settings().research_database)


def research_service(online: bool) -> ResearchService:
    settings = get_settings()
    return ResearchService(
        online=online and settings.live_research_enabled, cache_root=settings.source_cache_dir
    )


@router.get("/status")
def research_status() -> dict[str, object]:
    enabled = get_settings().live_research_enabled
    return {
        "live_enabled": enabled,
        "status_label": "Live research enabled"
        if enabled
        else "Offline — using cached/curated evidence",
        "sources": ["Europe PMC", "PubMed", "UniProt"],
        "notice": "Provider availability is checked during each bounded search. Enabling live research sends scientific search terms to these public sources; no LLM or telemetry is used.",
    }


@router.post("/interpret", response_model=ResearchInterpretation)
def interpret_research(payload: ResearchRequest) -> ResearchInterpretation:
    return route_question(payload.question, depth=payload.depth, context_updates=payload.context)


@router.post("", response_model=UniversalResearchResult)
def create_research(payload: ResearchRequest) -> UniversalResearchResult:
    result = research_service(payload.online).investigate(
        payload.question, depth=payload.depth, context_updates=payload.context
    )
    if result.mode in {
        ResearchMode.CURATED,
        ResearchMode.LIVE_RESEARCH,
        ResearchMode.EXPLANATORY,
        ResearchMode.GENERAL_EVIDENCE_SUMMARY,
    }:
        return research_store().save(result)
    return result


@router.get("/sessions")
def recent_research(limit: int = Query(default=20, ge=1, le=100)) -> object:
    return research_store().list_recent(limit)


@router.get("/{research_id}", response_model=UniversalResearchResult)
def saved_research(research_id: UUID) -> UniversalResearchResult:
    return research_store().load(research_id)


@router.get("/{research_id}/report/{report_format}")
def research_report(
    research_id: UUID, report_format: Literal["html", "md", "markdown", "json"]
) -> Response:
    rendered = research_store().report(research_id, report_format)
    extension = "md" if report_format == "markdown" else report_format
    media_type = {"html": "text/html", "md": "text/markdown", "json": "application/json"}[extension]
    return Response(
        content=rendered,
        media_type=media_type,
        headers={
            "content-disposition": f'{"inline" if extension == "html" else "attachment"}; filename="causalbio-research-{research_id}.{extension}"',
            "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
            "x-content-type-options": "nosniff",
        },
    )
