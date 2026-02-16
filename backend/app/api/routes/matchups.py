from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from app.database import get_db
from app.models import User, Roster, Matchup, Season
from typing import List, Dict, Any

router = APIRouter()


@router.get("/matchups/head-to-head/{user_id_1}/{user_id_2}")
async def get_head_to_head(user_id_1: str, user_id_2: str, db: AsyncSession = Depends(get_db)):
    """Get head-to-head history between two owners."""
    # Validate both users exist
    result = await db.execute(
        select(User).where(User.id.in_([user_id_1, user_id_2]))
    )
    users = result.scalars().all()

    if len(users) != 2:
        raise HTTPException(status_code=404, detail="One or both owners not found")

    user1 = next(u for u in users if u.id == user_id_1)
    user2 = next(u for u in users if u.id == user_id_2)

    # Get all rosters for both users
    result = await db.execute(
        select(Roster).where(Roster.user_id.in_([user_id_1, user_id_2]))
    )
    rosters = result.scalars().all()

    # Map roster IDs to user IDs
    roster_to_user = {r.id: r.user_id for r in rosters}
    user1_roster_ids = [r.id for r in rosters if r.user_id == user_id_1]
    user2_roster_ids = [r.id for r in rosters if r.user_id == user_id_2]

    # Find all matchups between these two users
    result = await db.execute(
        select(Matchup, Season)
        .join(Season, Matchup.season_id == Season.id)
        .where(
            or_(
                and_(
                    Matchup.home_roster_id.in_(user1_roster_ids),
                    Matchup.away_roster_id.in_(user2_roster_ids)
                ),
                and_(
                    Matchup.home_roster_id.in_(user2_roster_ids),
                    Matchup.away_roster_id.in_(user1_roster_ids)
                )
            )
        )
        .order_by(Season.year, Matchup.week)
    )
    matchups_with_seasons = result.all()

    # Calculate H2H record
    user1_wins = 0
    user2_wins = 0
    ties = 0
    user1_total_points = 0
    user2_total_points = 0

    games = []
    for matchup, season in matchups_with_seasons:
        # Determine which user was home and which was away
        home_is_user1 = matchup.home_roster_id in user1_roster_ids

        user1_points = matchup.home_points if home_is_user1 else matchup.away_points
        user2_points = matchup.away_points if home_is_user1 else matchup.home_points

        user1_total_points += user1_points
        user2_total_points += user2_points

        if user1_points > user2_points:
            user1_wins += 1
            winner = user_id_1
        elif user2_points > user1_points:
            user2_wins += 1
            winner = user_id_2
        else:
            ties += 1
            winner = None

        games.append({
            "season": season.year,
            "week": matchup.week,
            "user1_points": user1_points,
            "user2_points": user2_points,
            "winner": winner
        })

    total_games = len(games)
    avg_user1_points = round(user1_total_points / max(total_games, 1), 2)
    avg_user2_points = round(user2_total_points / max(total_games, 1), 2)

    return {
        "user1": {
            "user_id": user1.id,
            "display_name": user1.display_name or user1.username,
            "wins": user1_wins,
            "losses": user2_wins,
            "ties": ties,
            "total_points": user1_total_points,
            "avg_points": avg_user1_points
        },
        "user2": {
            "user_id": user2.id,
            "display_name": user2.display_name or user2.username,
            "wins": user2_wins,
            "losses": user1_wins,
            "ties": ties,
            "total_points": user2_total_points,
            "avg_points": avg_user2_points
        },
        "total_games": total_games,
        "games": games
    }
