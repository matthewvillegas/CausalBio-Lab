"""Tests for transparent medical and bioactive-query safety boundaries."""

from __future__ import annotations

import pytest
from causalbio.domain.enums import QuerySafetyClass
from causalbio.safety import classify_query
from causalbio.safety.classifier import RESEARCH_BOUNDARY


@pytest.mark.parametrize(
    ("text", "expected_class"),
    [
        ("How many mg should I take?", QuerySafetyClass.DOSING),
        ("How much metformin can I take?", QuerySafetyClass.DOSING),
        ("Where can I buy this peptide?", QuerySafetyClass.ACQUISITION),
        ("Where to buy BPC-157?", QuerySafetyClass.ACQUISITION),
        ("Where should I order this compound?", QuerySafetyClass.ACQUISITION),
        ("Give me a synthesis protocol for this peptide", QuerySafetyClass.SYNTHESIS),
        (
            "I want to inject myself as a self-experiment",
            QuerySafetyClass.DANGEROUS_SELF_EXPERIMENTATION,
        ),
        ("How do I inject BPC-157?", QuerySafetyClass.DANGEROUS_SELF_EXPERIMENTATION),
        ("How to administer this peptide?", QuerySafetyClass.DANGEROUS_SELF_EXPERIMENTATION),
        ("Which drug should I use for my memory?", QuerySafetyClass.PERSONALIZED_PRESCRIBING),
        ("Do I have patellar tendinopathy?", QuerySafetyClass.DIAGNOSTIC_REQUEST),
    ],
)
def test_restricted_queries_are_classified_without_operational_guidance(
    text: str, expected_class: QuerySafetyClass
) -> None:
    notice = classify_query(text)
    assert notice.query_class is expected_class
    assert notice.restricted is True
    assert notice.urgent is False
    assert RESEARCH_BOUNDARY in notice.message
    assert notice.allowed_scope


def test_urgent_warning_signs_take_precedence_over_dosing_language() -> None:
    notice = classify_query("I have chest pain; how many mg should I take?")

    assert notice.query_class is QuerySafetyClass.URGENT_SYMPTOMS
    assert notice.restricted is True
    assert notice.urgent is True
    assert "emergency services" in notice.message
    assert RESEARCH_BOUNDARY in notice.message


@pytest.mark.parametrize(
    ("text", "expected_class"),
    [
        ("How does NMDA signaling affect memory?", QuerySafetyClass.GENERAL_RESEARCH),
        ("Why can knee pain follow repeated jumping?", QuerySafetyClass.SYMPTOM_EDUCATION),
        ("How does this peptide bind its receptor?", QuerySafetyClass.INTERVENTION_RESEARCH),
        ("How do cells synthesize collagen?", QuerySafetyClass.GENERAL_RESEARCH),
        (
            "Explain dose-response relationships in receptor signaling",
            QuerySafetyClass.GENERAL_RESEARCH,
        ),
        (
            "What are the biological effects of injection-site inflammation?",
            QuerySafetyClass.SYMPTOM_EDUCATION,
        ),
    ],
)
def test_allowed_research_queries_keep_the_boundary_visible(
    text: str, expected_class: QuerySafetyClass
) -> None:
    notice = classify_query(text)
    assert notice.query_class is expected_class
    assert notice.restricted is False
    assert notice.urgent is False
    assert RESEARCH_BOUNDARY in notice.message
    assert notice.allowed_scope


def test_symptom_education_is_not_presented_as_diagnosis_or_treatment() -> None:
    notice = classify_query("What treatment mechanisms are studied for knee pain?")

    assert notice.query_class is QuerySafetyClass.SYMPTOM_EDUCATION
    assert "does not allow the system to diagnose" in notice.message
    assert "tell individuals what treatment" in notice.message
