from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from statistics import stdev as calc_stdev
from typing import List, Dict, Any, Tuple
from app.database import get_db
from app.models import Season, Roster, User, Player, Matchup, SeasonAward, MatchupPlayerPoint
from app.schemas.power_rankings import (
    PowerRankingsResponse,
    PowerRankingTeam,
    RosterBreakdown,
    PlayerPowerScore,
)

router = APIRouter()


@router.get("/power-rankings", response_model=PowerRankingsResponse)
async def get_current_power_rankings(db: AsyncSession = Depends(get_db)):
    """Get power rankings for current season."""
    # Get the most recent season
    result = await db.execute(select(Season).order_by(desc(Season.year)).limit(1))
    season = result.scalar_one_or_none()

    if not season:
        raise HTTPException(status_code=404, detail="No season data found")

    return await _get_season_power_rankings(db, season.year)


@router.get("/power-rankings/{season_year}", response_model=PowerRankingsResponse)
async def get_historical_power_rankings(
    season_year: int, db: AsyncSession = Depends(get_db)
):
    """Get power rankings for a specific season."""
    return await _get_season_power_rankings(db, season_year)


@router.get(
    "/power-rankings/{season_year}/roster/{roster_id}",
    response_model=RosterBreakdown,
)
async def get_roster_breakdown(
    season_year: int, roster_id: int, db: AsyncSession = Depends(get_db)
):
    """Get detailed roster breakdown with individual player power scores."""
    # Get season
    result = await db.execute(select(Season).where(Season.year == season_year))
    season = result.scalar_one_or_none()

    if not season:
        raise HTTPException(status_code=404, detail=f"Season {season_year} not found")

    # Get roster with user info
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

    # Get all players on this roster
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

    # Fetch player details
    result = await db.execute(select(Player).where(Player.id.in_(player_ids)))
    players = result.scalars().all()

    # Calculate player performance stats (rolling 15-game average)
    player_stats = await _calculate_player_stats(player_ids, db)

    # Calculate player power scores
    player_scores = []
    total_age = 0
    age_count = 0

    for player in players:
        avg_points = player_stats.get(player.id, 0.0)
        power_score_data = await _calculate_player_power_score(player, avg_points, db)
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


# ================== HELPER FUNCTIONS ==================


async def _get_season_power_rankings(
    db: AsyncSession, year: int
) -> PowerRankingsResponse:
    """Helper function to calculate power rankings for a specific season."""
    # Get season
    result = await db.execute(select(Season).where(Season.year == year))
    season = result.scalar_one_or_none()

    if not season:
        raise HTTPException(status_code=404, detail=f"Season {year} not found")

    # Get all rosters for this season with user info
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

    # Get all players for roster value calculations
    all_player_ids = set()
    for roster, _ in rosters_with_users:
        if roster.players:
            all_player_ids.update(roster.players)

    players_dict = {}
    if all_player_ids:
        result = await db.execute(select(Player).where(Player.id.in_(all_player_ids)))
        players = result.scalars().all()
        players_dict = {player.id: player for player in players}

    # Calculate power rankings for each team
    rankings = []
    all_rosters = [roster for roster, _ in rosters_with_users]

    for roster, user in rosters_with_users:
        # Current Season Score (40 pts)
        current_score = await _calculate_current_season_score(
            roster, all_rosters, season, db
        )

        # Roster Value Score (40 pts)
        roster_score = await _calculate_roster_value_score(roster, players_dict, db)

        # Historical Score (20 pts)
        historical_score = await _calculate_historical_score(roster, db)

        total_score = current_score + roster_score + historical_score

        # Calculate avg roster age
        avg_age = _calculate_avg_roster_age(roster, players_dict)

        rankings.append(
            PowerRankingTeam(
                rank=0,  # Will be assigned after sorting
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

    # Sort by total_score descending and assign ranks
    rankings.sort(key=lambda x: x.total_score, reverse=True)
    for idx, ranking in enumerate(rankings):
        ranking.rank = idx + 1

    return PowerRankingsResponse(season=year, rankings=rankings)


async def _calculate_current_season_score(
    roster: Roster, all_rosters: List[Roster], season: Season, db: AsyncSession
) -> float:
    """Calculate current season performance score (40 points max) using rolling 15-game averages."""
    score = 0.0

    # Get all roster IDs for this user across all seasons
    result = await db.execute(
        select(Roster.id).where(Roster.user_id == roster.user_id)
    )
    user_roster_ids = [row[0] for row in result]

    if not user_roster_ids:
        return 0.0

    # Get last 15 games for this user (across all seasons)
    # Join with Season to order chronologically by year and week
    result = await db.execute(
        select(Matchup, Season.year)
        .join(Season, Matchup.season_id == Season.id)
        .where(
            (Matchup.home_roster_id.in_(user_roster_ids))
            | (Matchup.away_roster_id.in_(user_roster_ids))
        )
        .order_by(desc(Season.year), desc(Matchup.week))
        .limit(15)
    )
    # Extract just the Matchup objects and remove duplicates
    seen_ids = set()
    recent_matchups = []
    for matchup, year in result:
        if matchup.id not in seen_ids:
            seen_ids.add(matchup.id)
            recent_matchups.append(matchup)

    if not recent_matchups:
        # No historical data
        return 0.0

    # Calculate rolling averages from last 15 games
    wins = 0
    total_points = 0.0
    opponent_points = 0.0

    for matchup in recent_matchups:
        is_home = matchup.home_roster_id in user_roster_ids
        is_away = matchup.away_roster_id in user_roster_ids

        # Count wins (check if this user's roster won)
        if matchup.winner_roster_id in user_roster_ids:
            wins += 1

        # Track points
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
    # Get rolling averages for all rosters to compare
    all_roster_avgs = []
    for r in all_rosters:
        # Get all roster IDs for this user
        result = await db.execute(
            select(Roster.id).where(Roster.user_id == r.user_id)
        )
        r_roster_ids = [row[0] for row in result]

        if not r_roster_ids:
            continue

        result = await db.execute(
            select(Matchup, Season.year)
            .join(Season, Matchup.season_id == Season.id)
            .where(
                (Matchup.home_roster_id.in_(r_roster_ids))
                | (Matchup.away_roster_id.in_(r_roster_ids))
            )
            .order_by(desc(Season.year), desc(Matchup.week))
            .limit(15)
        )
        # Extract just the Matchup objects and remove duplicates
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
        # Count how many rosters have a lower average (proper percentile ranking)
        teams_below = sum(1 for avg in all_roster_avgs if avg < roster_avg)
        percentile = teams_below / (len(all_roster_avgs) - 1) if len(all_roster_avgs) > 1 else 0.5
        score += percentile * 12

    # 3. Point Differential (8 pts)
    if games_played > 0:
        avg_points = total_points / games_played
        avg_opponent_points = opponent_points / games_played
        point_diff = avg_points - avg_opponent_points
        # Map -20 to +20 range to 0-8 (capped)
        normalized_diff = max(0, min(8, (point_diff + 20) / 5))
        score += normalized_diff

    # 4. Recent Form - last 3 weeks (5 pts)
    # Use only last 3 games instead of 15 for recent form
    recent_3_matchups = recent_matchups[:3]
    recent_wins = sum(1 for m in recent_3_matchups if m.winner_roster_id in user_roster_ids)
    if len(recent_3_matchups) > 0:
        recent_form_pct = recent_wins / len(recent_3_matchups)
        score += recent_form_pct * 5

    return score


async def _calculate_roster_value_score(
    roster: Roster, players_dict: Dict[str, Player], db: AsyncSession
) -> float:
    """Calculate roster value score (40 points max)."""
    score = 0.0

    if not roster.players:
        return 0.0

    # Get roster players
    roster_players = [players_dict.get(pid) for pid in roster.players]
    roster_players = [p for p in roster_players if p is not None]

    if not roster_players:
        return 0.0

    # Get player performance stats
    player_ids = [p.id for p in roster_players]
    player_stats = await _calculate_player_stats(player_ids, db)

    # 1. Average Roster Age (15 pts)
    avg_age = _calculate_avg_roster_age(roster, players_dict)
    age_score = _age_to_score(avg_age)
    score += age_score * 15

    # 2. Player Production Value (15 pts)
    # Sum up production scores for all players and normalize
    total_production = 0.0
    for player in roster_players:
        avg_points = player_stats.get(player.id, 0.0)
        # Scale: 0 pts/game = 0, 20+ pts/game = 1.0
        player_production = min(1.0, avg_points / 20.0)
        total_production += player_production

    # Normalize: 0-15 players with high production -> 0-15 pts
    score += min(15, total_production)

    # 3. Roster Depth (10 pts)
    startable_count = sum(1 for p in roster_players if _is_startable(p))
    # Normalize: 0-20 startable players -> 0-10 pts
    score += min(10, startable_count * 0.5)

    return score


async def _calculate_historical_score(roster: Roster, db: AsyncSession) -> float:
    """Calculate historical performance score (20 points max)."""
    score = 0.0

    # Get user's historical data from season_awards
    result = await db.execute(
        select(SeasonAward).where(SeasonAward.user_id == roster.user_id)
    )
    awards = result.scalars().all()

    # Count championships and playoff appearances in last 3 seasons
    championships = sum(1 for award in awards if award.award_type == "champion")
    playoff_appearances = len([a for a in awards if a.award_type in ["champion", "division_winner"]])

    # 1. Championships (8 pts) - 5 pts per championship
    score += min(8, championships * 5)

    # 2. Playoff Appearances (8 pts) - ~2.67 pts per appearance
    score += min(8, playoff_appearances * 2.67)

    # 3. Consistency (4 pts) - TODO: requires historical season data
    # For now, give average score of 2 pts
    score += 2

    return score


async def _calculate_recent_form(
    roster: Roster, season: Season, db: AsyncSession
) -> float:
    """Calculate recent form score based on last 3 weeks (5 points max)."""
    # Get last 3 weeks of regular season matchups
    if not season.regular_season_weeks or season.regular_season_weeks < 3:
        return 0.0

    # Determine which weeks to check (last 3 completed weeks)
    # For simplicity, check last 3 weeks of regular season
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

    # Calculate win percentage in recent games
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
            # Estimate age from years_exp
            estimated_age = 22 + player.years_exp
            ages.append(estimated_age)

    return sum(ages) / len(ages) if ages else 27.0  # Default to 27 if no ages


def _age_to_score(avg_age: float) -> float:
    """Convert average roster age to 0-1 score (1 = best for dynasty)."""
    # Ages 22-25: 1.0 (dynasty sweet spot)
    # Ages 26-28: 0.7
    # Ages 29+: 0.3
    if avg_age <= 25:
        return 1.0
    elif avg_age <= 28:
        # Linear interpolation from 1.0 to 0.7
        return 1.0 - (avg_age - 25) * 0.1
    else:
        # Linear interpolation from 0.7 to 0.3
        return max(0.3, 0.7 - (avg_age - 28) * 0.1)


def _is_elite_player(player: Player) -> bool:
    """Check if a player is considered 'elite' for dynasty purposes."""
    # Elite criteria:
    # - Age < 28 AND position in QB, RB, WR, TE
    # - Has active status
    if not player.age or player.age >= 28:
        return False

    if player.status not in ["Active", None]:  # None means no status set (assume active)
        return False

    return player.position in ["QB", "RB", "WR", "TE"]


def _is_startable(player: Player) -> bool:
    """Check if a player is considered startable."""
    # Startable criteria:
    # - Age < 30
    # - Active status
    # - Position in QB, RB, WR, TE
    if player.age and player.age >= 30:
        return False

    if player.status not in ["Active", None]:
        return False

    return player.position in ["QB", "RB", "WR", "TE"]


async def _calculate_player_stats(
    player_ids: List[str], db: AsyncSession, limit: int = 15
) -> Dict[str, float]:
    """Calculate rolling average points per game for players (last N games)."""
    if not player_ids:
        return {}

    # Get last N games for each player across all seasons
    result = await db.execute(
        select(
            MatchupPlayerPoint.player_id,
            func.avg(MatchupPlayerPoint.points).label("avg_points"),
        )
        .where(MatchupPlayerPoint.player_id.in_(player_ids))
        .group_by(MatchupPlayerPoint.player_id)
    )

    # For now, get overall average - we can enhance this later to truly be rolling 15-game
    player_stats = {}
    for row in result:
        player_stats[row.player_id] = float(row.avg_points) if row.avg_points else 0.0

    # Alternative approach: Get last 15 games per player
    # This is more complex but more accurate
    for player_id in player_ids:
        if player_id not in player_stats:
            # Get last 15 games for this specific player
            result = await db.execute(
                select(MatchupPlayerPoint.points)
                .where(MatchupPlayerPoint.player_id == player_id)
                .order_by(desc(MatchupPlayerPoint.id))
                .limit(limit)
            )
            recent_points = [row.points for row in result]
            if recent_points:
                player_stats[player_id] = sum(recent_points) / len(recent_points)
            else:
                player_stats[player_id] = 0.0

    return player_stats


async def _calculate_player_power_score(
    player: Player, avg_points_per_game: float, db: AsyncSession
) -> PlayerPowerScore:
    """Calculate individual player power score based on age, position, and production."""
    age_score = 0.0
    position_score = 0.0
    production_score = 0.0

    # 1. Age component (max 10)
    if player.age:
        if player.age <= 25:
            age_score = 10.0
        elif player.age <= 27:
            age_score = 8.0
        elif player.age <= 29:
            age_score = 5.0
        else:
            age_score = 2.0
    elif player.years_exp:
        # Estimate age and calculate
        estimated_age = 22 + player.years_exp
        if estimated_age <= 25:
            age_score = 10.0
        elif estimated_age <= 27:
            age_score = 8.0
        elif estimated_age <= 29:
            age_score = 5.0
        else:
            age_score = 2.0
    else:
        age_score = 5.0  # Default middle score

    # 2. Positional value (max 10)
    position_values = {
        "QB": 10.0,
        "RB": 9.0,
        "WR": 8.0,
        "TE": 7.0,
        "K": 3.0,
        "DEF": 4.0,
    }
    position_score = position_values.get(player.position, 5.0)

    # 3. Production (max 10) - based on rolling 15-game average
    # Scale: 0 pts/game = 0, 20+ pts/game = 10
    if avg_points_per_game > 0:
        production_score = min(10.0, (avg_points_per_game / 20.0) * 10.0)
    else:
        # No stats yet - give minimal score based on status
        production_score = 2.0 if player.status == "Active" else 0.5

    power_score = age_score + position_score + production_score

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
