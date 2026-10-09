"""Conservative metadata-driven interpretation; no arbitrary biological synthesis."""

from __future__ import annotations

import re
from collections.abc import Mapping

from causalbio.demo.metadata import question_from_metadata
from causalbio.demo.registry import DomainPackRegistry
from causalbio.domain.models import QuestionContext, ResearchQuestion


class QuestionInterpretationError(ValueError):
    alternatives: tuple[str, ...] = ()


class EmptyQuestionError(QuestionInterpretationError):
    pass


class UnsupportedQuestionError(QuestionInterpretationError):
    def __init__(self, message: str, alternatives: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.alternatives = alternatives


class AmbiguousQuestionError(QuestionInterpretationError):
    def __init__(self, message: str, alternatives: tuple[str, ...]) -> None:
        super().__init__(message)
        self.alternatives = alternatives


def normalize_question(text: str) -> str:
    return " ".join(text.strip().split())


def identify_domain(text: str, *, registry: DomainPackRegistry | None = None) -> str:
    selected_registry = registry or DomainPackRegistry()
    matches: list[str] = []
    metadata = {slug: selected_registry.metadata(slug) for slug in selected_registry.slugs()}
    for slug, item in metadata.items():
        for term, alternatives in item.ambiguous_terms.items():
            if normalize_question(text).casefold() == term.casefold():
                raise AmbiguousQuestionError(
                    f"“{term}” is ambiguous without a biological outcome.", alternatives
                )
        if any(
            re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.I)
            for term in item.recognition_terms
        ):
            matches.append(slug)
    if len(matches) > 1:
        raise AmbiguousQuestionError(
            "The question spans multiple curated demonstration domains. Investigate one outcome at a time.",
            tuple(metadata[slug].clarification_label for slug in matches),
        )
    if matches:
        return matches[0]
    titles = ", ".join(item.title for item in metadata.values())
    raise UnsupportedQuestionError(
        f"The offline MVP currently has curated evidence packs for: {titles}.",
        tuple(item.example_questions[0] for item in metadata.values()),
    )


def interpret_question(
    text: str,
    *,
    context_updates: Mapping[str, str | bool | None] | None = None,
    registry: DomainPackRegistry | None = None,
) -> tuple[str, ResearchQuestion]:
    normalized = normalize_question(text)
    if len(normalized) < 3:
        raise EmptyQuestionError("Enter a biological question with at least three characters.")
    selected_registry = registry or DomainPackRegistry()
    domain = identify_domain(normalized, registry=selected_registry)
    metadata = selected_registry.metadata(domain)
    context = metadata.context_defaults
    if context_updates:
        unknown = set(context_updates) - set(QuestionContext.model_fields)
        if unknown:
            raise ValueError(f"Unknown context fields: {', '.join(sorted(unknown))}")
        context = QuestionContext.model_validate({**context.model_dump(), **context_updates})
    return domain, question_from_metadata(domain, metadata, normalized, context)
