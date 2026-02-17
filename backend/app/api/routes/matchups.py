from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from statistics import median as calc_median
from collections import defaultdict
from app.database import get_db
from app.models import User, Roster, Matchup, Season
from typing import List, Dict, Any, Optional

router = APIRouter()


@router.get("/matchups/head-to-head-matrix")
async def get_head_to_head_matrix(
    match_type: Optional[str] = Query(None, pattern="^(regular|playoff|consolation)$"),
    db: AsyncSession = Depends(get_db),
):
    """Get head-to-head matrix for all active owners with median records."""
    # 1. Fetch all active users
    result = await db.execute(
        select(User).where(User.is_active == True)
    )
    users = result.scalars().all()
    user_map = {u.id: u for u in users}
    active_user_ids = set(user_map.keys())

    # 2. Fetch all rosters, build roster_id -> user_id mapping
    result = await db.execute(select(Roster))
    rosters = result.scalars().all()
    roster_to_user = {r.id: r.user_id for r in rosters}

    # 3. Fetch matchups (with optional match_type filter)
    query = select(Matchup)
    if match_type:
        query = query.where(Matchup.match_type == match_type)
    result = await db.execute(query)
    matchups = result.scalars().all()

    # 4. Build H2H matrix
    matrix: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"wins": 0, "losses": 0, "ties": 0})
    )

    for m in matchups:
        home_user = roster_to_user.get(m.home_roster_id)
        away_user = roster_to_user.get(m.away_roster_id)
        if not home_user or not away_user or home_user == away_user:
            continue
        if home_user not in active_user_ids or away_user not in active_user_ids:
            continue

        home_pts = m.home_points or 0
        away_pts = m.away_points or 0

        if home_pts > away_pts:
            matrix[home_user][away_user]["wins"] += 1
            matrix[away_user][home_user]["losses"] += 1
        elif away_pts > home_pts:
            matrix[away_user][home_user]["wins"] += 1
            matrix[home_user][away_user]["losses"] += 1
        else:
            matrix[home_user][away_user]["ties"] += 1
            matrix[away_user][home_user]["ties"] += 1

    # 5. Build median records
    week_scores: Dict[tuple, list] = defaultdict(list)
    for m in matchups:
        home_user = roster_to_user.get(m.home_roster_id)
        away_user = roster_to_user.get(m.away_roster_id)
        if home_user and home_user in active_user_ids:
            week_scores[(m.season_id, m.week)].append((home_user, m.home_points or 0))
        if away_user and away_user in active_user_ids:
            week_scores[(m.season_id, m.week)].append((away_user, m.away_points or 0))

    median_records: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"wins": 0, "losses": 0, "ties": 0}
    )
    for scores in week_scores.values():
        if len(scores) < 2:
            continue
        all_points = [s[1] for s in scores]
        week_median = calc_median(all_points)
        for user_id, pts in scores:
            if pts > week_median:
                median_records[user_id]["wins"] += 1
            elif pts < week_median:
                median_records[user_id]["losses"] += 1
            else:
                median_records[user_id]["ties"] += 1

    # 6. Build response
    owners_list = [
        {
            "user_id": u.id,
            "display_name": u.display_name or u.username,
            "username": u.username,
            "avatar": u.avatar,
        }
        for u in sorted(users, key=lambda u: (u.display_name or u.username or "").lower())
    ]

    return {
        "owners": owners_list,
        "matrix": {uid: dict(opponents) for uid, opponents in matrix.items()},
        "median_records": dict(median_records),
    }


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
