from tests.conftest import create_league, create_season, create_user, create_roster


async def test_get_all_owners_success(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user1 = await create_user(db_session, id="u1", display_name="Owner One")
    user2 = await create_user(db_session, id="u2", display_name="Owner Two")
    await create_roster(db_session, season, user1, roster_id=1, wins=10, losses=4)
    await create_roster(db_session, season, user2, roster_id=2, wins=8, losses=6)

    response = await client.get("/api/owners")
    assert response.status_code == 200
    data = response.json()
    assert data["total_owners"] == 2
    # Sorted by total_wins descending
    assert data["owners"][0]["total_wins"] == 10
    assert data["owners"][1]["total_wins"] == 8


async def test_get_all_owners_empty(client):
    response = await client.get("/api/owners")
    assert response.status_code == 200
    data = response.json()
    assert data["total_owners"] == 0
    assert data["owners"] == []


async def test_get_owner_details_success(client, db_session):
    league = await create_league(db_session)
    s2023 = await create_season(db_session, league, year=2023)
    s2024 = await create_season(db_session, league, year=2024)
    user = await create_user(db_session, id="u1")
    await create_roster(db_session, s2023, user, roster_id=1, wins=8, losses=6, points_for=1100, points_against=1000)
    await create_roster(db_session, s2024, user, roster_id=2, wins=10, losses=4, points_for=1500, points_against=1200)

    response = await client.get("/api/owners/u1")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "u1"
    assert data["career_stats"]["seasons_played"] == 2
    assert data["career_stats"]["total_wins"] == 18
    assert data["career_stats"]["total_losses"] == 10
    assert data["career_stats"]["total_points_for"] == 2600
    assert data["career_stats"]["total_points_against"] == 2200


async def test_get_owner_details_not_found(client):
    response = await client.get("/api/owners/nonexistent")
    assert response.status_code == 404
    assert "Owner not found" in response.json()["detail"]


async def test_owner_career_win_percentage(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user = await create_user(db_session, id="u1")
    await create_roster(db_session, season, user, roster_id=1, wins=7, losses=7, ties=0)

    response = await client.get("/api/owners/u1")
    assert response.status_code == 200
    assert response.json()["career_stats"]["career_win_percentage"] == 0.5


async def test_owner_with_no_rosters(client, db_session):
    await create_user(db_session, id="u1")

    response = await client.get("/api/owners")
    assert response.status_code == 200
    owner = response.json()["owners"][0]
    assert owner["total_wins"] == 0
    assert owner["seasons_played"] == 0


async def test_owner_details_seasons_ordered_desc(client, db_session):
    league = await create_league(db_session)
    s2022 = await create_season(db_session, league, year=2022)
    s2023 = await create_season(db_session, league, year=2023)
    s2024 = await create_season(db_session, league, year=2024)
    user = await create_user(db_session, id="u1")
    await create_roster(db_session, s2022, user, roster_id=1, wins=6, losses=8)
    await create_roster(db_session, s2023, user, roster_id=2, wins=8, losses=6)
    await create_roster(db_session, s2024, user, roster_id=3, wins=10, losses=4)

    response = await client.get("/api/owners/u1")
    assert response.status_code == 200
    seasons = response.json()["seasons"]
    assert seasons[0]["year"] == 2024
    assert seasons[1]["year"] == 2023
    assert seasons[2]["year"] == 2022
