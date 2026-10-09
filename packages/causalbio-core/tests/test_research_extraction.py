"""Presentation selection must preserve evidence and avoid inventing causal relations."""

from datetime import UTC, datetime
from uuid import uuid4

from causalbio.research.extraction import (
    build_mechanisms,
    matches_overview_topic,
    overview_claims,
    research_modifiers,
    source_claims,
)
from causalbio.research.models import ResearchEvidence


def record(abstract: str) -> ResearchEvidence:
    return ResearchEvidence(
        id=uuid4(),
        source="test_fixture",
        source_record_id="synthetic",
        title="Synthetic extraction fixture, not biological evidence",
        source_url="https://example.org/synthetic",
        abstract=abstract,
        retrieved_at=datetime(2026, 10, 2, tzinfo=UTC),
        cache_status="fetched",
    )


def test_mechanistic_sentence_precedes_procedural_sentence_without_rewriting() -> None:
    statement = "Mechanical loading regulates collagen remodeling through cellular signaling in this synthetic fixture."
    evidence = record(
        "This technical note describes a surgical technique for repair of injured tissue. "
        + statement
    )
    groups, _ = build_mechanisms((evidence,), topic="tendon collagen remodeling")
    assert groups
    assert all(group.claims[0].text == statement for group in groups)
    assert all(group.claims[0].text in (evidence.abstract or "") for group in groups)


def test_limiting_passage_is_not_automatically_a_contradiction() -> None:
    text = "However, the role of collagen remodeling in this synthetic system remains unclear."
    groups, complications = build_mechanisms((record(text),))
    assert len(complications) == 1
    assert complications[0].text == text
    assert complications[0].relation == "SUPPORTED_BY"
    assert all(claim.relation == "SUPPORTED_BY" for group in groups for claim in group.claims)


def test_missing_abstract_cannot_become_a_scientific_claim() -> None:
    evidence = record("Placeholder").model_copy(update={"abstract": None})
    assert source_claims(evidence) == ()
    assert build_mechanisms((evidence,)) == ((), ())


def test_section_labels_can_be_removed_without_altering_original_passage() -> None:
    statement = (
        "Cellular signaling regulates matrix remodeling in this synthetic tissue repair fixture."
    )
    evidence = record("Abstract Background " + statement)
    claims = source_claims(evidence)
    assert claims[0].text == statement
    assert claims[0].source_passage == statement


def test_operational_passages_are_not_promoted_as_answers_or_modifiers() -> None:
    evidence = record(
        "Inject the compound at a dose of 20 mg for this synthetic example. "
        "Mechanical loading regulates matrix remodeling in the synthetic fixture described here."
    )
    claims = source_claims(evidence)
    assert len(claims) == 1
    assert "dose" not in claims[0].text
    assert research_modifiers((evidence,), "loading") == claims


def test_short_evidence_does_not_invent_three_mechanism_families() -> None:
    evidence = record("Neuronal plasticity was observed in this explicitly synthetic test fixture.")
    groups, _ = build_mechanisms((evidence,))
    assert len(groups) == 1
    assert groups[0].model_eligibility == "GRAPH_ONLY"
    assert "Not resolved" in groups[0].evidence_dimensions["Organism context"]


def test_supplement_quantity_is_filtered_even_without_the_word_dose() -> None:
    evidence = record(
        "In this synthetic trial, creatine (2-10 g/day for 8-16 weeks) improved a measured outcome."
    )
    assert source_claims(evidence) == ()


def test_trailing_database_reference_list_keeps_verbatim_statement_and_source() -> None:
    statement = "Synthetic protein signaling participates in several cellular regulatory processes"
    evidence = record(statement + " (PubMed:12345678, PubMed:23456789).")
    claims = source_claims(evidence)
    assert claims[0].text == statement
    assert "PubMed:12345678" in (evidence.abstract or "")


def test_review_methods_do_not_become_direct_biological_answers() -> None:
    evidence = record(
        "Search terms included acne, inflammation and receptor signaling for this synthetic review. Acne inflammation involves cellular signaling in this explicitly synthetic fixture."
    )
    claims = overview_claims(evidence)
    assert len(claims) == 1
    assert claims[0].text.startswith("Acne inflammation")


def test_shared_entity_does_not_answer_an_unrelated_process_question() -> None:
    claim = source_claims(
        record(
            "Collagen binding activates platelets in this explicitly synthetic extraction fixture."
        )
    )[0]
    assert not matches_overview_topic(claim, "collagen synthesis")
    assert matches_overview_topic(claim, "collagen binding")


def test_recovery_aliases_retain_relevant_repair_excerpts() -> None:
    claim = source_claims(
        record("Tendon repair involves matrix remodeling in this explicitly synthetic fixture.")
    )[0]
    assert matches_overview_topic(claim, "tendon recovery")


def test_compound_query_does_not_promote_its_namesake_enzyme_alone() -> None:
    claim = source_claims(
        record("Creatine kinase is measured in muscle injury in this synthetic fixture.")
    )[0]
    assert not matches_overview_topic(claim, "creatine muscle energetics")
