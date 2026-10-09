"""Validated pack discovery and interpretation metadata, independent of pack loading."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Annotated

from pydantic import Field, StrictBool, StringConstraints, model_validator

from causalbio.domain.enums import QuestionClass
from causalbio.domain.identifiers import stable_uuid
from causalbio.domain.models import DomainModel, QuestionContext, ResearchQuestion

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class NumericalMetadata(DomainModel):
    """Availability declarations, never permission to fit an unspecified model."""

    observations_available: StrictBool = False
    unknown_parameters_defined: StrictBool = False
    priors_defined: StrictBool = False
    likelihood_defined: StrictBool = False
    identifiability_reviewed: StrictBool = False
    explanation: Text


class PackMetadata(DomainModel):
    title: Text
    clarification_label: Text
    version: Text
    description: Text
    educational_notice: Text
    curated_at: datetime
    retrieved_at: date
    display_order: int = 100
    example_questions: tuple[Text, ...] = Field(min_length=1)
    recognition_terms: tuple[Text, ...] = Field(min_length=1)
    ambiguous_terms: dict[Text, tuple[Text, ...]] = Field(default_factory=dict)
    context_defaults: QuestionContext
    interpreted_summary: Text
    question_classes: tuple[QuestionClass, ...] = Field(min_length=1)
    expected_hypothesis_keys: tuple[Text, ...] = Field(min_length=1)
    numerical_data: NumericalMetadata

    @model_validator(mode="after")
    def check_metadata(self) -> PackMetadata:
        if self.curated_at.tzinfo is None:
            raise ValueError("Pack curation timestamp must include its timezone")
        if len(set(self.expected_hypothesis_keys)) != len(self.expected_hypothesis_keys):
            raise ValueError("Expected hypothesis keys must be unique")
        if len({term.casefold() for term in self.recognition_terms}) != len(self.recognition_terms):
            raise ValueError("Recognition terms must be unique ignoring case")
        if any(not alternatives for alternatives in self.ambiguous_terms.values()):
            raise ValueError("Ambiguous terms must provide clarification alternatives")
        return self


def question_from_metadata(
    slug: str, metadata: PackMetadata, text: str, context: QuestionContext | None = None
) -> ResearchQuestion:
    normalized = " ".join(text.split())
    selected_context = context or metadata.context_defaults
    identity = json.dumps(
        {"pack": slug, "text": normalized.casefold(), "context": selected_context.model_dump()},
        sort_keys=True,
        separators=(",", ":"),
    )
    return ResearchQuestion(
        id=stable_uuid("question", identity),
        original_text=normalized,
        normalized_text=normalized.casefold(),
        question_classes=metadata.question_classes,
        interpreted_summary=metadata.interpreted_summary,
        context=selected_context,
    )
