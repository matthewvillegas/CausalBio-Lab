"""Tests for deterministic, schema-validated offline question interpretation."""

from __future__ import annotations

import pytest
from causalbio.domain.enums import QuestionClass
from causalbio.questions import (
    AmbiguousQuestionError,
    EmptyQuestionError,
    UnsupportedQuestionError,
    interpret_question,
)


@pytest.mark.parametrize("text", ["", "  ", "a", " \n x \t"])
def test_empty_or_too_short_questions_are_rejected(text: str) -> None:
    with pytest.raises(EmptyQuestionError, match="at least three characters"):
        interpret_question(text)


def test_retention_without_a_biological_outcome_returns_clarifying_alternatives() -> None:
    with pytest.raises(AmbiguousQuestionError, match="ambiguous") as error:
        interpret_question("retention")

    assert "long-term memory retention" in error.value.alternatives
    assert "fluid retention" in error.value.alternatives


def test_question_spanning_both_demo_domains_is_rejected_as_ambiguous() -> None:
    with pytest.raises(AmbiguousQuestionError, match="one outcome at a time") as error:
        interpret_question("Could knee pain interfere with memory after jumping?")

    assert error.value.alternatives == (
        "long-term memory retention",
        "activity-related knee pain",
    )


def test_unsupported_domain_reports_the_offline_pack_boundary() -> None:
    with pytest.raises(UnsupportedQuestionError, match="offline MVP"):
        interpret_question("How does liver metabolism regulate blood glucose?")


def test_memory_interpretation_normalizes_whitespace_and_is_deterministic() -> None:
    domain, question = interpret_question("  How   could memory persist after learning?  ")
    repeated_domain, repeated = interpret_question("How could memory persist after learning?")

    assert domain == repeated_domain == "memory"
    assert question.id == repeated.id
    assert question.original_text == "How could memory persist after learning?"
    assert question.normalized_text == "how could memory persist after learning?"
    assert question.question_classes == (
        QuestionClass.BIOLOGICAL_PROCESS,
        QuestionClass.PATHWAY,
    )
    assert question.context.anatomical_region == "brain"
    assert "animal evidence" in question.context.population


def test_knee_interpretation_keeps_diagnosis_uncertain() -> None:
    domain, question = interpret_question(
        "What mechanisms contribute to knee pain after repeated jumping?"
    )

    assert domain == "knee-pain"
    assert QuestionClass.SYMPTOM_MECHANISM in question.question_classes
    assert question.context.activity == "repeated jumping and landing"
    assert "not an individual diagnosis" in question.context.population
    assert "not as a diagnosis" in question.interpreted_summary


def test_context_updates_are_applied_but_unknown_fields_are_rejected() -> None:
    _, question = interpret_question(
        "How could memory persist after learning?",
        context_updates={"activity": "spaced learning", "wants_interventions": False},
    )
    assert question.context.activity == "spaced learning"
    assert question.context.wants_interventions is False

    with pytest.raises(ValueError, match="Unknown context fields: secret_field"):
        interpret_question(
            "How could memory persist after learning?",
            context_updates={"secret_field": "not allowed"},
        )
