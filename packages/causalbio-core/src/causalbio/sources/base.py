"""Shared cache and HTTP behavior for bounded source adapters."""

from __future__ import annotations

import math
import time
from abc import ABC, abstractmethod
from collections.abc import Mapping
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Generic, TypeVar, cast

from pydantic import ValidationError

from causalbio.sources.cache import CacheEntry, FileSystemSourceCache
from causalbio.sources.errors import (
    SourceAdapterError,
    SourceCacheError,
    SourceResponseError,
    SourceUnavailableError,
)
from causalbio.sources.models import CacheStatus, SourceSearchRequest, SourceSearchResultBase
from causalbio.sources.policy import DEFAULT_PACER, RequestPolicy, SourcePacer
from causalbio.sources.transport import HTTPResponse, HTTPTransport, HttpxTransport

ResultT = TypeVar("ResultT", bound=SourceSearchResultBase)
_DEADLINE: ContextVar[float | None] = ContextVar("source_search_deadline", default=None)


class CachedSourceAdapter(ABC, Generic[ResultT]):
    """Fetch, normalize, cache, and explicitly degrade to validated stale data."""

    name: str
    source_endpoint: str
    adapter_version = "1"

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
        if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 60:
            raise ValueError("timeout_seconds must be finite and between 0 and 60 seconds")
        if max_response_bytes < 1:
            raise ValueError("max_response_bytes must be positive")
        if not math.isfinite(max_search_seconds) or not 0 < max_search_seconds <= 120:
            raise ValueError("max_search_seconds must be finite and between 0 and 120 seconds")
        self.transport = transport or HttpxTransport(max_response_bytes=max_response_bytes)
        self.cache = cache or FileSystemSourceCache(Path("data/cache/sources"))
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes
        self.request_policy = request_policy or RequestPolicy()
        self.pacer = pacer or DEFAULT_PACER
        self.max_search_seconds = max_search_seconds

    def search(self, request: SourceSearchRequest) -> ResultT:
        token = _DEADLINE.set(time.monotonic() + self.max_search_seconds)
        try:
            return self._search(request)
        finally:
            _DEADLINE.reset(token)

    def _search(self, request: SourceSearchRequest) -> ResultT:
        key_material = self._cache_key_material(request)
        entry: CacheEntry | None = None
        cache_warning: str | None = None
        try:
            entry = self.cache.read(self.name, key_material)
            if entry is not None and not entry.stale and not request.refresh:
                cached = self._parse_cached(entry.payload)
                self._validate_identity(cached, request)
                return self._with_status(cached, CacheStatus.FRESH)
        except (SourceCacheError, ValueError):
            cache_warning = "An invalid cache entry was ignored and replaced after retrieval."
            entry = None

        try:
            try:
                result = self._fetch(request)
                self._validate_identity(result, request)
            except ValidationError as exc:
                raise SourceResponseError(
                    "Source records do not match the normalized schema"
                ) from exc
        except SourceAdapterError as exc:
            if entry is not None and request.allow_stale:
                try:
                    cached = self._parse_cached(entry.payload)
                    self._validate_identity(cached, request)
                except ValueError:
                    raise exc from None
                warning = "The external source was unavailable; returning previously validated stale cache data."
                return self._with_status(cached, CacheStatus.STALE, warning)
            raise

        if cache_warning:
            result = self._with_warning(result, cache_warning)
        try:
            self.cache.write(
                self.name,
                key_material,
                cast(Mapping[str, object], result.model_dump(mode="json")),
                stored_at=result.retrieved_at,
            )
        except SourceCacheError:
            result = self._with_warning(
                result, "The validated source result could not be written to the local cache."
            )
        return result

    def _validate_identity(self, result: ResultT, request: SourceSearchRequest) -> None:
        if result.query != request.query or str(result.source_endpoint) != self.source_endpoint:
            raise SourceResponseError("Source result identity does not match the bounded request")
        identifiers = result.record_ids()
        if len(identifiers) > request.limit or len(set(identifiers)) != len(identifiers):
            raise SourceResponseError(
                "Source records exceed the requested limit or contain duplicate identifiers"
            )
        if result.total_count is not None and result.total_count < len(identifiers):
            raise SourceResponseError(
                "Source total count is smaller than its returned record count"
            )

    def _cache_key_material(self, request: SourceSearchRequest) -> dict[str, object]:
        return {
            "adapter_version": self.adapter_version,
            "query": request.query,
            "limit": request.limit,
        }

    def _get_json(
        self,
        url: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
    ) -> tuple[dict[str, Any], HTTPResponse]:
        for attempt in range(self.request_policy.max_attempts):
            self.pacer.wait(
                self.name,
                self.request_policy.min_interval_seconds,
                max_wait_seconds=self._remaining_seconds(),
            )
            remaining = self._remaining_seconds()
            retry_after: str | None = None
            try:
                response = self.transport.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=min(self.timeout_seconds, remaining),
                )
                self._remaining_seconds()
                if response.status_code in {408, 425, 429} or 500 <= response.status_code <= 599:
                    retry_after = response.header("retry-after")
                    raise SourceUnavailableError(
                        f"The source is temporarily unavailable (HTTP {response.status_code})"
                    )
                break
            except SourceUnavailableError:
                if attempt + 1 == self.request_policy.max_attempts:
                    raise
                delay = self.request_policy.retry_delay(attempt, retry_after, self.cache.now())
                if delay is None:
                    raise
                if delay >= self._remaining_seconds():
                    raise SourceUnavailableError(
                        "The source search exceeded its time budget"
                    ) from None
                self.pacer.sleep(delay)
            except SourceAdapterError:
                raise
            except Exception as exc:
                raise SourceUnavailableError("The configured source transport failed") from exc
        if len(response.body) > self.max_response_bytes:
            raise SourceResponseError(
                f"The source response exceeds the {self.max_response_bytes}-byte safety limit"
            )
        if response.status_code != 200:
            raise SourceResponseError(
                f"The source rejected the bounded request (HTTP {response.status_code})"
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise SourceResponseError("The source JSON response must be an object")
        return cast(dict[str, Any], payload), response

    @staticmethod
    def _remaining_seconds() -> float:
        deadline = _DEADLINE.get()
        if deadline is None:
            return 120.0
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise SourceUnavailableError("The source search exceeded its time budget")
        return remaining

    @staticmethod
    def _with_status(
        result: ResultT,
        status: CacheStatus,
        warning: str | None = None,
    ) -> ResultT:
        warnings = result.warnings + ((warning,) if warning else ())
        return result.model_copy(update={"cache_status": status, "warnings": warnings})

    @staticmethod
    def _with_warning(result: ResultT, warning: str) -> ResultT:
        return result.model_copy(update={"warnings": (*result.warnings, warning)})

    @abstractmethod
    def _fetch(self, request: SourceSearchRequest) -> ResultT:
        raise NotImplementedError

    @abstractmethod
    def _parse_cached(self, payload: Mapping[str, object]) -> ResultT:
        raise NotImplementedError


def required_mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SourceResponseError(f"Source field '{label}' must be an object")
    return cast(dict[str, Any], value)


def required_list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise SourceResponseError(f"Source field '{label}' must be a list")
    return value


def required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SourceResponseError(f"Source field '{label}' must be non-empty text")
    return " ".join(value.split())


def optional_text(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return " ".join(value.split())


__all__ = [
    "CachedSourceAdapter",
    "optional_text",
    "required_list",
    "required_mapping",
    "required_text",
]
