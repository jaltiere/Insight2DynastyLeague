from tests.conftest import LEAGUE_PREFIX
"""Tests for power rankings endpoints including snapshot and trends."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.power_ranking_snapshot import PowerRankingSnapshot
from tests.conftest import (
    create_league,
    create_user,
    create_season,
    create_roster,
    create_matchup,
    create_player,
    create_matchup_player_point,
)


@pytest.mark.anyio
async def test_get_current_power_rankings_returns_200(client: AsyncClient, db_session: AsyncSession):
    """Basic smoke test: endpoint returns 200 with rankings list."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user1 = await create_user(db_session, id="u1", username="alice", display_name="Alice")
    user2 = await create_user(db_session, id="u2", username="bob", display_name="Bob")
    r1 = await create_roster(db_session, season, user1, roster_id=1, wins=8, losses=6)
    r2 = await create_roster(db_session, season, user2, roster_id=2, wins=5, losses=9)
    await create_matchup(
        db_session, season, r1, r2,
        home_points=130.0, away_points=110.0, winner_roster_id=r1.id
    )

    resp = await client.get(f"{LEAGUE_PREFIX}/power-rankings")
    assert resp.status_code == 200
    body = resp.json()
    assert "season" in body
    assert "rankings" in body
    assert len(body["rankings"]) == 2


@pytest.mark.anyio
async def test_power_rankings_response_has_all_fields(client: AsyncClient, db_session: AsyncSession):
    """Each ranking entry includes rank_change and previous_rank fields."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user = await create_user(db_session, id="u1", username="alice", display_name="Alice")
    await create_roster(db_session, season, user, roster_id=1)

    resp = await client.get(f"{LEAGUE_PREFIX}/power-rankings")
    assert resp.status_code == 200
    team = resp.json()["rankings"][0]
    expected_fields = [
        "rank", "roster_id", "user_id", "username", "display_name", "team_name",
        "total_score", "current_season_score", "roster_value_score", "historical_score",
        "wins", "losses", "ties", "points_for", "avg_roster_age",
        "rank_change", "previous_rank",
    ]
    for field in expected_fields:
        assert field in team, f"Missing field: {field}"


@pytest.mark.anyio
async def test_rank_change_is_none_without_snapshot(client: AsyncClient, db_session: AsyncSession):
    """rank_change and previous_rank are None when no prior snapshot exists."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user = await create_user(db_session, id="u1", username="alice", display_name="Alice")
    await create_roster(db_session, season, user, roster_id=1)

    resp = await client.get(f"{LEAGUE_PREFIX}/power-rankings")
    assert resp.status_code == 200
    team = resp.json()["rankings"][0]
    assert team["rank_change"] is None
    assert team["previous_rank"] is None


@pytest.mark.anyio
async def test_rank_change_populated_after_snapshot(client: AsyncClient, db_session: AsyncSession):
    """rank_change is populated when a prior week snapshot exists."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user1 = await create_user(db_session, id="u1", username="alice", display_name="Alice")
    user2 = await create_user(db_session, id="u2", username="bob", display_name="Bob")
    r1 = await create_roster(db_session, season, user1, roster_id=1, wins=10, losses=4)
    r2 = await create_roster(db_session, season, user2, roster_id=2, wins=4, losses=10)

    # Manually insert a snapshot where roster 1 was rank 2 and roster 2 was rank 1
    db_session.add(PowerRankingSnapshot(
        group_id="test_league_001", season_year=2024, week=5, roster_id=1, rank=2,
        total_score=60.0, current_season_score=20.0,
        roster_value_score=30.0, historical_score=10.0,
    ))
    db_session.add(PowerRankingSnapshot(
        group_id="test_league_001", season_year=2024, week=5, roster_id=2, rank=1,
        total_score=65.0, current_season_score=25.0,
        roster_value_score=30.0, historical_score=10.0,
    ))
    await db_session.flush()

    resp = await client.get(f"{LEAGUE_PREFIX}/power-rankings")
    assert resp.status_code == 200
    rankings = resp.json()["rankings"]

    # Both teams should have non-None rank_change now
    for team in rankings:
        assert team["previous_rank"] is not None
        assert team["rank_change"] is not None


@pytest.mark.anyio
async def test_trends_returns_empty_when_no_snapshots(client: AsyncClient, db_session: AsyncSession):
    """Trends endpoint returns empty weeks list when no snapshots exist."""
    league = await create_league(db_session)
    await create_season(db_session, league, year=2024)

    resp = await client.get(f"{LEAGUE_PREFIX}/power-rankings/2024/trends")
    assert resp.status_code == 200
    body = resp.json()
    assert body["season"] == 2024
    assert body["weeks"] == []
    assert body["teams"] == []


@pytest.mark.anyio
async def test_trends_returns_snapshot_data(client: AsyncClient, db_session: AsyncSession):
    """Trends endpoint returns correct weekly data when snapshots exist."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user = await create_user(db_session, id="u1", username="alice", display_name="Alice")
    await create_roster(db_session, season, user, roster_id=1, team_name="Team Alice")

    for week in (3, 5, 7):
        db_session.add(PowerRankingSnapshot(
            group_id="test_league_001", season_year=2024, week=week, roster_id=1, rank=1,
            total_score=75.0, current_season_score=25.0,
            roster_value_score=35.0, historical_score=15.0,
        ))
    await db_session.flush()

    resp = await client.get(f"{LEAGUE_PREFIX}/power-rankings/2024/trends")
    assert resp.status_code == 200
    body = resp.json()
    assert body["weeks"] == [3, 5, 7]
    assert len(body["teams"]) == 1
    team = body["teams"][0]
    assert team["roster_id"] == 1
    assert len(team["ranks_by_week"]) == 3
    assert all(w["rank"] == 1 for w in team["ranks_by_week"])


@pytest.mark.anyio
async def test_snapshot_endpoint_requires_auth(client: AsyncClient, db_session: AsyncSession):
    """POST /power-rankings/snapshot rejects missing or wrong Authorization."""
    league = await create_league(db_session)
    await create_season(db_session, league, year=2024)

    resp = await client.post(
        f"{LEAGUE_PREFIX}/power-rankings/snapshot",
        params={"season_year": 2024, "week": 6},
        headers={"Authorization": "Bearer wrong-secret"},
    )
    assert resp.status_code == 403

    resp = await client.post(
        f"{LEAGUE_PREFIX}/power-rankings/snapshot",
        params={"season_year": 2024, "week": 6},
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_snapshot_endpoint_saves_snapshot(client: AsyncClient, db_session: AsyncSession):
    """POST /power-rankings/snapshot with correct auth saves rows to DB."""
    # Matches the CRON_SECRET env var set in conftest.py
    cron_secret = "test-cron-secret"

    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user1 = await create_user(db_session, id="u1", username="alice", display_name="Alice")
    user2 = await create_user(db_session, id="u2", username="bob", display_name="Bob")
    await create_roster(db_session, season, user1, roster_id=1)
    await create_roster(db_session, season, user2, roster_id=2)

    resp = await client.post(
        f"{LEAGUE_PREFIX}/power-rankings/snapshot",
        params={"season_year": 2024, "week": 6},
        headers={"Authorization": f"Bearer {cron_secret}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["week"] == 6
    assert body["teams_saved"] == 2

    # Verify rows in DB
    result = await db_session.execute(
        select(PowerRankingSnapshot).where(
            PowerRankingSnapshot.season_year == 2024,
            PowerRankingSnapshot.week == 6,
        )
    )
    snapshots = result.scalars().all()
    assert len(snapshots) == 2
    assert all(s.group_id == "test_league_001" for s in snapshots)


@pytest.mark.anyio
async def test_snapshots_are_league_scoped(client: AsyncClient, db_session: AsyncSession):
    """Same (season, week, roster_id) can exist for two leagues; reads only see own league."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user = await create_user(db_session, id="u1", username="alice", display_name="Alice")
    await create_roster(db_session, season, user, roster_id=1, team_name="Team Alice")

    # Snapshot rows for our league and a sister league, colliding on
    # (season_year, week, roster_id) — the exact pre-fix corruption scenario
    db_session.add(PowerRankingSnapshot(
        group_id="test_league_001", season_year=2024, week=5, roster_id=1, rank=1,
        total_score=80.0, current_season_score=30.0,
        roster_value_score=35.0, historical_score=15.0,
    ))
    db_session.add(PowerRankingSnapshot(
        group_id="other_league_999", season_year=2024, week=5, roster_id=1, rank=9,
        total_score=10.0, current_season_score=3.0,
        roster_value_score=5.0, historical_score=2.0,
    ))
    await db_session.flush()

    # Trends must only include this league's snapshot
    resp = await client.get(f"{LEAGUE_PREFIX}/power-rankings/2024/trends")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["teams"]) == 1
    assert body["teams"][0]["ranks_by_week"] == [
        {"week": 5, "rank": 1, "total_score": 80.0}
    ]

    # rank_change must be computed against this league's rank (1), not the
    # sister league's rank (9)
    resp = await client.get(f"{LEAGUE_PREFIX}/power-rankings/2024")
    assert resp.status_code == 200
    team = resp.json()["rankings"][0]
    assert team["previous_rank"] == 1


@pytest.mark.anyio
async def test_rolling_window_excludes_other_league_games(client: AsyncClient, db_session: AsyncSession):
    """An owner in two leagues must not have games elsewhere counted here.

    u1 loses their only game in this league (50-100). In a sister league they
    win big three times. With correct scoping u1's current_season_score is 0
    (0% wins, 0th percentile points, negative differential, 0-for-recent).
    """
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    u1 = await create_user(db_session, id="u1", username="alice", display_name="Alice")
    u2 = await create_user(db_session, id="u2", username="bob", display_name="Bob")
    r1 = await create_roster(db_session, season, u1, roster_id=1, wins=0, losses=1)
    r2 = await create_roster(db_session, season, u2, roster_id=2, wins=1, losses=0)
    await create_matchup(db_session, season, r1, r2, week=1, matchup_id=1,
                         home_points=50.0, away_points=100.0, winner_roster_id=r2.id)

    # Sister league where u1 dominates
    league_b = await create_league(db_session, id="other_league_999", name="Sister League")
    season_b = await create_season(db_session, league_b, year=2024)
    u3 = await create_user(db_session, id="u3", username="carol", display_name="Carol")
    rb1 = await create_roster(db_session, season_b, u1, roster_id=1)
    rb2 = await create_roster(db_session, season_b, u3, roster_id=2)
    for week in (1, 2, 3):
        await create_matchup(db_session, season_b, rb1, rb2, week=week, matchup_id=1,
                             home_points=200.0, away_points=50.0, winner_roster_id=rb1.id)

    resp = await client.get(f"{LEAGUE_PREFIX}/power-rankings/2024")
    assert resp.status_code == 200
    rankings = {t["user_id"]: t for t in resp.json()["rankings"]}
    assert rankings["u1"]["current_season_score"] == 0.0
    assert rankings["u2"]["rank"] < rankings["u1"]["rank"]


@pytest.mark.anyio
async def test_player_stats_uses_recent_window_not_career_avg(db_session: AsyncSession):
    """_calculate_player_stats averages the last N games, not the whole career."""
    from app.api.routes.power_rankings import _calculate_player_stats

    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user = await create_user(db_session, id="u1", display_name="Alice")
    roster = await create_roster(db_session, season, user, roster_id=1)
    opp = await create_user(db_session, id="u2", display_name="Bob")
    opp_r = await create_roster(db_session, season, opp, roster_id=2)
    player = await create_player(db_session, id="p1", full_name="Star Guy", position="WR")

    # 20 games: first 5 at 0 pts, most recent 15 at 20 pts.
    # Career avg = 15; correct rolling-15 avg = 20.
    for week in range(1, 21):
        m = await create_matchup(db_session, season, roster, opp_r, week=week,
                                 matchup_id=1, home_points=100.0, away_points=90.0)
        await create_matchup_player_point(
            db_session, m, roster, player,
            points=(0.0 if week <= 5 else 20.0),
        )

    stats = await _calculate_player_stats([player.id], db_session, league.id)
    assert stats[player.id] == 20.0


@pytest.mark.anyio
async def test_player_stats_scoped_to_league(db_session: AsyncSession):
    """A player's point rows in another league don't affect this league's PPG."""
    from app.api.routes.power_rankings import _calculate_player_stats

    player = await create_player(db_session, id="p1", full_name="Dual Rostered", position="RB")

    league_a = await create_league(db_session, id="league_a")
    season_a = await create_season(db_session, league_a, year=2024)
    ua1 = await create_user(db_session, id="ua1", display_name="A1")
    ua2 = await create_user(db_session, id="ua2", display_name="A2")
    ra1 = await create_roster(db_session, season_a, ua1, roster_id=1)
    ra2 = await create_roster(db_session, season_a, ua2, roster_id=2)
    ma = await create_matchup(db_session, season_a, ra1, ra2, week=1, matchup_id=1,
                              home_points=100.0, away_points=90.0)
    await create_matchup_player_point(db_session, ma, ra1, player, points=10.0)

    league_b = await create_league(db_session, id="league_b", name="B")
    season_b = await create_season(db_session, league_b, year=2024)
    ub1 = await create_user(db_session, id="ub1", display_name="B1")
    ub2 = await create_user(db_session, id="ub2", display_name="B2")
    rb1 = await create_roster(db_session, season_b, ub1, roster_id=1)
    rb2 = await create_roster(db_session, season_b, ub2, roster_id=2)
    mb = await create_matchup(db_session, season_b, rb1, rb2, week=1, matchup_id=1,
                              home_points=100.0, away_points=90.0)
    await create_matchup_player_point(db_session, mb, rb1, player, points=30.0)

    stats_a = await _calculate_player_stats([player.id], db_session, "league_a")
    stats_b = await _calculate_player_stats([player.id], db_session, "league_b")
    assert stats_a[player.id] == 10.0
    assert stats_b[player.id] == 30.0


@pytest.mark.anyio
async def test_current_season_score_percentile_differentiates_teams(
    client: AsyncClient, db_session: AsyncSession
):
    """The precomputed rolling-window percentile still ranks a high scorer
    above a low scorer (covers the O(n) window precompute path)."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    users = []
    rosters = []
    for i in range(1, 4):
        u = await create_user(db_session, id=f"u{i}", username=f"o{i}", display_name=f"O{i}")
        r = await create_roster(db_session, season, u, roster_id=i, wins=0, losses=0)
        users.append(u)
        rosters.append(r)

    # Each team plays one game; team1 scores highest, team3 lowest
    await create_matchup(db_session, season, rosters[0], rosters[1], week=1, matchup_id=1,
                         home_points=150.0, away_points=90.0, winner_roster_id=rosters[0].id)
    await create_matchup(db_session, season, rosters[2], rosters[0], week=2, matchup_id=1,
                         home_points=70.0, away_points=140.0, winner_roster_id=rosters[0].id)

    resp = await client.get(f"{LEAGUE_PREFIX}/power-rankings/2024")
    assert resp.status_code == 200
    scores = {t["user_id"]: t["current_season_score"] for t in resp.json()["rankings"]}
    # u1 (highest points) outscores u3 (lowest points) on current-season score
    assert scores["u1"] > scores["u3"]


@pytest.mark.anyio
async def test_is_startable_position_aware_age_ceilings():
    """Veteran QBs/WRs/TEs stay startable past 30; RBs don't (position-aware)."""
    from app.api.routes.power_rankings import _is_startable
    from app.models import Player as P

    def mk(pos, age):
        return P(id=f"{pos}{age}", position=pos, age=age, status="Active")

    assert _is_startable(mk("QB", 31)) is True
    assert _is_startable(mk("RB", 31)) is False
    assert _is_startable(mk("WR", 31)) is True
    assert _is_startable(mk("WR", 32)) is False
    assert _is_startable(mk("TE", 32)) is True
    assert _is_startable(mk("QB", 38)) is False
    assert _is_startable(mk("K", 25)) is False
    assert _is_startable(P(id="x", position="RB", age=None, status="Active")) is True
    assert _is_startable(P(id="y", position="QB", age=24, status="Injured Reserve")) is False


@pytest.mark.anyio
async def test_historical_score_weights_and_max():
    """Championships up to 10, playoff appearances up to 10, no baseline, max 20."""
    from app.api.routes.power_rankings import _calculate_historical_score
    from app.models import SeasonAward

    class _FakeResult:
        def __init__(self, awards): self._awards = awards
        def scalars(self): return self
        def all(self): return self._awards

    class _FakeDB:
        def __init__(self, awards): self._awards = awards
        async def execute(self, _q): return _FakeResult(self._awards)

    def champ(): return SeasonAward(season_id=1, user_id="u", award_type="champion")
    def div(): return SeasonAward(season_id=1, user_id="u", award_type="division_winner")

    class _R:
        user_id = "u"

    # No awards -> 0 (no flat baseline anymore)
    assert await _calculate_historical_score(_R(), _FakeDB([])) == 0.0
    # 2 championships: champ cap 10; they're also 2 playoff appearances
    # -> min(10, 2*3.5)=7 -> 17
    assert await _calculate_historical_score(_R(), _FakeDB([champ(), champ()])) == 17.0
    # 2 champs + 1 division title: champ 10, 3 appearances -> min(10, 10.5)=10 -> 20 max
    assert await _calculate_historical_score(_R(), _FakeDB([champ(), champ(), div()])) == 20.0
    # 1 champ + 2 division titles: champ 5, 3 appearances -> 10 -> 15
    assert await _calculate_historical_score(_R(), _FakeDB([champ(), div(), div()])) == 15.0
