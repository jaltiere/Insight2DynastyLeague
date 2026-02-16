from tests.conftest import create_league, create_season, create_user, create_roster


async def test_get_current_standings_success(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user1 = await create_user(db_session, id="u1", display_name="Owner One")
    user2 = await create_user(db_session, id="u2", display_name="Owner Two")
    await create_roster(db_session, season, user1, roster_id=1, wins=10, losses=4, points_for=1500)
    await create_roster(db_session, season, user2, roster_id=2, wins=8, losses=6, points_for=1300)

    response = await client.get("/api/standings")
    assert response.status_code == 200
    data = response.json()
    assert data["season"] == 2024
    assert data["total_teams"] == 2
    # First team should have more wins
    assert data["standings"][0]["wins"] == 10
    assert data["standings"][1]["wins"] == 8


async def test_get_current_standings_no_seasons(client):
    response = await client.get("/api/standings")
    assert response.status_code == 404
    assert "No season data found" in response.json()["detail"]


async def test_get_historical_standings_success(client, db_session):
    league = await create_league(db_session)
    season_2023 = await create_season(db_session, league, year=2023)
    season_2024 = await create_season(db_session, league, year=2024)
    user = await create_user(db_session)
    await create_roster(db_session, season_2023, user, roster_id=1, wins=6, losses=8, points_for=1100)
    await create_roster(db_session, season_2024, user, roster_id=2, wins=11, losses=3, points_for=1600)

    response = await client.get("/api/standings/2023")
    assert response.status_code == 200
    data = response.json()
    assert data["season"] == 2023
    assert data["standings"][0]["wins"] == 6


async def test_get_historical_standings_not_found(client, db_session):
    league = await create_league(db_session)
    await create_season(db_session, league, year=2024)

    response = await client.get("/api/standings/2020")
    assert response.status_code == 404
    assert "Season 2020 not found" in response.json()["detail"]


async def test_standings_win_percentage_with_ties(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user = await create_user(db_session)
    await create_roster(db_session, season, user, roster_id=1, wins=7, losses=6, ties=1)

    response = await client.get("/api/standings")
    assert response.status_code == 200
    standing = response.json()["standings"][0]
    # 7 / (7 + 6 + 1) = 0.5
    assert standing["win_percentage"] == 0.5


async def test_standings_response_has_all_fields(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user = await create_user(db_session)
    await create_roster(db_session, season, user)

    response = await client.get("/api/standings")
    assert response.status_code == 200
    data = response.json()
    assert "season" in data
    assert "num_divisions" in data
    assert "division_names" in data
    assert "total_teams" in data

    standing = data["standings"][0]
    for key in ["roster_id", "user_id", "username", "display_name", "team_name", "division",
                "wins", "losses", "ties", "points_for", "points_against", "win_percentage"]:
        assert key in standing, f"Missing key: {key}"


async def test_standings_division_names_from_league_metadata(client, db_session):
    league = await create_league(
        db_session,
        league_metadata={"division_1": "Havoc", "division_2": "Vengeance"},
    )
    season = await create_season(db_session, league)
    user = await create_user(db_session)
    await create_roster(db_session, season, user)

    response = await client.get("/api/standings")
    assert response.status_code == 200
    data = response.json()
    assert data["division_names"] == {"1": "Havoc", "2": "Vengeance"}


async def test_standings_division_names_fallback_without_metadata(client, db_session):
    league = await create_league(db_session)  # no league_metadata
    season = await create_season(db_session, league)
    user = await create_user(db_session)
    await create_roster(db_session, season, user)

    response = await client.get("/api/standings")
    assert response.status_code == 200
    data = response.json()
    assert data["division_names"] == {"1": "Division 1", "2": "Division 2"}


async def test_standings_username_and_team_name(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user = await create_user(db_session, display_name="jaltiere")
    await create_roster(db_session, season, user, team_name="Shark Byte")

    response = await client.get("/api/standings")
    assert response.status_code == 200
    standing = response.json()["standings"][0]
    assert standing["username"] == "jaltiere"
    assert standing["team_name"] == "Shark Byte"
