from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from app.database import get_db
from app.models import User, Roster, Season, Matchup
from typing import Dict, Any, List

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

    # Sort by regular season wins descending
    owner_stats.sort(key=lambda x: x["total_wins"], reverse=True)

    return {
        "total_owners": len(owner_stats),
        "owners": owner_stats
    }


@router.get("/owners/{user_id}")
async def get_owner_details(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get detailed statistics for a specific owner."""
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

    # Build season-by-season breakdown with categorized stats
    seasons = []
    for roster, season in rosters_with_seasons:
        cats = await _calculate_categorized_stats(db, [roster.id])
        reg = cats["regular"]
        seasons.append({
            "year": season.year,
            "team_name": roster.team_name,
            "division": roster.division,
            "regular_season": cats["regular"],
            "playoff": cats["playoff"],
            "consolation": cats["consolation"],
            # Legacy flat fields (regular season)
            "wins": reg["wins"],
            "losses": reg["losses"],
            "ties": reg["ties"],
            "points_for": reg["points_for"],
            "points_against": reg["points_against"],
            "win_percentage": reg["win_percentage"],
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


async def _calculate_categorized_stats(db: AsyncSession, roster_ids: List[int]) -> Dict[str, Dict]:
    """Calculate W-L-T and points by match_type from matchup records."""
    result = await db.execute(
        select(Matchup).where(
            or_(
                Matchup.home_roster_id.in_(roster_ids),
                Matchup.away_roster_id.in_(roster_ids)
            )
        )
    )
    matchups = result.scalars().all()

    categories = {
        "regular": {"wins": 0, "losses": 0, "ties": 0, "points_for": 0.0, "points_against": 0.0},
        "playoff": {"wins": 0, "losses": 0, "ties": 0, "points_for": 0.0, "points_against": 0.0},
        "consolation": {"wins": 0, "losses": 0, "ties": 0, "points_for": 0.0, "points_against": 0.0},
    }

    for m in matchups:
        cat = m.match_type or "regular"
        if cat not in categories:
            cat = "regular"

        is_home = m.home_roster_id in roster_ids
        my_points = m.home_points if is_home else m.away_points
        opp_points = m.away_points if is_home else m.home_points

        categories[cat]["points_for"] += my_points or 0.0
        categories[cat]["points_against"] += opp_points or 0.0

        if m.winner_roster_id is None:
            categories[cat]["ties"] += 1
        elif m.winner_roster_id in roster_ids:
            categories[cat]["wins"] += 1
        else:
            categories[cat]["losses"] += 1

    # Add win_percentage to each category
    for cat in categories.values():
        total = cat["wins"] + cat["losses"] + cat["ties"]
        cat["win_percentage"] = round(cat["wins"] / max(total, 1), 3)
        cat["points_for"] = round(cat["points_for"], 2)
        cat["points_against"] = round(cat["points_against"], 2)

    return categories


async def _calculate_owner_stats(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    """Calculate owner career statistics across all categories."""
    result = await db.execute(
        select(Roster).where(Roster.user_id == user_id)
    )
    rosters = result.scalars().all()

    empty_category = {
        "wins": 0, "losses": 0, "ties": 0,
        "points_for": 0.0, "points_against": 0.0,
        "win_percentage": 0.0
    }

    if not rosters:
        return {
            "seasons_played": 0,
            "regular_season": dict(empty_category),
            "playoff": dict(empty_category),
            "consolation": dict(empty_category),
            "total_wins": 0,
            "total_losses": 0,
            "total_ties": 0,
            "total_points_for": 0,
            "total_points_against": 0,
            "career_win_percentage": 0.0,
            "championships": 0,
            "playoff_appearances": 0,
        }

    roster_ids = [r.id for r in rosters]
    cats = await _calculate_categorized_stats(db, roster_ids)
    reg = cats["regular"]

    return {
        "seasons_played": len(rosters),
        "regular_season": cats["regular"],
        "playoff": cats["playoff"],
        "consolation": cats["consolation"],
        # Legacy flat fields (regular season)
        "total_wins": reg["wins"],
        "total_losses": reg["losses"],
        "total_ties": reg["ties"],
        "total_points_for": reg["points_for"],
        "total_points_against": reg["points_against"],
        "career_win_percentage": reg["win_percentage"],
        "championships": 0,
        "playoff_appearances": 0,
    }
