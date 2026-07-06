import pytest
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from app.models import Matchup, Roster

# A single-entry LEAGUES list that matches the test DB's league_id so we don't
# run 4 real-league syncs in unit tests.
_TEST_LEAGUES = [{"id": "test_league_001", "slug": "test", "recaps_enabled": False}]

# Matches the CRON_SECRET env var set in conftest.py
_AUTH = {"Authorization": "Bearer test-cron-secret"}


@pytest.fixture(autouse=True)
def mock_ktc_refresh():
    """Prevent sync tests from making real HTTP calls to keeptradecut.com."""
    with patch(
        "app.services.ktc_service.refresh_ktc_values",
        new=AsyncMock(return_value={"status": "mocked"}),
    ) as mocked:
        yield mocked


def _make_mock_sleeper_client():
    """Create a mock SleeperClient with valid return data for all methods."""
    mock = AsyncMock()
    mock.get_nfl_state.return_value = {"season": "2024", "week": 2}
    mock.get_league.return_value = {
        "league_id": "test_league_001",
        "name": "Test League",
        "season": "2024",
        "status": "in_season",
        "settings": {"divisions": 2, "playoff_week_start": 15, "playoff_rounds": 3},
        "scoring_settings": {},
        "roster_positions": [],
    }
    mock.get_users.return_value = [
        {"user_id": "u1", "username": "owner1", "display_name": "Owner One", "avatar": "av1"},
    ]
    mock.get_rosters.return_value = [
        {
            "roster_id": 1,
            "owner_id": "u1",
            "players": ["p1"],
            "starters": ["p1"],
            "reserve": [],
            "taxi": [],
            "settings": {"wins": 5, "losses": 2, "ties": 0, "fpts": 800, "fpts_against": 700, "division": 1},
        },
    ]
    mock.get_matchups.return_value = []
    mock.get_drafts.return_value = []
    mock.get_all_players.return_value = {}
    return mock


async def test_sync_league_success(client):
    mock = _make_mock_sleeper_client()
    with patch("app.api.routes.sync.LEAGUES", _TEST_LEAGUES), \
         patch("app.services.sync_service.sleeper_client", mock):
        response = await client.post("/api/sync/league", headers=_AUTH)
    assert response.status_code == 200
    data = response.json()
    assert len(data["leagues"]) == 1
    assert data["leagues"][0]["status"] == "success"
    assert data["leagues"][0]["season"] == 2024
    assert data["errors"] == []


async def test_sync_league_external_api_failure(client):
    mock = _make_mock_sleeper_client()
    mock.get_nfl_state.side_effect = Exception("Sleeper API is down")
    with patch("app.api.routes.sync.LEAGUES", _TEST_LEAGUES), \
         patch("app.services.sync_service.sleeper_client", mock):
        response = await client.post("/api/sync/league", headers=_AUTH)
    assert response.status_code == 500
    assert "All syncs failed" in response.json()["detail"]


async def test_sync_league_idempotent(client):
    mock = _make_mock_sleeper_client()
    with patch("app.api.routes.sync.LEAGUES", _TEST_LEAGUES), \
         patch("app.services.sync_service.sleeper_client", mock):
        response1 = await client.post("/api/sync/league", headers=_AUTH)
        response2 = await client.post("/api/sync/league", headers=_AUTH)
    assert response1.status_code == 200
    assert response2.status_code == 200


async def test_sync_offseason_transactions(client):
    """Test that offseason transactions (week 0) sync weeks 1-3."""
    mock = _make_mock_sleeper_client()
    # Override NFL state to be offseason
    mock.get_nfl_state.return_value = {
        "season": "2026",
        "week": 0,
        "season_type": "off",
    }
    mock.get_league.return_value = {
        "league_id": "test_league_001",
        "name": "Test League Offseason",
        "season": "2026",
        "status": "pre_draft",
        "settings": {"divisions": 2, "playoff_week_start": 15, "playoff_rounds": 3},
        "scoring_settings": {},
        "roster_positions": [],
    }
    # Mock transactions for weeks 1-3
    mock.get_transactions.return_value = [
        {
            "transaction_id": "txn_offseason_1",
            "type": "free_agent",
            "status": "complete",
            "adds": None,
            "drops": {"8125": 2},  # Calvin Austin dropped
            "roster_ids": [2],
            "players": [],
            "draft_picks": [],
            "settings": {},
            "status_updated": 1710072000000,  # March 10, 2026
        }
    ]

    with patch("app.api.routes.sync.LEAGUES", _TEST_LEAGUES), \
         patch("app.services.sync_service.sleeper_client", mock):
        response = await client.post("/api/sync/league", headers=_AUTH)

    assert response.status_code == 200
    data = response.json()
    assert data["leagues"][0]["status"] == "success"
    assert data["leagues"][0]["season"] == 2026

    # Verify that get_transactions was called for weeks 1, 2, and 3
    # (not just week 0 or week 1)
    calls = mock.get_transactions.call_args_list
    weeks_called = [call[0][0] for call in calls]
    assert 1 in weeks_called
    assert 2 in weeks_called
    assert 3 in weeks_called


async def test_sync_regular_season_transactions(client):
    """Test that regular season transactions sync up to current week."""
    mock = _make_mock_sleeper_client()
    # Override NFL state to be week 5 of regular season
    mock.get_nfl_state.return_value = {
        "season": "2025",
        "week": 5,
        "season_type": "regular",
    }
    mock.get_league.return_value = {
        "league_id": "test_league_001",
        "name": "Test League Regular",
        "season": "2025",
        "status": "in_season",
        "settings": {"divisions": 2, "playoff_week_start": 15, "playoff_rounds": 3},
        "scoring_settings": {},
        "roster_positions": [],
    }
    mock.get_transactions.return_value = []

    with patch("app.api.routes.sync.LEAGUES", _TEST_LEAGUES), \
         patch("app.services.sync_service.sleeper_client", mock):
        response = await client.post("/api/sync/league", headers=_AUTH)

    assert response.status_code == 200
    data = response.json()
    assert data["leagues"][0]["status"] == "success"

    # Verify that get_transactions was called for weeks 1-5
    calls = mock.get_transactions.call_args_list
    weeks_called = [call[0][0] for call in calls]
    assert 1 in weeks_called
    assert 5 in weeks_called
    # Should NOT call week 6 or beyond
    assert 6 not in weeks_called


async def test_sync_rosters_preserve_fractional_points(client, db_session):
    """points_for/points_against keep Sleeper's fpts_decimal fraction."""
    mock = _make_mock_sleeper_client()
    mock.get_rosters.return_value = [
        {
            "roster_id": 1,
            "owner_id": "u1",
            "players": [],
            "starters": [],
            "reserve": [],
            "taxi": [],
            "settings": {
                "wins": 5, "losses": 2, "ties": 0,
                "fpts": 800, "fpts_decimal": 55,
                "fpts_against": 700, "fpts_against_decimal": 25,
                "division": 1,
            },
        },
    ]

    with patch("app.api.routes.sync.LEAGUES", _TEST_LEAGUES), \
         patch("app.services.sync_service.sleeper_client", mock):
        response = await client.post("/api/sync/league", headers=_AUTH)

    assert response.status_code == 200
    result = await db_session.execute(select(Roster))
    roster = result.scalars().one()
    assert roster.points_for == pytest.approx(800.55)
    assert roster.points_against == pytest.approx(700.25)


def _matchup_entry(roster_id: int, points: float) -> dict:
    return {
        "roster_id": roster_id,
        "matchup_id": 1,
        "points": points,
        "players_points": {},
        "starters": [],
    }


async def test_resync_keeps_home_away_assignment_stable(client, db_session):
    """Re-syncing with the matchup pair in reversed order must not swap scores.

    home_roster_id is fixed at matchup creation; a later sync that receives the
    two teams in the opposite order has to update home/away points for the
    same rosters, not by position in the API response.
    """
    mock = _make_mock_sleeper_client()
    mock.get_nfl_state.return_value = {"season": "2024", "week": 1, "season_type": "regular"}
    mock.get_rosters.return_value = [
        {
            "roster_id": rid, "owner_id": "u1", "players": [], "starters": [],
            "reserve": [], "taxi": [],
            "settings": {"wins": 0, "losses": 0, "ties": 0, "fpts": 0, "fpts_against": 0, "division": 1},
        }
        for rid in (1, 2)
    ]

    with patch("app.api.routes.sync.LEAGUES", _TEST_LEAGUES), \
         patch("app.services.sync_service.sleeper_client", mock):
        # First sync: roster 1 listed first -> becomes home
        mock.get_matchups.return_value = [_matchup_entry(1, 100.5), _matchup_entry(2, 90.25)]
        response1 = await client.post("/api/sync/league", headers=_AUTH)

        # Second sync: Sleeper returns the pair in reversed order with new points
        mock.get_matchups.return_value = [_matchup_entry(2, 95.5), _matchup_entry(1, 105.75)]
        response2 = await client.post("/api/sync/league", headers=_AUTH)

    assert response1.status_code == 200
    assert response2.status_code == 200

    result = await db_session.execute(select(Matchup))
    matchup = result.scalars().one()
    result = await db_session.execute(select(Roster).where(Roster.id == matchup.home_roster_id))
    home_roster = result.scalars().one()

    # Home is still roster 1, and its updated score (105.75) stays on the home side
    assert home_roster.roster_id == 1
    assert matchup.home_points == pytest.approx(105.75)
    assert matchup.away_points == pytest.approx(95.5)
    assert matchup.winner_roster_id == matchup.home_roster_id


async def test_sync_endpoints_require_auth(client):
    """All sync endpoints reject requests without an Authorization header."""
    for path in ("/api/sync/league", "/api/sync/history", "/api/cron/sync"):
        response = await client.post(path)
        assert response.status_code == 401, path


async def test_sync_endpoints_reject_wrong_token(client):
    """All sync endpoints reject requests with an incorrect bearer token."""
    headers = {"Authorization": "Bearer wrong-secret"}
    for path in ("/api/sync/league", "/api/sync/history", "/api/cron/sync"):
        response = await client.post(path, headers=headers)
        assert response.status_code == 403, path


async def test_sync_endpoints_reject_unconfigured_secret(client, monkeypatch):
    """Endpoints return 503 when CRON_SECRET is unset or the shipped placeholder."""
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "CRON_SECRET", "change-me-in-production")
    response = await client.post("/api/sync/league", headers=_AUTH)
    assert response.status_code == 503

    monkeypatch.setattr(get_settings(), "CRON_SECRET", "")
    response = await client.post("/api/sync/league", headers=_AUTH)
    assert response.status_code == 503


async def test_cron_sync_with_valid_auth(client):
    """POST /api/cron/sync succeeds with the correct bearer token."""
    mock = _make_mock_sleeper_client()
    with patch("app.api.routes.sync.LEAGUES", _TEST_LEAGUES), \
         patch("app.services.sync_service.sleeper_client", mock):
        response = await client.post("/api/cron/sync", headers=_AUTH)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
