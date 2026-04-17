from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from statistics import median

from app.database import get_db
from app.models import Roster, Season, User, Player
from app.api.routes.power_rankings import (
    _calculate_player_stats,
    _calculate_player_power_score,
    _calculate_avg_roster_age,
    _fetch_ktc_values,
)

router = APIRouter()

POSITION_ORDER = {"QB": 0, "RB": 1, "WR": 2, "TE": 3, "K": 4, "DEF": 5}


def _classify_team(avg_age: float, total_score: float, median_score: float) -> str:
    """Classify a team based on roster age curve and overall strength.

    2x2 matrix:
      Young (age <= 25.5) + Strong (score >= median) -> Future Contender
      Veteran (age > 25.5) + Strong                  -> Win Now
      Young                + Weak (score < median)   -> Rebuilding
      Veteran              + Weak                    -> Retooling
    """
    young = avg_age <= 25.5
    strong = total_score >= median_score
    if young and strong:
        return "Future Contender"
    elif not young and strong:
        return "Win Now"
    elif young and not strong:
        return "Rebuilding"
    else:
        return "Retooling"


@router.get("/roster-analysis")
async def get_roster_analysis(db: AsyncSession = Depends(get_db)):
    """Get full roster analysis for all teams in the current season."""

    # Get the latest season
    result = await db.execute(select(Season).order_by(desc(Season.year)).limit(1))
    season = result.scalar_one_or_none()
    if not season:
        return {"season": None, "teams": []}

    # Get all rosters with their owners
    result = await db.execute(
        select(Roster, User)
        .join(User, Roster.user_id == User.id)
        .where(Roster.season_id == season.id)
        .order_by(User.display_name)
    )
    roster_rows = result.all()

    if not roster_rows:
        return {"season": season.year, "teams": []}

    # Collect all player IDs across every roster for a single bulk fetch
    all_player_ids = set()
    for roster, _ in roster_rows:
        if roster.players:
            all_player_ids.update(roster.players)

    # Bulk-fetch all players
    players_dict: dict = {}
    if all_player_ids:
        result = await db.execute(select(Player).where(Player.id.in_(all_player_ids)))
        for player in result.scalars().all():
            players_dict[player.id] = player

    # Bulk-calculate avg points per game and KTC values for every player
    player_stats = await _calculate_player_stats(list(all_player_ids), db)
    ktc_values = await _fetch_ktc_values(list(all_player_ids), db)

    # Build per-team data
    teams = []
    for roster, user in roster_rows:
        player_ids = roster.players or []
        roster_players = [players_dict.get(pid) for pid in player_ids]
        roster_players = [p for p in roster_players if p is not None]

        player_data = []
        total_score = 0.0
        pos_scores: dict[str, float] = {}
        pos_counts: dict[str, int] = {}

        for player in roster_players:
            avg_pts = player_stats.get(player.id, 0.0)
            ktc_value = ktc_values.get(player.id, 0.0)
            score_obj = await _calculate_player_power_score(player, avg_pts, db, ktc_value=ktc_value)
            total_score += score_obj.power_score

            pos = player.position or "OTH"
            pos_scores[pos] = round(pos_scores.get(pos, 0.0) + score_obj.power_score, 1)
            pos_counts[pos] = pos_counts.get(pos, 0) + 1

            player_data.append({
                "player_id": player.id,
                "player_name": score_obj.player_name,
                "position": player.position,
                "team": player.team,
                "age": player.age,
                "power_score": score_obj.power_score,
            })

        # Sort players by position order, then power score descending
        player_data.sort(key=lambda p: (
            POSITION_ORDER.get(p["position"] or "OTH", 99),
            -p["power_score"],
        ))

        avg_age = _calculate_avg_roster_age(roster, players_dict)

        teams.append({
            "roster_id": roster.roster_id,
            "owner_name": user.display_name or user.username,
            "team_name": roster.team_name,
            "avatar": user.avatar,
            "avg_age": round(avg_age, 1),
            "total_roster_score": round(total_score, 1),
            "player_count": len(player_data),
            "positional_scores": pos_scores,
            "positional_counts": pos_counts,
            "players": player_data,
        })

    # Classify each team relative to the median roster score
    all_scores = [t["total_roster_score"] for t in teams]
    med_score = median(all_scores) if all_scores else 0.0

    for team in teams:
        team["classification"] = _classify_team(
            team["avg_age"], team["total_roster_score"], med_score
        )

    # Sort by total roster score descending
    teams.sort(key=lambda t: t["total_roster_score"], reverse=True)

    return {"season": season.year, "teams": teams}
