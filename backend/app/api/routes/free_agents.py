from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc, case
from typing import Optional

from app.database import get_db
from app.api.deps import get_league_id
from app.models import Player, PlayerValue, Roster, Season
from app.services.league_value_format import get_league_value_format

router = APIRouter()

# Kickers were dropped from every configured league's roster_positions for
# 2026, so they are no longer meaningful free agents.
STARTABLE_POSITIONS = {"QB", "RB", "WR", "TE"}


@router.get("/free-agents")
async def get_free_agents(
    league_id: str = Depends(get_league_id),
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None, description="Search by player name"),
    position: Optional[str] = Query(None, description="Filter by position (QB, RB, WR, TE)"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    """Return players not on any roster in the current season, sorted by KTC value."""

    season_result = await db.execute(
        select(Season)
        .where(Season.group_id == league_id)
        .order_by(desc(Season.year))
        .limit(1)
    )
    season = season_result.scalar_one_or_none()

    rostered_ids: set[str] = set()
    if season:
        roster_result = await db.execute(
            select(Roster.players, Roster.taxi, Roster.reserve)
            .where(Roster.season_id == season.id)
        )
        for row in roster_result.all():
            for id_list in (row.players, row.taxi, row.reserve):
                if id_list:
                    rostered_ids.update(str(pid) for pid in id_list)

    # KTC prices players per scoring format and TE-premium setting, both of
    # which differ between the configured leagues.
    fmt = await get_league_value_format(db, league_id)
    value_col = fmt.value_column.label("ktc_value")
    rank_col = fmt.rank_column.label("ktc_rank")

    # Base query: join Player with PlayerValue, exclude rostered players
    query = (
        select(Player, value_col, rank_col)
        .outerjoin(PlayerValue, PlayerValue.player_id == Player.id)
        .where(Player.position.in_(STARTABLE_POSITIONS))
        .where(Player.status == "Active")
        .where(Player.years_exp > 0)
    )

    if rostered_ids:
        query = query.where(Player.id.notin_(rostered_ids))

    if search:
        term = f"%{search}%"
        query = query.where(
            or_(
                Player.full_name.like(term),
                Player.first_name.like(term),
                Player.last_name.like(term),
            )
        )

    if position:
        query = query.where(Player.position == position.upper())

    # Count total before pagination
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()

    # Sort by KTC value descending (nulls last), then name
    query = (
        query
        .order_by(case((value_col == None, 1), else_=0), desc(value_col), Player.full_name)
        .offset(offset)
        .limit(limit)
    )

    rows = (await db.execute(query)).all()

    players = []
    for player, ktc_value, ktc_rank in rows:
        players.append({
            "player_id": player.id,
            "full_name": player.full_name,
            "position": player.position,
            "team": player.team,
            "age": player.age,
            "years_exp": player.years_exp,
            "ktc_value": ktc_value or 0,
            "ktc_rank": ktc_rank,
            "status": player.status,
            "injury_status": player.injury_status,
        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "season": season.year if season else None,
        "players": players,
    }
