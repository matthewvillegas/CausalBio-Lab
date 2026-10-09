"""Optional candidate extraction boundary; no provider or model is enabled by default.

Source content is data, never an instruction authority. This boundary checks schema,
source identity, and trust state; it cannot establish that a source entails a claim.
Every output still requires human review through CandidateReviewStore.
"""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import Field

from causalbio.evidence.curation import CandidateDraft, CandidateProvenance, ReviewModel, Text


class ExtractionRequest(ReviewModel):
    research_question: Text
    sources: tuple[CandidateProvenance, ...] = Field(min_length=1, max_length=12)


class GeneratedCandidate(ReviewModel):
    generated: Literal[True]
    provider: Text
    draft: CandidateDraft


class CandidateExtractionProvider(Protocol):
    """A future model integration returns JSON and receives only explicit sources."""

    name: str

    def extract(self, request: ExtractionRequest) -> str:
        """Return GeneratedCandidate JSON, never mutate a graph or review store."""


def extract_candidate(
    provider: CandidateExtractionProvider, request: ExtractionRequest
) -> GeneratedCandidate:
    """Validate a generated suggestion without persisting or promoting it.

    Citation membership is necessary but not an entailment check. Metadata alone
    rarely establishes a causal relation; the curator must inspect primary content.
    """

    request = ExtractionRequest.model_validate(request.model_dump(mode="json"))
    response = provider.extract(request)
    if not isinstance(response, str) or len(response.encode("utf-8")) > 500_000:
        raise ValueError("Provider output must be bounded JSON text")
    generated = GeneratedCandidate.model_validate_json(response)
    if generated.provider != provider.name or generated.draft.proposer != provider.name:
        raise ValueError("Generated candidate must preserve provider attribution")
    if generated.draft.origin != "llm_suggestion":
        raise ValueError("Generated candidate must retain its generated origin")
    supplied = {source.model_dump_json() for source in request.sources}
    if any(source.model_dump_json() not in supplied for source in generated.draft.provenance):
        raise ValueError("Generated candidate must cite unchanged sources supplied in its request")
    return generated
