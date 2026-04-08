import pytest
from tests.conftest import create_league, create_user, create_season, create_roster, create_player


@pytest.mark.asyncio
async def test_roster_analysis_returns_teams(client, db_session):
    """Teams are returned with roster data for the current season."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    user = await create_user(db_session, id="u1", username="owner1", display_name="Owner One")
    p1 = await create_player(db_session, id="p1", full_name="Patrick Mahomes", position="QB", team="KC", age=29)
    p2 = await create_player(db_session, id="p2", full_name="Breece Hall", position="RB", team="NYJ", age=23)
    await create_roster(db_session, season, user, roster_id=1, players=["p1", "p2"])
    await db_session.commit()

    resp = await client.get("/api/roster-analysis")
    assert resp.status_code == 200
    data = resp.json()

    assert data["season"] == 2025
    assert len(data["teams"]) == 1
    team = data["teams"][0]
    assert team["owner_name"] == "Owner One"
    assert team["player_count"] == 2


@pytest.mark.asyncio
async def test_roster_analysis_empty_when_no_season(client, db_session):
    """Returns empty teams list when no seasons exist."""
    resp = await client.get("/api/roster-analysis")
    assert resp.status_code == 200
    data = resp.json()

    assert data["season"] is None
    assert data["teams"] == []


@pytest.mark.asyncio
async def test_roster_analysis_uses_latest_season(client, db_session):
    """Only returns rosters from the most recent season."""
    league = await create_league(db_session)
    season_old = await create_season(db_session, league, year=2023)
    season_new = await create_season(db_session, league, year=2025)
    user = await create_user(db_session, id="u1", username="owner1", display_name="Owner One")
    player = await create_player(db_session, id="p1", full_name="CeeDee Lamb", position="WR", team="DAL", age=25)
    await create_roster(db_session, season_old, user, roster_id=1, players=["p1"])
    await create_roster(db_session, season_new, user, roster_id=2, players=[])
    await db_session.commit()

    resp = await client.get("/api/roster-analysis")
    data = resp.json()

    assert data["season"] == 2025
    assert data["teams"][0]["player_count"] == 0


@pytest.mark.asyncio
async def test_roster_analysis_classification_assigned(client, db_session):
    """Each team receives a classification string."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    user = await create_user(db_session, id="u1", username="owner1", display_name="Owner One")
    await create_roster(db_session, season, user, roster_id=1, players=[])
    await db_session.commit()

    resp = await client.get("/api/roster-analysis")
    data = resp.json()

    team = data["teams"][0]
    assert team["classification"] in ("Win Now", "Future Contender", "Rebuilding", "Retooling")


@pytest.mark.asyncio
async def test_roster_analysis_positional_counts(client, db_session):
    """Positional counts reflect players on the roster."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    user = await create_user(db_session, id="u1", username="owner1", display_name="Owner One")
    await create_player(db_session, id="p1", full_name="QB One", position="QB", team="KC", age=27)
    await create_player(db_session, id="p2", full_name="QB Two", position="QB", team="SF", age=25)
    await create_player(db_session, id="p3", full_name="RB One", position="RB", team="CLE", age=24)
    await create_roster(db_session, season, user, roster_id=1, players=["p1", "p2", "p3"])
    await db_session.commit()

    resp = await client.get("/api/roster-analysis")
    data = resp.json()

    team = data["teams"][0]
    assert team["positional_counts"].get("QB") == 2
    assert team["positional_counts"].get("RB") == 1


@pytest.mark.asyncio
async def test_roster_analysis_sorted_by_score_descending(client, db_session):
    """Teams are ordered by total roster score, highest first."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    user1 = await create_user(db_session, id="u1", username="owner1", display_name="Alpha")
    user2 = await create_user(db_session, id="u2", username="owner2", display_name="Beta")
    await create_player(db_session, id="p1", full_name="Star QB", position="QB", team="KC", age=27)
    # user1 has a player, user2 has no players → user1 should rank higher
    await create_roster(db_session, season, user1, roster_id=1, players=["p1"])
    await create_roster(db_session, season, user2, roster_id=2, players=[])
    await db_session.commit()

    resp = await client.get("/api/roster-analysis")
    data = resp.json()

    assert data["teams"][0]["owner_name"] == "Alpha"
    assert data["teams"][1]["owner_name"] == "Beta"


@pytest.mark.asyncio
async def test_roster_analysis_response_has_all_fields(client, db_session):
    """Verify all expected top-level and player-level fields are present."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    user = await create_user(db_session, id="u1", username="owner1", display_name="Owner One", avatar="abc123")
    await create_player(db_session, id="p1", full_name="Travis Kelce", position="TE", team="KC", age=35)
    await create_roster(db_session, season, user, roster_id=1, team_name="Dynasty Kings", players=["p1"])
    await db_session.commit()

    resp = await client.get("/api/roster-analysis")
    assert resp.status_code == 200
    data = resp.json()

    assert "season" in data
    assert "teams" in data

    team = data["teams"][0]
    expected_team_fields = {
        "roster_id", "owner_name", "team_name", "avatar",
        "avg_age", "total_roster_score", "player_count",
        "positional_scores", "positional_counts", "classification", "players",
    }
    assert expected_team_fields.issubset(set(team.keys()))
    assert team["avatar"] == "abc123"
    assert team["team_name"] == "Dynasty Kings"

    player = team["players"][0]
    expected_player_fields = {"player_id", "player_name", "position", "team", "age", "power_score"}
    assert expected_player_fields.issubset(set(player.keys()))
