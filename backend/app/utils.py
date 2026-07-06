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


def matchup_played(home_points, away_points) -> bool:
    """True once either side of a matchup has scored.

    The offseason sync stores future-week matchup pairings with 0-0 scores;
    record/streak/H2H tallies must skip those or they count as phantom ties.
    """
    return bool(home_points or away_points)
