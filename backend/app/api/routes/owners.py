from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from statistics import median as calc_median
from collections import defaultdict
from app.database import get_db
from app.models import User, Roster, Season, Matchup, League, SeasonAward
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
        trophies = await _count_trophies(db, user.id)
        owner_stats.append({
            "user_id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "avatar": user.avatar,
            "trophies": trophies,
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

    # Build a cache of division names per season
    division_names_cache: Dict[int, Dict[str, str]] = {}
    for roster, season in rosters_with_seasons:
        if season.id not in division_names_cache:
            league_result = await db.execute(
                select(League).where(League.id == season.league_id)
            )
            league = league_result.scalar_one_or_none()
            league_metadata = (league.league_metadata if league else None) or {}
            div_names = {}
            for i in range(1, (season.num_divisions or 2) + 1):
                div_names[str(i)] = league_metadata.get(f"division_{i}", f"Division {i}")
            division_names_cache[season.id] = div_names

    # Build season-by-season breakdown with categorized stats
    seasons = []
    for roster, season in rosters_with_seasons:
        cats = await _calculate_categorized_stats(db, [roster.id])
        reg = cats["regular"]
        median = await _calculate_median_records_for_roster(db, season.id, roster.id)
        div_names = division_names_cache.get(season.id, {})
        division_name = div_names.get(str(roster.division), f"Division {roster.division}")
        seasons.append({
            "year": season.year,
            "team_name": roster.team_name,
            "division": roster.division,
            "division_name": division_name,
            "regular_season": cats["regular"],
            "playoff": cats["playoff"],
            "consolation": cats["consolation"],
            "median_wins": median["wins"],
            "median_losses": median["losses"],
            "median_ties": median["ties"],
            # Legacy flat fields (regular season)
            "wins": reg["wins"],
            "losses": reg["losses"],
            "ties": reg["ties"],
            "points_for": reg["points_for"],
            "points_against": reg["points_against"],
            "win_percentage": reg["win_percentage"],
        })

    # Calculate career stats and trophies
    stats = await _calculate_owner_stats(db, user_id)
    trophies = await _count_trophies(db, user_id)

    return {
        "user_id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "avatar": user.avatar,
        "career_stats": stats,
        "trophies": trophies,
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


async def _count_trophies(db: AsyncSession, user_id: str) -> Dict[str, int]:
    """Count trophy awards for an owner: champion, division_winner, most_points."""
    result = await db.execute(
        select(SeasonAward).where(SeasonAward.user_id == user_id)
    )
    awards = result.scalars().all()

    counts = {"champion": 0, "division_winner": 0, "most_points": 0, "consolation": 0}
    for award in awards:
        if award.award_type in counts:
            counts[award.award_type] += 1
    return counts


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


async def _calculate_median_records_for_roster(
    db: AsyncSession, season_id: int, roster_id: int
) -> Dict[str, int]:
    """Calculate a single roster's record against the weekly median for a season."""
    result = await db.execute(
        select(Matchup).where(
            Matchup.season_id == season_id,
            Matchup.match_type == "regular"
        )
    )
    matchups = result.scalars().all()

    if not matchups:
        return {"wins": 0, "losses": 0, "ties": 0}

    # Group scores by week
    week_scores: Dict[int, list] = defaultdict(list)
    for m in matchups:
        week_scores[m.week].append((m.home_roster_id, m.home_points or 0))
        week_scores[m.week].append((m.away_roster_id, m.away_points or 0))

    median_record = {"wins": 0, "losses": 0, "ties": 0}
    for scores in week_scores.values():
        if len(scores) < 2:
            continue
        all_points = [s[1] for s in scores]
        week_median = calc_median(all_points)
        for rid, pts in scores:
            if rid == roster_id:
                if pts > week_median:
                    median_record["wins"] += 1
                elif pts < week_median:
                    median_record["losses"] += 1
                else:
                    median_record["ties"] += 1

    return median_record
