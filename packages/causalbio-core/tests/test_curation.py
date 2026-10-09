"""Candidate review preserves provenance and never writes to a trusted pack."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from causalbio.domain.enums import CausalStatus, CurationStatus, EvidenceGrade
from causalbio.evidence.curation import CandidateDraft, CandidateReviewStore
from causalbio.evidence.providers import ExtractionRequest, GeneratedCandidate, extract_candidate
from factories import make_assertion, make_entity, make_evidence, uid


def candidate_payload() -> dict[str, Any]:
    """Deliberately synthetic content; test PMID identity is not a scientific claim."""
    entities = tuple(
        make_entity(index, f"Fixture {index}", curation_status=CurationStatus.SUGGESTED)
        for index in (1, 2)
    )
    evidence = make_evidence(1, curation_status=CurationStatus.SUGGESTED).model_dump(mode="json")
    evidence["study"]["identifiers"] = [{"namespace": "PMID", "value": "123"}]
    evidence["study"]["source_url"] = "https://pubmed.ncbi.nlm.nih.gov/123/"
    evidence["source_adapter"] = "pubmed"
    evidence["supporting_excerpt"] = "Synthetic fixture excerpt; no biological evidence."
    assertion = make_assertion(
        1,
        entities[0].id,
        entities[1].id,
        supporting=(uid(10_001),),
        review_status=CurationStatus.SUGGESTED,
    )
    return {
        "id": str(uid(50_000)),
        "origin": "manual",
        "proposer": "Test curator",
        "assertion": assertion.model_dump(mode="json"),
        "entities": [entity.model_dump(mode="json") for entity in entities],
        "evidence": [evidence],
        "provenance": [
            {
                "record": {
                    "source": "pubmed",
                    "record_id": "123",
                    "title": evidence["study"]["title"],
                    "identifiers": [{"namespace": "PMID", "value": "123"}],
                    "canonical_url": "https://pubmed.ncbi.nlm.nih.gov/123/",
                },
                "retrieved_at": datetime(2025, 1, 1, tzinfo=UTC).isoformat(),
                "source_excerpt": evidence["supporting_excerpt"],
                "excerpt_locator": "Synthetic test fixture",
            }
        ],
    }


def test_submit_accept_export_and_edit_revoke_current_acceptance(tmp_path: Path) -> None:
    draft = CandidateDraft.model_validate(candidate_payload())
    store = CandidateReviewStore(tmp_path / "review.sqlite")
    first = store.submit(draft, actor="Curator one", rationale="Inspect source and context")
    assert first.revision == 1
    assert first.previous_hash == ""
    with pytest.raises(ValueError, match="accepted"):
        store.accepted_bundle(draft.id)
    with pytest.raises(ValueError, match="human"):
        store.review(
            draft.id,
            "accept",
            actor="Curator two",
            rationale="Checked original source",
            expected_revision=1,
        )
    accepted = store.review(
        draft.id,
        "accept",
        actor="Curator two",
        rationale="Checked original source",
        expected_revision=1,
        human_review_confirmed=True,
    )
    bundle = store.accepted_bundle(draft.id)
    assert bundle.assertion.review_status is CurationStatus.CURATED
    assert bundle.assertion.curator == "Curator two"
    assert all(record.curation_status is CurationStatus.CURATED for record in bundle.evidence)
    assert all(entity.curation_status is CurationStatus.CURATED for entity in bundle.entities)
    assert accepted.previous_hash == first.event_hash
    assert draft.assertion.review_status is CurationStatus.SUGGESTED
    assert bundle.review.draft == draft
    # Editing an accepted draft revokes export until a fresh human acceptance.
    changed = candidate_payload()
    changed["assertion"]["interpretation"] = "Revised contextual interpretation"
    store.edit(
        CandidateDraft.model_validate(changed),
        actor="Curator one",
        rationale="Corrected interpretation",
        expected_revision=2,
    )
    with pytest.raises(ValueError, match="accepted"):
        store.accepted_bundle(draft.id)
    assert [event.action for event in CandidateReviewStore(store.path).history(draft.id)] == [
        "submit",
        "accept",
        "edit",
    ]


def test_uncertain_downgrades_claim_and_rejection_remains_auditable(tmp_path: Path) -> None:
    draft = CandidateDraft.model_validate(candidate_payload())
    store = CandidateReviewStore(tmp_path / "review.sqlite")
    store.submit(draft, actor="Curator one", rationale="Source needs review")
    event = store.review(
        draft.id,
        "uncertain",
        actor="Curator one",
        rationale="Causal entailment is missing",
        expected_revision=1,
    )
    assert event.draft.assertion.confidence_classification is EvidenceGrade.U
    assert event.draft.assertion.causal_status is CausalStatus.HYPOTHESIS_ONLY
    assert event.draft.evidence[0].evidence_grade is EvidenceGrade.A
    assert event.draft.assertion.review_status is CurationStatus.SUGGESTED
    store.review(
        draft.id,
        "reject",
        actor="Curator one",
        rationale="Primary study does not support this relation",
        expected_revision=2,
    )
    assert len(store.history(draft.id)) == 3
    with pytest.raises(ValueError, match="accepted"):
        store.accepted_bundle(draft.id)


def test_audit_events_are_immutable_and_revision_conflicts_do_not_append(tmp_path: Path) -> None:
    draft = CandidateDraft.model_validate(candidate_payload())
    store = CandidateReviewStore(tmp_path / "review.sqlite")
    store.submit(draft, actor="Curator one", rationale="Submitted for review")
    with pytest.raises(ValueError, match="revision changed"):
        store.review(
            draft.id,
            "reject",
            actor="Curator one",
            rationale="Stale review form",
            expected_revision=0,
        )
    with sqlite3.connect(store.path) as connection:
        for operation in (
            "DELETE FROM candidate_events",
            "UPDATE candidate_events SET payload = '{}'",
        ):
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute(operation)
    assert len(store.history(draft.id)) == 1


def test_owner_tampering_is_detected_but_not_claimed_impossible(tmp_path: Path) -> None:
    draft = CandidateDraft.model_validate(candidate_payload())
    store = CandidateReviewStore(tmp_path / "review.sqlite")
    store.submit(draft, actor="Curator one", rationale="Submitted for review")
    with sqlite3.connect(store.path) as connection:
        connection.execute("DROP TRIGGER candidate_events_no_update")
        original = json.loads(
            connection.execute("SELECT payload FROM candidate_events").fetchone()[0]
        )
        original["rationale"] = "Changed after review"
        connection.execute("UPDATE candidate_events SET payload = ?", (json.dumps(original),))
    with pytest.raises(ValueError, match="integrity"):
        store.history(draft.id)


@pytest.mark.parametrize(
    "mutation",
    [
        "trusted_assertion",
        "trusted_evidence",
        "trusted_entity",
        "source_id",
        "date",
        "title",
        "quote",
        "missing_source",
        "missing_entity",
        "counterevidence_overlap",
        "duplicate_evidence",
    ],
)
def test_candidates_fail_closed_for_invalid_provenance_or_trust(mutation: str) -> None:
    data = candidate_payload()
    if mutation == "trusted_assertion":
        data["assertion"]["review_status"] = "CURATED"
    elif mutation == "trusted_evidence":
        data["evidence"][0]["curation_status"] = "CURATED"
    elif mutation == "trusted_entity":
        data["entities"][0]["curation_status"] = "CURATED"
    elif mutation == "source_id":
        data["evidence"][0]["study"]["identifiers"][0]["value"] = "456"
    elif mutation == "date":
        data["assertion"]["retrieval_date"] = "2025-01-02"
    elif mutation == "title":
        data["evidence"][0]["study"]["title"] = "Invented study title"
    elif mutation == "quote":
        data["evidence"][0]["supporting_excerpt"] = "Invented supporting quotation"
    elif mutation == "missing_source":
        data["provenance"] = []
    elif mutation == "missing_entity":
        data["entities"].pop()
    elif mutation == "counterevidence_overlap":
        data["assertion"]["contradictory_evidence_ids"] = data["assertion"][
            "supporting_evidence_ids"
        ]
    else:
        data["evidence"] *= 2
    with pytest.raises(ValueError):
        CandidateDraft.model_validate(data)


def test_store_revalidates_model_copy_and_requires_meaningful_actor(tmp_path: Path) -> None:
    draft = CandidateDraft.model_validate(candidate_payload())
    store = CandidateReviewStore(tmp_path / "review.sqlite")
    trusted = draft.assertion.model_copy(update={"review_status": CurationStatus.CURATED})
    with pytest.raises(ValueError, match="cannot arrive trusted"):
        store.submit(
            draft.model_copy(update={"assertion": trusted}),
            actor="Curator one",
            rationale="Unchecked mutation",
        )
    with pytest.raises(ValueError):
        store.submit(draft, actor="   ", rationale="No attributable reviewer")
    assert store.history(draft.id) == ()


class FixtureProvider:
    name = "Fixture provider"

    def __init__(self, output: dict[str, Any]) -> None:
        self.output = output

    def extract(self, request: ExtractionRequest) -> str:
        assert request.sources
        return json.dumps(self.output)


def generated_output() -> dict[str, Any]:
    data = candidate_payload()
    data.update(origin="llm_suggestion", proposer="Fixture provider")
    return {"generated": True, "provider": "Fixture provider", "draft": data}


def test_optional_provider_output_is_generated_grounded_and_untrusted(tmp_path: Path) -> None:
    draft = CandidateDraft.model_validate(candidate_payload())
    request = ExtractionRequest(
        research_question="Synthetic research question", sources=draft.provenance
    )
    result = extract_candidate(FixtureProvider(generated_output()), request)
    assert isinstance(result, GeneratedCandidate)
    assert result.generated is True
    assert result.draft.assertion.review_status is CurationStatus.SUGGESTED
    # Extraction is pure at this boundary: even the review store has no entry.
    assert CandidateReviewStore(tmp_path / "review.sqlite").history(result.draft.id) == ()


@pytest.mark.parametrize("mutation", ["provider", "origin", "generated", "source", "trusted"])
def test_generated_provider_cannot_forge_sources_or_trust(mutation: str) -> None:
    draft = CandidateDraft.model_validate(candidate_payload())
    request = ExtractionRequest(
        research_question="Synthetic research question", sources=draft.provenance
    )
    output = generated_output()
    if mutation == "source":
        output["draft"]["provenance"][0]["record"]["authors"] = ["Invented author"]
    elif mutation == "trusted":
        output["draft"]["assertion"]["review_status"] = "CURATED"
    elif mutation == "origin":
        output["draft"]["origin"] = "manual"
    elif mutation == "generated":
        output["generated"] = False
    else:
        output["provider"] = "Different provider"
    with pytest.raises(ValueError):
        extract_candidate(FixtureProvider(output), request)
