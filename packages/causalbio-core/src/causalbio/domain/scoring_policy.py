"""Explicit ranking policy and local sensitivity results; neither is a probability."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

POSITIVE_COMPONENTS = (
    "evidence_quality",
    "causal_directness",
    "human_relevance",
    "replication",
    "context_match",
)


class ScoringWeights(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    evidence_quality: float = Field(default=0.28, ge=0, le=1)
    causal_directness: float = Field(default=0.24, ge=0, le=1)
    human_relevance: float = Field(default=0.18, ge=0, le=1)
    replication: float = Field(default=0.12, ge=0, le=1)
    context_match: float = Field(default=0.18, ge=0, le=1)
    contradiction_penalty: float = Field(default=0.28, ge=0, le=1)
    extrapolation_penalty: float = Field(default=0.24, ge=0, le=1)
    path_length: float = Field(default=0.10, ge=0, le=1)
    unsupported_link: float = Field(default=0.32, ge=0, le=1)

    @model_validator(mode="after")
    def nonzero_positive_weight(self) -> ScoringWeights:
        if sum(getattr(self, name) for name in POSITIVE_COMPONENTS) <= 0:
            raise ValueError("At least one positive evidence component must have nonzero weight")
        return self


class MechanismRankRange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    hypothesis_id: UUID
    baseline_rank: int = Field(ge=1)
    best_rank: int = Field(ge=1)
    worst_rank: int = Field(ge=1)


class RankingSensitivity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    relative_change: float = Field(gt=0, le=0.5)
    tested_configurations: int = Field(ge=1)
    changed_configurations: int = Field(ge=0)
    stable: bool
    ranks: tuple[MechanismRankRange, ...]
    method: str = "One weight at a time; positive component weights are renormalized."
    limitation: str = (
        "A local policy check, not calibration or a test of source completeness. "
        "Joint weight changes and changes in evidence can produce different rankings."
    )
