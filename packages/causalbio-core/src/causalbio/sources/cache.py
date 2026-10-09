"""Deterministic JSON filesystem cache with explicit TTL semantics."""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock
from typing import Any, cast

from causalbio.sources.errors import SourceCacheError

_NAMESPACE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_CACHE_SCHEMA_VERSION = 1


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class CacheEntry:
    payload: dict[str, Any]
    stored_at: datetime
    stale: bool
    path: Path


class FileSystemSourceCache:
    """Store validated adapter results under content-addressed cache paths."""

    def __init__(
        self,
        root: Path,
        *,
        ttl: timedelta = timedelta(hours=24),
        clock: Callable[[], datetime] = utc_now,
        max_entry_bytes: int = 10_000_000,
    ) -> None:
        if ttl < timedelta(0):
            raise ValueError("Cache TTL must be non-negative")
        if max_entry_bytes < 1:
            raise ValueError("max_entry_bytes must be positive")
        self.root = root.resolve()
        self.ttl = ttl
        self._clock = clock
        self.max_entry_bytes = max_entry_bytes
        self._lock = RLock()

    def now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise SourceCacheError("Cache clocks must return timezone-aware timestamps")
        return value.astimezone(UTC)

    @staticmethod
    def _validate_namespace(namespace: str) -> None:
        if not _NAMESPACE.fullmatch(namespace):
            raise SourceCacheError(f"Unsafe cache namespace: {namespace!r}")

    def key_for(self, namespace: str, key_material: Mapping[str, object]) -> str:
        self._validate_namespace(namespace)
        try:
            canonical = json.dumps(
                {
                    "namespace": namespace,
                    "schema_version": _CACHE_SCHEMA_VERSION,
                    "key_material": key_material,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise SourceCacheError("Cache key material is not JSON-serializable") from exc
        return hashlib.sha256(canonical).hexdigest()

    def path_for(self, namespace: str, key_material: Mapping[str, object]) -> Path:
        key = self.key_for(namespace, key_material)
        path = (self.root / namespace / f"{key}.json").resolve()
        expected_parent = (self.root / namespace).resolve()
        if expected_parent.parent != self.root or path.parent != expected_parent:
            raise SourceCacheError("Resolved cache path escaped its namespace")
        return path

    def read(self, namespace: str, key_material: Mapping[str, object]) -> CacheEntry | None:
        path = self.path_for(namespace, key_material)
        if not path.is_file():
            return None
        try:
            with path.open("rb") as stream:
                encoded = stream.read(self.max_entry_bytes + 1)
            if len(encoded) > self.max_entry_bytes:
                raise SourceCacheError(f"Cache entry exceeds {self.max_entry_bytes} bytes")
            raw = cast(object, json.loads(encoded.decode("utf-8")))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SourceCacheError(f"Could not read cache entry {path.name}") from exc
        if not isinstance(raw, dict):
            raise SourceCacheError("Cache entry must be a JSON object")
        expected_key = self.key_for(namespace, key_material)
        if raw.get("schema_version") != _CACHE_SCHEMA_VERSION:
            raise SourceCacheError("Cache schema version is unsupported")
        if raw.get("namespace") != namespace or raw.get("key") != expected_key:
            raise SourceCacheError("Cache identity does not match its content-addressed path")
        try:
            stored_at = datetime.fromisoformat(str(raw["stored_at"]))
        except (KeyError, ValueError) as exc:
            raise SourceCacheError("Cache entry has an invalid stored_at timestamp") from exc
        if stored_at.tzinfo is None or stored_at.utcoffset() is None:
            raise SourceCacheError("Cache stored_at timestamp must be timezone-aware")
        payload = raw.get("payload")
        if not isinstance(payload, dict):
            raise SourceCacheError("Cache payload must be a JSON object")
        age = max(self.now() - stored_at.astimezone(UTC), timedelta(0))
        return CacheEntry(
            payload=cast(dict[str, Any], payload),
            stored_at=stored_at.astimezone(UTC),
            stale=age >= self.ttl,
            path=path,
        )

    def write(
        self,
        namespace: str,
        key_material: Mapping[str, object],
        payload: Mapping[str, object],
        *,
        stored_at: datetime | None = None,
    ) -> Path:
        path = self.path_for(namespace, key_material)
        timestamp = stored_at or self.now()
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise SourceCacheError("Cache write timestamps must be timezone-aware")
        envelope = {
            "schema_version": _CACHE_SCHEMA_VERSION,
            "namespace": namespace,
            "key": self.key_for(namespace, key_material),
            "stored_at": timestamp.astimezone(UTC).isoformat(),
            "payload": payload,
        }
        try:
            encoded = json.dumps(
                envelope,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as exc:
            raise SourceCacheError("Cache payload is not JSON-serializable") from exc
        if len(encoded.encode("utf-8")) > self.max_entry_bytes:
            raise SourceCacheError(f"Cache entry exceeds {self.max_entry_bytes} bytes")

        with self._lock:
            temporary: Path | None = None
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    newline="\n",
                    dir=path.parent,
                    prefix=path.stem,
                    suffix=".tmp",
                    delete=False,
                ) as stream:
                    temporary = Path(stream.name)
                    stream.write(encoded + "\n")
                temporary.replace(path)
            except OSError as exc:
                raise SourceCacheError(f"Could not write cache entry {path.name}") from exc
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
        return path


__all__ = ["CacheEntry", "FileSystemSourceCache", "utc_now"]
