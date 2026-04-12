"""Future Draft Pick Tracker endpoints.

GET /draft-picks/future  — full pick grid for all future seasons,
                           showing current owner vs original team with trade provenance.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models import Draft, Roster, Season, User
from app.services.sleeper_client import sleeper_client

router = APIRouter()


@router.get("/draft-picks/future")
async def get_future_draft_picks(db: AsyncSession = Depends(get_db)):
    """Return all future draft picks for every team, with trade provenance.

    For each (season, round, original_team) combination, returns who currently
    holds the pick and whether it was traded. Seasons shown: from the next
    un-drafted year through the furthest year referenced in traded picks
    (minimum: next 2 years).
    """
    # ── 1. Current season ─────────────────────────────────────────────────────
    season_result = await db.execute(select(Season).order_by(desc(Season.year)).limit(1))
    current_season = season_result.scalar_one_or_none()
    current_year = current_season.year if current_season else 2025

    # ── 2. All rosters + owners for current season ───────────────────────────
    roster_result = await db.execute(
        select(Roster, User)
        .join(User, Roster.user_id == User.id)
        .where(Roster.season_id == current_season.id if current_season else True)
    )
    roster_rows = roster_result.all()

    # roster_id -> owner info
    owner_map: dict[int, dict] = {}
    for roster, user in roster_rows:
        owner_map[roster.roster_id] = {
            "roster_id": roster.roster_id,
            "user_id": user.id,
            "display_name": user.display_name or user.username,
            "avatar": user.avatar,
        }

    all_roster_ids = sorted(owner_map.keys())

    # ── 3. Number of rounds from most recent complete draft ───────────────────
    draft_result = await db.execute(select(Draft).order_by(desc(Draft.year)).limit(1))
    latest_draft = draft_result.scalar_one_or_none()
    num_rounds = latest_draft.rounds if latest_draft else 5

    # ── 4. Traded picks from Sleeper ─────────────────────────────────────────
    try:
        traded_raw = await sleeper_client.get_traded_picks()
    except Exception:
        traded_raw = []

    # Build lookup: (season, round, original_roster_id) -> traded pick entry
    traded_map: dict[tuple, dict] = {}
    for tp in traded_raw:
        key = (int(tp["season"]), int(tp["round"]), int(tp["roster_id"]))
        # If a pick was traded multiple times, keep the latest owner
        existing = traded_map.get(key)
        if not existing or tp["owner_id"] != tp["roster_id"]:
            traded_map[key] = tp

    # ── 5. Determine future seasons to display ───────────────────────────────
    first_future = current_year + 1
    # Include any seasons referenced in traded picks beyond first_future
    traded_seasons = {int(tp["season"]) for tp in traded_raw if int(tp["season"]) >= first_future}
    # Always show at least 2 future years
    min_last = first_future + 1
    last_future = max(max(traded_seasons, default=min_last), min_last)
    future_seasons = list(range(first_future, last_future + 1))

    # ── 6. Build pick grid ────────────────────────────────────────────────────
    picks = []
    for season_year in future_seasons:
        for rnd in range(1, num_rounds + 1):
            for original_rid in all_roster_ids:
                key = (season_year, rnd, original_rid)
                tp = traded_map.get(key)

                if tp:
                    current_rid = int(tp["owner_id"])
                    is_traded = current_rid != original_rid
                else:
                    current_rid = original_rid
                    is_traded = False

                # Resolve owner info — owners may have different roster_ids between seasons
                original_owner = owner_map.get(original_rid, {
                    "roster_id": original_rid,
                    "user_id": None,
                    "display_name": f"Team {original_rid}",
                    "avatar": None,
                })
                current_owner = owner_map.get(current_rid, {
                    "roster_id": current_rid,
                    "user_id": None,
                    "display_name": f"Team {current_rid}",
                    "avatar": None,
                })

                picks.append({
                    "season": season_year,
                    "round": rnd,
                    "original_roster_id": original_rid,
                    "original_owner": original_owner,
                    "current_roster_id": current_rid,
                    "current_owner": current_owner,
                    "is_traded": is_traded,
                })

    # Sort owners list alphabetically for consistent display
    owners_list = sorted(owner_map.values(), key=lambda o: o["display_name"].lower())

    return {
        "current_season": current_year,
        "future_seasons": future_seasons,
        "num_rounds": num_rounds,
        "owners": owners_list,
        "picks": picks,
    }
