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


def ordinal(n: int) -> str:
    """1 -> '1st', 3 -> '3rd', 9 -> '9th', 11 -> '11th'."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def matchup_played(home_points, away_points) -> bool:
    """True once either side of a matchup has scored.

    The offseason sync stores future-week matchup pairings with 0-0 scores;
    record/streak/H2H tallies must skip those or they count as phantom ties.
    """
    return bool(home_points or away_points)
