from unittest.mock import AsyncMock, patch


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
    with patch("app.services.sync_service.sleeper_client", mock):
        response = await client.post("/api/sync/league")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["season"] == "2024"


async def test_sync_league_external_api_failure(client):
    mock = _make_mock_sleeper_client()
    mock.get_nfl_state.side_effect = Exception("Sleeper API is down")
    with patch("app.services.sync_service.sleeper_client", mock):
        response = await client.post("/api/sync/league")
    assert response.status_code == 500
    assert "Sync failed" in response.json()["detail"]


async def test_sync_league_idempotent(client):
    mock = _make_mock_sleeper_client()
    with patch("app.services.sync_service.sleeper_client", mock):
        response1 = await client.post("/api/sync/league")
        response2 = await client.post("/api/sync/league")
    assert response1.status_code == 200
    assert response2.status_code == 200
