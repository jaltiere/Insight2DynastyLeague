import pytest
from tests.conftest import (
    create_league, create_user, create_season, create_roster,
    create_matchup, create_player, create_matchup_player_point,
)


@pytest.fixture
async def seed_data(db_session):
    """Create a full set of test data for player records."""
    league = await create_league(db_session)
    user1 = await create_user(db_session, id="u1", username="owner1", display_name="Owner One")
    user2 = await create_user(db_session, id="u2", username="owner2", display_name="Owner Two")

    season = await create_season(db_session, league, year=2024)

    r1 = await create_roster(db_session, season, user1, roster_id=1, team_name="Team Alpha")
    r2 = await create_roster(db_session, season, user2, roster_id=2, team_name="Team Beta")

    qb = await create_player(db_session, id="qb1", full_name="Joe QB", first_name="Joe", last_name="QB", position="QB")
    rb = await create_player(db_session, id="rb1", full_name="Sam RB", first_name="Sam", last_name="RB", position="RB")
    wr = await create_player(db_session, id="wr1", full_name="Tim WR", first_name="Tim", last_name="WR", position="WR")

    # Regular season matchup week 1
    m1 = await create_matchup(db_session, season, r1, r2, week=1, matchup_id=1, match_type="regular",
                               home_points=120.0, away_points=100.0)
    await create_matchup_player_point(db_session, m1, r1, qb, points=30.0, is_starter=True)
    await create_matchup_player_point(db_session, m1, r1, rb, points=20.0, is_starter=True)
    await create_matchup_player_point(db_session, m1, r1, wr, points=5.0, is_starter=False)  # bench

    # Regular season matchup week 2
    m2 = await create_matchup(db_session, season, r1, r2, week=2, matchup_id=2, match_type="regular",
                               home_points=110.0, away_points=105.0)
    await create_matchup_player_point(db_session, m2, r1, qb, points=25.0, is_starter=True)
    await create_matchup_player_point(db_session, m2, r1, rb, points=35.0, is_starter=True)

    # Playoff matchup
    m3 = await create_matchup(db_session, season, r1, r2, week=15, matchup_id=3, match_type="playoff",
                               home_points=130.0, away_points=90.0)
    await create_matchup_player_point(db_session, m3, r1, qb, points=40.0, is_starter=True)

    # Consolation matchup (different owner has the player)
    m4 = await create_matchup(db_session, season, r2, r1, week=16, matchup_id=4, match_type="consolation",
                               home_points=95.0, away_points=85.0)
    await create_matchup_player_point(db_session, m4, r2, rb, points=18.0, is_starter=True)

    await db_session.commit()
    return {
        "league": league, "season": season,
        "user1": user1, "user2": user2,
        "r1": r1, "r2": r2,
        "qb": qb, "rb": rb, "wr": wr,
    }


# ---- By Game tests ----

@pytest.mark.anyio
async def test_game_records_top10_order(client, seed_data):
    """Top game records should be ordered by points descending."""
    resp = await client.get("/api/player-records?view=game&match_type=regular")
    assert resp.status_code == 200
    data = resp.json()
    records = data["records"]
    assert len(records) > 0
    # Check descending order
    points = [r["points"] for r in records]
    assert points == sorted(points, reverse=True)


@pytest.mark.anyio
async def test_game_records_filter_match_type(client, seed_data):
    """Only records for the requested match_type should be returned."""
    resp = await client.get("/api/player-records?view=game&match_type=playoff")
    assert resp.status_code == 200
    records = resp.json()["records"]
    assert len(records) == 1
    assert records[0]["player_name"] == "Joe QB"
    assert records[0]["points"] == 40.0


@pytest.mark.anyio
async def test_game_records_filter_starter(client, seed_data):
    """Filter by starter should exclude bench players."""
    resp = await client.get("/api/player-records?view=game&match_type=regular&roster_type=starter")
    records = resp.json()["records"]
    assert all(r["is_starter"] for r in records)
    # Tim WR was bench (5.0 pts) - should not appear
    names = [r["player_name"] for r in records]
    assert "Tim WR" not in names


@pytest.mark.anyio
async def test_game_records_filter_bench(client, seed_data):
    """Filter by bench should only return bench players."""
    resp = await client.get("/api/player-records?view=game&match_type=regular&roster_type=bench")
    records = resp.json()["records"]
    assert len(records) == 1
    assert records[0]["player_name"] == "Tim WR"
    assert records[0]["is_starter"] is False


@pytest.mark.anyio
async def test_game_records_filter_position(client, seed_data):
    """Filter by position should only return that position."""
    resp = await client.get("/api/player-records?view=game&match_type=regular&position=QB")
    records = resp.json()["records"]
    assert all(r["position"] == "QB" for r in records)
    assert len(records) == 2  # week 1 and week 2


@pytest.mark.anyio
async def test_game_response_has_all_fields(client, seed_data):
    """Game records should include all expected fields."""
    resp = await client.get("/api/player-records?view=game&match_type=regular")
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
    """Season records should aggregate points across weeks."""
    resp = await client.get("/api/player-records?view=season&match_type=regular&roster_type=starter")
    records = resp.json()["records"]
    # QB: 30 + 25 = 55, RB: 20 + 35 = 55
    assert len(records) >= 2
    qb_rec = next(r for r in records if r["player_name"] == "Joe QB")
    assert qb_rec["total_points"] == 55.0
    assert qb_rec["games_played"] == 2
    assert qb_rec["avg_points"] == 27.5


@pytest.mark.anyio
async def test_season_response_has_all_fields(client, seed_data):
    """Season records should include all expected fields."""
    resp = await client.get("/api/player-records?view=season&match_type=regular")
    rec = resp.json()["records"][0]
    expected_fields = {
        "rank", "player_name", "position", "team", "total_points",
        "games_played", "avg_points", "season", "owner_name", "team_name",
    }
    assert expected_fields.issubset(set(rec.keys()))


# ---- By Career tests ----

@pytest.mark.anyio
async def test_career_records_aggregation(client, seed_data):
    """Career records should aggregate across all seasons."""
    # QB has regular (30+25) + playoff (40) = 95 total across match types
    # But career only filters by one match_type at a time
    resp = await client.get("/api/player-records?view=career&match_type=regular&roster_type=starter")
    records = resp.json()["records"]
    qb_rec = next(r for r in records if r["player_name"] == "Joe QB")
    assert qb_rec["total_points"] == 55.0
    assert qb_rec["games_played"] == 2


@pytest.mark.anyio
async def test_career_response_has_all_fields(client, seed_data):
    """Career records should include all expected fields."""
    resp = await client.get("/api/player-records?view=career&match_type=regular")
    rec = resp.json()["records"][0]
    expected_fields = {
        "rank", "player_name", "position", "team", "total_points",
        "games_played", "avg_points", "seasons_played", "owner_name",
    }
    assert expected_fields.issubset(set(rec.keys()))


@pytest.mark.anyio
async def test_career_multiple_owners(client, db_session):
    """Career records should show '(multiple)' when player had different owners."""
    league = await create_league(db_session, id="league2")
    u1 = await create_user(db_session, id="mu1", username="multi1", display_name="Multi One")
    u2 = await create_user(db_session, id="mu2", username="multi2", display_name="Multi Two")

    s1 = await create_season(db_session, league, year=2022)
    s2 = await create_season(db_session, league, year=2023)

    r1 = await create_roster(db_session, s1, u1, roster_id=1, team_name="T1")
    r2 = await create_roster(db_session, s1, u1, roster_id=2, team_name="T1b")
    r3 = await create_roster(db_session, s2, u2, roster_id=1, team_name="T2")
    r4 = await create_roster(db_session, s2, u2, roster_id=2, team_name="T2b")

    p = await create_player(db_session, id="mp1", full_name="Traded Guy", position="WR")

    m1 = await create_matchup(db_session, s1, r1, r2, week=1, matchup_id=1, match_type="regular")
    await create_matchup_player_point(db_session, m1, r1, p, points=20.0)

    m2 = await create_matchup(db_session, s2, r3, r4, week=1, matchup_id=1, match_type="regular")
    await create_matchup_player_point(db_session, m2, r3, p, points=25.0)

    await db_session.commit()

    resp = await client.get("/api/player-records?view=career&match_type=regular&position=WR")
    records = resp.json()["records"]
    traded = next(r for r in records if r["player_name"] == "Traded Guy")
    assert traded["owner_name"] == "(multiple)"
    assert traded["total_points"] == 45.0
    assert traded["seasons_played"] == 2


# ---- Empty data test ----

@pytest.mark.anyio
async def test_empty_records(client):
    """Should return empty list when no data exists."""
    resp = await client.get("/api/player-records?view=game&match_type=regular")
    assert resp.status_code == 200
    assert resp.json()["records"] == []
