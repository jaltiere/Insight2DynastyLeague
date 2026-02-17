from tests.conftest import (
    create_league, create_season, create_user, create_season_award, create_roster,
)


async def test_get_all_history_success(client, db_session):
    league = await create_league(db_session)
    s2023 = await create_season(db_session, league, year=2023)
    s2024 = await create_season(db_session, league, year=2024)
    user1 = await create_user(db_session, id="u1", display_name="Champ 2023")
    user2 = await create_user(db_session, id="u2", display_name="Champ 2024")
    await create_roster(db_session, s2023, user1, roster_id=1)
    await create_roster(db_session, s2024, user2, roster_id=1)
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
    await create_roster(db_session, s2024, user, roster_id=1)
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

    await create_roster(db_session, season, champ, roster_id=1, team_name="Champ Team")
    await create_roster(db_session, season, div1, roster_id=2, team_name="Div1 Team")
    await create_roster(db_session, season, div2, roster_id=3, team_name="Div2 Team")
    await create_roster(db_session, season, consolation, roster_id=4, team_name="Consol Team")

    await create_season_award(db_session, season, champ, award_type="champion")
    await create_season_award(db_session, season, div1, award_type="division_winner", award_detail="Division 1")
    await create_season_award(db_session, season, div2, award_type="division_winner", award_detail="Division 2")
    await create_season_award(db_session, season, consolation, award_type="consolation")

    response = await client.get("/api/league-history/2024")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2024
    assert data["champion"]["username"] == "The Champion"
    assert data["champion"]["team_name"] == "Champ Team"
    assert len(data["division_winners"]) == 2
    assert data["consolation_winner"]["username"] == "Consolation"
    assert data["consolation_winner"]["team_name"] == "Consol Team"
    assert "division_names" in data


async def test_get_season_history_not_found(client):
    response = await client.get("/api/league-history/2020")
    assert response.status_code == 404
    assert "No history found for season 2020" in response.json()["detail"]


async def test_season_history_champion_only(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user = await create_user(db_session, id="u1")
    await create_roster(db_session, season, user, roster_id=1)
    await create_season_award(db_session, season, user, award_type="champion")

    response = await client.get("/api/league-history/2024")
    assert response.status_code == 200
    data = response.json()
    assert data["champion"] is not None
    assert data["division_winners"] == []
    assert data["consolation_winner"] is None


async def test_season_history_includes_division_names_from_metadata(client, db_session):
    league = await create_league(
        db_session,
        league_metadata={"division_1": "Havoc", "division_2": "Vengeance"},
    )
    season = await create_season(db_session, league, year=2024, num_divisions=2)
    user = await create_user(db_session, id="u1")
    await create_roster(db_session, season, user, roster_id=1)
    await create_season_award(
        db_session, season, user,
        award_type="division_winner", award_detail="Division 1",
    )

    response = await client.get("/api/league-history/2024")
    assert response.status_code == 200
    data = response.json()
    assert data["division_names"]["1"] == "Havoc"
    assert data["division_names"]["2"] == "Vengeance"
    # Division winner should use actual name, not generic
    assert data["division_winners"][0]["division"] == "Havoc"
