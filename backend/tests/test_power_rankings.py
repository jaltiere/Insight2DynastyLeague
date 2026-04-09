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

    resp = await client.get("/api/power-rankings")
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

    resp = await client.get("/api/power-rankings")
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

    resp = await client.get("/api/power-rankings")
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
        season_year=2024, week=5, roster_id=1, rank=2,
        total_score=60.0, current_season_score=20.0,
        roster_value_score=30.0, historical_score=10.0,
    ))
    db_session.add(PowerRankingSnapshot(
        season_year=2024, week=5, roster_id=2, rank=1,
        total_score=65.0, current_season_score=25.0,
        roster_value_score=30.0, historical_score=10.0,
    ))
    await db_session.flush()

    resp = await client.get("/api/power-rankings")
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

    resp = await client.get("/api/power-rankings/2024/trends")
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
            season_year=2024, week=week, roster_id=1, rank=1,
            total_score=75.0, current_season_score=25.0,
            roster_value_score=35.0, historical_score=15.0,
        ))
    await db_session.flush()

    resp = await client.get("/api/power-rankings/2024/trends")
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
    """POST /power-rankings/snapshot returns 401 without correct Authorization."""
    league = await create_league(db_session)
    await create_season(db_session, league, year=2024)

    resp = await client.post(
        "/api/power-rankings/snapshot",
        params={"season_year": 2024, "week": 6},
        headers={"Authorization": "Bearer wrong-secret"},
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_snapshot_endpoint_saves_snapshot(client: AsyncClient, db_session: AsyncSession):
    """POST /power-rankings/snapshot with correct auth saves rows to DB."""
    # Default CRON_SECRET from config.py is "change-me-in-production"
    cron_secret = "change-me-in-production"

    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user1 = await create_user(db_session, id="u1", username="alice", display_name="Alice")
    user2 = await create_user(db_session, id="u2", username="bob", display_name="Bob")
    await create_roster(db_session, season, user1, roster_id=1)
    await create_roster(db_session, season, user2, roster_id=2)

    resp = await client.post(
        "/api/power-rankings/snapshot",
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
