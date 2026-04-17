import pytest
from app.models import PlayerValue
from tests.conftest import create_league, create_user, create_season, create_roster, create_player


async def _create_player_value(db, player_id: str, value: int, rank: int | None = None, position: str = "WR"):
    pv = PlayerValue(player_id=player_id, ktc_name="test", value=value, rank=rank, position=position, source="ktc")
    db.add(pv)
    await db.flush()
    return pv


@pytest.mark.asyncio
async def test_free_agents_excludes_rostered_players(client, db_session):
    """Players on a current roster are not returned."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    user = await create_user(db_session, id="u1", username="owner1", display_name="Owner One")
    rostered = await create_player(db_session, id="p1", full_name="Rostered Guy", position="WR", team="KC", status="Active")
    free = await create_player(db_session, id="p2", full_name="Free Guy", position="WR", team="GB", status="Active")
    await create_roster(db_session, season, user, roster_id=1, players=["p1"])
    await db_session.commit()

    resp = await client.get("/api/free-agents")
    assert resp.status_code == 200
    data = resp.json()

    ids = [p["player_id"] for p in data["players"]]
    assert "p1" not in ids
    assert "p2" in ids


@pytest.mark.asyncio
async def test_free_agents_excludes_taxi_and_reserve(client, db_session):
    """Players on taxi squad or reserve are also excluded."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    user = await create_user(db_session, id="u1", username="owner1", display_name="Owner One")
    taxi_player = await create_player(db_session, id="p1", full_name="Taxi Guy", position="RB", team="LAR", status="Active")
    reserve_player = await create_player(db_session, id="p2", full_name="Reserve Guy", position="QB", team="DAL", status="Active")
    free = await create_player(db_session, id="p3", full_name="Free Guy", position="TE", team="SF", status="Active")
    await create_roster(db_session, season, user, roster_id=1, taxi=["p1"], reserve=["p2"])
    await db_session.commit()

    resp = await client.get("/api/free-agents")
    data = resp.json()

    ids = [p["player_id"] for p in data["players"]]
    assert "p1" not in ids
    assert "p2" not in ids
    assert "p3" in ids


@pytest.mark.asyncio
async def test_free_agents_sorted_by_ktc_value(client, db_session):
    """Players are returned sorted by KTC value descending."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    user = await create_user(db_session, id="u1", username="owner1", display_name="Owner One")
    await create_roster(db_session, season, user, roster_id=1)
    p_low = await create_player(db_session, id="p1", full_name="Low Value", position="WR", team="NYJ", status="Active")
    p_high = await create_player(db_session, id="p2", full_name="High Value", position="WR", team="KC", status="Active")
    await _create_player_value(db_session, "p1", value=1000, rank=50)
    await _create_player_value(db_session, "p2", value=9000, rank=5)
    await db_session.commit()

    resp = await client.get("/api/free-agents")
    data = resp.json()

    players = data["players"]
    assert players[0]["player_id"] == "p2"
    assert players[1]["player_id"] == "p1"


@pytest.mark.asyncio
async def test_free_agents_position_filter(client, db_session):
    """Position filter returns only players of that position."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    user = await create_user(db_session, id="u1", username="owner1", display_name="Owner One")
    await create_roster(db_session, season, user, roster_id=1)
    await create_player(db_session, id="p1", full_name="QB Player", position="QB", team="KC", status="Active")
    await create_player(db_session, id="p2", full_name="WR Player", position="WR", team="KC", status="Active")
    await db_session.commit()

    resp = await client.get("/api/free-agents", params={"position": "QB"})
    data = resp.json()

    assert all(p["position"] == "QB" for p in data["players"])
    assert any(p["player_id"] == "p1" for p in data["players"])
    assert all(p["player_id"] != "p2" for p in data["players"])


@pytest.mark.asyncio
async def test_free_agents_search_filter(client, db_session):
    """Search filter matches players by name."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    user = await create_user(db_session, id="u1", username="owner1", display_name="Owner One")
    await create_roster(db_session, season, user, roster_id=1)
    await create_player(db_session, id="p1", full_name="Tyreek Hill", first_name="Tyreek", last_name="Hill", position="WR", team="MIA", status="Active")
    await create_player(db_session, id="p2", full_name="Stefon Diggs", first_name="Stefon", last_name="Diggs", position="WR", team="HOU", status="Active")
    await db_session.commit()

    resp = await client.get("/api/free-agents", params={"search": "Tyreek"})
    data = resp.json()

    assert data["total"] == 1
    assert data["players"][0]["player_id"] == "p1"


@pytest.mark.asyncio
async def test_free_agents_excludes_inactive_players(client, db_session):
    """Inactive players are not shown as free agents."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    user = await create_user(db_session, id="u1", username="owner1", display_name="Owner One")
    await create_roster(db_session, season, user, roster_id=1)
    await create_player(db_session, id="p1", full_name="Active Player", position="RB", team="KC", status="Active")
    await create_player(db_session, id="p2", full_name="Inactive Player", position="RB", team="FA", status="Inactive")
    await db_session.commit()

    resp = await client.get("/api/free-agents")
    data = resp.json()

    ids = [p["player_id"] for p in data["players"]]
    assert "p1" in ids
    assert "p2" not in ids


@pytest.mark.asyncio
async def test_free_agents_response_has_all_fields(client, db_session):
    """Response contains all expected top-level and player fields."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    user = await create_user(db_session, id="u1", username="owner1", display_name="Owner One")
    await create_roster(db_session, season, user, roster_id=1)
    await create_player(db_session, id="p1", full_name="Ja'Marr Chase", position="WR", team="CIN", status="Active", age=25, years_exp=3)
    await _create_player_value(db_session, "p1", value=8500, rank=12)
    await db_session.commit()

    resp = await client.get("/api/free-agents")
    assert resp.status_code == 200
    data = resp.json()

    assert set(data.keys()) >= {"total", "limit", "offset", "season", "players"}
    assert data["season"] == 2025
    assert data["total"] == 1

    player = data["players"][0]
    assert set(player.keys()) == {
        "player_id", "full_name", "position", "team",
        "age", "years_exp", "ktc_value", "ktc_rank",
        "status", "injury_status",
    }
    assert player["ktc_value"] == 8500
    assert player["ktc_rank"] == 12


@pytest.mark.asyncio
async def test_free_agents_empty_when_no_season(client, db_session):
    """Returns empty list when no season exists."""
    resp = await client.get("/api/free-agents")
    data = resp.json()

    assert data["season"] is None
    assert data["players"] == []
    assert data["total"] == 0
