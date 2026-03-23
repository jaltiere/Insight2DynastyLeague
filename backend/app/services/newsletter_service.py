"""Newsletter data aggregation service."""
from statistics import median as calc_median
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Any

from app.models import (
    Season, Roster, User, Matchup, MatchupPlayerPoint,
    Player, MatchupRecap,
)


async def get_newsletter_data(
    db: AsyncSession,
    week: int,
    season_year: int | None = None,
) -> dict[str, Any]:
    """Aggregate all data needed to render the weekly newsletter."""
    season = await _get_season(db, season_year)

    rosters_map = await _build_rosters_map(db, season.id)

    week_matchups = await _get_week_matchups(db, season.id, week)
    score_data = _calc_scores(week_matchups, rosters_map)

    top_players = await _get_top_players_week(db, season.id, week)
    season_leaders = await _get_season_leaders(db, season.id, week)
    rookie_report = await _get_rookie_report(db, season.id, week, season.year)
    playoff_picture = _build_playoff_picture(rosters_map)
    potential_points = await _get_potential_points(db, season.id, rosters_map)
    recaps, upcoming = await _get_recaps(db, season.id, week)

    is_regular_season = week <= (season.regular_season_weeks or 14)
    standings = _build_standings(rosters_map)

    return {
        "week": week,
        "season": season.year,
        "is_regular_season": is_regular_season,
        "high_score": score_data["high_score"],
        "low_score": score_data["low_score"],
        "league_median": score_data["league_median"],
        "top_players": top_players,
        "season_leaders": season_leaders,
        "rookie_report": rookie_report,
        "standings": standings,
        "playoff_picture": playoff_picture,
        "potential_points": potential_points,
        "recaps": recaps,
        "upcoming_matchups": upcoming,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_season(db: AsyncSession, season_year: int | None) -> Season:
    from fastapi import HTTPException
    from sqlalchemy import desc as _desc

    if season_year:
        result = await db.execute(select(Season).where(Season.year == season_year))
    else:
        result = await db.execute(select(Season).order_by(_desc(Season.year)).limit(1))

    season = result.scalar_one_or_none()
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")
    return season


async def _build_rosters_map(db: AsyncSession, season_id: int) -> dict[int, dict]:
    """Build a map of db roster_id -> {roster_id, user_id, display_name, team_name, wins, losses,
    points_for, division, max_potential_points} for the season."""
    result = await db.execute(
        select(Roster, User)
        .join(User, Roster.user_id == User.id)
        .where(Roster.season_id == season_id)
    )
    rows = result.all()

    # Calculate max potential per roster from matchups
    mp_result = await db.execute(
        select(Matchup).where(
            Matchup.season_id == season_id,
            Matchup.match_type == "regular",
        )
    )
    matchups = mp_result.scalars().all()

    max_potential: dict[int, float] = defaultdict(float)
    for m in matchups:
        if m.home_max_potential_points is not None:
            max_potential[m.home_roster_id] += m.home_max_potential_points
        if m.away_max_potential_points is not None:
            max_potential[m.away_roster_id] += m.away_max_potential_points

    roster_map = {}
    for roster, user in rows:
        roster_map[roster.id] = {
            "db_id": roster.id,
            "roster_id": roster.roster_id,
            "user_id": user.id,
            "display_name": user.display_name or user.username,
            "team_name": roster.team_name or user.display_name or user.username,
            "wins": roster.wins or 0,
            "losses": roster.losses or 0,
            "ties": roster.ties or 0,
            "points_for": roster.points_for or 0.0,
            "division": roster.division or 1,
            "max_potential_points": round(max_potential.get(roster.id, 0.0), 2),
        }
    return roster_map


async def _get_week_matchups(db: AsyncSession, season_id: int, week: int) -> list[Matchup]:
    result = await db.execute(
        select(Matchup).where(
            Matchup.season_id == season_id,
            Matchup.week == week,
        )
    )
    return result.scalars().all()


def _calc_scores(
    matchups: list[Matchup],
    rosters_map: dict[int, dict],
) -> dict[str, Any]:
    """Derive high score, low score, and median data from week matchups."""
    scores: list[dict] = []
    for m in matchups:
        for roster_db_id, pts in [
            (m.home_roster_id, m.home_points),
            (m.away_roster_id, m.away_points),
        ]:
            if pts is None:
                continue
            r = rosters_map.get(roster_db_id, {})
            scores.append({
                "display_name": r.get("display_name", "Unknown"),
                "team_name": r.get("team_name", "Unknown"),
                "points": round(pts, 2),
            })

    if not scores:
        empty = {"display_name": "—", "team_name": "—", "points": 0.0}
        return {
            "high_score": empty,
            "low_score": empty,
            "league_median": {"median": 0.0, "teams": []},
        }

    scores.sort(key=lambda x: x["points"], reverse=True)
    week_median = round(calc_median(s["points"] for s in scores), 2)

    teams_with_median = [
        {**s, "beat_median": s["points"] > week_median}
        for s in scores
    ]

    return {
        "high_score": scores[0],
        "low_score": scores[-1],
        "league_median": {
            "median": week_median,
            "teams": teams_with_median,
        },
    }


async def _get_top_players_week(
    db: AsyncSession, season_id: int, week: int
) -> dict[str, dict | None]:
    """Top scorer per position for the given week (starters only)."""
    query = (
        select(
            MatchupPlayerPoint.player_id,
            MatchupPlayerPoint.points,
            func.coalesce(Player.full_name, MatchupPlayerPoint.player_id).label("player_name"),
            Player.position,
            Player.team,
            User.display_name.label("owner_name"),
            Roster.team_name,
        )
        .join(Matchup, MatchupPlayerPoint.matchup_id == Matchup.id)
        .join(Roster, MatchupPlayerPoint.roster_id == Roster.id)
        .join(User, Roster.user_id == User.id)
        .outerjoin(Player, MatchupPlayerPoint.player_id == Player.id)
        .where(
            Matchup.season_id == season_id,
            Matchup.week == week,
            MatchupPlayerPoint.is_starter == True,  # noqa: E712
            Player.position.in_(["QB", "RB", "WR", "TE", "DEF", "K"]),
        )
        .order_by(MatchupPlayerPoint.points.desc())
    )

    result = await db.execute(query)
    rows = result.all()

    top: dict[str, dict | None] = {pos: None for pos in ["QB", "RB", "WR", "TE", "DEF", "K"]}
    for row in rows:
        pos = row.position
        if pos in top and top[pos] is None:
            top[pos] = {
                "player_name": row.player_name,
                "points": round(row.points, 2),
                "team": row.team or "—",
                "owner": row.owner_name,
                "team_name": row.team_name,
            }
    return top


async def _get_season_leaders(
    db: AsyncSession, season_id: int, week: int
) -> dict[str, list[dict]]:
    """Top 12 cumulative season scorers per skill position (through given week)."""
    SKILL_POSITIONS = ["QB", "RB", "WR", "TE"]

    query = (
        select(
            MatchupPlayerPoint.player_id,
            func.sum(MatchupPlayerPoint.points).label("total_points"),
            func.coalesce(Player.full_name, MatchupPlayerPoint.player_id).label("player_name"),
            Player.position,
        )
        .join(Matchup, MatchupPlayerPoint.matchup_id == Matchup.id)
        .outerjoin(Player, MatchupPlayerPoint.player_id == Player.id)
        .where(
            Matchup.season_id == season_id,
            Matchup.week <= week,
            Player.position.in_(SKILL_POSITIONS),
        )
        .group_by(
            MatchupPlayerPoint.player_id,
            Player.full_name,
            Player.position,
        )
        .order_by(desc("total_points"))
    )

    result = await db.execute(query)
    rows = result.all()

    # Look up most-recent owner for each player
    owner_map = await _get_player_owners(db, season_id, week, [r.player_id for r in rows])

    leaders: dict[str, list[dict]] = {pos: [] for pos in SKILL_POSITIONS}
    position_rank: dict[str, int] = defaultdict(int)

    for row in rows:
        pos = row.position
        if pos not in leaders:
            continue
        position_rank[pos] += 1
        if len(leaders[pos]) >= 12:
            continue
        owner = owner_map.get(row.player_id, "—")
        leaders[pos].append({
            "rank": position_rank[pos],
            "player_name": row.player_name,
            "total_points": round(row.total_points, 2),
            "owner": owner,
        })

    return leaders


async def _get_rookie_report(
    db: AsyncSession, season_id: int, week: int, season_year: int
) -> dict[str, list[dict]]:
    """Top rookie scorers per skill position with overall positional rank."""
    SKILL_POSITIONS = ["QB", "RB", "WR", "TE"]

    # Get ALL season totals per player (for ranking purposes)
    all_query = (
        select(
            MatchupPlayerPoint.player_id,
            func.sum(MatchupPlayerPoint.points).label("total_points"),
            func.coalesce(Player.full_name, MatchupPlayerPoint.player_id).label("player_name"),
            Player.position,
            Player.years_exp,
            Player.rookie_year,
        )
        .join(Matchup, MatchupPlayerPoint.matchup_id == Matchup.id)
        .outerjoin(Player, MatchupPlayerPoint.player_id == Player.id)
        .where(
            Matchup.season_id == season_id,
            Matchup.week <= week,
            Player.position.in_(SKILL_POSITIONS),
        )
        .group_by(
            MatchupPlayerPoint.player_id,
            Player.full_name,
            Player.position,
            Player.years_exp,
            Player.rookie_year,
        )
        .order_by(desc("total_points"))
    )

    result = await db.execute(all_query)
    all_rows = result.all()

    # Build overall position rank
    pos_rank: dict[str, int] = defaultdict(int)
    overall_rank: dict[str, int] = {}
    for row in all_rows:
        if row.position:
            pos_rank[row.position] += 1
            overall_rank[row.player_id] = pos_rank[row.position]

    # Filter to rookies with points (years_exp == 0 or rookie_year == season_year)
    rookies = [
        r for r in all_rows
        if (r.years_exp == 0 or r.rookie_year == season_year) and (r.total_points or 0) > 0
    ]

    rookie_player_ids = [r.player_id for r in rookies]
    owner_map = await _get_player_owners(db, season_id, week, rookie_player_ids)

    report: dict[str, list[dict]] = {pos: [] for pos in SKILL_POSITIONS}
    rookie_pos_rank: dict[str, int] = defaultdict(int)

    for row in rookies:
        pos = row.position
        if pos not in report:
            continue
        rookie_pos_rank[pos] += 1
        owner = owner_map.get(row.player_id, "—")
        overall = overall_rank.get(row.player_id, 0)
        report[pos].append({
            "rank": rookie_pos_rank[pos],
            "player_name": row.player_name,
            "total_points": round(row.total_points, 2),
            "overall_rank": overall,
            "position_label": f"{pos}{overall}",
            "owner": owner,
        })

    return report


async def _get_player_owners(
    db: AsyncSession,
    season_id: int,
    week: int,
    player_ids: list[str],
) -> dict[str, str]:
    """For each player_id, find the owner display_name from their most recent
    entry at or before `week` in the season."""
    if not player_ids:
        return {}

    # Get the max week each player appeared and the corresponding roster owner
    subq = (
        select(
            MatchupPlayerPoint.player_id,
            func.max(Matchup.week).label("last_week"),
        )
        .join(Matchup, MatchupPlayerPoint.matchup_id == Matchup.id)
        .where(
            Matchup.season_id == season_id,
            Matchup.week <= week,
            MatchupPlayerPoint.player_id.in_(player_ids),
        )
        .group_by(MatchupPlayerPoint.player_id)
        .subquery()
    )

    query = (
        select(
            MatchupPlayerPoint.player_id,
            User.display_name.label("owner_name"),
        )
        .join(Matchup, MatchupPlayerPoint.matchup_id == Matchup.id)
        .join(Roster, MatchupPlayerPoint.roster_id == Roster.id)
        .join(User, Roster.user_id == User.id)
        .join(
            subq,
            (MatchupPlayerPoint.player_id == subq.c.player_id)
            & (Matchup.week == subq.c.last_week),
        )
        .where(
            Matchup.season_id == season_id,
        )
    )

    result = await db.execute(query)
    # Deduplicate in Python (one player per roster per week, so rarely needed)
    owner_map: dict[str, str] = {}
    for row in result.all():
        if row.player_id not in owner_map:
            owner_map[row.player_id] = row.owner_name
    return owner_map


def _build_standings(rosters_map: dict[int, dict]) -> list[dict]:
    """Return all teams sorted by wins desc, then points_for desc."""
    teams = sorted(
        rosters_map.values(),
        key=lambda t: (-t["wins"], -t["points_for"]),
    )
    return [
        {
            "rank": i + 1,
            "display_name": t["display_name"],
            "team_name": t["team_name"],
            "wins": t["wins"],
            "losses": t["losses"],
            "ties": t["ties"],
            "points_for": t["points_for"],
            "division": t["division"],
        }
        for i, t in enumerate(teams)
    ]


def _build_playoff_picture(rosters_map: dict[int, dict]) -> dict[str, list[dict]]:
    """Determine current playoff seeding from the rosters map."""
    teams = list(rosters_map.values())

    def sort_key(t):
        return (-t["wins"], -t["points_for"])

    # Find division leaders (best record per division)
    by_division: dict[int, list] = defaultdict(list)
    for t in teams:
        by_division[t["division"]].append(t)

    division_leaders = []
    for div_teams in by_division.values():
        div_teams.sort(key=sort_key)
        division_leaders.append(div_teams[0])

    # Sort division leaders so best record is #1
    division_leaders.sort(key=sort_key)

    leader_ids = {t["db_id"] for t in division_leaders}
    remaining = sorted(
        [t for t in teams if t["db_id"] not in leader_ids],
        key=sort_key,
    )

    playoff_teams = division_leaders + remaining[:4]
    consolation_teams = remaining[4:]

    def _entry(seed, t):
        return {
            "seed": seed,
            "display_name": t["display_name"],
            "team_name": t["team_name"],
            "wins": t["wins"],
            "losses": t["losses"],
            "ties": t["ties"],
        }

    return {
        "playoff": [_entry(i + 1, t) for i, t in enumerate(playoff_teams)],
        "consolation": [_entry(i + 1, t) for i, t in enumerate(consolation_teams)],
    }


async def _get_potential_points(
    db: AsyncSession, season_id: int, rosters_map: dict[int, dict]
) -> list[dict]:
    """Rank teams by max potential points (regular season only)."""
    teams = sorted(
        rosters_map.values(),
        key=lambda t: -t["max_potential_points"],
    )
    return [
        {
            "rank": i + 1,
            "display_name": t["display_name"],
            "team_name": t["team_name"],
            "max_potential_points": t["max_potential_points"],
        }
        for i, t in enumerate(teams)
    ]


async def _get_recaps(
    db: AsyncSession, season_id: int, week: int
) -> tuple[list[dict], list[dict]]:
    """Fetch matchup recaps for the given week."""
    result = await db.execute(
        select(MatchupRecap, Matchup)
        .join(Matchup, MatchupRecap.matchup_id == Matchup.id)
        .where(
            MatchupRecap.season_id == season_id,
            MatchupRecap.week == week,
        )
    )
    rows = result.all()

    recaps = []
    upcoming = []
    for recap, matchup in rows:
        entry = {
            "matchup_id": matchup.id,
            "week": recap.week,
            "recap_type": recap.recap_type,
            "recap_text": recap.recap_text,
            "predictions_text": recap.predictions_text,
            "recap_metadata": recap.recap_metadata,
            "home_points": matchup.home_points,
            "away_points": matchup.away_points,
        }
        if recap.recap_type == "prediction":
            upcoming.append(entry)
        else:
            recaps.append(entry)

    return recaps, upcoming
