"""Local candidate review with append-only, hash-linked audit events.

Retrieved metadata and provider suggestions are untrusted input. Only an explicit
human review can produce an exportable curated bundle; this module never inserts
anything into a domain pack or live graph.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from causalbio.domain.enums import CausalStatus, CurationStatus, EvidenceGrade
from causalbio.domain.models import BiologicalEntity, CausalAssertion, EvidenceRecord
from causalbio.graph.repository import LocalKnowledgeGraph
from causalbio.sources.models import NormalizedLiteratureRecord, NormalizedProteinRecord

Text = Annotated[str, Field(min_length=3, max_length=2000)]
Record = Annotated[
    NormalizedLiteratureRecord | NormalizedProteinRecord, Field(discriminator="source")
]


class ReviewModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class CandidateProvenance(ReviewModel):
    record: Record
    retrieved_at: datetime
    source_excerpt: str | None = Field(default=None, min_length=1, max_length=500)
    excerpt_locator: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def aware_timestamp(self) -> CandidateProvenance:
        if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
            raise ValueError("Candidate provenance requires a timezone-aware retrieval time")
        if (self.source_excerpt is None) != (self.excerpt_locator is None):
            raise ValueError("A source excerpt requires its section or page locator")
        return self


class CandidateDraft(ReviewModel):
    id: UUID = Field(default_factory=uuid4)
    origin: Literal["manual", "structured_extraction", "llm_suggestion"]
    proposer: Text
    assertion: CausalAssertion
    entities: tuple[BiologicalEntity, ...]
    evidence: tuple[EvidenceRecord, ...]
    provenance: tuple[CandidateProvenance, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def untrusted_and_grounded(self) -> CandidateDraft:
        untrusted = {CurationStatus.SUGGESTED, CurationStatus.EXTRACTED}
        if self.assertion.review_status not in untrusted:
            raise ValueError("Candidate assertions cannot arrive trusted or reviewed")
        if any(record.curation_status not in untrusted for record in self.evidence):
            raise ValueError("Candidate evidence cannot arrive trusted or reviewed")
        if any(entity.curation_status not in untrusted for entity in self.entities):
            raise ValueError("Candidate entities cannot arrive trusted or reviewed")
        referenced = set(self.assertion.supporting_evidence_ids) | set(
            self.assertion.contradictory_evidence_ids
        )
        if set(self.assertion.supporting_evidence_ids) & set(
            self.assertion.contradictory_evidence_ids
        ):
            raise ValueError("Candidate support and counterevidence must be distinct records")
        if not self.assertion.supporting_evidence_ids or referenced != {
            record.id for record in self.evidence
        }:
            raise ValueError("Candidate evidence must exactly cover its assertion references")
        sources = {str(item.record.canonical_url): item for item in self.provenance}
        if len(sources) != len(self.provenance):
            raise ValueError("Candidate source provenance must be unique")
        if set(sources) != {str(record.study.source_url) for record in self.evidence}:
            raise ValueError("Every candidate evidence record requires matching source provenance")
        for evidence in self.evidence:
            source = sources[str(evidence.study.source_url)]
            namespace = "PMID" if source.record.source == "pubmed" else "UniProtKB"
            if not any(
                item.namespace == namespace and item.value == source.record.record_id
                for item in evidence.study.identifiers
            ):
                raise ValueError("Candidate evidence identifiers must match source provenance")
            if source.record.source == "pubmed" and " ".join(
                evidence.study.title.split()
            ) != " ".join(source.record.title.split()):
                raise ValueError("Candidate study title must preserve retrieved citation metadata")
            if (
                evidence.supporting_excerpt is not None
                and evidence.supporting_excerpt != source.source_excerpt
            ):
                raise ValueError("Candidate excerpts must preserve supplied source text")
            if (
                evidence.source_adapter != source.record.source
                or evidence.retrieved_at != source.retrieved_at.date()
            ):
                raise ValueError(
                    "Candidate evidence source and retrieval date must match provenance"
                )
        if self.assertion.retrieval_date != max(
            item.retrieved_at.date() for item in self.provenance
        ):
            raise ValueError("Assertion retrieval date must match its most recent candidate source")
        LocalKnowledgeGraph(
            self.entities, (self.assertion,), self.evidence, graph_id=self.id, version="candidate"
        )
        return self


class ReviewEvent(ReviewModel):
    candidate_id: UUID
    revision: int = Field(ge=1)
    action: Literal["submit", "edit", "accept", "reject", "uncertain"]
    actor: Text
    rationale: Text
    created_at: datetime
    draft: CandidateDraft
    previous_hash: str
    event_hash: str


class CuratedBundle(ReviewModel):
    assertion: CausalAssertion
    entities: tuple[BiologicalEntity, ...]
    evidence: tuple[EvidenceRecord, ...]
    provenance: tuple[CandidateProvenance, ...]
    review: ReviewEvent


def _canonical(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class CandidateReviewStore:
    """Append-only local curation log, with optimistic revision checks.

    Actor names are local attribution, not authenticated user identities. Database
    owners can remove SQLite triggers; the log is not a tamper-proof service.
    """

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                "CREATE TABLE IF NOT EXISTS candidate_events ("
                "candidate_id TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL,"
                "PRIMARY KEY(candidate_id, revision));"
                "CREATE TRIGGER IF NOT EXISTS candidate_events_no_update "
                "BEFORE UPDATE ON candidate_events BEGIN SELECT RAISE(ABORT, 'audit events are immutable'); END;"
                "CREATE TRIGGER IF NOT EXISTS candidate_events_no_delete "
                "BEFORE DELETE ON candidate_events BEGIN SELECT RAISE(ABORT, 'audit events are immutable'); END;"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)

    @staticmethod
    def _history(connection: sqlite3.Connection, candidate_id: UUID) -> tuple[ReviewEvent, ...]:
        rows = connection.execute(
            "SELECT payload FROM candidate_events WHERE candidate_id = ? ORDER BY revision",
            (str(candidate_id),),
        ).fetchall()
        events: list[ReviewEvent] = []
        previous_hash = ""
        for index, row in enumerate(rows, start=1):
            event = ReviewEvent.model_validate_json(row[0])
            payload = event.model_dump(mode="json", exclude={"event_hash"})
            digest = hashlib.sha256(_canonical(payload).encode()).hexdigest()
            if (
                event.candidate_id != candidate_id
                or event.draft.id != candidate_id
                or event.revision != index
                or event.previous_hash != previous_hash
                or event.event_hash != digest
            ):
                raise ValueError("Candidate audit history failed its integrity check")
            events.append(event)
            previous_hash = digest
        return tuple(events)

    def history(self, candidate_id: UUID) -> tuple[ReviewEvent, ...]:
        with self._connect() as connection:
            return self._history(connection, candidate_id)

    def submit(self, draft: CandidateDraft, *, actor: str, rationale: str) -> ReviewEvent:
        return self._append(draft.id, "submit", actor, rationale, expected_revision=0, draft=draft)

    def review(
        self,
        candidate_id: UUID,
        action: Literal["accept", "reject", "uncertain"],
        *,
        actor: str,
        rationale: str,
        expected_revision: int,
        human_review_confirmed: bool = False,
    ) -> ReviewEvent:
        if action == "accept" and human_review_confirmed is not True:
            raise ValueError(
                "Acceptance requires explicit human source-entailment and context review"
            )
        return self._append(
            candidate_id, action, actor, rationale, expected_revision=expected_revision
        )

    def edit(
        self,
        draft: CandidateDraft,
        *,
        actor: str,
        rationale: str,
        expected_revision: int,
    ) -> ReviewEvent:
        return self._append(
            draft.id, "edit", actor, rationale, expected_revision=expected_revision, draft=draft
        )

    def _append(
        self,
        candidate_id: UUID,
        action: Literal["submit", "edit", "accept", "reject", "uncertain"],
        actor: str,
        rationale: str,
        *,
        expected_revision: int,
        draft: CandidateDraft | None = None,
    ) -> ReviewEvent:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            history = self._history(connection, candidate_id)
            if len(history) != expected_revision:
                raise ValueError("Candidate revision changed; inspect history before retrying")
            if not history and action != "submit":
                raise KeyError(f"Unknown candidate: {candidate_id}")
            if history and action == "submit":
                raise ValueError("A candidate can only be submitted once")
            current = draft or history[-1].draft
            if current.id != candidate_id:
                raise ValueError("Candidate identity cannot change during review")
            # Revalidate even if a caller used Pydantic model_copy to bypass checks.
            current = CandidateDraft.model_validate(current.model_dump(mode="json"))
            if action == "uncertain":
                payload = current.model_dump(mode="json")
                payload["assertion"]["confidence_classification"] = EvidenceGrade.U.value
                payload["assertion"]["causal_status"] = CausalStatus.HYPOTHESIS_ONLY.value
                current = CandidateDraft.model_validate(payload)
            unsigned: dict[str, object] = {
                "candidate_id": str(candidate_id),
                "revision": len(history) + 1,
                "action": action,
                "actor": actor.strip(),
                "rationale": rationale.strip(),
                "created_at": datetime.now(UTC).isoformat(),
                "draft": current.model_dump(mode="json"),
                "previous_hash": history[-1].event_hash if history else "",
            }
            # Pydantic normalizes timestamps; hash its normalized serialization.
            event = ReviewEvent.model_validate({**unsigned, "event_hash": ""})
            digest = hashlib.sha256(
                _canonical(event.model_dump(mode="json", exclude={"event_hash"})).encode()
            ).hexdigest()
            event = event.model_copy(update={"event_hash": digest})
            connection.execute(
                "INSERT INTO candidate_events(candidate_id, revision, payload) VALUES (?, ?, ?)",
                (str(candidate_id), event.revision, event.model_dump_json()),
            )
            return event

    def accepted_bundle(self, candidate_id: UUID) -> CuratedBundle:
        history = self.history(candidate_id)
        if not history or history[-1].action != "accept":
            raise ValueError("Only a currently accepted candidate can be exported as curated")
        review = history[-1]
        draft = review.draft
        assertion = CausalAssertion.model_validate(
            {
                **draft.assertion.model_dump(),
                "review_status": CurationStatus.CURATED,
                "curator": review.actor,
                "extraction_method": "manual_curation",
            }
        )
        evidence = tuple(
            EvidenceRecord.model_validate(
                {
                    **record.model_dump(),
                    "curation_status": CurationStatus.CURATED,
                }
            )
            for record in draft.evidence
        )
        entities = tuple(
            BiologicalEntity.model_validate(
                {
                    **entity.model_dump(),
                    "curation_status": CurationStatus.CURATED,
                }
            )
            for entity in draft.entities
        )
        LocalKnowledgeGraph(
            entities, (assertion,), evidence, graph_id=candidate_id, version="reviewed-candidate"
        )
        return CuratedBundle(
            assertion=assertion,
            evidence=evidence,
            entities=entities,
            provenance=draft.provenance,
            review=review,
        )
