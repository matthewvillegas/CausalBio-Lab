"""Universal routing covers new topics without granting them curated provenance."""

from __future__ import annotations

import pytest
from causalbio.questions import EmptyQuestionError
from causalbio.research.models import ResearchMode
from causalbio.research.router import route_question
from pydantic import ValidationError


@pytest.mark.parametrize(
    ("text", "pack"),
    [
        ("How could memory persist after learning?", "memory"),
        ("What mechanisms contribute to knee pain after repeated jumping?", "knee-pain"),
    ],
)
def test_curated_routes_preserve_installed_pack_scope(text: str, pack: str) -> None:
    route = route_question(text)
    assert route.mode is ResearchMode.CURATED
    assert route.domain_pack == pack
    assert route.search_queries == ()


@pytest.mark.parametrize(
    "text",
    [
        "What mechanisms influence tendon recovery?",
        "How does cartilage repair work?",
        "How does muscle hypertrophy happen?",
        "How does skin wound healing work?",
        "How does acne inflammation develop?",
        "How does insulin sensitivity change?",
        "How does mitochondrial ATP production work?",
        "How does mechanotransduction affect cells?",
        "How does liver metabolism regulate blood glucose?",
        "How does immune signaling regulate tissue repair?",
    ],
)
def test_new_biological_questions_have_bounded_provisional_searches(text: str) -> None:
    route = route_question(text)
    assert route.mode in {ResearchMode.LIVE_RESEARCH, ResearchMode.EXPLANATORY}
    assert route.domain_pack is None
    assert 1 <= len(route.search_queries) <= 2
    assert all(2 <= len(query) <= 500 for query in route.search_queries)
    assert "provisional" in route.notice.casefold()
    assert not route.safety_notice.restricted


@pytest.mark.parametrize(
    "text", ["What is BDNF?", "What is COL1A1?", "Explain MTOR protein signaling"]
)
def test_named_entity_explanations_do_not_require_a_symptom(text: str) -> None:
    route = route_question(text)
    assert route.mode is ResearchMode.EXPLANATORY
    assert route.entities
    assert not route.clarifications


@pytest.mark.parametrize(
    "text",
    [
        "How does metformin affect cell metabolism?",
        "What mechanisms connect caffeine and sleep?",
        "What biological pathways involve Substance P?",
    ],
)
def test_interventions_are_allowed_as_research_objects(text: str) -> None:
    route = route_question(text)
    assert route.mode in {ResearchMode.LIVE_RESEARCH, ResearchMode.EXPLANATORY}
    assert route.question.context.candidate_intervention
    assert not route.safety_notice.restricted


@pytest.mark.parametrize(
    "text",
    ["retention", "How does drug X work?", "Could knee pain interfere with memory after jumping?"],
)
def test_ambiguous_topics_return_short_clarification_without_search(text: str) -> None:
    route = route_question(text)
    assert route.mode is ResearchMode.CLARIFICATION_REQUIRED
    assert 1 <= len(route.clarifications) <= 3
    assert not route.search_queries


@pytest.mark.parametrize(
    "text",
    [
        "How much metformin should I take?",
        "Where can I buy BPC-157?",
        "Give me a synthesis protocol for Substance P",
    ],
)
def test_operational_requests_offer_a_separate_safe_research_question(text: str) -> None:
    route = route_question(text)
    assert route.mode is ResearchMode.RESTRICTED_WITH_SAFE_ALTERNATIVE
    assert route.safety_notice.restricted
    assert not route.search_queries
    assert route.safe_research_question
    alternative = route_question(route.safe_research_question)
    assert alternative.mode in {ResearchMode.LIVE_RESEARCH, ResearchMode.EXPLANATORY}
    assert not alternative.safety_notice.restricted


def test_urgent_request_does_not_offer_an_automatic_research_detour() -> None:
    route = route_question("I have chest pain; how much metformin should I take?")
    assert route.safety_notice.urgent
    assert route.mode is ResearchMode.RESTRICTED_WITH_SAFE_ALTERNATIVE
    assert route.safe_research_question is None


def test_restricted_context_cannot_downgrade_an_urgent_question() -> None:
    route = route_question(
        "I have chest pain; how does metformin work?",
        context_updates={"candidate_intervention": "How much metformin should I take?"},
    )
    assert route.safety_notice.urgent
    assert route.mode is ResearchMode.RESTRICTED_WITH_SAFE_ALTERNATIVE
    assert route.safe_research_question is None


@pytest.mark.parametrize(
    "text", ["What is the stock price?", "Explain computer memory", "What is tomorrow's weather?"]
)
def test_nonbiological_keywords_do_not_trigger_biological_search(text: str) -> None:
    route = route_question(text)
    assert route.mode is ResearchMode.OUT_OF_DOMAIN
    assert not route.search_queries


@pytest.mark.parametrize("text", ["", "  ", "x"])
def test_empty_questions_are_input_errors(text: str) -> None:
    with pytest.raises(EmptyQuestionError):
        route_question(text)


def test_context_edits_are_validated_and_part_of_interpretation_identity() -> None:
    initial = route_question("How does tendon recovery work?")
    edited = route_question(
        "How does tendon recovery work?", context_updates={"duration": "three weeks"}
    )
    assert initial.question.id != edited.question.id
    assert edited.question.context.duration == "three weeks"
    with pytest.raises(ValidationError):
        route_question(
            "How does tendon recovery work?", context_updates={"unrecognized_field": "ignored?"}
        )
    with pytest.raises(ValidationError):
        route_question("How does tendon recovery work?", context_updates={"tissue": True})


def test_edited_context_cannot_bypass_operational_request_boundary() -> None:
    result = route_question(
        "How does tendon repair work?",
        context_updates={"candidate_intervention": "Where can I buy BPC-157?"},
    )
    assert result.mode is ResearchMode.RESTRICTED_WITH_SAFE_ALTERNATIVE
    assert result.search_queries == ()


@pytest.mark.parametrize(
    "text", ["How does caffeine affect memory?", "How does BDNF affect memory?"]
)
def test_named_entities_outside_pack_scope_are_provisional_research(text: str) -> None:
    result = route_question(text)
    assert result.mode in {ResearchMode.LIVE_RESEARCH, ResearchMode.EXPLANATORY}
    assert result.domain_pack is None


def test_sleep_consolidation_is_not_mistaken_for_the_curated_memory_pack() -> None:
    result = route_question("What biological systems are involved in sleep consolidation?")
    assert result.mode in {ResearchMode.LIVE_RESEARCH, ResearchMode.EXPLANATORY}
    assert result.domain_pack is None


def test_explicit_memory_consolidation_remains_in_the_curated_memory_pack() -> None:
    result = route_question("How does sleep affect memory consolidation?")
    assert result.mode is ResearchMode.CURATED
    assert result.domain_pack == "memory"
