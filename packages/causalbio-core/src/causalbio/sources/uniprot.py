"""Bounded UniProtKB JSON adapter with normalized protein metadata."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from causalbio.sources.base import (
    CachedSourceAdapter,
    optional_text,
    required_list,
    required_mapping,
    required_text,
)
from causalbio.sources.cache import FileSystemSourceCache
from causalbio.sources.errors import SourceResponseError
from causalbio.sources.models import (
    CacheStatus,
    NormalizedIdentifier,
    NormalizedProteinRecord,
    ProteinFunctionAnnotation,
    ProteinFunctionEvidence,
    SourceSearchRequest,
    UniProtSearchResult,
)
from causalbio.sources.policy import RequestPolicy, SourcePacer
from causalbio.sources.transport import HTTPTransport

UNIPROT_SEARCH_URL = "https://rest.uniprot.org/uniprotkb/search"
UNIPROT_FIELDS = (
    "accession,id,protein_name,gene_names,organism_name,organism_id,reviewed,length,cc_function"
)


class UniProtAdapter(CachedSourceAdapter[UniProtSearchResult]):
    """Retrieve bounded UniProtKB records without inventing missing annotations."""

    name = "uniprot"
    adapter_version = "uniprotkb-json-search-3"
    source_endpoint = UNIPROT_SEARCH_URL

    def __init__(
        self,
        *,
        transport: HTTPTransport | None = None,
        cache: FileSystemSourceCache | None = None,
        timeout_seconds: float = 10.0,
        max_response_bytes: int = 5_000_000,
        request_policy: RequestPolicy | None = None,
        pacer: SourcePacer | None = None,
        max_search_seconds: float = 30.0,
    ) -> None:
        super().__init__(
            transport=transport,
            cache=cache,
            timeout_seconds=timeout_seconds,
            max_response_bytes=max_response_bytes,
            request_policy=request_policy,
            pacer=pacer,
            max_search_seconds=max_search_seconds,
        )

    def _fetch(self, request: SourceSearchRequest) -> UniProtSearchResult:
        payload, response = self._get_json(
            UNIPROT_SEARCH_URL,
            params={
                "query": request.query,
                "format": "json",
                "fields": UNIPROT_FIELDS,
                "size": str(request.limit),
            },
            headers={"accept": "application/json", "user-agent": "CausalBio-Lab/1.0.0"},
        )
        raw_results = required_list(payload.get("results"), "results")
        if len(raw_results) > request.limit:
            raise SourceResponseError("UniProt records exceed the requested limit")
        records = tuple(
            self._normalize_record(required_mapping(item, "results item")) for item in raw_results
        )
        total_header = response.header("x-total-results")
        total_count: int | None = None
        if total_header is not None:
            try:
                total_count = int(total_header)
            except ValueError as exc:
                raise SourceResponseError(
                    "UniProt x-total-results must be a non-negative integer"
                ) from exc
            if total_count < 0:
                raise SourceResponseError("UniProt x-total-results must be a non-negative integer")
        return UniProtSearchResult(
            query=request.query,
            records=records,
            total_count=total_count,
            retrieved_at=self.cache.now(),
            cache_status=CacheStatus.FETCHED,
            source_endpoint=UNIPROT_SEARCH_URL,
        )

    @classmethod
    def _normalize_record(cls, item: Mapping[str, Any]) -> NormalizedProteinRecord:
        accession = required_text(item.get("primaryAccession"), "primaryAccession")
        entry_name = optional_text(item.get("uniProtkbId"))
        protein_name = cls._protein_name(item.get("proteinDescription"))
        organism = required_mapping(item.get("organism"), "organism")
        organism_name = required_text(organism.get("scientificName"), "organism.scientificName")
        taxon_value = organism.get("taxonId")
        if isinstance(taxon_value, bool) or not isinstance(taxon_value, int) or taxon_value <= 0:
            raise SourceResponseError("UniProt organism.taxonId must be a positive integer")

        gene_names: list[str] = []
        for gene in required_list(item.get("genes", []), "genes"):
            gene_mapping = required_mapping(gene, "gene")
            primary = gene_mapping.get("geneName")
            if primary is not None:
                value = optional_text(required_mapping(primary, "geneName").get("value"))
                if value:
                    gene_names.append(value)
            for synonym in required_list(gene_mapping.get("synonyms", []), "gene synonyms"):
                value = optional_text(required_mapping(synonym, "gene synonym").get("value"))
                if value:
                    gene_names.append(value)

        functions: list[str] = []
        function_annotations: list[ProteinFunctionAnnotation] = []
        for comment in required_list(item.get("comments", []), "comments"):
            comment_mapping = required_mapping(comment, "comment")
            if optional_text(comment_mapping.get("commentType")) != "FUNCTION":
                continue
            raw_molecule = comment_mapping.get("molecule")
            molecule = (
                required_text(raw_molecule, "function molecule")
                if raw_molecule is not None
                else None
            )
            for text in required_list(comment_mapping.get("texts", []), "function texts"):
                text_mapping = required_mapping(text, "function text")
                value = optional_text(text_mapping.get("value"))
                if value:
                    functions.append(value)
                    evidences = []
                    for raw_evidence in required_list(
                        text_mapping.get("evidences", []), "function evidences"
                    ):
                        evidence = required_mapping(raw_evidence, "function evidence")
                        evidences.append(
                            ProteinFunctionEvidence(
                                evidence_code=required_text(
                                    evidence.get("evidenceCode"), "function evidence code"
                                ),
                                source=optional_text(evidence.get("source")),
                                identifier=optional_text(evidence.get("id")),
                            )
                        )
                    function_annotations.append(
                        ProteinFunctionAnnotation(
                            text=value, molecule=molecule, evidences=tuple(evidences)
                        )
                    )

        sequence_length: int | None = None
        sequence = item.get("sequence")
        if sequence is not None:
            length = required_mapping(sequence, "sequence").get("length")
            if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
                raise SourceResponseError("UniProt sequence.length must be a positive integer")
            sequence_length = length

        identifiers = [NormalizedIdentifier(namespace="UniProtKB", value=accession)]
        if entry_name:
            identifiers.append(
                NormalizedIdentifier(namespace="UniProtKB entry name", value=entry_name)
            )
        entry_type = required_text(item.get("entryType"), "entryType")
        review_states = {
            "UniProtKB reviewed (Swiss-Prot)": True,
            "UniProtKB unreviewed (TrEMBL)": False,
        }
        if entry_type not in review_states:
            raise SourceResponseError("UniProt entryType has an unknown review status")
        return NormalizedProteinRecord(
            record_id=accession,
            entry_name=entry_name,
            protein_name=protein_name,
            gene_names=tuple(dict.fromkeys(gene_names)),
            organism_name=organism_name,
            organism_taxon_id=taxon_value,
            reviewed=review_states[entry_type],
            sequence_length=sequence_length,
            functions=tuple(dict.fromkeys(functions)),
            function_annotations=tuple(function_annotations),
            identifiers=tuple(identifiers),
            canonical_url=f"https://www.uniprot.org/uniprotkb/{accession}/entry",
        )

    @staticmethod
    def _protein_name(value: object) -> str:
        description = required_mapping(value, "proteinDescription")
        recommended = description.get("recommendedName")
        if recommended is not None:
            full_name = required_mapping(recommended, "recommendedName").get("fullName")
            if full_name is not None:
                candidate = optional_text(required_mapping(full_name, "fullName").get("value"))
                if candidate:
                    return candidate
        for submitted in required_list(description.get("submissionNames", []), "submissionNames"):
            full_name = required_mapping(submitted, "submissionName").get("fullName")
            if full_name is None:
                continue
            candidate = optional_text(required_mapping(full_name, "fullName").get("value"))
            if candidate:
                return candidate
        raise SourceResponseError("UniProt record has no normalized protein name")

    def _parse_cached(self, payload: Mapping[str, object]) -> UniProtSearchResult:
        return UniProtSearchResult.model_validate(payload)


__all__ = ["UNIPROT_FIELDS", "UNIPROT_SEARCH_URL", "UniProtAdapter"]
