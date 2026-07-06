"""Tests for matchup recap read endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    LEAGUE_PREFIX,
    create_league,
    create_season,
    create_user,
    create_roster,
    create_matchup,
)


@pytest.mark.anyio
async def test_week_recaps_returns_matchups(client: AsyncClient, db_session: AsyncSession):
    """Week endpoint returns matchups with owner display names."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user1 = await create_user(db_session, id="u1", username="alice", display_name="Alice")
    user2 = await create_user(db_session, id="u2", username="bob", display_name="Bob")
    r1 = await create_roster(db_session, season, user1, roster_id=1)
    r2 = await create_roster(db_session, season, user2, roster_id=2)
    await create_matchup(db_session, season, r1, r2, week=3)

    resp = await client.get(f"{LEAGUE_PREFIX}/matchup-recaps/week/3", params={"season": 2024})
    assert resp.status_code == 200
    body = resp.json()
    assert body["week"] == 3
    assert len(body["recaps"]) == 1
    assert body["recaps"][0]["home_team"] == "Alice"
    assert body["recaps"][0]["away_team"] == "Bob"


@pytest.mark.anyio
async def test_week_recaps_tolerates_ownerless_roster(client: AsyncClient, db_session: AsyncSession):
    """A roster with no owner (user_id NULL) must not 500 the recap page."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user1 = await create_user(db_session, id="u1", username="alice", display_name="Alice")
    user2 = await create_user(db_session, id="u2", username="bob", display_name="Bob")
    r1 = await create_roster(db_session, season, user1, roster_id=1)
    # Ownerless roster: Sleeper allows user-less teams mid-transition
    r2 = await create_roster(
        db_session, season, user2, roster_id=2, user_id=None, team_name="Orphan FC"
    )
    await create_matchup(db_session, season, r1, r2, week=3)

    resp = await client.get(f"{LEAGUE_PREFIX}/matchup-recaps/week/3", params={"season": 2024})
    assert resp.status_code == 200
    recap = resp.json()["recaps"][0]
    assert recap["home_team"] == "Alice"
    assert recap["away_team"] == "Orphan FC"
