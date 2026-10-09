"""Versioned API request and lightweight response schemas."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from causalbio.domain.models import QuestionContext, ResearchQuestion, SafetyNotice
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(ApiModel):
    status: Literal["ok"] = "ok"
    version: str
    mode: Literal["local-demo"] = "local-demo"
    no_llm: bool
    no_telemetry: bool
    demo_pack_count: int


class QuestionRequest(ApiModel):
    question: str = Field(min_length=1, max_length=2000)
    context: dict[str, str | bool | None] = Field(default_factory=dict)


class InterpretationResponse(ApiModel):
    domain_pack: str
    question: ResearchQuestion
    safety_notice: SafetyNotice


class PathSearchRequest(ApiModel):
    investigation_id: UUID
    source_id: UUID
    target_id: UUID
    max_length: int = Field(default=6, ge=1, le=10)


class SimulationRequest(ApiModel):
    model_id: UUID
    scenario: str = Field(default="baseline", max_length=120)
    duration: float = Field(default=24.0, gt=0, le=1000)
    steps: int = Field(default=121, ge=3, le=5000)
    seed: int = 1729
    parameter_overrides: dict[str, float] = Field(default_factory=dict)
    initial_overrides: dict[str, float] = Field(default_factory=dict)


class HMCDemoRequest(ApiModel):
    chains: int = Field(default=4, ge=2, le=8)
    warmup: int = Field(default=500, ge=100, le=5000)
    draws: int = Field(default=750, ge=100, le=5000)
    leapfrog_steps: int = Field(default=8, ge=1, le=50)
    step_size: float = Field(default=0.55, gt=0, le=1)
    seed: int = 1729


class ReportRequest(ApiModel):
    investigation_id: UUID
    persist_artifacts: bool = True


class ReportArtifact(ApiModel):
    format: str
    filename: str
    media_type: str
    download_url: str


class ReportResponse(ApiModel):
    report_id: UUID
    citation_coverage: float
    artifacts: tuple[ReportArtifact, ...]


class LiteratureSearchRequest(ApiModel):
    query: str = Field(min_length=2, max_length=500)
    mode: Literal["bundled", "live"] = "bundled"

    @field_validator("query", mode="before")
    @classmethod
    def trim_query(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class LiteratureSearchResponse(ApiModel):
    mode: Literal["bundled"]
    records: tuple[dict[str, object], ...]
    cached: bool = True
    notice: str = "Bundled curated records only; not a real-time systematic search."


class ContextUpdateRequest(ApiModel):
    context: QuestionContext
