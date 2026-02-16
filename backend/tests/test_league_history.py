from tests.conftest import (
    create_league, create_season, create_user, create_season_award,
)


async def test_get_all_history_success(client, db_session):
    league = await create_league(db_session)
    s2023 = await create_season(db_session, league, year=2023)
    s2024 = await create_season(db_session, league, year=2024)
    user1 = await create_user(db_session, id="u1", display_name="Champ 2023")
    user2 = await create_user(db_session, id="u2", display_name="Champ 2024")
    await create_season_award(db_session, s2023, user1, award_type="champion")
    await create_season_award(db_session, s2024, user2, award_type="champion")

    response = await client.get("/api/league-history")
    assert response.status_code == 200
    data = response.json()
    assert data["total_seasons"] == 2
    # Ordered by year desc
    assert data["seasons"][0]["year"] == 2024
    assert data["seasons"][1]["year"] == 2023


async def test_get_all_history_empty(client):
    response = await client.get("/api/league-history")
    assert response.status_code == 200
    data = response.json()
    assert data["total_seasons"] == 0
    assert data["seasons"] == []


async def test_get_all_history_season_without_awards_excluded(client, db_session):
    league = await create_league(db_session)
    await create_season(db_session, league, year=2023)  # no awards
    s2024 = await create_season(db_session, league, year=2024)
    user = await create_user(db_session, id="u1")
    await create_season_award(db_session, s2024, user, award_type="champion")

    response = await client.get("/api/league-history")
    assert response.status_code == 200
    data = response.json()
    assert data["total_seasons"] == 1
    assert data["seasons"][0]["year"] == 2024


async def test_get_season_history_success(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    champ = await create_user(db_session, id="u1", display_name="The Champion")
    div1 = await create_user(db_session, id="u2", display_name="Div 1 Winner")
    div2 = await create_user(db_session, id="u3", display_name="Div 2 Winner")
    consolation = await create_user(db_session, id="u4", display_name="Consolation")

    await create_season_award(db_session, season, champ, award_type="champion")
    await create_season_award(db_session, season, div1, award_type="division_winner", award_detail="Division 1")
    await create_season_award(db_session, season, div2, award_type="division_winner", award_detail="Division 2")
    await create_season_award(db_session, season, consolation, award_type="consolation")

    response = await client.get("/api/league-history/2024")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2024
    assert data["champion"]["display_name"] == "The Champion"
    assert len(data["division_winners"]) == 2
    assert data["consolation_winner"]["display_name"] == "Consolation"
    # Check division detail is passed through
    divisions = {dw["division"] for dw in data["division_winners"]}
    assert "Division 1" in divisions
    assert "Division 2" in divisions


async def test_get_season_history_not_found(client):
    response = await client.get("/api/league-history/2020")
    assert response.status_code == 404
    assert "No history found for season 2020" in response.json()["detail"]


async def test_season_history_champion_only(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user = await create_user(db_session, id="u1")
    await create_season_award(db_session, season, user, award_type="champion")

    response = await client.get("/api/league-history/2024")
    assert response.status_code == 200
    data = response.json()
    assert data["champion"] is not None
    assert data["division_winners"] == []
    assert data["consolation_winner"] is None
