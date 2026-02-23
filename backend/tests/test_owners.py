from tests.conftest import (
    create_league, create_season, create_user, create_roster, create_matchup,
)


async def test_get_all_owners_success(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user1 = await create_user(db_session, id="u1", display_name="Owner One")
    user2 = await create_user(db_session, id="u2", display_name="Owner Two")
    r1 = await create_roster(db_session, season, user1, roster_id=1)
    r2 = await create_roster(db_session, season, user2, roster_id=2)

    # user1 wins both matchups
    await create_matchup(db_session, season, r1, r2, week=1, matchup_id=1,
                         home_points=120, away_points=100, winner_roster_id=r1.id)
    await create_matchup(db_session, season, r1, r2, week=2, matchup_id=1,
                         home_points=110, away_points=105, winner_roster_id=r1.id)

    response = await client.get("/api/owners")
    assert response.status_code == 200
    data = response.json()
    assert data["total_owners"] == 2
    # Sorted by total_wins descending
    assert data["owners"][0]["total_wins"] == 2
    assert data["owners"][1]["total_wins"] == 0


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
    opp = await create_user(db_session, id="u2", username="opponent")
    r1_2023 = await create_roster(db_session, s2023, user, roster_id=1)
    r2_2023 = await create_roster(db_session, s2023, opp, roster_id=2)
    r1_2024 = await create_roster(db_session, s2024, user, roster_id=3)
    r2_2024 = await create_roster(db_session, s2024, opp, roster_id=4)

    # 2023: 1 win
    await create_matchup(db_session, s2023, r1_2023, r2_2023, week=1, matchup_id=1,
                         home_points=110, away_points=100, winner_roster_id=r1_2023.id)
    # 2024: 1 win
    await create_matchup(db_session, s2024, r1_2024, r2_2024, week=1, matchup_id=1,
                         home_points=120, away_points=105, winner_roster_id=r1_2024.id)

    response = await client.get("/api/owners/u1")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "u1"
    assert data["career_stats"]["seasons_played"] == 2
    assert data["career_stats"]["total_wins"] == 2
    assert data["career_stats"]["total_losses"] == 0


async def test_get_owner_details_not_found(client):
    response = await client.get("/api/owners/nonexistent")
    assert response.status_code == 404
    assert "Owner not found" in response.json()["detail"]


async def test_owner_career_win_percentage(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user = await create_user(db_session, id="u1")
    opp = await create_user(db_session, id="u2", username="opponent")
    r1 = await create_roster(db_session, season, user, roster_id=1)
    r2 = await create_roster(db_session, season, opp, roster_id=2)

    # 1 win, 1 loss = 50%
    await create_matchup(db_session, season, r1, r2, week=1, matchup_id=1,
                         home_points=120, away_points=100, winner_roster_id=r1.id)
    await create_matchup(db_session, season, r2, r1, week=2, matchup_id=1,
                         home_points=130, away_points=100, winner_roster_id=r2.id)

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
    await create_roster(db_session, s2022, user, roster_id=1)
    await create_roster(db_session, s2023, user, roster_id=2)
    await create_roster(db_session, s2024, user, roster_id=3)

    response = await client.get("/api/owners/u1")
    assert response.status_code == 200
    seasons = response.json()["seasons"]
    assert seasons[0]["year"] == 2024
    assert seasons[1]["year"] == 2023
    assert seasons[2]["year"] == 2022


async def test_owners_categorized_stats(client, db_session):
    """Test that owner stats include separate regular, playoff, consolation records."""
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user = await create_user(db_session, id="u1")
    opp = await create_user(db_session, id="u2", username="opponent")
    r1 = await create_roster(db_session, season, user, roster_id=1)
    r2 = await create_roster(db_session, season, opp, roster_id=2)

    # Regular season win
    await create_matchup(db_session, season, r1, r2, week=1, matchup_id=1,
                         home_points=120, away_points=100, winner_roster_id=r1.id,
                         match_type="regular")
    # Playoff loss
    await create_matchup(db_session, season, r1, r2, week=15, matchup_id=2,
                         home_points=90, away_points=110, winner_roster_id=r2.id,
                         match_type="playoff")
    # Consolation win
    await create_matchup(db_session, season, r2, r1, week=16, matchup_id=3,
                         home_points=95, away_points=105, winner_roster_id=r1.id,
                         match_type="consolation")

    response = await client.get("/api/owners/u1")
    assert response.status_code == 200
    stats = response.json()["career_stats"]

    assert stats["regular_season"]["wins"] == 1
    assert stats["regular_season"]["losses"] == 0
    assert stats["playoff"]["wins"] == 0
    assert stats["playoff"]["losses"] == 1
    assert stats["consolation"]["wins"] == 1
    assert stats["consolation"]["losses"] == 0


async def test_owners_list_includes_categories(client, db_session):
    """Test that /api/owners response includes categorized stats."""
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user = await create_user(db_session, id="u1")
    await create_roster(db_session, season, user, roster_id=1)

    response = await client.get("/api/owners")
    assert response.status_code == 200
    owner = response.json()["owners"][0]
    assert "regular_season" in owner
    assert "playoff" in owner
    assert "consolation" in owner
    assert "wins" in owner["regular_season"]
    assert "win_percentage" in owner["regular_season"]


async def test_owners_backward_compat(client, db_session):
    """Test that legacy flat fields still exist for backward compatibility."""
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user = await create_user(db_session, id="u1")
    await create_roster(db_session, season, user, roster_id=1)

    response = await client.get("/api/owners")
    owner = response.json()["owners"][0]
    assert "total_wins" in owner
    assert "total_losses" in owner
    assert "career_win_percentage" in owner
    assert "seasons_played" in owner


async def test_owner_details_season_categories(client, db_session):
    """Test that season breakdown includes per-category stats."""
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user = await create_user(db_session, id="u1")
    opp = await create_user(db_session, id="u2", username="opponent")
    r1 = await create_roster(db_session, season, user, roster_id=1)
    r2 = await create_roster(db_session, season, opp, roster_id=2)

    await create_matchup(db_session, season, r1, r2, week=1, matchup_id=1,
                         home_points=120, away_points=100, winner_roster_id=r1.id,
                         match_type="regular")
    await create_matchup(db_session, season, r1, r2, week=15, matchup_id=2,
                         home_points=130, away_points=110, winner_roster_id=r1.id,
                         match_type="playoff")

    response = await client.get("/api/owners/u1")
    assert response.status_code == 200
    season_data = response.json()["seasons"][0]
    assert season_data["regular_season"]["wins"] == 1
    assert season_data["playoff"]["wins"] == 1
    assert season_data["consolation"]["wins"] == 0
    # Legacy flat fields still present (regular season)
    assert season_data["wins"] == 1


async def test_owner_details_division_name(client, db_session):
    """Test that season breakdown includes division_name from league metadata."""
    league = await create_league(db_session, league_metadata={
        "division_1": "East",
        "division_2": "West",
    })
    season = await create_season(db_session, league, num_divisions=2)
    user = await create_user(db_session, id="u1")
    await create_roster(db_session, season, user, roster_id=1, division=2)

    response = await client.get("/api/owners/u1")
    assert response.status_code == 200
    season_data = response.json()["seasons"][0]
    assert season_data["division"] == 2
    assert season_data["division_name"] == "West"


async def test_owner_details_division_name_fallback(client, db_session):
    """Test that division_name falls back to 'Division N' when metadata is missing."""
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user = await create_user(db_session, id="u1")
    await create_roster(db_session, season, user, roster_id=1, division=1)

    response = await client.get("/api/owners/u1")
    assert response.status_code == 200
    season_data = response.json()["seasons"][0]
    assert season_data["division_name"] == "Division 1"


async def test_owner_details_median_record(client, db_session):
    """Test that season breakdown includes median wins/losses/ties."""
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user1 = await create_user(db_session, id="u1", display_name="Owner One")
    user2 = await create_user(db_session, id="u2", display_name="Owner Two")
    user3 = await create_user(db_session, id="u3", display_name="Owner Three")
    user4 = await create_user(db_session, id="u4", display_name="Owner Four")
    r1 = await create_roster(db_session, season, user1, roster_id=1)
    r2 = await create_roster(db_session, season, user2, roster_id=2)
    r3 = await create_roster(db_session, season, user3, roster_id=3)
    r4 = await create_roster(db_session, season, user4, roster_id=4)

    # Week 1: scores 130, 110, 90, 70 -> median = 100
    # u1 (130) > 100 -> median win, u2 (110) > 100 -> median win
    await create_matchup(db_session, season, r1, r2, week=1, matchup_id=1,
                         home_points=130, away_points=110, winner_roster_id=r1.id)
    await create_matchup(db_session, season, r3, r4, week=1, matchup_id=2,
                         home_points=90, away_points=70, winner_roster_id=r3.id)

    # Week 2: scores 80, 120, 100, 60 -> median = 90
    # u1 (80) < 90 -> median loss
    await create_matchup(db_session, season, r1, r2, week=2, matchup_id=1,
                         home_points=80, away_points=120, winner_roster_id=r2.id)
    await create_matchup(db_session, season, r3, r4, week=2, matchup_id=2,
                         home_points=100, away_points=60, winner_roster_id=r3.id)

    response = await client.get("/api/owners/u1")
    assert response.status_code == 200
    season_data = response.json()["seasons"][0]
    assert season_data["median_wins"] == 1
    assert season_data["median_losses"] == 1
    assert season_data["median_ties"] == 0


async def test_owner_details_median_record_no_matchups(client, db_session):
    """Test that median record is 0-0-0 when no matchups exist."""
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user = await create_user(db_session, id="u1")
    await create_roster(db_session, season, user, roster_id=1)

    response = await client.get("/api/owners/u1")
    assert response.status_code == 200
    season_data = response.json()["seasons"][0]
    assert season_data["median_wins"] == 0
    assert season_data["median_losses"] == 0
    assert season_data["median_ties"] == 0
