from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models import Season, Roster, User, League
from typing import List, Dict, Any

router = APIRouter()


@router.get("/standings")
async def get_current_standings(db: AsyncSession = Depends(get_db)):
    """Get current season standings."""
    # Get the most recent season
    result = await db.execute(
        select(Season).order_by(desc(Season.year)).limit(1)
    )
    season = result.scalar_one_or_none()

    if not season:
        raise HTTPException(status_code=404, detail="No season data found")

    return await _get_season_standings(db, season.year)


@router.get("/standings/{season_year}")
async def get_historical_standings(season_year: int, db: AsyncSession = Depends(get_db)):
    """Get historical standings for a specific season."""
    return await _get_season_standings(db, season_year)


async def _get_season_standings(db: AsyncSession, year: int) -> Dict[str, Any]:
    """Helper function to get standings for a specific season."""
    # Get season
    result = await db.execute(
        select(Season).where(Season.year == year)
    )
    season = result.scalar_one_or_none()

    if not season:
        raise HTTPException(status_code=404, detail=f"Season {year} not found")

    # Get league metadata for division names
    result = await db.execute(
        select(League).where(League.id == season.league_id)
    )
    league = result.scalar_one_or_none()
    league_metadata = (league.league_metadata if league else None) or {}

    # Build division names from league metadata
    division_names = {}
    for i in range(1, (season.num_divisions or 2) + 1):
        division_names[str(i)] = league_metadata.get(f"division_{i}", f"Division {i}")

    # Get all rosters for this season with user info
    result = await db.execute(
        select(Roster, User)
        .join(User, Roster.user_id == User.id)
        .where(Roster.season_id == season.id)
        .order_by(desc(Roster.wins), desc(Roster.points_for))
    )
    rosters_with_users = result.all()

    # Build standings data
    standings = []
    for roster, user in rosters_with_users:
        standings.append({
            "roster_id": roster.roster_id,
            "user_id": user.id,
            "username": user.display_name or user.username,
            "display_name": user.display_name or user.username,
            "team_name": roster.team_name,
            "division": roster.division,
            "wins": roster.wins,
            "losses": roster.losses,
            "ties": roster.ties,
            "points_for": roster.points_for,
            "points_against": roster.points_against,
            "win_percentage": round(roster.wins / max(roster.wins + roster.losses + roster.ties, 1), 3)
        })

    return {
        "season": year,
        "num_divisions": season.num_divisions,
        "division_names": division_names,
        "total_teams": len(standings),
        "standings": standings
    }
