"""Injectable HTTP boundary for scientific source adapters."""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol, cast

import httpx

from causalbio.sources.errors import SourceResponseError, SourceUnavailableError


@dataclass(frozen=True, slots=True)
class HTTPResponse:
    status_code: int
    body: bytes
    headers: Mapping[str, str] = field(default_factory=dict)

    def json(self) -> object:
        try:
            return cast(object, json.loads(self.body.decode("utf-8")))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SourceResponseError("The source returned invalid UTF-8 JSON") from exc

    def header(self, name: str) -> str | None:
        requested = name.casefold()
        for key, value in self.headers.items():
            if key.casefold() == requested:
                return value
        return None


class HTTPTransport(Protocol):
    def get(
        self,
        url: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
        timeout: float,
    ) -> HTTPResponse:
        """Perform one GET against an adapter-controlled URL."""


class HttpxTransport:
    """Production transport; tests inject fixture transports instead."""

    def __init__(
        self, client: httpx.Client | None = None, *, max_response_bytes: int = 5_000_000
    ) -> None:
        if max_response_bytes < 1:
            raise ValueError("max_response_bytes must be positive")
        self._client = client
        self.max_response_bytes = max_response_bytes

    def _read(
        self,
        client: httpx.Client,
        url: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
        timeout: float,
    ) -> HTTPResponse:
        deadline = time.monotonic() + timeout
        with client.stream(
            "GET", url, params=params, headers=headers, timeout=timeout, follow_redirects=False
        ) as response:
            body = bytearray()
            # Bound decoded bytes too: a small compressed payload can expand dramatically.
            # Check each decoded transport chunk; an additional output buffer would
            # hide a slowly trickling response until that buffer became full.
            for chunk in response.iter_bytes():
                if time.monotonic() >= deadline:
                    raise SourceUnavailableError(
                        "The source response exceeded its read time budget"
                    )
                if len(body) + len(chunk) > self.max_response_bytes:
                    raise SourceResponseError(
                        f"The source response exceeds the {self.max_response_bytes}-byte safety limit"
                    )
                body.extend(chunk)
            if time.monotonic() >= deadline:
                raise SourceUnavailableError("The source response exceeded its read time budget")
            return HTTPResponse(response.status_code, bytes(body), dict(response.headers))

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
        timeout: float,
    ) -> HTTPResponse:
        try:
            if self._client is not None:
                return self._read(
                    self._client, url, params=params, headers=headers, timeout=timeout
                )
            else:
                with httpx.Client(follow_redirects=False) as client:
                    return self._read(client, url, params=params, headers=headers, timeout=timeout)
        except httpx.HTTPError as exc:
            raise SourceUnavailableError("The configured source could not be reached") from exc


__all__ = ["HTTPResponse", "HTTPTransport", "HttpxTransport"]
