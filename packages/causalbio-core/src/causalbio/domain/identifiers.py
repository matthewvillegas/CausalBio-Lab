"""Stable internal identifier helpers."""

from uuid import UUID, uuid5

CAUSALBIO_NAMESPACE = UUID("7640f4f7-ddb9-49c8-b7ef-e595526b4e5a")


def stable_uuid(kind: str, key: str) -> UUID:
    """Return a stable UUID for a versioned curated-data key."""

    return uuid5(CAUSALBIO_NAMESPACE, f"{kind}:{key.strip().lower()}")
