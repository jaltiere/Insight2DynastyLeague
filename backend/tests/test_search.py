import pytest
from tests.conftest import (
    create_player, create_user, create_league, create_season, create_draft,
)


async def test_search_requires_query(client):
    response = await client.get("/api/search")
    assert response.status_code == 422


async def test_search_requires_min_length(client):
    response = await client.get("/api/search?q=a")
    assert response.status_code == 422


async def test_search_returns_structure(client, db_session):
    response = await client.get("/api/search?q=no_match_xyz")
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "results" in data
    assert data["query"] == "no_match_xyz"
    assert data["results"] == []


async def test_search_finds_player_by_name(client, db_session):
    await create_player(
        db_session,
        id="p1",
        full_name="Justin Jefferson",
        first_name="Justin",
        last_name="Jefferson",
        position="WR",
        team="MIN",
    )
    await create_player(
        db_session,
        id="p2",
        full_name="Travis Kelce",
        first_name="Travis",
        last_name="Kelce",
        position="TE",
        team="KC",
    )

    response = await client.get("/api/search?q=Justin")
    assert response.status_code == 200
    data = response.json()
    players = [r for r in data["results"] if r["type"] == "player"]
    assert len(players) == 1
    assert players[0]["id"] == "p1"
    assert players[0]["label"] == "Justin Jefferson"
    assert "WR" in players[0]["subtitle"]
    assert "MIN" in players[0]["subtitle"]


async def test_search_finds_player_by_last_name(client, db_session):
    await create_player(
        db_session,
        id="p1",
        full_name="Patrick Mahomes",
        first_name="Patrick",
        last_name="Mahomes",
        position="QB",
        team="KC",
    )

    response = await client.get("/api/search?q=Mahomes")
    assert response.status_code == 200
    data = response.json()
    player_ids = [r["id"] for r in data["results"] if r["type"] == "player"]
    assert "p1" in player_ids


async def test_search_finds_owner_by_display_name(client, db_session):
    await create_user(db_session, id="u1", username="jsmith", display_name="Jack Smith")
    await create_user(db_session, id="u2", username="bdoe", display_name="Bob Doe")

    response = await client.get("/api/search?q=Jack")
    assert response.status_code == 200
    data = response.json()
    owners = [r for r in data["results"] if r["type"] == "owner"]
    assert len(owners) == 1
    assert owners[0]["id"] == "u1"
    assert owners[0]["label"] == "Jack Smith"
    assert owners[0]["subtitle"] == "Owner"


async def test_search_finds_owner_by_username(client, db_session):
    await create_user(db_session, id="u1", username="dynastyking", display_name="Dave K")

    response = await client.get("/api/search?q=dynastyking")
    assert response.status_code == 200
    data = response.json()
    owners = [r for r in data["results"] if r["type"] == "owner"]
    assert len(owners) == 1
    assert owners[0]["id"] == "u1"


async def test_search_finds_draft_by_year(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2022)
    await create_draft(db_session, season, id="d2022", year=2022, rounds=14, status="complete")

    response = await client.get("/api/search?q=2022")
    assert response.status_code == 200
    data = response.json()
    drafts = [r for r in data["results"] if r["type"] == "draft"]
    assert len(drafts) == 1
    assert drafts[0]["id"] == "d2022"
    assert "2022" in drafts[0]["label"]


async def test_search_finds_draft_by_keyword(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2023)
    await create_draft(db_session, season, id="d2023", year=2023, rounds=14, status="complete")

    response = await client.get("/api/search?q=draft")
    assert response.status_code == 200
    data = response.json()
    drafts = [r for r in data["results"] if r["type"] == "draft"]
    assert len(drafts) >= 1


async def test_search_result_has_required_fields(client, db_session):
    await create_player(
        db_session,
        id="p1",
        full_name="Tyreek Hill",
        first_name="Tyreek",
        last_name="Hill",
        position="WR",
        team="MIA",
    )

    response = await client.get("/api/search?q=Tyreek")
    assert response.status_code == 200
    data = response.json()
    result = next(r for r in data["results"] if r["type"] == "player")
    assert "type" in result
    assert "id" in result
    assert "label" in result
    assert "subtitle" in result


async def test_search_returns_multiple_types(client, db_session):
    await create_player(
        db_session,
        id="p1",
        full_name="Jackson Smith",
        first_name="Jackson",
        last_name="Smith",
        position="RB",
        team="SF",
    )
    await create_user(db_session, id="u1", username="jacksonf", display_name="Jackson Fan")

    response = await client.get("/api/search?q=Jackson")
    assert response.status_code == 200
    data = response.json()
    types = {r["type"] for r in data["results"]}
    assert "player" in types
    assert "owner" in types


async def test_search_is_case_insensitive(client, db_session):
    await create_player(
        db_session,
        id="p1",
        full_name="Derek Carr",
        first_name="Derek",
        last_name="Carr",
        position="QB",
        team="NO",
    )

    response = await client.get("/api/search?q=derek")
    assert response.status_code == 200
    data = response.json()
    player_ids = [r["id"] for r in data["results"] if r["type"] == "player"]
    assert "p1" in player_ids
