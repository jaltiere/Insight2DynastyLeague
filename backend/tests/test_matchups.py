from tests.conftest import (
    create_league, create_season, create_user, create_roster, create_matchup,
)


async def test_head_to_head_success(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user1 = await create_user(db_session, id="u1", display_name="Owner One")
    user2 = await create_user(db_session, id="u2", display_name="Owner Two")
    r1 = await create_roster(db_session, season, user1, roster_id=1)
    r2 = await create_roster(db_session, season, user2, roster_id=2)

    # user1 wins 2, user2 wins 1
    await create_matchup(db_session, season, r1, r2, week=1, matchup_id=1, home_points=120.0, away_points=100.0, winner_roster_id=r1.id)
    await create_matchup(db_session, season, r1, r2, week=2, matchup_id=2, home_points=90.0, away_points=110.0, winner_roster_id=r2.id)
    await create_matchup(db_session, season, r1, r2, week=3, matchup_id=3, home_points=130.0, away_points=105.0, winner_roster_id=r1.id)

    response = await client.get("/api/matchups/head-to-head/u1/u2")
    assert response.status_code == 200
    data = response.json()
    assert data["total_games"] == 3
    assert data["user1"]["wins"] == 2
    assert data["user1"]["losses"] == 1
    assert data["user2"]["wins"] == 1
    assert data["user2"]["losses"] == 2


async def test_head_to_head_user_not_found(client, db_session):
    await create_user(db_session, id="u1")

    response = await client.get("/api/matchups/head-to-head/u1/nonexistent")
    assert response.status_code == 404
    assert "One or both owners not found" in response.json()["detail"]


async def test_head_to_head_both_users_not_found(client):
    response = await client.get("/api/matchups/head-to-head/fake1/fake2")
    assert response.status_code == 404


async def test_head_to_head_no_matchups(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user1 = await create_user(db_session, id="u1")
    user2 = await create_user(db_session, id="u2")
    await create_roster(db_session, season, user1, roster_id=1)
    await create_roster(db_session, season, user2, roster_id=2)

    response = await client.get("/api/matchups/head-to-head/u1/u2")
    assert response.status_code == 200
    data = response.json()
    assert data["total_games"] == 0
    assert data["user1"]["wins"] == 0
    assert data["user2"]["wins"] == 0


async def test_head_to_head_across_multiple_seasons(client, db_session):
    league = await create_league(db_session)
    s2023 = await create_season(db_session, league, year=2023)
    s2024 = await create_season(db_session, league, year=2024)
    user1 = await create_user(db_session, id="u1")
    user2 = await create_user(db_session, id="u2")
    r1_2023 = await create_roster(db_session, s2023, user1, roster_id=1)
    r2_2023 = await create_roster(db_session, s2023, user2, roster_id=2)
    r1_2024 = await create_roster(db_session, s2024, user1, roster_id=3)
    r2_2024 = await create_roster(db_session, s2024, user2, roster_id=4)

    await create_matchup(db_session, s2023, r1_2023, r2_2023, week=1, matchup_id=1, home_points=100.0, away_points=90.0, winner_roster_id=r1_2023.id)
    await create_matchup(db_session, s2024, r1_2024, r2_2024, week=1, matchup_id=1, home_points=80.0, away_points=95.0, winner_roster_id=r2_2024.id)

    response = await client.get("/api/matchups/head-to-head/u1/u2")
    assert response.status_code == 200
    data = response.json()
    assert data["total_games"] == 2
    assert data["user1"]["wins"] == 1
    assert data["user2"]["wins"] == 1
    # Games should be ordered by season, then week
    assert data["games"][0]["season"] == 2023
    assert data["games"][1]["season"] == 2024


async def test_head_to_head_points_calculation(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user1 = await create_user(db_session, id="u1")
    user2 = await create_user(db_session, id="u2")
    r1 = await create_roster(db_session, season, user1, roster_id=1)
    r2 = await create_roster(db_session, season, user2, roster_id=2)

    await create_matchup(db_session, season, r1, r2, week=1, matchup_id=1, home_points=100.0, away_points=90.0, winner_roster_id=r1.id)
    await create_matchup(db_session, season, r1, r2, week=2, matchup_id=2, home_points=120.0, away_points=110.0, winner_roster_id=r1.id)

    response = await client.get("/api/matchups/head-to-head/u1/u2")
    assert response.status_code == 200
    data = response.json()
    assert data["user1"]["total_points"] == 220.0
    assert data["user2"]["total_points"] == 200.0
    assert data["user1"]["avg_points"] == 110.0
    assert data["user2"]["avg_points"] == 100.0
