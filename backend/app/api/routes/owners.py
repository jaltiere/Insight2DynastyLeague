from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models import User, Roster, Season
from typing import Dict, Any

router = APIRouter()


@router.get("/owners")
async def get_all_owners(db: AsyncSession = Depends(get_db)):
    """Get all owners with their career statistics."""
    result = await db.execute(select(User))
    users = result.scalars().all()

    owner_stats = []
    for user in users:
        stats = await _calculate_owner_stats(db, user.id)
        owner_stats.append({
            "user_id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "avatar": user.avatar,
            **stats
        })

    # Sort by total wins descending
    owner_stats.sort(key=lambda x: x["total_wins"], reverse=True)

    return {
        "total_owners": len(owner_stats),
        "owners": owner_stats
    }


@router.get("/owners/{user_id}")
async def get_owner_details(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get detailed statistics for a specific owner."""
    # Get user
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Owner not found")

    # Get all rosters for this owner
    result = await db.execute(
        select(Roster, Season)
        .join(Season, Roster.season_id == Season.id)
        .where(Roster.user_id == user_id)
        .order_by(desc(Season.year))
    )
    rosters_with_seasons = result.all()

    # Build season-by-season breakdown
    seasons = []
    for roster, season in rosters_with_seasons:
        seasons.append({
            "year": season.year,
            "team_name": roster.team_name,
            "division": roster.division,
            "wins": roster.wins,
            "losses": roster.losses,
            "ties": roster.ties,
            "points_for": roster.points_for,
            "points_against": roster.points_against,
            "win_percentage": round(roster.wins / max(roster.wins + roster.losses + roster.ties, 1), 3)
        })

    # Calculate career stats
    stats = await _calculate_owner_stats(db, user_id)

    return {
        "user_id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "avatar": user.avatar,
        "career_stats": stats,
        "seasons": seasons
    }


async def _calculate_owner_stats(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    """Helper function to calculate owner career statistics."""
    # Get all rosters for this owner
    result = await db.execute(
        select(Roster).where(Roster.user_id == user_id)
    )
    rosters = result.scalars().all()

    if not rosters:
        return {
            "seasons_played": 0,
            "total_wins": 0,
            "total_losses": 0,
            "total_ties": 0,
            "total_points_for": 0,
            "total_points_against": 0,
            "career_win_percentage": 0.0,
            "championships": 0,
            "playoff_appearances": 0
        }

    total_wins = sum(r.wins for r in rosters)
    total_losses = sum(r.losses for r in rosters)
    total_ties = sum(r.ties for r in rosters)
    total_points_for = sum(r.points_for for r in rosters)
    total_points_against = sum(r.points_against for r in rosters)

    total_games = total_wins + total_losses + total_ties
    win_percentage = round(total_wins / max(total_games, 1), 3)

    # TODO: Calculate championships and playoff appearances
    # This will require querying SeasonAward table once populated
    championships = 0
    playoff_appearances = 0

    return {
        "seasons_played": len(rosters),
        "total_wins": total_wins,
        "total_losses": total_losses,
        "total_ties": total_ties,
        "total_points_for": total_points_for,
        "total_points_against": total_points_against,
        "career_win_percentage": win_percentage,
        "championships": championships,
        "playoff_appearances": playoff_appearances
    }
