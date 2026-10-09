"""Bounded, cached, normalized external scientific source adapters."""

from causalbio.sources.cache import CacheEntry, FileSystemSourceCache
from causalbio.sources.errors import (
    SourceAdapterError,
    SourceCacheError,
    SourceResponseError,
    SourceUnavailableError,
)
from causalbio.sources.europepmc import EuropePMCAdapter
from causalbio.sources.models import (
    CacheStatus,
    EuropePMCSearchResult,
    NormalizedIdentifier,
    NormalizedLiteratureRecord,
    NormalizedProteinRecord,
    NormalizedResearchArticle,
    ProteinFunctionAnnotation,
    ProteinFunctionEvidence,
    PubMedSearchResult,
    SourceAdapter,
    SourceSearchRequest,
    SourceSearchResultBase,
    UniProtSearchResult,
)
from causalbio.sources.pubmed import PubMedAdapter
from causalbio.sources.transport import HTTPResponse, HTTPTransport, HttpxTransport
from causalbio.sources.uniprot import UniProtAdapter

__all__ = [
    "CacheEntry",
    "CacheStatus",
    "EuropePMCAdapter",
    "EuropePMCSearchResult",
    "FileSystemSourceCache",
    "HTTPResponse",
    "HTTPTransport",
    "HttpxTransport",
    "NormalizedIdentifier",
    "NormalizedLiteratureRecord",
    "NormalizedProteinRecord",
    "NormalizedResearchArticle",
    "ProteinFunctionAnnotation",
    "ProteinFunctionEvidence",
    "PubMedAdapter",
    "PubMedSearchResult",
    "SourceAdapter",
    "SourceAdapterError",
    "SourceCacheError",
    "SourceResponseError",
    "SourceSearchRequest",
    "SourceSearchResultBase",
    "SourceUnavailableError",
    "UniProtAdapter",
    "UniProtSearchResult",
]
