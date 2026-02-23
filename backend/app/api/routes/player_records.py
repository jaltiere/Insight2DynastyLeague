from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import MatchupPlayerPoint, Matchup, Roster, Player, User, Season
from typing import Optional

router = APIRouter()


@router.get("/player-records")
async def get_player_records(
    view: str = Query("game", pattern="^(game|season|career)$"),
    match_type: str = Query("regular", pattern="^(regular|playoff|consolation)$"),
    roster_type: str = Query("all", pattern="^(all|starter|bench)$"),
    position: Optional[str] = Query(None, pattern="^(QB|RB|WR|TE|K|DEF)$"),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get top player scoring records by game, season, or career."""

    if view == "game":
        records = await _get_game_records(db, match_type, roster_type, position, limit)
    elif view == "season":
        records = await _get_season_records(db, match_type, roster_type, position, limit)
    else:
        records = await _get_career_records(db, match_type, roster_type, position, limit)

    return {"view": view, "match_type": match_type, "roster_type": roster_type, "records": records}


async def _get_game_records(db, match_type, roster_type, position, limit):
    """Top individual game performances."""
    query = (
        select(
            MatchupPlayerPoint.points,
            MatchupPlayerPoint.is_starter,
            MatchupPlayerPoint.player_id,
            func.coalesce(Player.full_name, MatchupPlayerPoint.player_id).label("player_name"),
            Player.position,
            Player.team,
            Matchup.week,
            Matchup.match_type,
            Season.year.label("season"),
            User.display_name.label("owner_name"),
            User.username.label("owner_username"),
            Roster.team_name,
        )
        .join(Matchup, MatchupPlayerPoint.matchup_id == Matchup.id)
        .join(Roster, MatchupPlayerPoint.roster_id == Roster.id)
        .outerjoin(Player, MatchupPlayerPoint.player_id == Player.id)
        .join(User, Roster.user_id == User.id)
        .join(Season, Matchup.season_id == Season.id)
        .where(Matchup.match_type == match_type)
    )

    query = _apply_filters(query, roster_type, position)
    query = query.order_by(MatchupPlayerPoint.points.desc()).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "rank": i + 1,
            "player_name": row.player_name,
            "position": row.position or "—",
            "team": row.team or "—",
            "points": row.points,
            "season": row.season,
            "week": row.week,
            "match_type": row.match_type,
            "is_starter": row.is_starter,
            "owner_name": row.owner_name or row.owner_username,
            "team_name": row.team_name,
        }
        for i, row in enumerate(rows)
    ]


async def _get_season_records(db, match_type, roster_type, position, limit):
    """Top player season totals."""
    query = (
        select(
            MatchupPlayerPoint.player_id,
            func.coalesce(Player.full_name, MatchupPlayerPoint.player_id).label("player_name"),
            Player.position,
            Player.team,
            func.sum(MatchupPlayerPoint.points).label("total_points"),
            func.count(MatchupPlayerPoint.id).label("games_played"),
            func.avg(MatchupPlayerPoint.points).label("avg_points"),
            Season.year.label("season"),
            User.display_name.label("owner_name"),
            User.username.label("owner_username"),
            Roster.team_name,
        )
        .join(Matchup, MatchupPlayerPoint.matchup_id == Matchup.id)
        .join(Roster, MatchupPlayerPoint.roster_id == Roster.id)
        .outerjoin(Player, MatchupPlayerPoint.player_id == Player.id)
        .join(User, Roster.user_id == User.id)
        .join(Season, Matchup.season_id == Season.id)
        .where(Matchup.match_type == match_type)
    )

    query = _apply_filters(query, roster_type, position)
    query = (
        query
        .group_by(
            MatchupPlayerPoint.player_id, Player.full_name, Player.position, Player.team,
            Season.year, User.display_name, User.username, Roster.team_name,
        )
        .order_by(func.sum(MatchupPlayerPoint.points).desc())
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "rank": i + 1,
            "player_name": row.player_name,
            "position": row.position or "—",
            "team": row.team or "—",
            "total_points": round(row.total_points, 2),
            "games_played": row.games_played,
            "avg_points": round(row.avg_points, 2),
            "season": row.season,
            "owner_name": row.owner_name or row.owner_username,
            "team_name": row.team_name,
        }
        for i, row in enumerate(rows)
    ]


async def _get_career_records(db, match_type, roster_type, position, limit):
    """Top player career totals."""
    # Subquery to count distinct owners per player
    owner_count_sub = (
        select(
            MatchupPlayerPoint.player_id,
            func.count(func.distinct(User.id)).label("owner_count"),
        )
        .join(Roster, MatchupPlayerPoint.roster_id == Roster.id)
        .join(User, Roster.user_id == User.id)
        .join(Matchup, MatchupPlayerPoint.matchup_id == Matchup.id)
        .where(Matchup.match_type == match_type)
    )
    owner_count_sub = _apply_filters(owner_count_sub, roster_type, position=None)
    owner_count_sub = owner_count_sub.group_by(MatchupPlayerPoint.player_id).subquery()

    query = (
        select(
            MatchupPlayerPoint.player_id,
            func.coalesce(Player.full_name, MatchupPlayerPoint.player_id).label("player_name"),
            Player.position,
            Player.team,
            func.sum(MatchupPlayerPoint.points).label("total_points"),
            func.count(MatchupPlayerPoint.id).label("games_played"),
            func.avg(MatchupPlayerPoint.points).label("avg_points"),
            func.count(func.distinct(Season.year)).label("seasons_played"),
            owner_count_sub.c.owner_count,
            func.min(User.display_name).label("owner_name"),
            func.min(User.username).label("owner_username"),
        )
        .join(Matchup, MatchupPlayerPoint.matchup_id == Matchup.id)
        .join(Roster, MatchupPlayerPoint.roster_id == Roster.id)
        .outerjoin(Player, MatchupPlayerPoint.player_id == Player.id)
        .join(User, Roster.user_id == User.id)
        .join(Season, Matchup.season_id == Season.id)
        .outerjoin(owner_count_sub, MatchupPlayerPoint.player_id == owner_count_sub.c.player_id)
        .where(Matchup.match_type == match_type)
    )

    query = _apply_filters(query, roster_type, position)
    query = (
        query
        .group_by(
            MatchupPlayerPoint.player_id, Player.full_name, Player.position, Player.team,
            owner_count_sub.c.owner_count,
        )
        .order_by(func.sum(MatchupPlayerPoint.points).desc())
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "rank": i + 1,
            "player_name": row.player_name,
            "position": row.position or "—",
            "team": row.team or "—",
            "total_points": round(row.total_points, 2),
            "games_played": row.games_played,
            "avg_points": round(row.avg_points, 2),
            "seasons_played": row.seasons_played,
            "owner_name": row.owner_name or row.owner_username if (row.owner_count or 0) <= 1 else "(multiple)",
            "team_name": None,
        }
        for i, row in enumerate(rows)
    ]


def _apply_filters(query, roster_type, position):
    """Apply starter/bench and position filters to a query."""
    if roster_type == "starter":
        query = query.where(MatchupPlayerPoint.is_starter == True)
    elif roster_type == "bench":
        query = query.where(MatchupPlayerPoint.is_starter == False)

    if position:
        query = query.where(Player.position == position)

    return query
