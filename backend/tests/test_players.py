from tests.conftest import create_player


async def test_get_players_default(client, db_session):
    await create_player(db_session, id="p1", full_name="Aaron Rodgers", first_name="Aaron", last_name="Rodgers", position="QB", team="NYJ")
    await create_player(db_session, id="p2", full_name="Derrick Henry", first_name="Derrick", last_name="Henry", position="RB", team="TEN")
    await create_player(db_session, id="p3", full_name="Tyreek Hill", first_name="Tyreek", last_name="Hill", position="WR", team="MIA")

    response = await client.get("/api/players")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["players"]) == 3
    assert data["limit"] == 50
    assert data["offset"] == 0


async def test_get_players_search_by_name(client, db_session):
    await create_player(db_session, id="p1", full_name="Patrick Mahomes", first_name="Patrick", last_name="Mahomes")
    await create_player(db_session, id="p2", full_name="Travis Kelce", first_name="Travis", last_name="Kelce")
    await create_player(db_session, id="p3", full_name="Patrick Surtain", first_name="Patrick", last_name="Surtain")

    response = await client.get("/api/players?search=Patrick")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    names = {p["full_name"] for p in data["players"]}
    assert "Patrick Mahomes" in names
    assert "Patrick Surtain" in names


async def test_get_players_filter_by_position(client, db_session):
    await create_player(db_session, id="p1", full_name="QB Player", position="QB")
    await create_player(db_session, id="p2", full_name="RB Player", position="RB")
    await create_player(db_session, id="p3", full_name="WR Player", position="WR")

    response = await client.get("/api/players?position=QB")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["players"][0]["position"] == "QB"


async def test_get_players_filter_by_team(client, db_session):
    await create_player(db_session, id="p1", full_name="KC Player", team="KC")
    await create_player(db_session, id="p2", full_name="DAL Player", team="DAL")

    response = await client.get("/api/players?team=KC")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["players"][0]["team"] == "KC"


async def test_get_players_combined_filters(client, db_session):
    await create_player(db_session, id="p1", full_name="KC QB", position="QB", team="KC")
    await create_player(db_session, id="p2", full_name="DAL QB", position="QB", team="DAL")
    await create_player(db_session, id="p3", full_name="KC RB", position="RB", team="KC")

    response = await client.get("/api/players?position=QB&team=KC")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["players"][0]["full_name"] == "KC QB"


async def test_get_players_pagination(client, db_session):
    for i in range(5):
        await create_player(db_session, id=f"p{i}", full_name=f"Player {i:02d}", first_name="Player", last_name=f"{i:02d}")

    response = await client.get("/api/players?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["players"]) == 2

    response2 = await client.get("/api/players?limit=2&offset=2")
    data2 = response2.json()
    assert len(data2["players"]) == 2
    # Different players than first page
    first_ids = {p["id"] for p in data["players"]}
    second_ids = {p["id"] for p in data2["players"]}
    assert first_ids.isdisjoint(second_ids)


async def test_get_players_empty_database(client):
    response = await client.get("/api/players")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["players"] == []


async def test_get_player_details_success(client, db_session):
    await create_player(db_session, id="mahomes_1", full_name="Patrick Mahomes", college="Texas Tech")

    response = await client.get("/api/players/mahomes_1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "mahomes_1"
    assert data["full_name"] == "Patrick Mahomes"
    assert data["college"] == "Texas Tech"
    # Verify all detail fields are present
    for key in ["first_name", "last_name", "position", "team", "number", "age",
                "height", "weight", "years_exp", "status", "injury_status", "stats"]:
        assert key in data


async def test_get_player_details_not_found(client):
    response = await client.get("/api/players/nonexistent_id")
    assert response.status_code == 404
    assert "Player not found" in response.json()["detail"]


async def test_get_players_position_case_insensitive(client, db_session):
    await create_player(db_session, id="p1", full_name="QB Player", position="QB")

    response = await client.get("/api/players?position=qb")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
