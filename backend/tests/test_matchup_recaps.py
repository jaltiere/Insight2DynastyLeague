"""Tests for matchup recap read endpoints."""
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

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


@contextmanager
def mock_nfl_state(**state):
    """Patch the Sleeper NFL state the recap routes read."""
    mock = AsyncMock()
    mock.get_nfl_state.return_value = state
    with patch("app.api.routes.matchup_recaps.sleeper_client", mock):
        yield mock


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


@pytest.mark.anyio
async def test_bracket_label_from_placement(client: AsyncClient, db_session: AsyncSession):
    """Labels come from Sleeper bracket placement, not hardcoded matchup IDs."""
    league = await create_league(db_session, settings={"playoff_teams": 6})
    season = await create_season(db_session, league, year=2024)
    u1 = await create_user(db_session, id="u1", username="alice", display_name="Alice")
    u2 = await create_user(db_session, id="u2", username="bob", display_name="Bob")
    r1 = await create_roster(db_session, season, u1, roster_id=1)
    r2 = await create_roster(db_session, season, u2, roster_id=2)

    # Championship in week 16 with a non-1 matchup_id: the old heuristic
    # (week >= 17, matchup_id == 1) would have missed both conditions
    await create_matchup(db_session, season, r1, r2, week=16, matchup_id=7,
                         match_type="playoff", bracket_placement=1)
    # Consolation 3rd-place game: overall finish = 6 playoff teams + 3 = 9th
    await create_matchup(db_session, season, r1, r2, week=16, matchup_id=8,
                         match_type="consolation", bracket_placement=3)

    resp = await client.get(f"{LEAGUE_PREFIX}/matchup-recaps/week/16", params={"season": 2024})
    assert resp.status_code == 200
    labels = {r["recap_metadata"]["match_type"]: r["recap_metadata"].get("bracket_label")
              for r in resp.json()["recaps"]}
    assert labels["playoff"] == "🏆 Championship"
    assert labels["consolation"] == "🎯 9th Place"


@pytest.mark.anyio
async def test_bracket_label_legacy_fallback(client: AsyncClient, db_session: AsyncSession):
    """Rows without bracket_placement still get labels from the old layout."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2023)
    u1 = await create_user(db_session, id="u1", username="alice", display_name="Alice")
    u2 = await create_user(db_session, id="u2", username="bob", display_name="Bob")
    r1 = await create_roster(db_session, season, u1, roster_id=1)
    r2 = await create_roster(db_session, season, u2, roster_id=2)

    await create_matchup(db_session, season, r1, r2, week=17, matchup_id=1,
                         match_type="playoff", bracket_placement=None)

    resp = await client.get(f"{LEAGUE_PREFIX}/matchup-recaps/week/17", params={"season": 2023})
    assert resp.status_code == 200
    recap = resp.json()["recaps"][0]
    assert recap["recap_metadata"]["bracket_label"] == "🏆 Championship"


@pytest.mark.anyio
async def test_current_week_preseason_returns_empty(client: AsyncClient, db_session: AsyncSession):
    """Preseason (season_type 'pre') has no real games, so report week 0 like the offseason.

    Sleeper reports week 1 / 'pre' from the season start date until the regular
    season opens. Serving those placeholder matchups made the page render nothing.
    """
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2026)
    u1 = await create_user(db_session, id="u1", username="alice", display_name="Alice")
    u2 = await create_user(db_session, id="u2", username="bob", display_name="Bob")
    r1 = await create_roster(db_session, season, u1, roster_id=1)
    r2 = await create_roster(db_session, season, u2, roster_id=2)
    # Week 1 rows exist in the DB during preseason but have never been played
    await create_matchup(db_session, season, r1, r2, week=1)

    with mock_nfl_state(season="2026", week=1, season_type="pre"):
        resp = await client.get(f"{LEAGUE_PREFIX}/matchup-recaps/current")

    assert resp.status_code == 200
    body = resp.json()
    assert body["week"] == 0
    assert body["matchups"] == []


@pytest.mark.anyio
async def test_current_week_regular_season_returns_week_one(
    client: AsyncClient, db_session: AsyncSession
):
    """Once the regular season opens, week 1 predictions must be served."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2026)
    u1 = await create_user(db_session, id="u1", username="alice", display_name="Alice")
    u2 = await create_user(db_session, id="u2", username="bob", display_name="Bob")
    r1 = await create_roster(db_session, season, u1, roster_id=1)
    r2 = await create_roster(db_session, season, u2, roster_id=2)
    await create_matchup(db_session, season, r1, r2, week=1)

    with mock_nfl_state(season="2026", week=1, season_type="regular"):
        resp = await client.get(f"{LEAGUE_PREFIX}/matchup-recaps/current")

    assert resp.status_code == 200
    body = resp.json()
    assert body["week"] == 1
    assert len(body["matchups"]) == 1


@pytest.mark.anyio
async def test_previous_week_preseason_shows_last_season(
    client: AsyncClient, db_session: AsyncSession
):
    """Preseason keeps showing last season's championship, same as the offseason."""
    league = await create_league(db_session)
    prior = await create_season(db_session, league, year=2025)
    u1 = await create_user(db_session, id="u1", username="alice", display_name="Alice")
    u2 = await create_user(db_session, id="u2", username="bob", display_name="Bob")
    r1 = await create_roster(db_session, prior, u1, roster_id=1)
    r2 = await create_roster(db_session, prior, u2, roster_id=2)
    await create_matchup(db_session, prior, r1, r2, week=17, matchup_id=1,
                         match_type="playoff", bracket_placement=1)

    with mock_nfl_state(season="2026", week=1, season_type="pre"):
        resp = await client.get(f"{LEAGUE_PREFIX}/matchup-recaps/previous")

    assert resp.status_code == 200
    body = resp.json()
    assert body["week"] == 17
    assert body["season"] == 2025
    assert len(body["recaps"]) == 1


# Matches the CRON_SECRET env var set in conftest.py
_AUTH = {"Authorization": "Bearer test-cron-secret"}


@pytest.mark.anyio
@pytest.mark.parametrize("endpoint", ["regenerate", "regenerate-predictions"])
async def test_regenerate_skipped_during_preseason(client: AsyncClient, endpoint: str):
    """Preseason must not burn Claude tokens on games that have not been scheduled."""
    with mock_nfl_state(season="2026", week=1, season_type="pre"):
        resp = await client.post(f"{LEAGUE_PREFIX}/matchup-recaps/{endpoint}/1", headers=_AUTH)

    assert resp.status_code == 200
    assert resp.json()["status"] == "skipped"


@pytest.mark.anyio
@pytest.mark.parametrize("endpoint", ["regenerate", "regenerate-predictions"])
async def test_regenerate_force_overrides_preseason(client: AsyncClient, endpoint: str):
    """?force=true still bypasses the guard.

    With no season row present the request falls through to a 404, which proves
    it got past the preseason check rather than short-circuiting to "skipped".
    """
    with mock_nfl_state(season="2026", week=1, season_type="pre"):
        resp = await client.post(
            f"{LEAGUE_PREFIX}/matchup-recaps/{endpoint}/1",
            params={"season": 2026, "force": "true"},
            headers=_AUTH,
        )

    assert resp.status_code == 404
