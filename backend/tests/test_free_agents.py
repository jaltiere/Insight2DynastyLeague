from tests.conftest import LEAGUE_PREFIX
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

    resp = await client.get(f"{LEAGUE_PREFIX}/free-agents")
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

    resp = await client.get(f"{LEAGUE_PREFIX}/free-agents")
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

    resp = await client.get(f"{LEAGUE_PREFIX}/free-agents")
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

    resp = await client.get(f"{LEAGUE_PREFIX}/free-agents", params={"position": "QB"})
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

    resp = await client.get(f"{LEAGUE_PREFIX}/free-agents", params={"search": "Tyreek"})
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

    resp = await client.get(f"{LEAGUE_PREFIX}/free-agents")
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

    resp = await client.get(f"{LEAGUE_PREFIX}/free-agents")
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
    resp = await client.get(f"{LEAGUE_PREFIX}/free-agents")
    data = resp.json()

    assert data["season"] is None
    assert data["players"] == []
    assert data["total"] == 0


# --- league-aware values and startable positions -----------------------------

@pytest.mark.asyncio
async def test_free_agents_excludes_kickers(client, db_session):
    """No configured league starts a kicker as of 2026, so they are not
    meaningful free agents."""
    league = await create_league(db_session)
    await create_season(db_session, league, year=2026)
    await create_player(db_session, id="k1", full_name="Some Kicker", position="K", team="KC", status="Active", years_exp=3)
    await create_player(db_session, id="w1", full_name="Some Receiver", position="WR", team="GB", status="Active", years_exp=3)
    await db_session.commit()

    resp = await client.get(f"{LEAGUE_PREFIX}/free-agents")
    assert resp.status_code == 200

    ids = [p["player_id"] for p in resp.json()["players"]]
    assert "k1" not in ids
    assert "w1" in ids


@pytest.mark.asyncio
async def test_free_agents_use_the_leagues_value_format(client, db_session):
    """A superflex TE-premium league must not read 1QB base values."""
    league = await create_league(
        db_session,
        roster_positions=["QB", "RB", "WR", "TE", "FLEX", "SUPER_FLEX"],
        scoring_settings={"bonus_rec_te": 0.5},
    )
    await create_season(db_session, league, year=2026)
    await create_player(db_session, id="te1", full_name="Premium TE", position="TE", team="LV", status="Active", years_exp=2)
    db_session.add(
        PlayerValue(
            player_id="te1", ktc_name="Premium TE", position="TE", source="ktc",
            value=8280, rank=6,
            superflex_value=8222, superflex_rank=9,
            tep_value=9161, tep_rank=5,
            superflex_tep_value=9098, superflex_tep_rank=7,
        )
    )
    await db_session.commit()

    resp = await client.get(f"{LEAGUE_PREFIX}/free-agents")
    assert resp.status_code == 200

    te = next(p for p in resp.json()["players"] if p["player_id"] == "te1")
    assert te["ktc_value"] == 9098
    assert te["ktc_rank"] == 7


@pytest.mark.asyncio
async def test_free_agents_sort_by_the_leagues_value_not_the_base(client, db_session):
    """Ordering happens in SQL alongside pagination, so it must use the same
    column the response reports."""
    league = await create_league(
        db_session,
        roster_positions=["QB", "RB", "WR", "TE", "FLEX", "SUPER_FLEX"],
        scoring_settings={"bonus_rec_te": 0.5},
    )
    await create_season(db_session, league, year=2026)
    await create_player(db_session, id="te1", full_name="Premium TE", position="TE", team="LV", status="Active", years_exp=2)
    await create_player(db_session, id="wr1", full_name="Plain WR", position="WR", team="GB", status="Active", years_exp=2)
    # Base values rank the WR first; the premium column flips the order.
    db_session.add(PlayerValue(player_id="te1", ktc_name="Premium TE", position="TE", source="ktc", value=8000, superflex_value=8000, tep_value=9500, superflex_tep_value=9500))
    db_session.add(PlayerValue(player_id="wr1", ktc_name="Plain WR", position="WR", source="ktc", value=9000, superflex_value=9000, tep_value=9000, superflex_tep_value=9000))
    await db_session.commit()

    resp = await client.get(f"{LEAGUE_PREFIX}/free-agents")
    ids = [p["player_id"] for p in resp.json()["players"]]

    assert ids.index("te1") < ids.index("wr1")
