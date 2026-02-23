from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import Roster, Season, User, Player

router = APIRouter()

POSITION_ORDER = {"QB": 0, "RB": 1, "WR": 2, "TE": 3, "K": 4, "DEF": 5}


@router.get("/taxi-squads")
async def get_taxi_squads(db: AsyncSession = Depends(get_db)):
    """Get all taxi squads for the current (latest) season."""

    # Get the latest season
    result = await db.execute(
        select(Season).order_by(Season.year.desc()).limit(1)
    )
    season = result.scalar_one_or_none()
    if not season:
        return {"season": None, "teams": []}

    # Get all rosters for this season with their owners
    result = await db.execute(
        select(Roster, User)
        .join(User, Roster.user_id == User.id)
        .where(Roster.season_id == season.id)
        .order_by(User.display_name)
    )
    roster_rows = result.all()

    # Collect all taxi player IDs across all rosters
    all_taxi_ids = set()
    for roster, _ in roster_rows:
        taxi = roster.taxi or []
        all_taxi_ids.update(str(pid) for pid in taxi)

    # Bulk-fetch all taxi players
    player_map = {}
    if all_taxi_ids:
        result = await db.execute(
            select(Player).where(Player.id.in_(all_taxi_ids))
        )
        for player in result.scalars().all():
            player_map[player.id] = player

    # Build response
    teams = []
    for roster, user in roster_rows:
        taxi = roster.taxi or []
        if not taxi:
            continue

        players = []
        for pid in taxi:
            pid_str = str(pid)
            player = player_map.get(pid_str)
            players.append({
                "player_id": pid_str,
                "full_name": player.full_name if player else pid_str,
                "position": player.position if player else None,
                "team": player.team if player else None,
            })

        # Sort by position order, then name
        players.sort(key=lambda p: (
            POSITION_ORDER.get(p["position"] or "", 99),
            p["full_name"],
        ))

        teams.append({
            "owner_name": user.display_name or user.username,
            "team_name": roster.team_name,
            "avatar": user.avatar,
            "players": players,
        })

    return {"season": season.year, "teams": teams}
