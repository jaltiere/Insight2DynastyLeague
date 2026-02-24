import pytest
from tests.conftest import (
    create_league, create_user, create_season, create_roster,
    create_matchup, create_player, create_matchup_player_point,
)


@pytest.fixture
async def seed_data(db_session):
    """Create test data with both rookies and non-rookies."""
    league = await create_league(db_session)
    user1 = await create_user(db_session, id="u1", username="owner1", display_name="Owner One")
    user2 = await create_user(db_session, id="u2", username="owner2", display_name="Owner Two")

    s2023 = await create_season(db_session, league, year=2023)
    s2024 = await create_season(db_session, league, year=2024)

    r1_2023 = await create_roster(db_session, s2023, user1, roster_id=1, team_name="Team Alpha")
    r2_2023 = await create_roster(db_session, s2023, user2, roster_id=2, team_name="Team Beta")
    r1_2024 = await create_roster(db_session, s2024, user1, roster_id=1, team_name="Team Alpha")
    r2_2024 = await create_roster(db_session, s2024, user2, roster_id=2, team_name="Team Beta")

    # Rookie in 2024 (rookie_year=2024)
    rookie_qb = await create_player(
        db_session, id="rqb1", full_name="Rookie QB", first_name="Rookie", last_name="QB",
        position="QB", rookie_year=2024, years_exp=0,
    )
    # Rookie in 2023 (rookie_year=2023) — not a rookie in 2024
    veteran_rb = await create_player(
        db_session, id="vrb1", full_name="Veteran RB", first_name="Veteran", last_name="RB",
        position="RB", rookie_year=2023, years_exp=1,
    )
    # Rookie in 2024 (rookie_year=2024)
    rookie_wr = await create_player(
        db_session, id="rwr1", full_name="Rookie WR", first_name="Rookie", last_name="WR",
        position="WR", rookie_year=2024, years_exp=0,
    )

    # 2023 matchups — veteran_rb is a rookie here
    m1 = await create_matchup(db_session, s2023, r1_2023, r2_2023, week=1, matchup_id=1,
                               match_type="regular", home_points=100.0, away_points=90.0)
    await create_matchup_player_point(db_session, m1, r1_2023, veteran_rb, points=25.0, is_starter=True)

    # 2024 matchups — rookie_qb and rookie_wr are rookies; veteran_rb is NOT
    m2 = await create_matchup(db_session, s2024, r1_2024, r2_2024, week=1, matchup_id=1,
                               match_type="regular", home_points=120.0, away_points=100.0)
    await create_matchup_player_point(db_session, m2, r1_2024, rookie_qb, points=30.0, is_starter=True)
    await create_matchup_player_point(db_session, m2, r1_2024, veteran_rb, points=20.0, is_starter=True)
    await create_matchup_player_point(db_session, m2, r1_2024, rookie_wr, points=5.0, is_starter=False)

    m3 = await create_matchup(db_session, s2024, r1_2024, r2_2024, week=2, matchup_id=2,
                               match_type="regular", home_points=110.0, away_points=105.0)
    await create_matchup_player_point(db_session, m3, r1_2024, rookie_qb, points=35.0, is_starter=True)
    await create_matchup_player_point(db_session, m3, r1_2024, veteran_rb, points=22.0, is_starter=True)

    # Playoff matchup in 2024
    m4 = await create_matchup(db_session, s2024, r1_2024, r2_2024, week=15, matchup_id=3,
                               match_type="playoff", home_points=130.0, away_points=90.0)
    await create_matchup_player_point(db_session, m4, r1_2024, rookie_qb, points=40.0, is_starter=True)

    await db_session.commit()
    return {
        "league": league, "s2023": s2023, "s2024": s2024,
        "user1": user1, "user2": user2,
        "rookie_qb": rookie_qb, "veteran_rb": veteran_rb, "rookie_wr": rookie_wr,
    }


# ---- By Game tests ----

@pytest.mark.anyio
async def test_game_records_only_rookies(client, seed_data):
    """Only rookie-year performances should appear."""
    resp = await client.get("/api/rookie-records?view=game&match_type=regular")
    assert resp.status_code == 200
    records = resp.json()["records"]
    names = [r["player_name"] for r in records]
    # Rookie QB (2024) and Rookie WR (2024) should appear for 2024 matchups
    # Veteran RB should appear for 2023 (his rookie year) but NOT for 2024
    assert "Rookie QB" in names
    assert "Rookie WR" in names
    # Veteran RB's 2024 games should NOT appear (not his rookie year)
    # But his 2023 game SHOULD appear (that was his rookie year)
    veteran_records = [r for r in records if r["player_name"] == "Veteran RB"]
    assert len(veteran_records) == 1
    assert veteran_records[0]["season"] == 2023


@pytest.mark.anyio
async def test_game_records_order(client, seed_data):
    """Game records should be ordered by points descending."""
    resp = await client.get("/api/rookie-records?view=game&match_type=regular")
    records = resp.json()["records"]
    points = [r["points"] for r in records]
    assert points == sorted(points, reverse=True)


@pytest.mark.anyio
async def test_game_records_filter_match_type(client, seed_data):
    """Only records for the requested match_type should be returned."""
    resp = await client.get("/api/rookie-records?view=game&match_type=playoff")
    records = resp.json()["records"]
    assert len(records) == 1
    assert records[0]["player_name"] == "Rookie QB"
    assert records[0]["points"] == 40.0


@pytest.mark.anyio
async def test_game_records_filter_starter(client, seed_data):
    """Filter by starter should exclude bench players."""
    resp = await client.get("/api/rookie-records?view=game&match_type=regular&roster_type=starter")
    records = resp.json()["records"]
    names = [r["player_name"] for r in records]
    assert "Rookie WR" not in names  # was on bench


@pytest.mark.anyio
async def test_game_records_filter_bench(client, seed_data):
    """Filter by bench should only return bench players."""
    resp = await client.get("/api/rookie-records?view=game&match_type=regular&roster_type=bench")
    records = resp.json()["records"]
    assert len(records) == 1
    assert records[0]["player_name"] == "Rookie WR"


@pytest.mark.anyio
async def test_game_records_filter_position(client, seed_data):
    """Filter by position should only return that position."""
    resp = await client.get("/api/rookie-records?view=game&match_type=regular&position=QB")
    records = resp.json()["records"]
    assert all(r["position"] == "QB" for r in records)
    assert len(records) == 2  # week 1 and week 2


@pytest.mark.anyio
async def test_game_response_has_all_fields(client, seed_data):
    """Game records should include all expected fields."""
    resp = await client.get("/api/rookie-records?view=game&match_type=regular")
    rec = resp.json()["records"][0]
    expected_fields = {
        "rank", "player_name", "position", "team", "points",
        "season", "week", "match_type", "is_starter",
        "owner_name", "team_name",
    }
    assert expected_fields.issubset(set(rec.keys()))


# ---- By Season tests ----

@pytest.mark.anyio
async def test_season_records_aggregation(client, seed_data):
    """Season records should aggregate points across weeks for rookies only."""
    resp = await client.get("/api/rookie-records?view=season&match_type=regular&roster_type=starter")
    records = resp.json()["records"]
    # Rookie QB: 30 + 35 = 65 (2024, his rookie year)
    qb_rec = next(r for r in records if r["player_name"] == "Rookie QB")
    assert qb_rec["total_points"] == 65.0
    assert qb_rec["games_played"] == 2
    assert qb_rec["avg_points"] == 32.5


@pytest.mark.anyio
async def test_season_records_excludes_non_rookie_year(client, seed_data):
    """Veteran RB's 2024 season should not appear (not his rookie year)."""
    resp = await client.get("/api/rookie-records?view=season&match_type=regular")
    records = resp.json()["records"]
    veteran_records = [r for r in records if r["player_name"] == "Veteran RB"]
    # Only his 2023 season (rookie year) should show
    assert len(veteran_records) == 1
    assert veteran_records[0]["season"] == 2023
    assert veteran_records[0]["total_points"] == 25.0


@pytest.mark.anyio
async def test_season_response_has_all_fields(client, seed_data):
    """Season records should include all expected fields."""
    resp = await client.get("/api/rookie-records?view=season&match_type=regular")
    rec = resp.json()["records"][0]
    expected_fields = {
        "rank", "player_name", "position", "team", "total_points",
        "games_played", "avg_points", "season", "owner_name", "team_name",
    }
    assert expected_fields.issubset(set(rec.keys()))


# ---- Validation tests ----

@pytest.mark.anyio
async def test_invalid_view_rejected(client, seed_data):
    """Career view should be rejected for rookie records."""
    resp = await client.get("/api/rookie-records?view=career")
    assert resp.status_code == 422


# ---- Empty data test ----

@pytest.mark.anyio
async def test_empty_records(client):
    """Should return empty list when no data exists."""
    resp = await client.get("/api/rookie-records?view=game&match_type=regular")
    assert resp.status_code == 200
    assert resp.json()["records"] == []
