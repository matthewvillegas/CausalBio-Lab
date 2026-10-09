"""Small local-mode security and observability middleware."""

from __future__ import annotations

import re
import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import Request
from starlette.datastructures import Headers, MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_SAFE_CORRELATION_ID = re.compile(r"^[A-Za-z0-9._-]{1,80}$")


class CorrelationAndSecurityMiddleware:
    """Bound actual body bytes, including chunked requests, before JSON parsing."""

    def __init__(self, app: ASGIApp, *, max_request_bytes: int) -> None:
        self.app = app
        self.max_request_bytes = max_request_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        supplied = headers.get("x-correlation-id", "")
        correlation_id = supplied if _SAFE_CORRELATION_ID.fullmatch(supplied) else str(uuid4())
        scope.setdefault("state", {})["correlation_id"] = correlation_id

        async def secured_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                response_headers["x-correlation-id"] = correlation_id
                response_headers["x-content-type-options"] = "nosniff"
                response_headers["referrer-policy"] = "no-referrer"
                response_headers["permissions-policy"] = "camera=(), microphone=(), geolocation=()"
            await send(message)

        async def reject(status: int, title: str, detail: str) -> None:
            response = JSONResponse(
                status_code=status,
                content={
                    "type": "https://causalbio.example/problems/"
                    + ("request-too-large" if status == 413 else "invalid-content-length"),
                    "title": title,
                    "status": status,
                    "detail": detail,
                    "correlation_id": correlation_id,
                    "alternatives": [],
                },
            )
            await response(scope, receive, secured_send)

        length = headers.get("content-length")
        if length is not None and (not length.isascii() or not length.isdecimal()):
            await reject(
                400, "Invalid request length", "Content-Length must be a nonnegative integer."
            )
            return
        if length is not None and int(length) > self.max_request_bytes:
            await reject(
                413,
                "Request body is too large",
                f"Request bodies are limited to {self.max_request_bytes} bytes.",
            )
            return
        chunks: list[bytes] = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > self.max_request_bytes:
                await reject(
                    413,
                    "Request body is too large",
                    f"Request bodies are limited to {self.max_request_bytes} bytes.",
                )
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        body = b"".join(chunks)
        delivered = False

        async def replay_body() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay_body, secured_send)


class LocalRateLimitMiddleware(BaseHTTPMiddleware):
    """Process-local protection for demo mode; production should use a shared limiter."""

    def __init__(self, app: object, *, requests_per_minute: int) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.requests_per_minute = requests_per_minute
        self._requests: defaultdict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client = request.client.host if request.client else "local"
        now = time.monotonic()
        bucket = self._requests[client]
        while bucket and now - bucket[0] >= 60:
            bucket.popleft()
        if len(bucket) >= self.requests_per_minute:
            correlation_id = str(getattr(request.state, "correlation_id", uuid4()))
            return JSONResponse(
                status_code=429,
                content={
                    "type": "https://causalbio.example/problems/rate-limit",
                    "title": "Local request limit reached",
                    "status": 429,
                    "detail": "Wait briefly before retrying the analysis.",
                    "correlation_id": correlation_id,
                    "alternatives": [],
                },
                headers={"retry-after": "60"},
            )
        bucket.append(now)
        return await call_next(request)
