"""Storage-owned failures that callers may handle without importing SQLite."""


class RepositoryError(Exception):
    """The local library repository could not complete a storage operation."""


class RepositoryCorruptionError(RepositoryError):
    """Persisted library data could not be decoded safely."""
