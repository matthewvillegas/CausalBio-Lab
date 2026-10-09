"""Bounded PubMed ESearch/ESummary adapter with normalized literature metadata."""

from __future__ import annotations

import re
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
    NormalizedLiteratureRecord,
    PubMedSearchResult,
    SourceSearchRequest,
)
from causalbio.sources.policy import RequestPolicy, SourcePacer
from causalbio.sources.transport import HTTPTransport

PUBMED_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


class PubMedAdapter(CachedSourceAdapter[PubMedSearchResult]):
    """Retrieve bounded PubMed search results without inferring absent metadata."""

    name = "pubmed"
    adapter_version = "pubmed-esearch-esummary-2"
    source_endpoint = PUBMED_ESEARCH_URL

    def __init__(
        self,
        *,
        transport: HTTPTransport | None = None,
        cache: FileSystemSourceCache | None = None,
        timeout_seconds: float = 10.0,
        max_response_bytes: int = 5_000_000,
        tool: str = "causalbio_lab",
        email: str | None = None,
        api_key: str | None = None,
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
        self.tool = required_text(tool, "tool")
        self.email = optional_text(email)
        self.api_key = optional_text(api_key)

    def _fetch(self, request: SourceSearchRequest) -> PubMedSearchResult:
        common = {"db": "pubmed", "retmode": "json", "tool": self.tool}
        if self.email:
            common["email"] = self.email
        if self.api_key:
            common["api_key"] = self.api_key
        search_payload, _ = self._get_json(
            PUBMED_ESEARCH_URL,
            params={
                **common,
                "term": request.query,
                "retmax": str(request.limit),
                "sort": "relevance",
            },
            headers={"accept": "application/json", "user-agent": "CausalBio-Lab/1.0.0"},
        )
        search_result = required_mapping(search_payload.get("esearchresult"), "esearchresult")
        raw_ids = required_list(search_result.get("idlist"), "esearchresult.idlist")
        identifiers = tuple(required_text(item, "esearchresult.idlist item") for item in raw_ids)
        if len(identifiers) > request.limit or len(set(identifiers)) != len(identifiers):
            raise SourceResponseError("PubMed IDs exceed the requested limit or contain duplicates")
        if any(not re.fullmatch(r"[1-9][0-9]{0,11}", value) for value in identifiers):
            raise SourceResponseError("PubMed search returned a malformed PMID")
        try:
            total_count = int(required_text(search_result.get("count"), "esearchresult.count"))
        except ValueError as exc:
            raise SourceResponseError("PubMed count must be a non-negative integer") from exc
        if total_count < 0:
            raise SourceResponseError("PubMed count must be a non-negative integer")

        records: tuple[NormalizedLiteratureRecord, ...] = ()
        if identifiers:
            summary_payload, _ = self._get_json(
                PUBMED_ESUMMARY_URL,
                params={
                    **common,
                    "id": ",".join(identifiers),
                    "version": "2.0",
                },
                headers={"accept": "application/json", "user-agent": "CausalBio-Lab/1.0.0"},
            )
            records = self._normalize_summaries(summary_payload, identifiers)

        return PubMedSearchResult(
            query=request.query,
            records=records,
            total_count=total_count,
            retrieved_at=self.cache.now(),
            cache_status=CacheStatus.FETCHED,
            source_endpoint=PUBMED_ESEARCH_URL,
        )

    @staticmethod
    def _normalize_summaries(
        payload: Mapping[str, Any], identifiers: tuple[str, ...]
    ) -> tuple[NormalizedLiteratureRecord, ...]:
        result = required_mapping(payload.get("result"), "result")
        summary_ids = tuple(
            required_text(item, "result.uids item")
            for item in required_list(result.get("uids"), "result.uids")
        )
        if len(summary_ids) != len(identifiers) or set(summary_ids) != set(identifiers):
            raise SourceResponseError("PubMed summary identifiers do not match requested PMIDs")
        records: list[NormalizedLiteratureRecord] = []
        for identifier in identifiers:
            summary = required_mapping(result.get(identifier), f"result.{identifier}")
            if summary.get("uid") != identifier:
                raise SourceResponseError("PubMed summary uid does not match its requested PMID")
            title = required_text(summary.get("title"), f"result.{identifier}.title")
            authors = tuple(
                name
                for item in required_list(summary.get("authors", []), "authors")
                if (name := optional_text(required_mapping(item, "author").get("name")))
            )
            article_ids = required_list(summary.get("articleids", []), "articleids")
            normalized_ids = [NormalizedIdentifier(namespace="PMID", value=identifier)]
            for item in article_ids:
                article_id = required_mapping(item, "article identifier")
                namespace = optional_text(article_id.get("idtype"))
                value = optional_text(article_id.get("value"))
                if namespace and value and namespace.casefold() != "pubmed":
                    normalized_ids.append(
                        NormalizedIdentifier(namespace=namespace.upper(), value=value)
                    )
            publication_types = tuple(
                value
                for item in required_list(summary.get("pubtype", []), "pubtype")
                if (value := optional_text(item))
            )
            records.append(
                NormalizedLiteratureRecord(
                    record_id=identifier,
                    title=title,
                    authors=authors,
                    journal=optional_text(summary.get("fulljournalname") or summary.get("source")),
                    publication_date=optional_text(
                        summary.get("pubdate") or summary.get("sortpubdate")
                    ),
                    publication_types=publication_types,
                    identifiers=tuple(normalized_ids),
                    canonical_url=f"https://pubmed.ncbi.nlm.nih.gov/{identifier}/",
                )
            )
        return tuple(records)

    def _parse_cached(self, payload: Mapping[str, object]) -> PubMedSearchResult:
        return PubMedSearchResult.model_validate(payload)


__all__ = ["PUBMED_ESEARCH_URL", "PUBMED_ESUMMARY_URL", "PubMedAdapter"]
