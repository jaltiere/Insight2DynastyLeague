from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models import SeasonAward, Season, User, League, Roster
from typing import List, Dict, Any

router = APIRouter()


@router.get("/league-history")
async def get_all_history(db: AsyncSession = Depends(get_db)):
    """Get all season winners (champion, division winners, consolation)."""
    # Get all seasons ordered by year descending
    result = await db.execute(
        select(Season).order_by(desc(Season.year))
    )
    seasons = result.scalars().all()

    history = []
    for season in seasons:
        season_data = await _get_season_awards(db, season.year)
        if season_data:  # Only include seasons with award data
            history.append(season_data)

    return {
        "total_seasons": len(history),
        "seasons": history
    }


@router.get("/league-history/{year}")
async def get_season_history(year: int, db: AsyncSession = Depends(get_db)):
    """Get specific season winners."""
    season_data = await _get_season_awards(db, year)

    if not season_data:
        raise HTTPException(status_code=404, detail=f"No history found for season {year}")

    return season_data


async def _get_season_awards(db: AsyncSession, year: int) -> Dict[str, Any]:
    """Helper function to get all awards for a specific season."""
    # Get season
    result = await db.execute(
        select(Season).where(Season.year == year)
    )
    season = result.scalar_one_or_none()

    if not season:
        return None

    # Get league metadata for division names
    result = await db.execute(
        select(League).where(League.id == season.league_id)
    )
    league = result.scalar_one_or_none()
    league_metadata = (league.league_metadata if league else None) or {}

    division_names = {}
    for i in range(1, (season.num_divisions or 2) + 1):
        division_names[str(i)] = league_metadata.get(f"division_{i}", f"Division {i}")

    # Build roster_id -> team_name mapping for this season
    result = await db.execute(
        select(Roster).where(Roster.season_id == season.id)
    )
    rosters = result.scalars().all()
    user_team_names = {r.user_id: r.team_name for r in rosters if r.team_name}

    # Get all awards for this season
    result = await db.execute(
        select(SeasonAward, User)
        .join(User, SeasonAward.user_id == User.id)
        .where(SeasonAward.season_id == season.id)
    )
    awards_with_users = result.all()

    # Group awards by type
    champion = None
    division_winners = []
    consolation_winner = None

    for award, user in awards_with_users:
        award_data = {
            "user_id": user.id,
            "username": user.display_name or user.username,
            "team_name": user_team_names.get(user.id),
        }

        if award.award_type == "champion":
            champion = award_data
        elif award.award_type == "division_winner":
            # Map generic "Division 1" to actual name
            div_num = award.award_detail.replace("Division ", "") if award.award_detail else None
            division_winners.append({
                **award_data,
                "division": division_names.get(div_num, award.award_detail),
            })
        elif award.award_type == "consolation":
            consolation_winner = award_data

    # Only show seasons where a champion has been determined
    if not champion:
        return None

    return {
        "year": year,
        "num_divisions": season.num_divisions,
        "division_names": division_names,
        "champion": champion,
        "division_winners": division_winners,
        "consolation_winner": consolation_winner
    }
