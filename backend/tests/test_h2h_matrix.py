from tests.conftest import (
    create_league, create_season, create_user, create_roster, create_matchup,
)


async def test_h2h_matrix_basic(client, db_session):
    """Three users with matchups, verify correct W-L-T and symmetry."""
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    u1 = await create_user(db_session, id="u1", display_name="Alice")
    u2 = await create_user(db_session, id="u2", display_name="Bob")
    u3 = await create_user(db_session, id="u3", display_name="Charlie")
    r1 = await create_roster(db_session, season, u1, roster_id=1)
    r2 = await create_roster(db_session, season, u2, roster_id=2)
    r3 = await create_roster(db_session, season, u3, roster_id=3)

    # u1 beats u2 twice
    await create_matchup(db_session, season, r1, r2, week=1, matchup_id=1, home_points=120.0, away_points=100.0)
    await create_matchup(db_session, season, r1, r2, week=2, matchup_id=2, home_points=115.0, away_points=105.0)
    # u2 beats u3 once
    await create_matchup(db_session, season, r2, r3, week=1, matchup_id=3, home_points=110.0, away_points=90.0)
    # u3 beats u1 once
    await create_matchup(db_session, season, r3, r1, week=3, matchup_id=4, home_points=130.0, away_points=100.0)

    response = await client.get("/api/matchups/head-to-head-matrix")
    assert response.status_code == 200
    data = response.json()

    matrix = data["matrix"]
    # u1 vs u2: 2-0
    assert matrix["u1"]["u2"]["wins"] == 2
    assert matrix["u1"]["u2"]["losses"] == 0
    # Symmetry: u2 vs u1: 0-2
    assert matrix["u2"]["u1"]["wins"] == 0
    assert matrix["u2"]["u1"]["losses"] == 2
    # u2 vs u3: 1-0
    assert matrix["u2"]["u3"]["wins"] == 1
    assert matrix["u2"]["u3"]["losses"] == 0
    # u3 vs u1: 1-0
    assert matrix["u3"]["u1"]["wins"] == 1
    assert matrix["u3"]["u1"]["losses"] == 0


async def test_h2h_matrix_filter_by_match_type(client, db_session):
    """Mixed match types, verify filtering works."""
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    u1 = await create_user(db_session, id="u1", display_name="Alice")
    u2 = await create_user(db_session, id="u2", display_name="Bob")
    r1 = await create_roster(db_session, season, u1, roster_id=1)
    r2 = await create_roster(db_session, season, u2, roster_id=2)

    # Regular season: u1 wins
    await create_matchup(db_session, season, r1, r2, week=1, matchup_id=1, home_points=120.0, away_points=100.0, match_type="regular")
    # Playoff: u2 wins
    await create_matchup(db_session, season, r1, r2, week=15, matchup_id=2, home_points=90.0, away_points=110.0, match_type="playoff")

    # Filter regular only
    response = await client.get("/api/matchups/head-to-head-matrix?match_type=regular")
    assert response.status_code == 200
    data = response.json()
    assert data["matrix"]["u1"]["u2"]["wins"] == 1
    assert data["matrix"]["u1"]["u2"]["losses"] == 0

    # Filter playoff only
    response = await client.get("/api/matchups/head-to-head-matrix?match_type=playoff")
    data = response.json()
    assert data["matrix"]["u1"]["u2"]["wins"] == 0
    assert data["matrix"]["u1"]["u2"]["losses"] == 1


async def test_h2h_matrix_no_filter_returns_all(client, db_session):
    """No param returns all types aggregated."""
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    u1 = await create_user(db_session, id="u1", display_name="Alice")
    u2 = await create_user(db_session, id="u2", display_name="Bob")
    r1 = await create_roster(db_session, season, u1, roster_id=1)
    r2 = await create_roster(db_session, season, u2, roster_id=2)

    await create_matchup(db_session, season, r1, r2, week=1, matchup_id=1, home_points=120.0, away_points=100.0, match_type="regular")
    await create_matchup(db_session, season, r1, r2, week=15, matchup_id=2, home_points=130.0, away_points=110.0, match_type="playoff")
    await create_matchup(db_session, season, r1, r2, week=15, matchup_id=3, home_points=90.0, away_points=110.0, match_type="consolation")

    response = await client.get("/api/matchups/head-to-head-matrix")
    assert response.status_code == 200
    data = response.json()
    # u1: 2 wins (regular + playoff), 1 loss (consolation)
    assert data["matrix"]["u1"]["u2"]["wins"] == 2
    assert data["matrix"]["u1"]["u2"]["losses"] == 1


async def test_h2h_matrix_median_records(client, db_session):
    """4 owners with known scores, verify median calculation."""
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    u1 = await create_user(db_session, id="u1", display_name="Alice")
    u2 = await create_user(db_session, id="u2", display_name="Bob")
    u3 = await create_user(db_session, id="u3", display_name="Charlie")
    u4 = await create_user(db_session, id="u4", display_name="Diana")
    r1 = await create_roster(db_session, season, u1, roster_id=1)
    r2 = await create_roster(db_session, season, u2, roster_id=2)
    r3 = await create_roster(db_session, season, u3, roster_id=3)
    r4 = await create_roster(db_session, season, u4, roster_id=4)

    # Week 1: scores 80, 90, 110, 120 -> median = 100
    # u1(80) < 100 -> loss, u2(90) < 100 -> loss, u3(110) > 100 -> win, u4(120) > 100 -> win
    await create_matchup(db_session, season, r1, r2, week=1, matchup_id=1, home_points=80.0, away_points=90.0)
    await create_matchup(db_session, season, r3, r4, week=1, matchup_id=2, home_points=110.0, away_points=120.0)

    response = await client.get("/api/matchups/head-to-head-matrix")
    assert response.status_code == 200
    data = response.json()
    median = data["median_records"]
    assert median["u1"]["losses"] == 1
    assert median["u2"]["losses"] == 1
    assert median["u3"]["wins"] == 1
    assert median["u4"]["wins"] == 1


async def test_h2h_matrix_median_with_match_type_filter(client, db_session):
    """Median calculation only considers matchups of the filtered type."""
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    u1 = await create_user(db_session, id="u1", display_name="Alice")
    u2 = await create_user(db_session, id="u2", display_name="Bob")
    r1 = await create_roster(db_session, season, u1, roster_id=1)
    r2 = await create_roster(db_session, season, u2, roster_id=2)

    # Regular: u1 scores 120, u2 scores 80 -> median 100 -> u1 win, u2 loss
    await create_matchup(db_session, season, r1, r2, week=1, matchup_id=1, home_points=120.0, away_points=80.0, match_type="regular")
    # Playoff: u1 scores 70, u2 scores 130 -> median 100 -> u1 loss, u2 win
    await create_matchup(db_session, season, r1, r2, week=15, matchup_id=2, home_points=70.0, away_points=130.0, match_type="playoff")

    # Filter regular only
    response = await client.get("/api/matchups/head-to-head-matrix?match_type=regular")
    data = response.json()
    assert data["median_records"]["u1"]["wins"] == 1
    assert data["median_records"]["u1"]["losses"] == 0
    assert data["median_records"]["u2"]["wins"] == 0
    assert data["median_records"]["u2"]["losses"] == 1

    # Filter playoff only
    response = await client.get("/api/matchups/head-to-head-matrix?match_type=playoff")
    data = response.json()
    assert data["median_records"]["u1"]["wins"] == 0
    assert data["median_records"]["u1"]["losses"] == 1
    assert data["median_records"]["u2"]["wins"] == 1
    assert data["median_records"]["u2"]["losses"] == 0


async def test_h2h_matrix_across_multiple_seasons(client, db_session):
    """Records accumulate correctly across seasons."""
    league = await create_league(db_session)
    s2023 = await create_season(db_session, league, year=2023)
    s2024 = await create_season(db_session, league, year=2024)
    u1 = await create_user(db_session, id="u1", display_name="Alice")
    u2 = await create_user(db_session, id="u2", display_name="Bob")
    r1_23 = await create_roster(db_session, s2023, u1, roster_id=1)
    r2_23 = await create_roster(db_session, s2023, u2, roster_id=2)
    r1_24 = await create_roster(db_session, s2024, u1, roster_id=3)
    r2_24 = await create_roster(db_session, s2024, u2, roster_id=4)

    # 2023: u1 wins
    await create_matchup(db_session, s2023, r1_23, r2_23, week=1, matchup_id=1, home_points=120.0, away_points=100.0)
    # 2024: u2 wins
    await create_matchup(db_session, s2024, r1_24, r2_24, week=1, matchup_id=1, home_points=90.0, away_points=110.0)

    response = await client.get("/api/matchups/head-to-head-matrix")
    assert response.status_code == 200
    data = response.json()
    assert data["matrix"]["u1"]["u2"]["wins"] == 1
    assert data["matrix"]["u1"]["u2"]["losses"] == 1


async def test_h2h_matrix_empty_league(client, db_session):
    """No matchups returns empty matrix and median records."""
    # Create active users but no matchups
    await create_user(db_session, id="u1", display_name="Alice")
    await create_user(db_session, id="u2", display_name="Bob")

    response = await client.get("/api/matchups/head-to-head-matrix")
    assert response.status_code == 200
    data = response.json()
    assert len(data["owners"]) == 2
    assert data["matrix"] == {}
    assert data["median_records"] == {}


async def test_h2h_matrix_only_active_users(client, db_session):
    """Only active users appear in owners list."""
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    u1 = await create_user(db_session, id="u1", display_name="Alice", is_active=True)
    u2 = await create_user(db_session, id="u2", display_name="Bob", is_active=True)
    u_inactive = await create_user(db_session, id="u3", display_name="Inactive", is_active=False)
    r1 = await create_roster(db_session, season, u1, roster_id=1)
    r_inactive = await create_roster(db_session, season, u_inactive, roster_id=3)

    # Matchup between active and inactive user
    await create_matchup(db_session, season, r1, r_inactive, week=1, matchup_id=1, home_points=120.0, away_points=100.0)

    response = await client.get("/api/matchups/head-to-head-matrix")
    assert response.status_code == 200
    data = response.json()
    owner_ids = [o["user_id"] for o in data["owners"]]
    assert "u1" in owner_ids
    assert "u2" in owner_ids
    assert "u3" not in owner_ids
    # Inactive user matchups should not appear in matrix
    assert "u3" not in data["matrix"].get("u1", {})


async def test_h2h_matrix_response_has_all_fields(client, db_session):
    """Verify response shape includes owners, matrix, and median_records."""
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    u1 = await create_user(db_session, id="u1", display_name="Alice", username="alice")
    u2 = await create_user(db_session, id="u2", display_name="Bob", username="bob")
    r1 = await create_roster(db_session, season, u1, roster_id=1)
    r2 = await create_roster(db_session, season, u2, roster_id=2)

    await create_matchup(db_session, season, r1, r2, week=1, matchup_id=1, home_points=120.0, away_points=100.0)

    response = await client.get("/api/matchups/head-to-head-matrix")
    assert response.status_code == 200
    data = response.json()

    # Top-level keys
    assert "owners" in data
    assert "matrix" in data
    assert "median_records" in data

    # Owner fields
    owner = data["owners"][0]
    assert "user_id" in owner
    assert "display_name" in owner
    assert "username" in owner
    assert "avatar" in owner

    # Matrix record fields
    record = data["matrix"]["u1"]["u2"]
    assert "wins" in record
    assert "losses" in record
    assert "ties" in record

    # Median record fields
    median = data["median_records"]["u1"]
    assert "wins" in median
    assert "losses" in median
    assert "ties" in median
