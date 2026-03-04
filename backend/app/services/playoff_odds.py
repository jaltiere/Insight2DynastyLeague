"""Monte Carlo simulation engine for playoff odds calculation."""

import random
import math
from collections import defaultdict
from statistics import median as calc_median
from typing import Dict, List, Any, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models import Season, Roster, User, League, Matchup

NUM_SIMULATIONS = 10_000
NUM_PLAYOFF_TEAMS = 6
NUM_DIVISIONS = 2


class TeamState:
    """Tracks a team's state during simulation."""

    __slots__ = (
        "roster_db_id", "roster_id", "user_id", "display_name", "username",
        "team_name", "avatar", "division", "wins", "losses", "median_wins",
        "median_losses", "points_for", "points_against", "max_potential_points",
        "avg_ppg", "rating",
    )

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def total_wins(self) -> int:
        return self.wins + self.median_wins

    def total_losses(self) -> int:
        return self.losses + self.median_losses

    def tiebreaker_key(self) -> Tuple:
        """Sort key for tiebreaking: (total wins desc, PF desc, PA desc)."""
        return (-self.total_wins(), -self.points_for, -self.points_against)


def _compute_team_rating(team: TeamState, games_played: int) -> float:
    """Compute a composite team rating scaled to ~600-1000."""
    if games_played == 0:
        return 750.0

    win_pct = team.wins / max(games_played, 1)
    median_games = team.median_wins + team.median_losses
    median_pct = team.median_wins / max(median_games, 1) if median_games > 0 else 0.5
    efficiency = team.points_for / max(team.max_potential_points, 1) if team.max_potential_points else 0.5

    # Weighted composite: 40% win%, 25% median%, 20% ppg relative, 15% efficiency
    composite = (
        win_pct * 0.40
        + median_pct * 0.25
        + min(team.avg_ppg / 150.0, 1.0) * 0.20
        + efficiency * 0.15
    )

    # Scale to 600-1000 range
    return round(600 + composite * 400)


def _win_probability(rating_a: float, rating_b: float) -> float:
    """Logistic win probability based on rating difference."""
    diff = rating_a - rating_b
    return 1.0 / (1.0 + math.exp(-diff / 60.0))


def _simulate_score(team: TeamState, rng: random.Random) -> float:
    """Simulate a game score for a team based on their average and variance."""
    # Use normal distribution centered on avg_ppg with reasonable spread
    std_dev = max(team.avg_ppg * 0.15, 10.0)
    return max(rng.gauss(team.avg_ppg, std_dev), 30.0)


def _determine_playoff_teams(
    teams: Dict[int, TeamState],
) -> Tuple[List[int], Dict[int, int]]:
    """Determine which teams make playoffs and their seeds.

    Returns (playoff_roster_db_ids, seed_map: {roster_db_id: seed}).
    Seeds: 1-2 = division winners (bye), 3-6 = wild cards.
    """
    # Find division winners
    division_teams: Dict[int, List[TeamState]] = defaultdict(list)
    for t in teams.values():
        division_teams[t.division].append(t)

    division_winners = []
    for div in sorted(division_teams.keys()):
        div_sorted = sorted(division_teams[div], key=lambda t: t.tiebreaker_key())
        division_winners.append(div_sorted[0])

    div_winner_ids = {t.roster_db_id for t in division_winners}

    # Sort division winners between themselves for seeds 1-2
    division_winners.sort(key=lambda t: t.tiebreaker_key())

    # Wild cards: top 4 non-division-winners by overall record
    non_winners = [t for t in teams.values() if t.roster_db_id not in div_winner_ids]
    non_winners.sort(key=lambda t: t.tiebreaker_key())
    wild_cards = non_winners[:4]

    # Build seed map
    seed_map = {}
    for i, t in enumerate(division_winners):
        seed_map[t.roster_db_id] = i + 1  # Seeds 1-2
    for i, t in enumerate(wild_cards):
        seed_map[t.roster_db_id] = i + 3  # Seeds 3-6

    playoff_ids = [t.roster_db_id for t in division_winners + wild_cards]
    return playoff_ids, seed_map


def _simulate_playoff_bracket(
    seed_map: Dict[int, int],
    teams: Dict[int, TeamState],
    rng: random.Random,
) -> Tuple[int, Dict[int, int]]:
    """Simulate a single-elimination playoff bracket.

    Bracket: Seeds 1-2 get byes. Round 1: 3v6, 4v5.
    Semis: 1 vs winner(4v5), 2 vs winner(3v6).
    Finals: semi winners.

    Returns (champion_roster_db_id, finish_map: {roster_db_id: finish_position}).
    Finish positions: 1=champion, 2=runner-up, 3-4=semi losers, 5-6=round1 losers.
    """
    by_seed = {seed: rid for rid, seed in seed_map.items()}

    def play_game(rid_a, rid_b):
        prob = _win_probability(teams[rid_a].rating, teams[rid_b].rating)
        return rid_a if rng.random() < prob else rid_b

    # Round 1
    r1_winner_a = play_game(by_seed[3], by_seed[6])
    r1_loser_a = by_seed[6] if r1_winner_a == by_seed[3] else by_seed[3]
    r1_winner_b = play_game(by_seed[4], by_seed[5])
    r1_loser_b = by_seed[5] if r1_winner_b == by_seed[4] else by_seed[4]

    # Semis
    semi_winner_a = play_game(by_seed[1], r1_winner_b)
    semi_loser_a = r1_winner_b if semi_winner_a == by_seed[1] else by_seed[1]
    semi_winner_b = play_game(by_seed[2], r1_winner_a)
    semi_loser_b = r1_winner_a if semi_winner_b == by_seed[2] else by_seed[2]

    # Finals
    champion = play_game(semi_winner_a, semi_winner_b)
    runner_up = semi_winner_b if champion == semi_winner_a else semi_winner_a

    finish = {
        champion: 1,
        runner_up: 2,
        semi_loser_a: 3,
        semi_loser_b: 4,
        r1_loser_a: 5,
        r1_loser_b: 6,
    }
    return champion, finish


async def calculate_playoff_odds(
    db: AsyncSession, season_year: int
) -> Dict[str, Any]:
    """Run Monte Carlo simulation for playoff odds."""

    # Get season
    result = await db.execute(
        select(Season).where(Season.year == season_year)
    )
    season = result.scalar_one_or_none()
    if not season:
        return None

    # Get league status
    result = await db.execute(
        select(League).where(League.id == season.league_id)
    )
    league = result.scalar_one_or_none()
    league_metadata = (league.league_metadata if league else None) or {}

    # Build division names
    division_names = {}
    for i in range(1, (season.num_divisions or 2) + 1):
        division_names[str(i)] = league_metadata.get(f"division_{i}", f"Division {i}")

    # Get rosters with users
    result = await db.execute(
        select(Roster, User)
        .join(User, Roster.user_id == User.id)
        .where(Roster.season_id == season.id)
    )
    rosters_with_users = result.all()

    if not rosters_with_users:
        return {
            "season": season_year,
            "season_started": False,
            "current_week": 0,
            "regular_season_weeks": season.regular_season_weeks,
            "playoff_odds": [],
            "draft_order": [],
        }

    # Get all regular season matchups
    result = await db.execute(
        select(Matchup).where(
            Matchup.season_id == season.id,
            Matchup.match_type == "regular",
        )
    )
    all_matchups = result.scalars().all()

    # Determine current week from played matchups
    played_weeks = {m.week for m in all_matchups if m.winner_roster_id is not None}
    current_week = max(played_weeks) if played_weeks else 0

    if current_week == 0:
        return {
            "season": season_year,
            "season_started": False,
            "current_week": 0,
            "regular_season_weeks": season.regular_season_weeks,
            "playoff_odds": [],
            "draft_order": [],
        }

    # Calculate median records from played matchups
    week_scores: Dict[int, list] = defaultdict(list)
    for m in all_matchups:
        if m.winner_roster_id is not None:
            week_scores[m.week].append((m.home_roster_id, m.home_points or 0))
            week_scores[m.week].append((m.away_roster_id, m.away_points or 0))

    median_records: Dict[int, Dict[str, int]] = defaultdict(
        lambda: {"wins": 0, "losses": 0}
    )
    for scores in week_scores.values():
        if len(scores) < 2:
            continue
        all_points = [s[1] for s in scores]
        week_median = calc_median(all_points)
        for roster_id, pts in scores:
            if pts > week_median:
                median_records[roster_id]["wins"] += 1
            elif pts < week_median:
                median_records[roster_id]["losses"] += 1

    # Calculate max potential points from played matchups
    max_potential_stats: Dict[int, float] = defaultdict(float)
    for m in all_matchups:
        if m.winner_roster_id is not None:
            if m.home_max_potential_points is not None:
                max_potential_stats[m.home_roster_id] += m.home_max_potential_points
            if m.away_max_potential_points is not None:
                max_potential_stats[m.away_roster_id] += m.away_max_potential_points

    # Build team states
    teams: Dict[int, TeamState] = {}
    for roster, user in rosters_with_users:
        games_played = roster.wins + roster.losses + roster.ties
        avg_ppg = roster.points_for / max(games_played, 1) if games_played > 0 else 100.0
        med = median_records.get(roster.id, {"wins": 0, "losses": 0})

        team = TeamState(
            roster_db_id=roster.id,
            roster_id=roster.roster_id,
            user_id=user.id,
            display_name=user.display_name or user.username,
            username=user.username,
            team_name=roster.team_name,
            avatar=user.avatar,
            division=roster.division,
            wins=roster.wins,
            losses=roster.losses,
            median_wins=med["wins"],
            median_losses=med["losses"],
            points_for=roster.points_for or 0,
            points_against=roster.points_against or 0,
            max_potential_points=max_potential_stats.get(roster.id, 0.0),
            avg_ppg=avg_ppg,
            rating=0.0,
        )
        team.rating = _compute_team_rating(team, games_played)
        teams[roster.id] = team

    # Identify remaining matchups (unplayed regular season games)
    remaining_matchups = [
        m for m in all_matchups if m.winner_roster_id is None
    ]

    remaining_weeks = season.regular_season_weeks - current_week

    # Run Monte Carlo simulations
    rng = random.Random(42)  # Deterministic seed for consistency

    # Counters
    made_playoffs = defaultdict(int)
    won_division = defaultdict(int)
    got_bye = defaultdict(int)
    won_finals = defaultdict(int)
    projected_wins = defaultdict(float)
    projected_losses = defaultdict(float)
    projected_median_wins = defaultdict(float)
    projected_median_losses = defaultdict(float)

    for _ in range(NUM_SIMULATIONS):
        # Clone team states for this simulation
        sim_teams: Dict[int, TeamState] = {}
        for rid, t in teams.items():
            sim_teams[rid] = TeamState(
                roster_db_id=t.roster_db_id,
                roster_id=t.roster_id,
                user_id=t.user_id,
                display_name=t.display_name,
                username=t.username,
                team_name=t.team_name,
                avatar=t.avatar,
                division=t.division,
                wins=t.wins,
                losses=t.losses,
                median_wins=t.median_wins,
                median_losses=t.median_losses,
                points_for=t.points_for,
                points_against=t.points_against,
                max_potential_points=t.max_potential_points,
                avg_ppg=t.avg_ppg,
                rating=t.rating,
            )

        # Simulate remaining games
        # Group remaining matchups by week for median calculation
        remaining_by_week: Dict[int, List[Matchup]] = defaultdict(list)
        for m in remaining_matchups:
            remaining_by_week[m.week].append(m)

        for week, matchups in remaining_by_week.items():
            week_sim_scores = []

            for m in matchups:
                home = sim_teams.get(m.home_roster_id)
                away = sim_teams.get(m.away_roster_id)
                if not home or not away:
                    continue

                home_score = _simulate_score(home, rng)
                away_score = _simulate_score(away, rng)

                # Apply rating-based adjustment
                prob = _win_probability(home.rating, away.rating)
                if rng.random() < prob:
                    # Home wins - ensure score reflects it
                    if home_score <= away_score:
                        home_score, away_score = away_score, home_score
                    home.wins += 1
                    away.losses += 1
                else:
                    # Away wins
                    if away_score <= home_score:
                        home_score, away_score = away_score, home_score
                    away.wins += 1
                    home.losses += 1

                home.points_for += home_score
                away.points_for += away_score
                week_sim_scores.append((m.home_roster_id, home_score))
                week_sim_scores.append((m.away_roster_id, away_score))

            # Simulate median for this week
            if len(week_sim_scores) >= 2:
                all_pts = [s[1] for s in week_sim_scores]
                week_med = calc_median(all_pts)
                for rid, pts in week_sim_scores:
                    st = sim_teams.get(rid)
                    if st:
                        if pts > week_med:
                            st.median_wins += 1
                        elif pts < week_med:
                            st.median_losses += 1

        # Determine playoff teams
        playoff_ids, seed_map = _determine_playoff_teams(sim_teams)

        for rid in playoff_ids:
            made_playoffs[rid] += 1
        for rid, seed in seed_map.items():
            if seed <= NUM_DIVISIONS:
                won_division[rid] += 1
                got_bye[rid] += 1

        # Simulate playoff bracket
        if len(seed_map) >= NUM_PLAYOFF_TEAMS:
            champion, finish_map = _simulate_playoff_bracket(
                seed_map, sim_teams, rng
            )
            won_finals[champion] += 1

        # Accumulate projected records
        for rid, st in sim_teams.items():
            projected_wins[rid] += st.wins
            projected_losses[rid] += st.losses
            projected_median_wins[rid] += st.median_wins
            projected_median_losses[rid] += st.median_losses

    # Build results
    playoff_odds = []
    for rid, team in teams.items():
        games_played = team.wins + team.losses
        proj_w = round(projected_wins[rid] / NUM_SIMULATIONS)
        proj_l = round(projected_losses[rid] / NUM_SIMULATIONS)
        proj_mw = round(projected_median_wins[rid] / NUM_SIMULATIONS)
        proj_ml = round(projected_median_losses[rid] / NUM_SIMULATIONS)

        make_pct = round(made_playoffs[rid] / NUM_SIMULATIONS * 100, 0)
        div_pct = round(won_division[rid] / NUM_SIMULATIONS * 100, 0)
        bye_pct = round(got_bye[rid] / NUM_SIMULATIONS * 100, 0)
        finals_pct = round(won_finals[rid] / NUM_SIMULATIONS * 100, 0)

        # Format percentages nicely
        def fmt_pct(val):
            if val >= 99.5:
                return ">99%"
            elif val <= 0.5 and val > 0:
                return "<1%"
            else:
                return f"{int(val)}%"

        playoff_odds.append({
            "roster_id": team.roster_id,
            "user_id": team.user_id,
            "display_name": team.display_name,
            "username": team.username,
            "team_name": team.team_name,
            "avatar": team.avatar,
            "division": team.division,
            "division_name": division_names.get(str(team.division), f"Division {team.division}"),
            "current_record": f"{team.wins} - {team.losses}",
            "projected_record": f"{proj_w} - {proj_l}",
            "team_rating": team.rating,
            "rating_change": 0,  # Will be computed when we have historical data
            "make_playoffs_pct": make_pct,
            "make_playoffs_display": fmt_pct(make_pct),
            "win_division_pct": div_pct,
            "win_division_display": fmt_pct(div_pct),
            "first_round_bye_pct": bye_pct,
            "first_round_bye_display": fmt_pct(bye_pct),
            "win_finals_pct": finals_pct,
            "win_finals_display": fmt_pct(finals_pct),
            "points_for": team.points_for,
            "points_against": team.points_against,
            "median_wins": team.median_wins,
            "median_losses": team.median_losses,
            "max_potential_points": round(team.max_potential_points, 1),
        })

    # Sort by team rating descending
    playoff_odds.sort(key=lambda x: -x["team_rating"])

    # Compute draft order
    draft_order = _compute_draft_order(playoff_odds, teams, NUM_SIMULATIONS, made_playoffs)

    return {
        "season": season_year,
        "season_started": True,
        "current_week": current_week,
        "regular_season_weeks": season.regular_season_weeks,
        "playoff_odds": playoff_odds,
        "draft_order": draft_order,
    }


def _compute_draft_order(
    playoff_odds: List[Dict],
    teams: Dict[int, TeamState],
    num_sims: int,
    made_playoffs: Dict[int, int],
) -> List[Dict]:
    """Compute projected draft order.

    Picks 1-6: Non-playoff teams by lowest max potential points.
    Picks 7-12: Playoff teams by estimated finish (worst first).
    """
    # Build lookup by roster_db_id
    team_by_roster_id = {}
    for rid, t in teams.items():
        team_by_roster_id[t.roster_id] = t

    odds_by_roster_id = {o["roster_id"]: o for o in playoff_odds}

    # Classify likely playoff vs non-playoff teams based on simulation
    # Teams with > 50% playoff chance are considered "playoff teams"
    playoff_team_rids = []
    non_playoff_team_rids = []

    for rid, t in teams.items():
        pct = made_playoffs[rid] / num_sims * 100
        if pct > 50:
            playoff_team_rids.append(rid)
        else:
            non_playoff_team_rids.append(rid)

    # Sort non-playoff by lowest max potential points (pick 1 = lowest)
    non_playoff_team_rids.sort(key=lambda rid: teams[rid].max_potential_points)

    # Sort playoff teams by rating ascending (worst playoff team picks first)
    playoff_team_rids.sort(key=lambda rid: teams[rid].rating)

    draft_order = []
    pick = 1

    # Picks for non-playoff teams
    for rid in non_playoff_team_rids:
        t = teams[rid]
        o = odds_by_roster_id.get(t.roster_id, {})
        draft_order.append({
            "pick": pick,
            "roster_id": t.roster_id,
            "user_id": t.user_id,
            "display_name": t.display_name,
            "team_name": t.team_name,
            "avatar": t.avatar,
            "reason": "Lowest max potential points",
            "max_potential_points": round(t.max_potential_points, 1),
            "projected_record": o.get("projected_record", ""),
        })
        pick += 1

    # Picks for playoff teams
    for rid in playoff_team_rids:
        t = teams[rid]
        o = odds_by_roster_id.get(t.roster_id, {})
        draft_order.append({
            "pick": pick,
            "roster_id": t.roster_id,
            "user_id": t.user_id,
            "display_name": t.display_name,
            "team_name": t.team_name,
            "avatar": t.avatar,
            "reason": "Playoff team (est. finish)",
            "max_potential_points": round(t.max_potential_points, 1),
            "projected_record": o.get("projected_record", ""),
        })
        pick += 1

    return draft_order
