"""KeepTradeCut value service.

Fetches dynasty player and pick values from keeptradecut.com/dynasty-rankings,
parses the embedded `playersArray` JavaScript variable, fuzzy-matches player
names against our Player table, and upserts everything into `player_values`.

Pick entries on KTC use position "RDP" and names like "2026 Early 1st".
We convert these to canonical pick_keys: "{year}_{round}_{tier}" e.g.
"2026_1_early", "2027_2_mid", "2028_3_late".

For players not found on KTC (rare FAs, recently retired), the trade calculator
falls back to an internal scoring model at query time — this service only
handles KTC data.
"""

import json
import logging
import re
import unicodedata
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Player
from app.models.player_value import PlayerValue

logger = logging.getLogger(__name__)

KTC_URL = "https://keeptradecut.com/dynasty-rankings?picks=1"
KTC_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Regex to grab the full playersArray JS variable from the HTML
_PLAYERS_ARRAY_RE = re.compile(r"var playersArray\s*=\s*(\[.*?\]);", re.DOTALL)

# Map KTC tier words to our canonical tier strings
_TIER_MAP = {
    "early": "early",
    "mid": "mid",
    "late": "late",
}

# Ordinal round words KTC uses
_ROUND_MAP = {
    "1st": 1,
    "2nd": 2,
    "3rd": 3,
    "4th": 4,
    "5th": 5,
}

# Name normalization: remove suffixes and non-alpha chars for matching
_SUFFIX_RE = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b\.?", re.IGNORECASE)
_NON_ALPHA_RE = re.compile(r"[^a-z0-9 ]")


def _normalize_name(name: str) -> str:
    """Lowercase, strip accents, remove suffixes and punctuation."""
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    name = name.lower()
    name = _SUFFIX_RE.sub("", name)
    name = _NON_ALPHA_RE.sub("", name)
    return " ".join(name.split())


def _parse_pick_key(ktc_name: str) -> Optional[str]:
    """Convert "2026 Early 1st" → "2026_1_early". Returns None if unparseable."""
    # Expected format: "{year} {Tier} {Ordinal}"
    parts = ktc_name.strip().split()
    if len(parts) != 3:
        return None
    year_str, tier_str, round_str = parts
    try:
        year = int(year_str)
    except ValueError:
        return None
    tier = _TIER_MAP.get(tier_str.lower())
    round_num = _ROUND_MAP.get(round_str.lower())
    if not tier or not round_num:
        return None
    return f"{year}_{round_num}_{tier}"


async def _fetch_ktc_html() -> str:
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(KTC_URL, headers=KTC_HEADERS)
        resp.raise_for_status()
        return resp.text


def _extract_players_array(html: str) -> list[dict]:
    match = _PLAYERS_ARRAY_RE.search(html)
    if not match:
        raise ValueError("Could not find playersArray in KTC HTML")
    return json.loads(match.group(1))


def _get_value(entry: dict, scoring_format: str) -> int:
    """Extract the KTC value for the configured scoring format."""
    if scoring_format == "superflex":
        vals = entry.get("superflexValues") or entry.get("oneQBValues") or {}
    else:
        vals = entry.get("oneQBValues") or entry.get("superflexValues") or {}
    return int(vals.get("value") or 0)


def _get_rank(entry: dict, scoring_format: str) -> Optional[int]:
    if scoring_format == "superflex":
        vals = entry.get("superflexValues") or entry.get("oneQBValues") or {}
    else:
        vals = entry.get("oneQBValues") or entry.get("superflexValues") or {}
    r = vals.get("rank")
    return int(r) if r is not None else None


async def refresh_ktc_values(db: AsyncSession, scoring_format: str = "1qb") -> dict:
    """Fetch KTC values and upsert into player_values table.

    Returns a summary dict with counts of updated/skipped entries.
    """
    logger.info("Fetching KTC dynasty values (format=%s)...", scoring_format)

    try:
        html = await _fetch_ktc_html()
    except Exception as exc:
        logger.error("Failed to fetch KTC page: %s", exc)
        return {"status": "error", "error": str(exc)}

    try:
        raw_players = _extract_players_array(html)
    except Exception as exc:
        logger.error("Failed to parse KTC playersArray: %s", exc)
        return {"status": "error", "error": str(exc)}

    # Build a normalized-name → Player.id lookup from our DB
    result = await db.execute(select(Player.id, Player.full_name, Player.position))
    db_players = result.all()
    name_to_id: dict[str, str] = {}
    for pid, full_name, _ in db_players:
        if full_name:
            name_to_id[_normalize_name(full_name)] = pid

    now = datetime.utcnow()
    updated = 0
    skipped_no_match = 0
    picks_updated = 0

    for entry in raw_players:
        position = entry.get("position", "")
        ktc_name = entry.get("playerName", "")
        value = _get_value(entry, scoring_format)
        rank = _get_rank(entry, scoring_format)
        team = entry.get("team") or None
        age_raw = entry.get("age")
        age_str = str(age_raw) if age_raw is not None else None

        if position == "RDP":
            # Draft pick entry
            pick_key = _parse_pick_key(ktc_name)
            if not pick_key:
                logger.debug("Could not parse pick key for: %s", ktc_name)
                continue

            existing = await db.execute(
                select(PlayerValue).where(PlayerValue.pick_key == pick_key)
            )
            row = existing.scalar_one_or_none()
            if row:
                row.ktc_name = ktc_name
                row.value = value
                row.rank = rank
                row.source = "ktc"
                row.position = "RDP"
                row.last_updated = now
            else:
                db.add(PlayerValue(
                    pick_key=pick_key,
                    ktc_name=ktc_name,
                    value=value,
                    rank=rank,
                    source="ktc",
                    position="RDP",
                    last_updated=now,
                ))
            picks_updated += 1

        else:
            # Regular player entry — match by normalized name
            norm = _normalize_name(ktc_name)
            player_id = name_to_id.get(norm)

            if not player_id:
                # Try last-name-only match as fallback (less reliable, skip for now)
                skipped_no_match += 1
                logger.debug("No DB match for KTC player: %s", ktc_name)
                continue

            existing = await db.execute(
                select(PlayerValue).where(PlayerValue.player_id == player_id)
            )
            row = existing.scalar_one_or_none()
            if row:
                row.ktc_name = ktc_name
                row.value = value
                row.rank = rank
                row.source = "ktc"
                row.position = position
                row.team = team
                row.age = age_str
                row.last_updated = now
            else:
                db.add(PlayerValue(
                    player_id=player_id,
                    ktc_name=ktc_name,
                    value=value,
                    rank=rank,
                    source="ktc",
                    position=position,
                    team=team,
                    age=age_str,
                    last_updated=now,
                ))
            updated += 1

    await db.commit()

    summary = {
        "status": "ok",
        "players_updated": updated,
        "picks_updated": picks_updated,
        "players_skipped_no_match": skipped_no_match,
        "scoring_format": scoring_format,
        "refreshed_at": now.isoformat(),
    }
    logger.info("KTC refresh complete: %s", summary)
    return summary
