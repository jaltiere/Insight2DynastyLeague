from tests.conftest import create_league, create_season


async def test_get_seasons_returns_years_descending(client, db_session):
    league = await create_league(db_session)
    await create_season(db_session, league, year=2022)
    await create_season(db_session, league, year=2023)
    await create_season(db_session, league, year=2024)

    response = await client.get("/api/seasons")
    assert response.status_code == 200
    data = response.json()
    assert data["seasons"] == [2024, 2023, 2022]


async def test_get_seasons_empty(client):
    response = await client.get("/api/seasons")
    assert response.status_code == 200
    assert response.json()["seasons"] == []
