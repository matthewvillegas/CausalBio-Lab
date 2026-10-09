"""Typed normalized records shared by bounded scientific source adapters."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Generic, Literal, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class SourceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CacheStatus(StrEnum):
    FETCHED = "fetched"
    FRESH = "fresh_cache"
    STALE = "stale_cache"


class SourceSearchRequest(SourceModel):
    query: str = Field(min_length=2, max_length=500)
    limit: int = Field(default=10, ge=1, le=50)
    refresh: bool = False
    allow_stale: bool = True

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("A source query needs at least two non-whitespace characters")
        return normalized


class NormalizedIdentifier(SourceModel):
    namespace: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=300)


class NormalizedLiteratureRecord(SourceModel):
    source: Literal["pubmed"] = "pubmed"
    record_type: Literal["literature"] = "literature"
    record_id: str = Field(pattern=r"^[1-9][0-9]{0,11}$")
    title: str = Field(min_length=1, max_length=2000)
    authors: tuple[str, ...] = ()
    journal: str | None = None
    publication_date: str | None = None
    publication_types: tuple[str, ...] = ()
    identifiers: tuple[NormalizedIdentifier, ...]
    canonical_url: HttpUrl

    @model_validator(mode="after")
    def validate_provenance(self) -> NormalizedLiteratureRecord:
        if str(self.canonical_url) != f"https://pubmed.ncbi.nlm.nih.gov/{self.record_id}/":
            raise ValueError("PubMed canonical URL must match the record PMID")
        if not any(
            item.namespace == "PMID" and item.value == self.record_id for item in self.identifiers
        ):
            raise ValueError("PubMed records require their matching PMID identifier")
        return self


class ProteinFunctionEvidence(SourceModel):
    evidence_code: str = Field(min_length=1, max_length=100)
    source: str | None = Field(default=None, min_length=1, max_length=100)
    identifier: str | None = Field(default=None, min_length=1, max_length=300)


class ProteinFunctionAnnotation(SourceModel):
    """A source function statement scoped to the molecule named by UniProt."""

    text: str = Field(min_length=1, max_length=50_000)
    molecule: str | None = Field(default=None, min_length=1, max_length=1000)
    evidences: tuple[ProteinFunctionEvidence, ...] = ()


class NormalizedProteinRecord(SourceModel):
    source: Literal["uniprot"] = "uniprot"
    record_type: Literal["protein"] = "protein"
    record_id: str = Field(
        pattern=r"^(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})$"
    )
    entry_name: str | None = None
    protein_name: str = Field(min_length=1, max_length=1000)
    gene_names: tuple[str, ...] = ()
    organism_name: str = Field(min_length=1, max_length=300)
    organism_taxon_id: int = Field(gt=0)
    reviewed: bool
    sequence_length: int | None = Field(default=None, gt=0)
    functions: tuple[str, ...] = ()
    function_annotations: tuple[ProteinFunctionAnnotation, ...] = ()
    identifiers: tuple[NormalizedIdentifier, ...]
    canonical_url: HttpUrl

    @model_validator(mode="after")
    def validate_provenance(self) -> NormalizedProteinRecord:
        if str(self.canonical_url) != f"https://www.uniprot.org/uniprotkb/{self.record_id}/entry":
            raise ValueError("UniProt canonical URL must match the accession")
        if not any(
            item.namespace == "UniProtKB" and item.value == self.record_id
            for item in self.identifiers
        ):
            raise ValueError("UniProt records require their matching accession identifier")
        return self


class SourceSearchResultBase(SourceModel):
    query: str
    total_count: int | None = Field(default=None, ge=0)
    retrieved_at: datetime
    cache_status: CacheStatus
    source_endpoint: HttpUrl
    warnings: tuple[str, ...] = ()

    def record_ids(self) -> tuple[str, ...]:
        raise NotImplementedError

    @model_validator(mode="after")
    def retrieved_at_is_timezone_aware(self) -> SourceSearchResultBase:
        if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
            raise ValueError("Source retrieval timestamps must be timezone-aware")
        return self


class PubMedSearchResult(SourceSearchResultBase):
    source: Literal["pubmed"] = "pubmed"
    records: tuple[NormalizedLiteratureRecord, ...]

    def record_ids(self) -> tuple[str, ...]:
        return tuple(record.record_id for record in self.records)


class UniProtSearchResult(SourceSearchResultBase):
    source: Literal["uniprot"] = "uniprot"
    records: tuple[NormalizedProteinRecord, ...]

    def record_ids(self) -> tuple[str, ...]:
        return tuple(record.record_id for record in self.records)


class NormalizedResearchArticle(SourceModel):
    """Literature metadata plus source-supplied abstract; no inferred biological context."""

    source: Literal["europe_pmc"] = "europe_pmc"
    record_id: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,11}:[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")
    record_source: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,11}$")
    title: str = Field(min_length=1, max_length=2000)
    authors: tuple[str, ...] = ()
    publication_year: int | None = Field(default=None, ge=1600, le=2200)
    journal: str | None = None
    doi: str | None = Field(default=None, pattern=r"^10\.[0-9]{4,9}/\S{1,190}$")
    pmid: str | None = Field(default=None, pattern=r"^[1-9][0-9]{0,11}$")
    pmcid: str | None = Field(default=None, pattern=r"^PMC[1-9][0-9]{0,11}$")
    abstract: str | None = Field(default=None, min_length=1, max_length=50_000)
    publication_types: tuple[str, ...] = ()
    license: str | None = Field(default=None, max_length=300)
    identifiers: tuple[NormalizedIdentifier, ...]
    canonical_url: HttpUrl

    @model_validator(mode="after")
    def validate_provenance(self) -> NormalizedResearchArticle:
        origin, identifier = self.record_id.split(":", 1)
        if origin != self.record_source:
            raise ValueError("Europe PMC record identity must match its source namespace")
        if str(self.canonical_url) != f"https://europepmc.org/article/{origin}/{identifier}":
            raise ValueError("Europe PMC URL must match its source and record identifier")
        if origin == "MED" and self.pmid != identifier:
            raise ValueError("MED record identity must match its PMID")
        if origin == "PMC" and self.pmcid != identifier:
            raise ValueError("PMC record identity must match its PMCID")
        expected = {(origin, identifier)}
        expected.update(
            (namespace, value)
            for namespace, value in (("PMID", self.pmid), ("PMCID", self.pmcid), ("DOI", self.doi))
            if value
        )
        if not expected <= {(item.namespace, item.value) for item in self.identifiers}:
            raise ValueError("Europe PMC normalized identifiers must preserve source identity")
        return self


class EuropePMCSearchResult(SourceSearchResultBase):
    source: Literal["europe_pmc"] = "europe_pmc"
    records: tuple[NormalizedResearchArticle, ...]

    def record_ids(self) -> tuple[str, ...]:
        return tuple(record.record_id for record in self.records)


ResultT_co = TypeVar("ResultT_co", bound=SourceSearchResultBase, covariant=True)


@runtime_checkable
class SourceAdapter(Protocol, Generic[ResultT_co]):
    """Common typed interface for a bounded normalized source adapter."""

    name: str

    def search(self, request: SourceSearchRequest) -> ResultT_co:
        """Return validated source records or raise an explicit source error."""


__all__ = [
    "CacheStatus",
    "EuropePMCSearchResult",
    "NormalizedIdentifier",
    "NormalizedLiteratureRecord",
    "NormalizedProteinRecord",
    "NormalizedResearchArticle",
    "ProteinFunctionAnnotation",
    "ProteinFunctionEvidence",
    "PubMedSearchResult",
    "SourceAdapter",
    "SourceSearchRequest",
    "SourceSearchResultBase",
    "UniProtSearchResult",
]
