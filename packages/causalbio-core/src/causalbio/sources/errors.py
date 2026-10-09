"""Explicit failure modes for external scientific source adapters."""


class SourceAdapterError(RuntimeError):
    """Base class for source retrieval, validation, and cache failures."""


class SourceUnavailableError(SourceAdapterError):
    """A configured source could not be reached or was temporarily unavailable."""


class SourceResponseError(SourceAdapterError, ValueError):
    """A source returned an unsuccessful or structurally invalid response."""


class SourceCacheError(SourceAdapterError, ValueError):
    """A filesystem cache entry was unsafe, corrupt, or inconsistent."""


__all__ = [
    "SourceAdapterError",
    "SourceCacheError",
    "SourceResponseError",
    "SourceUnavailableError",
]
