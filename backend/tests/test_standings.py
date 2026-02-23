from tests.conftest import create_league, create_season, create_user, create_roster, create_matchup


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
    assert "total_teams" in data

    standing = data["standings"][0]
    for key in ["roster_id", "user_id", "display_name", "team_name", "division",
                "wins", "losses", "ties", "points_for", "points_against", "win_percentage",
                "median_wins", "median_losses", "median_ties"]:
        assert key in standing, f"Missing key: {key}"


async def test_standings_median_record(client, db_session):
    """Median record is calculated from regular season matchups."""
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    u1 = await create_user(db_session, id="u1", display_name="Owner 1")
    u2 = await create_user(db_session, id="u2", display_name="Owner 2")
    u3 = await create_user(db_session, id="u3", display_name="Owner 3")
    u4 = await create_user(db_session, id="u4", display_name="Owner 4")
    r1 = await create_roster(db_session, season, u1, roster_id=1, wins=3, losses=0)
    r2 = await create_roster(db_session, season, u2, roster_id=2, wins=2, losses=1)
    r3 = await create_roster(db_session, season, u3, roster_id=3, wins=1, losses=2)
    r4 = await create_roster(db_session, season, u4, roster_id=4, wins=0, losses=3)

    # Week 1: r1(150) vs r2(100), r3(120) vs r4(80) -> median=110
    # Above median: r1(150), r3(120). Below: r2(100), r4(80)
    await create_matchup(db_session, season, r1, r2, week=1, matchup_id=1,
                         home_points=150, away_points=100, match_type="regular")
    await create_matchup(db_session, season, r3, r4, week=1, matchup_id=2,
                         home_points=120, away_points=80, match_type="regular")

    # Week 2: r1(130) vs r3(90), r2(110) vs r4(70) -> median=100
    # Above median: r1(130), r2(110). Below: r3(90), r4(70)
    await create_matchup(db_session, season, r1, r3, week=2, matchup_id=1,
                         home_points=130, away_points=90, match_type="regular")
    await create_matchup(db_session, season, r2, r4, week=2, matchup_id=2,
                         home_points=110, away_points=70, match_type="regular")

    response = await client.get("/api/standings")
    assert response.status_code == 200
    standings = {s["user_id"]: s for s in response.json()["standings"]}

    # r1: beat median both weeks -> 2-0-0
    assert standings["u1"]["median_wins"] == 2
    assert standings["u1"]["median_losses"] == 0

    # r4: below median both weeks -> 0-2-0
    assert standings["u4"]["median_wins"] == 0
    assert standings["u4"]["median_losses"] == 2


async def test_standings_median_excludes_playoffs(client, db_session):
    """Playoff matchups should not affect median record."""
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    u1 = await create_user(db_session, id="u1", display_name="Owner 1")
    u2 = await create_user(db_session, id="u2", display_name="Owner 2")
    r1 = await create_roster(db_session, season, u1, roster_id=1)
    r2 = await create_roster(db_session, season, u2, roster_id=2)

    # One regular season matchup
    await create_matchup(db_session, season, r1, r2, week=1, matchup_id=1,
                         home_points=120, away_points=100, match_type="regular")
    # One playoff matchup (should be excluded)
    await create_matchup(db_session, season, r1, r2, week=15, matchup_id=1,
                         home_points=80, away_points=150, match_type="playoff")

    response = await client.get("/api/standings")
    standings = {s["user_id"]: s for s in response.json()["standings"]}

    # Only 1 regular season week counted
    assert standings["u1"]["median_wins"] + standings["u1"]["median_losses"] + standings["u1"]["median_ties"] == 1
