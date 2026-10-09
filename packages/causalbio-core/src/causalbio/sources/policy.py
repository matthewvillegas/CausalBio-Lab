"""Bounded retry policy and process-local per-source request pacing."""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from threading import Lock

from causalbio.sources.errors import SourceUnavailableError


@dataclass(frozen=True, slots=True)
class RequestPolicy:
    max_attempts: int = 3
    min_interval_seconds: float = 0.34
    initial_retry_seconds: float = 0.25
    max_retry_seconds: float = 2.0

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_attempts, bool)
            or not isinstance(self.max_attempts, int)
            or not 1 <= self.max_attempts <= 5
        ):
            raise ValueError("max_attempts must be an integer between 1 and 5")
        for value in (
            self.min_interval_seconds,
            self.initial_retry_seconds,
            self.max_retry_seconds,
        ):
            if not math.isfinite(value) or not 0 <= value <= 10:
                raise ValueError("Request delays must be finite and between 0 and 10 seconds")
        if self.initial_retry_seconds > self.max_retry_seconds:
            raise ValueError("Initial retry delay must not exceed the retry cap")

    def retry_delay(self, attempt: int, retry_after: str | None, now: datetime) -> float | None:
        delay = min(self.max_retry_seconds, self.initial_retry_seconds * 2**attempt)
        if retry_after:
            try:
                requested = float(retry_after)
            except ValueError:
                try:
                    date = parsedate_to_datetime(retry_after)
                    if date.tzinfo is None:
                        date = date.replace(tzinfo=UTC)
                    requested = max(0.0, (date - now).total_seconds())
                except (ValueError, TypeError, OverflowError):
                    requested = 0.0
            # Never retry earlier than a source's explicit backoff requirement.
            # If it exceeds our wait budget, stop and let the caller use stale data.
            if math.isfinite(requested) and requested > self.max_retry_seconds:
                return None
            if math.isfinite(requested):
                delay = max(delay, max(0.0, requested))
        return float(delay)


class SourcePacer:
    def __init__(
        self,
        *,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.sleep = sleep
        self.monotonic = monotonic
        self._lock = Lock()
        self._last_start: dict[str, float] = {}

    def wait(self, source: str, interval: float, *, max_wait_seconds: float = 120.0) -> None:
        deadline = self.monotonic() + max_wait_seconds
        if not self._lock.acquire(timeout=max_wait_seconds):
            raise SourceUnavailableError("The source search exceeded its pacing time budget")
        try:
            now = self.monotonic()
            previous = self._last_start.get(source)
            if previous is not None and (remaining := interval - (now - previous)) > 0:
                if remaining >= deadline - now:
                    raise SourceUnavailableError(
                        "The source search exceeded its pacing time budget"
                    )
                self.sleep(remaining)
            self._last_start[source] = self.monotonic()
        finally:
            self._lock.release()


DEFAULT_PACER = SourcePacer()
