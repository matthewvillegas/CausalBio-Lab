"""Bounded Europe PMC core search preserving abstracts and citation provenance."""

from __future__ import annotations

from collections.abc import Mapping
from html.parser import HTMLParser
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
    EuropePMCSearchResult,
    NormalizedIdentifier,
    NormalizedResearchArticle,
    SourceSearchRequest,
)
from causalbio.sources.policy import RequestPolicy, SourcePacer
from causalbio.sources.transport import HTTPTransport

EUROPE_PMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


class _PlainText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.fragments: list[str] = []
        self.suppressed = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in {"script", "style"}:
            self.suppressed += 1
        if tag in {"p", "br", "div", "h1", "h2", "h3", "h4", "li"}:
            self.fragments.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self.suppressed = max(0, self.suppressed - 1)
        if tag in {"p", "div", "h1", "h2", "h3", "h4", "li"}:
            self.fragments.append(" ")

    def handle_data(self, data: str) -> None:
        if not self.suppressed:
            self.fragments.append(data)


def plain_source_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SourceResponseError(f"Europe PMC {label} must be text")
    if len(value) > 100_000:
        raise SourceResponseError(f"Europe PMC {label} exceeds the text limit")
    parser = _PlainText()
    parser.feed(value)
    parser.close()
    return optional_text("".join(parser.fragments))


class EuropePMCAdapter(CachedSourceAdapter[EuropePMCSearchResult]):
    name = "europe_pmc"
    adapter_version = "europe-pmc-core-search-1"
    source_endpoint = EUROPE_PMC_SEARCH_URL

    def __init__(
        self,
        *,
        transport: HTTPTransport | None = None,
        cache: FileSystemSourceCache | None = None,
        timeout_seconds: float = 8.0,
        max_response_bytes: int = 5_000_000,
        request_policy: RequestPolicy | None = None,
        pacer: SourcePacer | None = None,
        max_search_seconds: float = 20.0,
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

    def _fetch(self, request: SourceSearchRequest) -> EuropePMCSearchResult:
        payload, _ = self._get_json(
            EUROPE_PMC_SEARCH_URL,
            params={
                "query": request.query,
                "format": "json",
                "resultType": "core",
                "pageSize": str(request.limit),
            },
            headers={"accept": "application/json", "user-agent": "CausalBio-Lab/1.0.0"},
        )
        count = payload.get("hitCount")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise SourceResponseError("Europe PMC hitCount must be a non-negative integer")
        echoed = required_mapping(payload.get("request"), "request")
        if (
            echoed.get("queryString") != request.query
            or required_text(echoed.get("resultType"), "request.resultType").casefold() != "core"
            or echoed.get("pageSize") != request.limit
        ):
            raise SourceResponseError("Europe PMC response does not match the bounded query")
        results = required_list(
            required_mapping(payload.get("resultList"), "resultList").get("result"),
            "resultList.result",
        )
        if len(results) > request.limit:
            raise SourceResponseError("Europe PMC records exceed the requested limit")
        records = tuple(self._normalize(required_mapping(item, "result")) for item in results)
        return EuropePMCSearchResult(
            query=request.query,
            total_count=count,
            retrieved_at=self.cache.now(),
            cache_status=CacheStatus.FETCHED,
            source_endpoint=EUROPE_PMC_SEARCH_URL,
            records=records,
        )

    @staticmethod
    def _normalize(item: Mapping[str, Any]) -> NormalizedResearchArticle:
        origin = required_text(item.get("source"), "source")
        identifier = required_text(item.get("id"), "id")
        pmid = optional_text(item.get("pmid")) or (identifier if origin == "MED" else None)
        pmcid = optional_text(item.get("pmcid")) or (identifier if origin == "PMC" else None)
        doi = optional_text(item.get("doi"))
        title = plain_source_text(item.get("title"), "title")
        if not title:
            raise SourceResponseError("Europe PMC title must contain text")
        authors: tuple[str, ...] = ()
        if item.get("authorList") is not None:
            authors = tuple(
                required_text(required_mapping(author, "author").get("fullName"), "author.fullName")
                for author in required_list(
                    required_mapping(item["authorList"], "authorList").get("author", []),
                    "authorList.author",
                )
            )
        elif text := optional_text(item.get("authorString")):
            authors = (text,)
        year: int | None = None
        if (value := item.get("pubYear")) is not None:
            try:
                year = int(required_text(value, "pubYear"))
            except ValueError as exc:
                raise SourceResponseError("Europe PMC pubYear must be a year") from exc
        journal: str | None = None
        if item.get("journalInfo") is not None:
            info = required_mapping(item["journalInfo"], "journalInfo")
            if info.get("journal") is not None:
                journal = optional_text(required_mapping(info["journal"], "journal").get("title"))
        types: tuple[str, ...] = ()
        if item.get("pubTypeList") is not None:
            types = tuple(
                required_text(value, "publication type")
                for value in required_list(
                    required_mapping(item["pubTypeList"], "pubTypeList").get("pubType", []),
                    "pubTypeList.pubType",
                )
            )
        identities = [(origin, identifier)] + [
            (namespace, value)
            for namespace, value in (("PMID", pmid), ("PMCID", pmcid), ("DOI", doi))
            if value
        ]
        return NormalizedResearchArticle(
            record_id=f"{origin}:{identifier}",
            record_source=origin,
            title=title,
            authors=authors,
            publication_year=year,
            journal=journal,
            doi=doi,
            pmid=pmid,
            pmcid=pmcid,
            abstract=plain_source_text(item.get("abstractText"), "abstractText"),
            publication_types=types,
            license=optional_text(item.get("license")),
            identifiers=tuple(
                NormalizedIdentifier(namespace=namespace, value=value)
                for namespace, value in identities
            ),
            canonical_url=f"https://europepmc.org/article/{origin}/{identifier}",
        )

    def _parse_cached(self, payload: Mapping[str, object]) -> EuropePMCSearchResult:
        return EuropePMCSearchResult.model_validate(payload)
