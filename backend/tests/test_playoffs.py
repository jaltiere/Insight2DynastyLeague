from tests.conftest import create_league, create_season, create_user, create_roster, create_matchup


async def test_playoffs_no_season(client):
    """Returns 404 when no season exists."""
    response = await client.get("/api/playoffs")
    assert response.status_code == 404
    assert "No season data found" in response.json()["detail"]


async def test_playoffs_specific_season_not_found(client, db_session):
    """Returns 404 for a non-existent season year."""
    league = await create_league(db_session)
    await create_season(db_session, league, year=2024)

    response = await client.get("/api/playoffs/2020")
    assert response.status_code == 404
    assert "Season 2020 not found" in response.json()["detail"]


async def test_playoffs_season_not_started(client, db_session):
    """Returns season_started=false when no matchups have been played."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user1 = await create_user(db_session, id="u1", display_name="Owner One")
    user2 = await create_user(db_session, id="u2", display_name="Owner Two")
    await create_roster(db_session, season, user1, roster_id=1, wins=0, losses=0)
    await create_roster(db_session, season, user2, roster_id=2, wins=0, losses=0)

    response = await client.get("/api/playoffs")
    assert response.status_code == 200
    data = response.json()
    assert data["season_started"] is False
    assert data["playoff_odds"] == []
    assert data["draft_order"] == []


async def test_playoffs_season_not_started_no_rosters(client, db_session):
    """Returns season_started=false when season has no rosters."""
    league = await create_league(db_session)
    await create_season(db_session, league, year=2024)

    response = await client.get("/api/playoffs")
    assert response.status_code == 200
    data = response.json()
    assert data["season_started"] is False


async def test_playoffs_with_active_season(client, db_session):
    """Returns playoff odds when there are played matchups."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024, regular_season_weeks=14)

    # Create 4 users/rosters across 2 divisions
    users = []
    rosters = []
    for i in range(4):
        u = await create_user(
            db_session, id=f"u{i}", username=f"user{i}", display_name=f"Owner {i}"
        )
        users.append(u)
        r = await create_roster(
            db_session, season, u,
            roster_id=i + 1,
            division=1 if i < 2 else 2,
            wins=10 - i * 2,
            losses=4 + i * 2,
            points_for=1500 - i * 100,
            points_against=1200 + i * 50,
        )
        rosters.append(r)

    # Create some played matchups (week 1)
    await create_matchup(
        db_session, season, rosters[0], rosters[1],
        week=1, matchup_id=1,
        home_points=120.0, away_points=100.0,
        winner_roster_id=rosters[0].id,
        home_max_potential_points=140.0, away_max_potential_points=130.0,
    )
    await create_matchup(
        db_session, season, rosters[2], rosters[3],
        week=1, matchup_id=2,
        home_points=110.0, away_points=90.0,
        winner_roster_id=rosters[2].id,
        home_max_potential_points=135.0, away_max_potential_points=125.0,
    )

    # Create an unplayed matchup (week 2 - future game)
    await create_matchup(
        db_session, season, rosters[0], rosters[2],
        week=2, matchup_id=1,
        home_points=0.0, away_points=0.0,
        winner_roster_id=None,
    )
    await create_matchup(
        db_session, season, rosters[1], rosters[3],
        week=2, matchup_id=2,
        home_points=0.0, away_points=0.0,
        winner_roster_id=None,
    )

    response = await client.get("/api/playoffs")
    assert response.status_code == 200
    data = response.json()

    assert data["season"] == 2024
    assert data["season_started"] is True
    assert data["current_week"] == 1
    assert data["regular_season_weeks"] == 14
    assert len(data["playoff_odds"]) == 4

    # Check that all required fields are present
    team = data["playoff_odds"][0]
    assert "roster_id" in team
    assert "user_id" in team
    assert "display_name" in team
    assert "team_name" in team
    assert "division_name" in team
    assert "current_record" in team
    assert "projected_record" in team
    assert "team_rating" in team
    assert "make_playoffs_pct" in team
    assert "make_playoffs_display" in team
    assert "win_division_pct" in team
    assert "win_division_display" in team
    assert "first_round_bye_pct" in team
    assert "first_round_bye_display" in team
    assert "win_finals_pct" in team
    assert "win_finals_display" in team
    assert "max_potential_points" in team

    # Teams should be sorted by rating descending
    ratings = [t["team_rating"] for t in data["playoff_odds"]]
    assert ratings == sorted(ratings, reverse=True)


async def test_playoffs_draft_order_present(client, db_session):
    """Verify draft order is returned with correct fields."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024, regular_season_weeks=14)

    users = []
    rosters = []
    for i in range(4):
        u = await create_user(
            db_session, id=f"u{i}", username=f"user{i}", display_name=f"Owner {i}"
        )
        users.append(u)
        r = await create_roster(
            db_session, season, u,
            roster_id=i + 1,
            division=1 if i < 2 else 2,
            wins=10 - i * 2,
            losses=4 + i * 2,
            points_for=1500 - i * 100,
            points_against=1200,
        )
        rosters.append(r)

    await create_matchup(
        db_session, season, rosters[0], rosters[1],
        week=1, matchup_id=1,
        home_points=120.0, away_points=100.0,
        winner_roster_id=rosters[0].id,
        home_max_potential_points=140.0, away_max_potential_points=130.0,
    )
    await create_matchup(
        db_session, season, rosters[2], rosters[3],
        week=1, matchup_id=2,
        home_points=110.0, away_points=90.0,
        winner_roster_id=rosters[2].id,
        home_max_potential_points=135.0, away_max_potential_points=125.0,
    )

    response = await client.get("/api/playoffs")
    assert response.status_code == 200
    data = response.json()

    assert "draft_order" in data
    assert len(data["draft_order"]) == 4

    entry = data["draft_order"][0]
    assert "pick" in entry
    assert "roster_id" in entry
    assert "display_name" in entry
    assert "team_name" in entry
    assert "reason" in entry
    assert "max_potential_points" in entry
    assert "projected_record" in entry
    assert entry["pick"] == 1


async def test_playoffs_historical_season(client, db_session):
    """Can retrieve playoff odds for a specific historical season."""
    league = await create_league(db_session)
    season_2023 = await create_season(db_session, league, year=2023, regular_season_weeks=14)
    await create_season(db_session, league, year=2024, regular_season_weeks=14)

    u1 = await create_user(db_session, id="u1", display_name="Owner One")
    u2 = await create_user(db_session, id="u2", display_name="Owner Two")
    r1 = await create_roster(
        db_session, season_2023, u1, roster_id=1, division=1,
        wins=10, losses=4, points_for=1500,
    )
    r2 = await create_roster(
        db_session, season_2023, u2, roster_id=2, division=2,
        wins=8, losses=6, points_for=1300,
    )

    await create_matchup(
        db_session, season_2023, r1, r2,
        week=1, matchup_id=1,
        home_points=120.0, away_points=100.0,
        winner_roster_id=r1.id,
        home_max_potential_points=140.0, away_max_potential_points=130.0,
    )

    response = await client.get("/api/playoffs/2023")
    assert response.status_code == 200
    data = response.json()
    assert data["season"] == 2023
    assert data["season_started"] is True
    assert len(data["playoff_odds"]) == 2


async def test_playoffs_response_percentages_format(client, db_session):
    """Verify percentage displays use correct format (<1%, >99%, or integer %)."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024, regular_season_weeks=14)

    users = []
    rosters = []
    for i in range(4):
        u = await create_user(
            db_session, id=f"u{i}", username=f"user{i}", display_name=f"Owner {i}"
        )
        users.append(u)
        r = await create_roster(
            db_session, season, u,
            roster_id=i + 1,
            division=1 if i < 2 else 2,
            wins=12 - i * 3,
            losses=2 + i * 3,
            points_for=1600 - i * 200,
            points_against=1200,
        )
        rosters.append(r)

    await create_matchup(
        db_session, season, rosters[0], rosters[1],
        week=1, matchup_id=1,
        home_points=130.0, away_points=95.0,
        winner_roster_id=rosters[0].id,
        home_max_potential_points=145.0, away_max_potential_points=120.0,
    )
    await create_matchup(
        db_session, season, rosters[2], rosters[3],
        week=1, matchup_id=2,
        home_points=115.0, away_points=80.0,
        winner_roster_id=rosters[2].id,
        home_max_potential_points=130.0, away_max_potential_points=110.0,
    )

    response = await client.get("/api/playoffs")
    assert response.status_code == 200
    data = response.json()

    for team in data["playoff_odds"]:
        for field in ["make_playoffs_display", "win_division_display",
                      "first_round_bye_display", "win_finals_display"]:
            display = team[field]
            # Should be one of: ">99%", "<1%", or "N%" format
            assert display.endswith("%"), f"{field} = '{display}' should end with %"
