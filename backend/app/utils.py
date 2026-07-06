"""Shared helpers."""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Current UTC time as a naive datetime.

    DB DateTime columns store naive UTC values; this replaces the deprecated
    datetime.utcnow() with identical semantics.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utcfromtimestamp_ms(ms: float) -> datetime:
    """Convert a millisecond epoch (as Sleeper returns) to a naive UTC datetime."""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).replace(tzinfo=None)
