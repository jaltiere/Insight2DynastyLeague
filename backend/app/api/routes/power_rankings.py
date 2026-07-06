from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from statistics import stdev as calc_stdev
from typing import List, Dict, Any, Tuple, Optional
from app.database import get_db
from app.api.deps import get_league_id, verify_cron_secret
from app.models import Season, Roster, User, Player, Matchup, SeasonAward, MatchupPlayerPoint
from app.models.player_value import PlayerValue
from app.models.power_ranking_snapshot import PowerRankingSnapshot
from app.schemas.power_rankings import (
    PowerRankingsResponse,
    PowerRankingTeam,
    RosterBreakdown,
    PlayerPowerScore,
    PowerRankingTrendsResponse,
    PowerRankingTrendTeam,
    PowerRankingSnapshotWeek,
)

router = APIRouter()


@router.get("/power-rankings", response_model=PowerRankingsResponse)
async def get_current_power_rankings(
    league_id: str = Depends(get_league_id),
    db: AsyncSession = Depends(get_db),
):
    """Get power rankings for current season, with rank change vs. last snapshot."""
    result = await db.execute(
        select(Season).where(Season.group_id == league_id).order_by(desc(Season.year)).limit(1)
    )
    season = result.scalar_one_or_none()

    if not season:
        raise HTTPException(status_code=404, detail="No season data found")

    return await _get_season_power_rankings(db, season.year, league_id)


@router.get("/power-rankings/{season_year}", response_model=PowerRankingsResponse)
async def get_historical_power_rankings(
    season_year: int,
    league_id: str = Depends(get_league_id),
    db: AsyncSession = Depends(get_db),
):
    """Get power rankings for a specific season, with rank change vs. last snapshot."""
    return await _get_season_power_rankings(db, season_year, league_id)


@router.get(
    "/power-rankings/{season_year}/roster/{roster_id}",
    response_model=RosterBreakdown,
)
async def get_roster_breakdown(
    season_year: int,
    roster_id: int,
    league_id: str = Depends(get_league_id),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed roster breakdown with individual player power scores."""
    result = await db.execute(
        select(Season).where(Season.year == season_year, Season.group_id == league_id)
    )
    season = result.scalar_one_or_none()

    if not season:
        raise HTTPException(status_code=404, detail=f"Season {season_year} not found")

    result = await db.execute(
        select(Roster, User)
        .join(User, Roster.user_id == User.id)
        .where(Roster.season_id == season.id, Roster.roster_id == roster_id)
    )
    roster_user = result.first()

    if not roster_user:
        raise HTTPException(
            status_code=404,
            detail=f"Roster {roster_id} not found for season {season_year}",
        )

    roster, user = roster_user

    player_ids = roster.players or []
    if not player_ids:
        return RosterBreakdown(
            roster_id=roster.roster_id,
            team_name=roster.team_name,
            owner_name=user.display_name or user.username,
            total_roster_score=0.0,
            avg_roster_age=0.0,
            players=[],
        )

    result = await db.execute(select(Player).where(Player.id.in_(player_ids)))
    players = list(result.scalars().all())

    player_stats = await _calculate_player_stats(player_ids, db, league_id)
    ktc_values = await _fetch_ktc_values(player_ids, db)
    position_averages = _calculate_position_averages(players, player_stats)

    player_scores = []
    total_age = 0
    age_count = 0

    for player in players:
        avg_points = player_stats.get(player.id, 0.0)
        ktc_value = ktc_values.get(player.id, 0.0)
        pos_avg = position_averages.get(player.position or "OTH", 0.0)
        power_score_data = await _calculate_player_power_score(
            player, avg_points, db, ktc_value=ktc_value, position_avg=pos_avg
        )
        player_scores.append(power_score_data)

        if player.age:
            total_age += player.age
            age_count += 1

    avg_roster_age = total_age / age_count if age_count > 0 else 0.0
    total_roster_score = sum(p.power_score for p in player_scores)

    return RosterBreakdown(
        roster_id=roster.roster_id,
        team_name=roster.team_name,
        owner_name=user.display_name or user.username,
        total_roster_score=round(total_roster_score, 2),
        avg_roster_age=round(avg_roster_age, 1),
        players=player_scores,
    )


@router.get("/power-rankings/{season_year}/trends", response_model=PowerRankingTrendsResponse)
async def get_power_rankings_trends(
    season_year: int,
    league_id: str = Depends(get_league_id),
    db: AsyncSession = Depends(get_db),
):
    """Return weekly rank snapshots for all teams for the season line chart."""
    # Non-fatal: if table doesn't exist yet (migration pending), return empty
    try:
        result = await db.execute(
            select(PowerRankingSnapshot)
            .where(
                PowerRankingSnapshot.season_year == season_year,
                PowerRankingSnapshot.group_id == league_id,
            )
            .order_by(PowerRankingSnapshot.week, PowerRankingSnapshot.rank)
        )
        snapshots = result.scalars().all()
    except Exception:
        return PowerRankingTrendsResponse(season=season_year, weeks=[], teams=[])

    if not snapshots:
        return PowerRankingTrendsResponse(season=season_year, weeks=[], teams=[])

    # Collect all weeks and build roster_id -> week -> snapshot mapping
    weeks = sorted(set(s.week for s in snapshots))
    roster_snapshots: Dict[int, List[PowerRankingSnapshot]] = {}
    for s in snapshots:
        roster_snapshots.setdefault(s.roster_id, []).append(s)

    # Get current display names/team names from most recent rosters
    result = await db.execute(
        select(Season).where(Season.year == season_year, Season.group_id == league_id)
    )
    season = result.scalar_one_or_none()

    roster_names: Dict[int, Tuple[str, Optional[str]]] = {}
    if season:
        result = await db.execute(
            select(Roster, User)
            .join(User, Roster.user_id == User.id)
            .where(Roster.season_id == season.id)
        )
        for roster, user in result.all():
            roster_names[roster.roster_id] = (
                user.display_name or user.username,
                roster.team_name,
            )

    # Get current ranks from latest snapshot week
    latest_week = max(weeks)
    current_ranks: Dict[int, int] = {
        s.roster_id: s.rank
        for s in snapshots
        if s.week == latest_week
    }

    teams = []
    for roster_id, snaps in sorted(roster_snapshots.items()):
        display_name, team_name = roster_names.get(roster_id, (f"Roster {roster_id}", None))
        ranks_by_week = [
            PowerRankingSnapshotWeek(week=s.week, rank=s.rank, total_score=s.total_score)
            for s in sorted(snaps, key=lambda x: x.week)
        ]
        teams.append(
            PowerRankingTrendTeam(
                roster_id=roster_id,
                display_name=display_name,
                team_name=team_name,
                current_rank=current_ranks.get(roster_id, 0),
                ranks_by_week=ranks_by_week,
            )
        )

    # Sort teams by current rank
    teams.sort(key=lambda t: t.current_rank)

    return PowerRankingTrendsResponse(season=season_year, weeks=weeks, teams=teams)


@router.post("/power-rankings/snapshot", dependencies=[Depends(verify_cron_secret)])
async def save_power_rankings_snapshot(
    season_year: int,
    week: int,
    league_id: str = Depends(get_league_id),
    db: AsyncSession = Depends(get_db),
):
    """Save a power rankings snapshot for the given week. Requires CRON_SECRET auth."""
    saved = await _save_snapshot(db, season_year, week, league_id=league_id)
    await db.commit()
    return {"status": "ok", "week": week, "season_year": season_year, "teams_saved": saved}


# ================== HELPER FUNCTIONS ==================


async def _get_season_power_rankings(
    db: AsyncSession, year: int, league_id: str
) -> PowerRankingsResponse:
    """Helper function to calculate power rankings for a specific season."""
    result = await db.execute(
        select(Season).where(Season.year == year, Season.group_id == league_id)
    )
    season = result.scalar_one_or_none()

    if not season:
        raise HTTPException(status_code=404, detail=f"Season {year} not found")

    result = await db.execute(
        select(Roster, User)
        .join(User, Roster.user_id == User.id)
        .where(Roster.season_id == season.id)
    )
    rosters_with_users = result.all()

    if not rosters_with_users:
        raise HTTPException(
            status_code=404, detail=f"No rosters found for season {year}"
        )

    all_player_ids = set()
    for roster, _ in rosters_with_users:
        if roster.players:
            all_player_ids.update(roster.players)

    players_dict = {}
    if all_player_ids:
        result = await db.execute(select(Player).where(Player.id.in_(all_player_ids)))
        players = result.scalars().all()
        players_dict = {player.id: player for player in players}

    # Load most-recent prior snapshot for rank-change calculation.
    # Non-fatal: if the table doesn't exist yet (migration not run), skip trend data.
    try:
        prior_ranks = await _get_prior_snapshot_ranks(db, year, league_id)
    except Exception:
        prior_ranks = {}

    rankings = []
    all_rosters = [roster for roster, _ in rosters_with_users]

    for roster, user in rosters_with_users:
        current_score = await _calculate_current_season_score(
            roster, all_rosters, season, db, league_id
        )
        roster_score = await _calculate_roster_value_score(roster, players_dict, db, league_id)
        historical_score = await _calculate_historical_score(roster, db)
        total_score = current_score + roster_score + historical_score
        avg_age = _calculate_avg_roster_age(roster, players_dict)

        rankings.append(
            PowerRankingTeam(
                rank=0,
                roster_id=roster.roster_id,
                user_id=user.id,
                username=user.username,
                display_name=user.display_name or user.username,
                team_name=roster.team_name,
                total_score=round(total_score, 2),
                current_season_score=round(current_score, 2),
                roster_value_score=round(roster_score, 2),
                historical_score=round(historical_score, 2),
                wins=roster.wins,
                losses=roster.losses,
                ties=roster.ties,
                points_for=roster.points_for,
                avg_roster_age=round(avg_age, 1),
            )
        )

    rankings.sort(key=lambda x: x.total_score, reverse=True)
    for idx, ranking in enumerate(rankings):
        ranking.rank = idx + 1
        prev = prior_ranks.get(ranking.roster_id)
        if prev is not None:
            ranking.previous_rank = prev
            ranking.rank_change = prev - ranking.rank  # positive = moved up

    return PowerRankingsResponse(season=year, rankings=rankings)


async def _get_prior_snapshot_ranks(
    db: AsyncSession, season_year: int, league_id: str
) -> Dict[int, int]:
    """Return {roster_id: rank} from the most recent snapshot week for this season."""
    # Find the latest week that has snapshots
    result = await db.execute(
        select(func.max(PowerRankingSnapshot.week))
        .where(
            PowerRankingSnapshot.season_year == season_year,
            PowerRankingSnapshot.group_id == league_id,
        )
    )
    latest_week = result.scalar_one_or_none()
    if latest_week is None:
        return {}

    result = await db.execute(
        select(PowerRankingSnapshot)
        .where(
            PowerRankingSnapshot.season_year == season_year,
            PowerRankingSnapshot.week == latest_week,
            PowerRankingSnapshot.group_id == league_id,
        )
    )
    snapshots = result.scalars().all()
    return {s.roster_id: s.rank for s in snapshots}


async def _save_snapshot(db: AsyncSession, season_year: int, week: int, league_id: str | None = None) -> int:
    """
    Calculate current power rankings and upsert a snapshot row for each team.
    Returns the number of teams saved.
    """
    rankings_response = await _get_season_power_rankings(db, season_year, league_id=league_id)

    for team in rankings_response.rankings:
        # Try to find an existing row for this (group, season_year, week, roster_id)
        result = await db.execute(
            select(PowerRankingSnapshot).where(
                PowerRankingSnapshot.group_id == league_id,
                PowerRankingSnapshot.season_year == season_year,
                PowerRankingSnapshot.week == week,
                PowerRankingSnapshot.roster_id == team.roster_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.rank = team.rank
            existing.total_score = team.total_score
            existing.current_season_score = team.current_season_score
            existing.roster_value_score = team.roster_value_score
            existing.historical_score = team.historical_score
        else:
            db.add(
                PowerRankingSnapshot(
                    group_id=league_id,
                    season_year=season_year,
                    week=week,
                    roster_id=team.roster_id,
                    rank=team.rank,
                    total_score=team.total_score,
                    current_season_score=team.current_season_score,
                    roster_value_score=team.roster_value_score,
                    historical_score=team.historical_score,
                )
            )

    return len(rankings_response.rankings)


async def _calculate_current_season_score(
    roster: Roster, all_rosters: List[Roster], season: Season, db: AsyncSession,
    league_id: str,
) -> float:
    """Calculate current season performance score (40 points max) using rolling 15-game averages."""
    score = 0.0

    # Scope to this league group: owners can be in multiple configured
    # leagues, and their games elsewhere must not bleed into these rankings.
    result = await db.execute(
        select(Roster.id)
        .join(Season, Roster.season_id == Season.id)
        .where(Roster.user_id == roster.user_id, Season.group_id == league_id)
    )
    user_roster_ids = [row[0] for row in result]

    if not user_roster_ids:
        return 0.0

    result = await db.execute(
        select(Matchup, Season.year)
        .join(Season, Matchup.season_id == Season.id)
        .where(
            (Matchup.home_roster_id.in_(user_roster_ids))
            | (Matchup.away_roster_id.in_(user_roster_ids)),
            # Unplayed matchups (offseason-synced future weeks) are 0-0 and
            # must not consume rolling-window slots or zero the recent form
            (Matchup.home_points > 0) | (Matchup.away_points > 0),
        )
        .order_by(desc(Season.year), desc(Matchup.week))
        .limit(15)
    )
    seen_ids = set()
    recent_matchups = []
    for matchup, year in result:
        if matchup.id not in seen_ids:
            seen_ids.add(matchup.id)
            recent_matchups.append(matchup)

    if not recent_matchups:
        return 0.0

    wins = 0
    total_points = 0.0
    opponent_points = 0.0

    for matchup in recent_matchups:
        is_home = matchup.home_roster_id in user_roster_ids
        is_away = matchup.away_roster_id in user_roster_ids

        if matchup.winner_roster_id in user_roster_ids:
            wins += 1

        if is_home:
            total_points += matchup.home_points or 0.0
            opponent_points += matchup.away_points or 0.0
        elif is_away:
            total_points += matchup.away_points or 0.0
            opponent_points += matchup.home_points or 0.0

    games_played = len(recent_matchups)

    # 1. Win Percentage (15 pts)
    if games_played > 0:
        win_pct = wins / games_played
        score += win_pct * 15

    # 2. Points For Percentile (12 pts)
    all_roster_avgs = []
    for r in all_rosters:
        result = await db.execute(
            select(Roster.id)
            .join(Season, Roster.season_id == Season.id)
            .where(Roster.user_id == r.user_id, Season.group_id == league_id)
        )
        r_roster_ids = [row[0] for row in result]

        if not r_roster_ids:
            continue

        result = await db.execute(
            select(Matchup, Season.year)
            .join(Season, Matchup.season_id == Season.id)
            .where(
                (Matchup.home_roster_id.in_(r_roster_ids))
                | (Matchup.away_roster_id.in_(r_roster_ids)),
                (Matchup.home_points > 0) | (Matchup.away_points > 0),
            )
            .order_by(desc(Season.year), desc(Matchup.week))
            .limit(15)
        )
        seen_ids = set()
        r_matchups = []
        for matchup, year in result:
            if matchup.id not in seen_ids:
                seen_ids.add(matchup.id)
                r_matchups.append(matchup)

        if r_matchups:
            r_total_points = 0.0
            for m in r_matchups:
                if m.home_roster_id in r_roster_ids:
                    r_total_points += m.home_points or 0.0
                elif m.away_roster_id in r_roster_ids:
                    r_total_points += m.away_points or 0.0
            r_avg = r_total_points / len(r_matchups)
            all_roster_avgs.append(r_avg)

    if all_roster_avgs:
        roster_avg = total_points / games_played
        teams_below = sum(1 for avg in all_roster_avgs if avg < roster_avg)
        percentile = teams_below / (len(all_roster_avgs) - 1) if len(all_roster_avgs) > 1 else 0.5
        score += percentile * 12

    # 3. Point Differential (8 pts)
    if games_played > 0:
        avg_points = total_points / games_played
        avg_opponent_points = opponent_points / games_played
        point_diff = avg_points - avg_opponent_points
        normalized_diff = max(0, min(8, (point_diff + 20) / 5))
        score += normalized_diff

    # 4. Recent Form - last 3 weeks (5 pts)
    recent_3_matchups = recent_matchups[:3]
    recent_wins = sum(1 for m in recent_3_matchups if m.winner_roster_id in user_roster_ids)
    if len(recent_3_matchups) > 0:
        recent_form_pct = recent_wins / len(recent_3_matchups)
        score += recent_form_pct * 5

    return score


async def _calculate_roster_value_score(
    roster: Roster, players_dict: Dict[str, Player], db: AsyncSession,
    league_id: Optional[str] = None,
) -> float:
    """Calculate roster value score (40 points max)."""
    score = 0.0

    if not roster.players:
        return 0.0

    roster_players = [players_dict.get(pid) for pid in roster.players]
    roster_players = [p for p in roster_players if p is not None]

    if not roster_players:
        return 0.0

    player_ids = [p.id for p in roster_players]
    player_stats = await _calculate_player_stats(player_ids, db, league_id)

    # 1. Average Roster Age (15 pts)
    avg_age = _calculate_avg_roster_age(roster, players_dict)
    age_score = _age_to_score(avg_age)
    score += age_score * 15

    # 2. Player Production Value (15 pts)
    total_production = 0.0
    for player in roster_players:
        avg_points = player_stats.get(player.id, 0.0)
        player_production = min(1.0, avg_points / 20.0)
        total_production += player_production
    score += min(15, total_production)

    # 3. Roster Depth (10 pts)
    startable_count = sum(1 for p in roster_players if _is_startable(p))
    score += min(10, startable_count * 0.5)

    return score


async def _calculate_historical_score(roster: Roster, db: AsyncSession) -> float:
    """Calculate historical performance score (20 points max)."""
    score = 0.0

    result = await db.execute(
        select(SeasonAward).where(SeasonAward.user_id == roster.user_id)
    )
    awards = result.scalars().all()

    championships = sum(1 for award in awards if award.award_type == "champion")
    playoff_appearances = len([a for a in awards if a.award_type in ["champion", "division_winner"]])

    score += min(8, championships * 5)
    score += min(8, playoff_appearances * 2.67)
    score += 2  # consistency baseline

    return score


async def _calculate_recent_form(
    roster: Roster, season: Season, db: AsyncSession
) -> float:
    """Calculate recent form score based on last 3 weeks (5 points max)."""
    if not season.regular_season_weeks or season.regular_season_weeks < 3:
        return 0.0

    weeks_to_check = range(
        max(1, season.regular_season_weeks - 2), season.regular_season_weeks + 1
    )

    result = await db.execute(
        select(Matchup)
        .where(
            Matchup.season_id == season.id,
            Matchup.week.in_(weeks_to_check),
            Matchup.match_type == "regular",
        )
        .where(
            (Matchup.home_roster_id == roster.id)
            | (Matchup.away_roster_id == roster.id)
        )
    )
    recent_matchups = result.scalars().all()

    if not recent_matchups:
        return 0.0

    wins = 0
    for matchup in recent_matchups:
        if matchup.winner_roster_id == roster.id:
            wins += 1

    win_pct = wins / len(recent_matchups)
    return win_pct * 5


def _calculate_avg_roster_age(roster: Roster, players_dict: Dict[str, Player]) -> float:
    """Calculate average age of players on roster."""
    if not roster.players:
        return 0.0

    ages = []
    for player_id in roster.players:
        player = players_dict.get(player_id)
        if player and player.age:
            ages.append(player.age)
        elif player and player.years_exp:
            estimated_age = 22 + player.years_exp
            ages.append(estimated_age)

    return sum(ages) / len(ages) if ages else 27.0


def _age_to_score(avg_age: float) -> float:
    """Convert average roster age to 0-1 score (1 = best for dynasty)."""
    if avg_age <= 25:
        return 1.0
    elif avg_age <= 28:
        return 1.0 - (avg_age - 25) * 0.1
    else:
        return max(0.3, 0.7 - (avg_age - 28) * 0.1)


def _is_elite_player(player: Player) -> bool:
    """Check if a player is considered 'elite' for dynasty purposes."""
    if not player.age or player.age >= 28:
        return False
    if player.status not in ["Active", None]:
        return False
    return player.position in ["QB", "RB", "WR", "TE"]


def _is_startable(player: Player) -> bool:
    """Check if a player is considered startable."""
    if player.age and player.age >= 30:
        return False
    if player.status not in ["Active", None]:
        return False
    return player.position in ["QB", "RB", "WR", "TE"]


async def _fetch_ktc_values(player_ids: List[str], db: AsyncSession) -> Dict[str, float]:
    """Return {player_id: ktc_value} for the given player IDs."""
    if not player_ids:
        return {}
    result = await db.execute(
        select(PlayerValue.player_id, PlayerValue.value).where(
            PlayerValue.player_id.in_(player_ids)
        )
    )
    return {row.player_id: float(row.value) for row in result if row.player_id}


async def _calculate_player_stats(
    player_ids: List[str], db: AsyncSession, league_id: Optional[str] = None,
    limit: int = 15,
) -> Dict[str, float]:
    """Average points per game over each player's most recent `limit` games.

    Scoped to one league group when league_id is given — the same player's
    point rows exist per league, and mixing them misstates league PPG.
    """
    if not player_ids:
        return {}

    query = (
        select(
            MatchupPlayerPoint.player_id,
            MatchupPlayerPoint.points,
            Season.year,
            Matchup.week,
        )
        .join(Matchup, MatchupPlayerPoint.matchup_id == Matchup.id)
        .join(Season, Matchup.season_id == Season.id)
        .where(MatchupPlayerPoint.player_id.in_(player_ids))
    )
    if league_id:
        query = query.where(Season.group_id == league_id)
    result = await db.execute(query)

    rows_by_player: Dict[str, list] = {}
    for pid, points, year, week in result.all():
        rows_by_player.setdefault(pid, []).append((year, week, points or 0.0))

    player_stats = {pid: 0.0 for pid in player_ids}
    for pid, rows in rows_by_player.items():
        rows.sort(reverse=True)  # most recent (year, week) first
        recent = rows[:limit]
        player_stats[pid] = sum(r[2] for r in recent) / len(recent)

    return player_stats


def _calculate_position_averages(
    players: List[Player], player_stats: Dict[str, float]
) -> Dict[str, float]:
    """Return average PPG per position across all provided players with recorded production."""
    pos_ppg: Dict[str, List[float]] = {}
    for player in players:
        pos = player.position or "OTH"
        ppg = player_stats.get(player.id, 0.0)
        if ppg > 0:
            pos_ppg.setdefault(pos, []).append(ppg)
    return {pos: sum(vals) / len(vals) for pos, vals in pos_ppg.items() if vals}


async def _calculate_player_power_score(
    player: Player,
    avg_points_per_game: float,
    db: AsyncSession,
    ktc_value: float = 0.0,
    position_avg: float = 0.0,
) -> PlayerPowerScore:
    """Calculate individual player power score: KTC + league production + age.

    Formula (max 30):
      - League production vs position average (max 14): how does this player score
        compared to other players at their position in *this* league's format
      - KTC dynasty value (max 8): market-consensus dynasty worth
      - Age (max 8): dynasty longevity tiebreaker

    Fallback when no KTC value: position (max 5) replaces KTC component.
    """
    # --- Age component (max 8) ---
    if player.age:
        effective_age = player.age
    elif player.years_exp:
        effective_age = 22 + player.years_exp
    else:
        effective_age = 27

    if effective_age <= 23:
        age_score = 8.0
    elif effective_age <= 25:
        age_score = 7.0
    elif effective_age <= 27:
        age_score = 5.5
    elif effective_age <= 29:
        age_score = 3.5
    else:
        age_score = 1.5

    # --- League production vs position average (max 10) ---
    if avg_points_per_game > 0 and position_avg > 0:
        # Ratio to position average; average scorer = 5/10, elite (2x avg) = 10
        ratio = avg_points_per_game / position_avg
        production_score = min(10.0, ratio * 5.0)
    elif avg_points_per_game > 0:
        # No position average available — fall back to absolute PPG scale
        production_score = min(10.0, (avg_points_per_game / 20.0) * 10.0)
    else:
        production_score = 0.5 if player.status == "Active" else 0.0

    # --- KTC dynasty value (max 12) ---
    if ktc_value > 0:
        ktc_component = min(12.0, (ktc_value / 10000.0) * 12.0)
        position_score = 0.0
    else:
        # Fallback: low floor for unranked players (KTC not ranking them is itself a signal)
        ktc_component = 1.5
        position_score = 0.0

    power_score = ktc_component + production_score + age_score

    return PlayerPowerScore(
        player_id=player.id,
        player_name=player.full_name or f"{player.first_name} {player.last_name}",
        position=player.position,
        team=player.team,
        age=player.age,
        power_score=round(power_score, 2),
        age_score=round(age_score, 1),
        position_score=round(position_score, 1),
        production_score=round(production_score, 1),
    )
