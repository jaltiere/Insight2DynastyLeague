from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from collections import defaultdict
from app.database import get_db
from app.api.deps import get_league_id
from app.models import User, Roster, Matchup, Season, SeasonAward
from app.utils import matchup_played
from typing import List, Dict, Any

router = APIRouter()


def _owner_label(user) -> str:
    return user.display_name or user.username or "Unknown"


def _compute_streaks(games: List[Dict], result_char: str) -> tuple:
    """Return (max_streak, start, end) for a given result char ('W' or 'L')."""
    max_streak = 0
    cur = 0
    cur_start = None
    best_start = None
    best_end = None

    for game in games:
        if game["result"] == result_char:
            if cur == 0:
                cur_start = (game["season"], game["week"])
            cur += 1
            cur_end = (game["season"], game["week"])
            if cur > max_streak:
                max_streak = cur
                best_start = cur_start
                best_end = cur_end
        else:
            cur = 0
            cur_start = None

    return max_streak, best_start, best_end


@router.get("/team-records")
async def get_team_records(
    league_id: str = Depends(get_league_id),
    db: AsyncSession = Depends(get_db),
):
    """All-time team-level records: scoring, season totals, margins, streaks, unluckiest."""

    # Load users active in this league
    result = await db.execute(
        select(User)
        .join(Roster, User.id == Roster.user_id)
        .join(Season, Roster.season_id == Season.id)
        .where(Season.group_id == league_id)
        .distinct()
    )
    users = result.scalars().all()
    user_map = {u.id: u for u in users}

    # Load rosters scoped to this league
    result = await db.execute(
        select(Roster)
        .join(Season, Roster.season_id == Season.id)
        .where(Season.group_id == league_id)
    )
    rosters = result.scalars().all()
    roster_to_user = {r.id: r.user_id for r in rosters}
    roster_map = {r.id: r for r in rosters}

    # Load all matchups scoped to this league
    result = await db.execute(
        select(Matchup, Season)
        .join(Season, Matchup.season_id == Season.id)
        .where(Season.group_id == league_id)
        .order_by(Season.year, Matchup.week)
    )
    matchups_with_seasons = result.all()

    # Load champions per season for this league
    result = await db.execute(
        select(SeasonAward, Season)
        .join(Season, SeasonAward.season_id == Season.id)
        .where(SeasonAward.award_type == "champion", Season.group_id == league_id)
    )
    champion_rows = result.all()
    champion_user_per_season: Dict[int, str] = {season.id: award.user_id for award, season in champion_rows}

    # ------------------------------------------------------------------ #
    # 1. Per-game scoring records
    # ------------------------------------------------------------------ #
    game_scores: List[Dict] = []

    for matchup, season in matchups_with_seasons:
        for roster_id, points in [
            (matchup.home_roster_id, matchup.home_points),
            (matchup.away_roster_id, matchup.away_points),
        ]:
            if points is None:
                continue
            user_id = roster_to_user.get(roster_id)
            user = user_map.get(user_id) if user_id else None
            roster = roster_map.get(roster_id)
            if not user:
                continue
            won = matchup.winner_roster_id == roster_id
            game_scores.append({
                "points": round(points, 2),
                "owner_name": _owner_label(user),
                "team_name": roster.team_name if roster else None,
                "season": season.year,
                "week": matchup.week,
                "match_type": matchup.match_type or "regular",
                "won": won,
            })

    valid_game_scores = [s for s in game_scores if s["points"] > 0]
    highest_game = [
        {"rank": i + 1, **s}
        for i, s in enumerate(sorted(valid_game_scores, key=lambda x: x["points"], reverse=True)[:10])
    ]
    lowest_game = [
        {"rank": i + 1, **s}
        for i, s in enumerate(
            sorted(
                [s for s in valid_game_scores if s["match_type"] == "regular"],
                key=lambda x: x["points"],
            )[:10]
        )
    ]

    # ------------------------------------------------------------------ #
    # 2. Season totals (from Roster aggregate columns)
    # ------------------------------------------------------------------ #
    result = await db.execute(
        select(Roster, Season, User)
        .join(Season, Roster.season_id == Season.id)
        .join(User, Roster.user_id == User.id)
        .where(Roster.user_id.isnot(None), Season.group_id == league_id)
    )
    roster_season_rows = result.all()

    season_scores: List[Dict] = []
    for roster, season, user in roster_season_rows:
        pf = round(float(roster.points_for or 0), 2)
        if pf == 0:
            continue
        season_scores.append({
            "points_for": pf,
            "owner_name": _owner_label(user),
            "team_name": roster.team_name,
            "season": season.year,
            "wins": roster.wins or 0,
            "losses": roster.losses or 0,
            "ties": roster.ties or 0,
        })

    highest_season = [
        {"rank": i + 1, **s}
        for i, s in enumerate(sorted(season_scores, key=lambda x: x["points_for"], reverse=True)[:10])
    ]
    lowest_season = [
        {"rank": i + 1, **s}
        for i, s in enumerate(sorted(season_scores, key=lambda x: x["points_for"])[:10])
    ]

    # ------------------------------------------------------------------ #
    # 3. Margins
    # ------------------------------------------------------------------ #
    margins: List[Dict] = []

    for matchup, season in matchups_with_seasons:
        home_pts = matchup.home_points or 0
        away_pts = matchup.away_points or 0
        if home_pts == away_pts:
            continue

        if home_pts > away_pts:
            winner_rid, loser_rid = matchup.home_roster_id, matchup.away_roster_id
            winner_pts, loser_pts = home_pts, away_pts
        else:
            winner_rid, loser_rid = matchup.away_roster_id, matchup.home_roster_id
            winner_pts, loser_pts = away_pts, home_pts

        winner_uid = roster_to_user.get(winner_rid)
        loser_uid = roster_to_user.get(loser_rid)
        winner_user = user_map.get(winner_uid) if winner_uid else None
        loser_user = user_map.get(loser_uid) if loser_uid else None
        if not winner_user or not loser_user:
            continue

        margins.append({
            "margin": round(winner_pts - loser_pts, 2),
            "winner_name": _owner_label(winner_user),
            "winner_points": round(winner_pts, 2),
            "loser_name": _owner_label(loser_user),
            "loser_points": round(loser_pts, 2),
            "season": season.year,
            "week": matchup.week,
            "match_type": matchup.match_type or "regular",
        })

    biggest_blowout = [
        {"rank": i + 1, **m}
        for i, m in enumerate(sorted(margins, key=lambda x: x["margin"], reverse=True)[:10])
    ]
    closest_game = [
        {"rank": i + 1, **m}
        for i, m in enumerate(sorted(margins, key=lambda x: x["margin"])[:10])
    ]

    # ------------------------------------------------------------------ #
    # 4. Streaks (regular season and playoff, computed separately)
    # ------------------------------------------------------------------ #
    # Build per-user game lists split by match type
    reg_games: Dict[str, List] = defaultdict(list)
    playoff_games: Dict[str, List] = defaultdict(list)

    for matchup, season in matchups_with_seasons:
        # Skip unplayed matchups (offseason-synced future weeks are 0-0);
        # their NULL winner would otherwise register as a phantom tie streak
        if not matchup_played(matchup.home_points, matchup.away_points):
            continue

        mtype = matchup.match_type or "regular"
        for roster_id in (matchup.home_roster_id, matchup.away_roster_id):
            user_id = roster_to_user.get(roster_id)
            if not user_id:
                continue
            if matchup.winner_roster_id is None:
                res = "T"
            elif matchup.winner_roster_id == roster_id:
                res = "W"
            else:
                res = "L"
            entry = {"season": season.year, "week": matchup.week, "result": res}
            if mtype == "regular":
                reg_games[user_id].append(entry)
            elif mtype == "playoff":
                playoff_games[user_id].append(entry)

    def build_streak_records(games_by_user: Dict[str, List], result_char: str) -> List[Dict]:
        records = []
        for user_id, games in games_by_user.items():
            user = user_map.get(user_id)
            if not user:
                continue
            streak, start, end = _compute_streaks(games, result_char)
            if streak > 0 and start and end:
                records.append({
                    "streak": streak,
                    "owner_name": _owner_label(user),
                    "start_season": start[0],
                    "start_week": start[1],
                    "end_season": end[0],
                    "end_week": end[1],
                })
        return [
            {"rank": i + 1, **r}
            for i, r in enumerate(sorted(records, key=lambda x: x["streak"], reverse=True)[:10])
        ]

    reg_win_streaks = build_streak_records(reg_games, "W")
    reg_loss_streaks = build_streak_records(reg_games, "L")
    playoff_win_streaks = build_streak_records(playoff_games, "W")
    playoff_loss_streaks = build_streak_records(playoff_games, "L")

    # ------------------------------------------------------------------ #
    # 5. Unluckiest: most PF in a season without winning the title
    # ------------------------------------------------------------------ #
    unlucky_seasons: List[Dict] = []
    for roster, season, user in roster_season_rows:
        pf = round(float(roster.points_for or 0), 2)
        if pf == 0:
            continue
        is_champion = champion_user_per_season.get(season.id) == user.id
        if not is_champion:
            unlucky_seasons.append({
                "points_for": pf,
                "owner_name": _owner_label(user),
                "team_name": roster.team_name,
                "season": season.year,
                "wins": roster.wins or 0,
                "losses": roster.losses or 0,
                "ties": roster.ties or 0,
            })

    most_points_no_title = [
        {"rank": i + 1, **s}
        for i, s in enumerate(sorted(unlucky_seasons, key=lambda x: x["points_for"], reverse=True)[:10])
    ]

    # Highest-scoring losses (regular season)
    losing_scores = [s for s in valid_game_scores if not s["won"] and s["match_type"] == "regular"]
    most_points_in_loss = [
        {"rank": i + 1, **s}
        for i, s in enumerate(sorted(losing_scores, key=lambda x: x["points"], reverse=True)[:10])
    ]

    return {
        "scoring": {
            "highest_game": highest_game,
            "lowest_game": lowest_game,
        },
        "season": {
            "highest_season": highest_season,
            "lowest_season": lowest_season,
        },
        "margins": {
            "biggest_blowout": biggest_blowout,
            "closest_game": closest_game,
        },
        "streaks": {
            "reg_win": reg_win_streaks,
            "reg_loss": reg_loss_streaks,
            "playoff_win": playoff_win_streaks,
            "playoff_loss": playoff_loss_streaks,
        },
        "unluckiest": {
            "most_points_no_title": most_points_no_title,
            "most_points_in_loss": most_points_in_loss,
        },
    }
