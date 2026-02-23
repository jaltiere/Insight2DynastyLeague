import pytest
from tests.conftest import create_league, create_user, create_season, create_roster, create_player


@pytest.mark.asyncio
async def test_taxi_squads_returns_teams_with_players(client, db_session):
    """Teams with taxi squad players are returned with player details."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    user = await create_user(db_session, id="u1", username="owner1", display_name="Owner One")
    player1 = await create_player(db_session, id="p1", full_name="Bijan Robinson", position="RB", team="ATL")
    player2 = await create_player(db_session, id="p2", full_name="Drake London", position="WR", team="ATL")
    await create_roster(db_session, season, user, roster_id=1, taxi=["p1", "p2"])
    await db_session.commit()

    resp = await client.get("/api/taxi-squads")
    assert resp.status_code == 200
    data = resp.json()

    assert data["season"] == 2025
    assert len(data["teams"]) == 1
    team = data["teams"][0]
    assert team["owner_name"] == "Owner One"
    assert len(team["players"]) == 2
    # RB should come before WR in position order
    assert team["players"][0]["full_name"] == "Bijan Robinson"
    assert team["players"][0]["position"] == "RB"
    assert team["players"][1]["full_name"] == "Drake London"
    assert team["players"][1]["position"] == "WR"


@pytest.mark.asyncio
async def test_taxi_squads_excludes_empty_teams(client, db_session):
    """Teams with empty taxi squads are excluded from the response."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    user1 = await create_user(db_session, id="u1", username="owner1", display_name="Owner One")
    user2 = await create_user(db_session, id="u2", username="owner2", display_name="Owner Two")
    player = await create_player(db_session, id="p1", full_name="Test Player", position="QB", team="KC")
    await create_roster(db_session, season, user1, roster_id=1, taxi=["p1"])
    await create_roster(db_session, season, user2, roster_id=2, taxi=[])
    await db_session.commit()

    resp = await client.get("/api/taxi-squads")
    data = resp.json()

    assert len(data["teams"]) == 1
    assert data["teams"][0]["owner_name"] == "Owner One"


@pytest.mark.asyncio
async def test_taxi_squads_unknown_player_shows_id(client, db_session):
    """Unknown player IDs fall back to showing the player ID as the name."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    user = await create_user(db_session, id="u1", username="owner1", display_name="Owner One")
    await create_roster(db_session, season, user, roster_id=1, taxi=["unknown_999"])
    await db_session.commit()

    resp = await client.get("/api/taxi-squads")
    data = resp.json()

    assert len(data["teams"]) == 1
    player = data["teams"][0]["players"][0]
    assert player["full_name"] == "unknown_999"
    assert player["position"] is None
    assert player["team"] is None


@pytest.mark.asyncio
async def test_taxi_squads_empty_when_no_data(client, db_session):
    """Returns empty teams list when no seasons exist."""
    resp = await client.get("/api/taxi-squads")
    data = resp.json()

    assert data["season"] is None
    assert data["teams"] == []


@pytest.mark.asyncio
async def test_taxi_squads_uses_latest_season(client, db_session):
    """Returns taxi squads from the most recent season only."""
    league = await create_league(db_session)
    season_old = await create_season(db_session, league, year=2023)
    season_new = await create_season(db_session, league, year=2025)
    user = await create_user(db_session, id="u1", username="owner1", display_name="Owner One")
    player = await create_player(db_session, id="p1", full_name="Test Player", position="WR", team="GB")
    await create_roster(db_session, season_old, user, roster_id=1, taxi=["p1"])
    await create_roster(db_session, season_new, user, roster_id=2, taxi=[])
    await db_session.commit()

    resp = await client.get("/api/taxi-squads")
    data = resp.json()

    assert data["season"] == 2025
    # New season roster has no taxi players
    assert len(data["teams"]) == 0


@pytest.mark.asyncio
async def test_taxi_squads_response_has_all_fields(client, db_session):
    """Verify all expected fields are present in the response."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    user = await create_user(db_session, id="u1", username="owner1", display_name="Owner One", avatar="abc123")
    player = await create_player(db_session, id="p1", full_name="Ja'Marr Chase", position="WR", team="CIN")
    await create_roster(db_session, season, user, roster_id=1, team_name="Team Alpha", taxi=["p1"])
    await db_session.commit()

    resp = await client.get("/api/taxi-squads")
    data = resp.json()

    assert "season" in data
    assert "teams" in data
    team = data["teams"][0]
    assert set(team.keys()) == {"owner_name", "team_name", "avatar", "players"}
    assert team["avatar"] == "abc123"
    assert team["team_name"] == "Team Alpha"
    player_data = team["players"][0]
    assert set(player_data.keys()) == {"player_id", "full_name", "position", "team"}
