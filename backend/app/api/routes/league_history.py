from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models import SeasonAward, Season, User
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
            "display_name": user.display_name or user.username,
            "team_name": award.team_name
        }

        if award.award_type == "champion":
            champion = award_data
        elif award.award_type == "division_winner":
            division_winners.append({
                **award_data,
                "division": award.division
            })
        elif award.award_type == "consolation":
            consolation_winner = award_data

    # If no awards exist, return None
    if not champion and not division_winners and not consolation_winner:
        return None

    return {
        "year": year,
        "num_divisions": season.num_divisions,
        "champion": champion,
        "division_winners": division_winners,
        "consolation_winner": consolation_winner
    }
