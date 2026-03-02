from tests.conftest import (
    create_league, create_season, create_user, create_roster,
    create_player, create_transaction, create_matchup,
    create_matchup_player_point, create_draft, create_draft_pick,
)


# ---------------------------------------------------------------------------
# Helper to set up a basic trade scenario
# ---------------------------------------------------------------------------

async def _setup_basic_trade(db):
    """Create a 2-team trade: user1 sends player_a, receives player_b.
    Returns (season, roster1, roster2, player_a, player_b, txn)."""
    league = await create_league(db)
    season = await create_season(db, league, year=2024, regular_season_weeks=14)
    user1 = await create_user(db, id="user1", username="owner1", display_name="Owner One")
    user2 = await create_user(db, id="user2", username="owner2", display_name="Owner Two")
    roster1 = await create_roster(db, season, user1, roster_id=1)
    roster2 = await create_roster(db, season, user2, roster_id=2)

    player_a = await create_player(db, id="pa", full_name="Player A", position="WR", team="KC")
    player_b = await create_player(db, id="pb", full_name="Player B", position="RB", team="SF")

    # Trade at week 5: user1 drops pa, adds pb; user2 drops pb, adds pa
    txn = await create_transaction(
        db, season,
        id="trade_001",
        type="trade",
        status="complete",
        week=5,
        roster_ids=[1, 2],
        adds={"pa": 2, "pb": 1},   # pa goes to roster 2, pb goes to roster 1
        drops={"pa": 1, "pb": 2},   # pa dropped by roster 1, pb dropped by roster 2
        picks=None,
        waiver_bid=None,
        status_updated=1700000010000,
    )
    await db.flush()
    return season, roster1, roster2, player_a, player_b, txn


async def _add_player_points(db, season, roster, player, week, points, is_starter=True):
    """Helper: create a matchup + player point entry for a given week."""
    # We need a matchup for the week. Create a dummy one if needed.
    # Use a second roster as opponent (or self-match for simplicity)
    matchup = await create_matchup(
        db, season, roster, roster,
        week=week,
        matchup_id=week * 100 + roster.id,
        home_points=points,
        away_points=0.0,
    )
    await create_matchup_player_point(
        db, matchup, roster, player,
        points=points,
        is_starter=is_starter,
    )
    return matchup


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_trade_grades_empty(client):
    """No trades should return an empty list."""
    response = await client.get("/api/trade-grades")
    assert response.status_code == 200
    assert response.json()["trades"] == []


async def test_trade_grades_basic_trade(client, db_session):
    """A basic 2-team trade with known scoring should produce grades."""
    season, r1, r2, pa, pb, txn = await _setup_basic_trade(db_session)

    # Player A scores big for roster2 after the trade (weeks 6-8)
    for wk in [6, 7, 8]:
        await _add_player_points(db_session, season, r2, pa, wk, 20.0, is_starter=True)

    # Player B scores less for roster1 after the trade (weeks 6-8)
    for wk in [6, 7, 8]:
        await _add_player_points(db_session, season, r1, pb, wk, 8.0, is_starter=True)

    await db_session.flush()

    response = await client.get("/api/trade-grades")
    assert response.status_code == 200
    data = response.json()
    assert len(data["trades"]) == 1

    trade = data["trades"][0]
    assert trade["trade_id"] == "trade_001"
    assert trade["season"] == 2024
    assert trade["week"] == 5
    assert len(trade["sides"]) == 2

    # Side that got Player A (roster 2) should have higher value
    winner = trade["sides"][0]  # sorted by value_share desc
    loser = trade["sides"][1]
    assert winner["total_value"] > loser["total_value"]
    assert winner["value_share"] > loser["value_share"]


async def test_trade_grades_even_trade(client, db_session):
    """An even trade should give both sides B-range grades."""
    season, r1, r2, pa, pb, txn = await _setup_basic_trade(db_session)

    # Both players score equally after the trade
    for wk in [6, 7, 8]:
        await _add_player_points(db_session, season, r2, pa, wk, 15.0, is_starter=True)
        await _add_player_points(db_session, season, r1, pb, wk, 15.0, is_starter=True)

    await db_session.flush()

    response = await client.get("/api/trade-grades")
    data = response.json()
    trade = data["trades"][0]

    # Both sides should have roughly equal value shares (near 50% = B-)
    for side in trade["sides"]:
        assert side["grade"] in ("B-", "C+", "B"), f"Expected B-/C+ grade for even trade, got {side['grade']}"


async def test_trade_grades_lopsided_trade(client, db_session):
    """A very lopsided trade should give A-range and D/F-range grades."""
    season, r1, r2, pa, pb, txn = await _setup_basic_trade(db_session)

    # Player A scores big, Player B scores nothing
    for wk in [6, 7, 8, 9, 10]:
        await _add_player_points(db_session, season, r2, pa, wk, 25.0, is_starter=True)
        await _add_player_points(db_session, season, r1, pb, wk, 1.0, is_starter=True)

    await db_session.flush()

    response = await client.get("/api/trade-grades")
    data = response.json()
    trade = data["trades"][0]

    winner = trade["sides"][0]
    loser = trade["sides"][1]
    assert winner["grade"] in ("A+", "A", "A-", "B+")
    assert loser["grade"] in ("F", "D-", "D", "D+")


async def test_trade_grades_bench_weighting(client, db_session):
    """Bench points should be weighted at 0.1 (much less than starter 1.5)."""
    season, r1, r2, pa, pb, txn = await _setup_basic_trade(db_session)

    # Player A: 20pts as bench, Player B: 6pts as starter
    # Weighted: A = 20 * 0.1 = 2, B = 6 * 1.5 = 9
    for wk in [6, 7, 8]:
        await _add_player_points(db_session, season, r2, pa, wk, 20.0, is_starter=False)
        await _add_player_points(db_session, season, r1, pb, wk, 6.0, is_starter=True)

    await db_session.flush()

    response = await client.get("/api/trade-grades")
    data = response.json()
    trade = data["trades"][0]

    # Roster1 got pb (6pts starter each wk) - should have more value
    # than roster2 who got pa (20pts bench = 5pts weighted each wk)
    side_r1 = next(s for s in trade["sides"] if s["roster_id"] == 1)
    side_r2 = next(s for s in trade["sides"] if s["roster_id"] == 2)
    assert side_r1["total_value"] > side_r2["total_value"]


async def test_trade_grades_player_cut(client, db_session):
    """Player cut after trade contributes 0 for missing weeks."""
    season, r1, r2, pa, pb, txn = await _setup_basic_trade(db_session)

    # Player A scores in weeks 6-7 then cut (no points week 8+)
    for wk in [6, 7]:
        await _add_player_points(db_session, season, r2, pa, wk, 15.0, is_starter=True)

    # Player B scores all weeks
    for wk in [6, 7, 8, 9, 10]:
        await _add_player_points(db_session, season, r1, pb, wk, 10.0, is_starter=True)

    await db_session.flush()

    response = await client.get("/api/trade-grades")
    data = response.json()
    trade = data["trades"][0]

    # Roster 1 got pb = 10 * 5 = 50 value
    # Roster 2 got pa = 15 * 2 = 30 value (cut after week 7)
    side_r1 = next(s for s in trade["sides"] if s["roster_id"] == 1)
    side_r2 = next(s for s in trade["sides"] if s["roster_id"] == 2)
    assert side_r1["total_value"] > side_r2["total_value"]


async def test_trade_grades_with_draft_picks(client, db_session):
    """Trade involving draft picks should include pick value."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user1 = await create_user(db_session, id="user1", username="owner1", display_name="Owner One")
    user2 = await create_user(db_session, id="user2", username="owner2", display_name="Owner Two")
    r1 = await create_roster(db_session, season, user1, roster_id=1)
    r2 = await create_roster(db_session, season, user2, roster_id=2)

    player_a = await create_player(db_session, id="pa", full_name="Player A", position="WR")

    # Trade: roster1 sends Player A, receives roster 2's 2025 round 1 pick
    txn = await create_transaction(
        db_session, season,
        id="trade_picks",
        type="trade",
        status="complete",
        week=5,
        roster_ids=[1, 2],
        adds={"pa": 2},
        drops={"pa": 1},
        picks=[{
            "season": 2025,
            "round": 1,
            "roster_id": 2,          # originally roster 2's slot
            "previous_owner_id": 2,
            "owner_id": 1,           # now owned by roster 1
        }],
        status_updated=1700000020000,
    )

    # Player A scores for roster2 post-trade
    for wk in [6, 7, 8]:
        await _add_player_points(db_session, season, r2, player_a, wk, 15.0, is_starter=True)

    await db_session.flush()

    response = await client.get("/api/trade-grades")
    data = response.json()
    assert len(data["trades"]) == 1

    trade = data["trades"][0]
    side_r1 = next(s for s in trade["sides"] if s["roster_id"] == 1)
    # Roster 1 received a draft pick
    assert len(side_r1["assets_received"]["draft_picks"]) == 1
    pick = side_r1["assets_received"]["draft_picks"][0]
    assert pick["season"] == 2025
    assert pick["round"] == 1


async def test_trade_grades_pick_resolved(client, db_session):
    """Traded pick that was used in a draft should show the actual player."""
    league = await create_league(db_session)
    season_2024 = await create_season(db_session, league, year=2024)
    season_2025 = await create_season(db_session, league, year=2025)
    user1 = await create_user(db_session, id="user1", username="owner1", display_name="Owner One")
    user2 = await create_user(db_session, id="user2", username="owner2", display_name="Owner Two")
    r1_2024 = await create_roster(db_session, season_2024, user1, roster_id=1)
    r2_2024 = await create_roster(db_session, season_2024, user2, roster_id=2)
    r1_2025 = await create_roster(db_session, season_2025, user1, roster_id=1)

    player_a = await create_player(db_session, id="pa", full_name="Player A", position="WR")
    drafted_player = await create_player(db_session, id="dp1", full_name="Drafted Rookie", position="QB")

    # Trade in 2024: roster1 gives Player A, gets 2025 round 1 pick
    # roster_id=2 means the pick originally belongs to roster 2's slot
    txn = await create_transaction(
        db_session, season_2024,
        id="trade_res",
        type="trade",
        status="complete",
        week=5,
        roster_ids=[1, 2],
        adds={"pa": 2},
        drops={"pa": 1},
        picks=[{
            "season": 2025,
            "round": 1,
            "roster_id": 2,          # originally roster 2's draft slot
            "previous_owner_id": 2,
            "owner_id": 1,           # now owned by roster 1
        }],
        status_updated=1700000030000,
    )

    # 2025 draft: roster 1 used roster 2's pick (slot 2) to draft "Drafted Rookie"
    # draft_order maps slot -> original roster: slot 1 = roster 1, slot 2 = roster 2
    draft_2025 = await create_draft(
        db_session, season_2025, id="draft_2025", year=2025,
        draft_order={"1": 1, "2": 2},
    )
    await create_draft_pick(
        db_session, draft_2025,
        pick_no=2, round=1, pick_in_round=2,  # slot 2 = roster 2's original pick
        roster_id=1, player_id="dp1",          # but roster 1 made it (they traded for it)
    )

    # Drafted Rookie scores some points for roster 1 in 2025
    matchup = await create_matchup(
        db_session, season_2025, r1_2025, r1_2025,
        week=1, matchup_id=201, home_points=20.0, away_points=0.0,
    )
    await create_matchup_player_point(
        db_session, matchup, r1_2025, drafted_player,
        points=20.0, is_starter=True,
    )

    await db_session.flush()

    response = await client.get("/api/trade-grades")
    data = response.json()
    trade = data["trades"][0]

    side_r1 = next(s for s in trade["sides"] if s["roster_id"] == 1)
    pick_detail = side_r1["assets_received"]["draft_picks"][0]
    assert pick_detail["status"] == "actual"
    assert pick_detail["drafted_player"] == "Drafted Rookie"


async def test_trade_grades_season_filter(client, db_session):
    """Season filter should only return trades from that year."""
    league = await create_league(db_session)
    season_2023 = await create_season(db_session, league, year=2023)
    season_2024 = await create_season(db_session, league, year=2024)
    user1 = await create_user(db_session, id="user1", username="owner1", display_name="Owner One")
    user2 = await create_user(db_session, id="user2", username="owner2", display_name="Owner Two")
    await create_roster(db_session, season_2023, user1, roster_id=1)
    await create_roster(db_session, season_2023, user2, roster_id=2)
    await create_roster(db_session, season_2024, user1, roster_id=1)
    await create_roster(db_session, season_2024, user2, roster_id=2)

    await create_transaction(
        db_session, season_2023,
        id="trade_2023", type="trade", status="complete",
        week=5, roster_ids=[1, 2],
        adds={"pa": 2}, drops={"pa": 1},
        status_updated=1700000001000,
    )
    await create_transaction(
        db_session, season_2024,
        id="trade_2024", type="trade", status="complete",
        week=3, roster_ids=[1, 2],
        adds={"pb": 1}, drops={"pb": 2},
        status_updated=1700000002000,
    )
    await db_session.flush()

    response = await client.get("/api/trade-grades?season=2024")
    data = response.json()
    assert len(data["trades"]) == 1
    assert data["trades"][0]["season"] == 2024


async def test_trade_grades_sort_options(client, db_session):
    """All three sort modes should work."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user1 = await create_user(db_session, id="user1", username="owner1", display_name="Owner One")
    user2 = await create_user(db_session, id="user2", username="owner2", display_name="Owner Two")
    r1 = await create_roster(db_session, season, user1, roster_id=1)
    r2 = await create_roster(db_session, season, user2, roster_id=2)

    pa = await create_player(db_session, id="pa", full_name="Player A", position="WR")
    pb = await create_player(db_session, id="pb", full_name="Player B", position="RB")
    pc = await create_player(db_session, id="pc", full_name="Player C", position="QB")
    pd = await create_player(db_session, id="pd", full_name="Player D", position="TE")

    # Trade 1: lopsided (week 3)
    await create_transaction(
        db_session, season,
        id="trade_lopsided", type="trade", status="complete",
        week=3, roster_ids=[1, 2],
        adds={"pa": 2, "pb": 1}, drops={"pa": 1, "pb": 2},
        status_updated=1700000001000,
    )
    # Trade 2: even (week 7)
    await create_transaction(
        db_session, season,
        id="trade_even", type="trade", status="complete",
        week=7, roster_ids=[1, 2],
        adds={"pc": 2, "pd": 1}, drops={"pc": 1, "pd": 2},
        status_updated=1700000002000,
    )

    # Lopsided scoring for trade 1
    for wk in [4, 5, 6]:
        await _add_player_points(db_session, season, r2, pa, wk, 25.0, is_starter=True)
        await _add_player_points(db_session, season, r1, pb, wk, 2.0, is_starter=True)

    # Even scoring for trade 2
    for wk in [8, 9, 10]:
        await _add_player_points(db_session, season, r2, pc, wk, 12.0, is_starter=True)
        await _add_player_points(db_session, season, r1, pd, wk, 12.0, is_starter=True)

    await db_session.flush()

    # Sort by lopsided (default)
    resp = await client.get("/api/trade-grades?sort=lopsided")
    data = resp.json()
    assert len(data["trades"]) == 2
    assert data["trades"][0]["lopsidedness"] >= data["trades"][1]["lopsidedness"]

    # Sort by recent
    resp = await client.get("/api/trade-grades?sort=recent")
    data = resp.json()
    assert data["trades"][0]["date"] >= data["trades"][1]["date"]

    # Sort by even
    resp = await client.get("/api/trade-grades?sort=even")
    data = resp.json()
    assert data["trades"][0]["lopsidedness"] <= data["trades"][1]["lopsidedness"]


async def test_trade_grades_single_trade(client, db_session):
    """GET /trade-grades/{trade_id} should return a single trade."""
    season, r1, r2, pa, pb, txn = await _setup_basic_trade(db_session)

    for wk in [6, 7]:
        await _add_player_points(db_session, season, r2, pa, wk, 15.0, is_starter=True)
        await _add_player_points(db_session, season, r1, pb, wk, 10.0, is_starter=True)

    await db_session.flush()

    response = await client.get("/api/trade-grades/trade_001")
    assert response.status_code == 200
    data = response.json()
    assert data["trade_id"] == "trade_001"
    assert len(data["sides"]) == 2


async def test_trade_grades_single_trade_not_found(client):
    """GET /trade-grades/{trade_id} should 404 for missing trade."""
    response = await client.get("/api/trade-grades/nonexistent")
    assert response.status_code == 404


async def test_trade_grades_response_fields(client, db_session):
    """Response should have all expected keys."""
    season, r1, r2, pa, pb, txn = await _setup_basic_trade(db_session)

    for wk in [6, 7]:
        await _add_player_points(db_session, season, r2, pa, wk, 15.0, is_starter=True)
        await _add_player_points(db_session, season, r1, pb, wk, 10.0, is_starter=True)

    await db_session.flush()

    response = await client.get("/api/trade-grades")
    data = response.json()
    trade = data["trades"][0]

    for key in ["trade_id", "season", "week", "date", "weeks_of_data",
                "lopsidedness", "sides"]:
        assert key in trade, f"Missing key: {key}"

    side = trade["sides"][0]
    for key in ["roster_id", "owner_name", "user_id", "grade",
                "total_value", "value_share", "assets_received"]:
        assert key in side, f"Missing key in side: {key}"

    assets = side["assets_received"]
    assert "players" in assets
    assert "draft_picks" in assets

    if assets["players"]:
        player = assets["players"][0]
        for key in ["player_id", "player_name", "position",
                    "weighted_points", "adjusted_points", "starter_weeks",
                    "bench_weeks", "replacement_factor"]:
            assert key in player, f"Missing key in player: {key}"


async def test_trade_grades_replacement_factor(client, db_session):
    """Position replacement factor should reduce value when team replaces well."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024, regular_season_weeks=14)
    user1 = await create_user(db_session, id="user1", username="owner1", display_name="Owner One")
    user2 = await create_user(db_session, id="user2", username="owner2", display_name="Owner Two")
    r1 = await create_roster(db_session, season, user1, roster_id=1)
    r2 = await create_roster(db_session, season, user2, roster_id=2)

    # Two WRs on roster 1: player_a (will be traded) and player_backup
    player_a = await create_player(db_session, id="pa", full_name="Player A", position="WR")
    player_backup = await create_player(db_session, id="pb_backup", full_name="Backup WR", position="WR")
    player_b = await create_player(db_session, id="pb", full_name="Player B", position="RB")

    # Trade at week 5: roster1 sends pa, receives pb
    txn = await create_transaction(
        db_session, season,
        id="trade_repl",
        type="trade",
        status="complete",
        week=5,
        roster_ids=[1, 2],
        adds={"pa": 2, "pb": 1},
        drops={"pa": 1, "pb": 2},
        status_updated=1700000050000,
    )

    # Before trade (weeks 2-5): roster1 starts pa at WR, scoring 20/wk
    for wk in [2, 3, 4, 5]:
        m = await create_matchup(
            db_session, season, r1, r2,
            week=wk, matchup_id=wk * 100,
            home_points=20.0, away_points=10.0,
        )
        await create_matchup_player_point(db_session, m, r1, player_a, points=20.0, is_starter=True)

    # After trade (weeks 6-9): roster1 starts backup WR, also scoring ~20/wk
    # (good replacement)
    for wk in [6, 7, 8, 9]:
        m = await create_matchup(
            db_session, season, r1, r2,
            week=wk, matchup_id=wk * 100,
            home_points=20.0, away_points=15.0,
        )
        await create_matchup_player_point(db_session, m, r1, player_backup, points=20.0, is_starter=True)
        # Player A scores for roster2
        await create_matchup_player_point(db_session, m, r2, player_a, points=20.0, is_starter=True)
        # Player B scores for roster1
        await create_matchup_player_point(db_session, m, r1, player_b, points=10.0, is_starter=True)

    await db_session.flush()

    response = await client.get("/api/trade-grades")
    data = response.json()
    trade = data["trades"][0]

    # Roster2 got player_a. But roster1 replaced well at WR,
    # so replacement_factor should be 0.5 (halved gain)
    side_r2 = next(s for s in trade["sides"] if s["roster_id"] == 2)
    pa_detail = next(p for p in side_r2["assets_received"]["players"] if p["player_id"] == "pa")
    assert pa_detail["replacement_factor"] == 0.5
    # adjusted_points should be half of weighted_points
    assert pa_detail["adjusted_points"] == pa_detail["weighted_points"] * 0.5


async def test_trade_grades_owner_filter(client, db_session):
    """Owner filter should only return trades involving that owner."""
    season, r1, r2, pa, pb, txn = await _setup_basic_trade(db_session)

    # Create a third user with a separate trade
    user3 = await create_user(db_session, id="user3", username="owner3", display_name="Owner Three")
    r3 = await create_roster(db_session, season, user3, roster_id=3)
    pc = await create_player(db_session, id="pc", full_name="Player C", position="QB")
    pd = await create_player(db_session, id="pd", full_name="Player D", position="TE")

    await create_transaction(
        db_session, season,
        id="trade_other", type="trade", status="complete",
        week=6, roster_ids=[2, 3],
        adds={"pc": 3, "pd": 2}, drops={"pc": 2, "pd": 3},
        status_updated=1700000060000,
    )
    await db_session.flush()

    # Filter to user1 — should only get trade_001 (involves roster 1)
    response = await client.get("/api/trade-grades?owner_id=user1")
    data = response.json()
    assert len(data["trades"]) == 1
    assert data["trades"][0]["trade_id"] == "trade_001"

    # Filter to user3 — should only get trade_other
    response = await client.get("/api/trade-grades?owner_id=user3")
    data = response.json()
    assert len(data["trades"]) == 1
    assert data["trades"][0]["trade_id"] == "trade_other"

    # No filter — should get both
    response = await client.get("/api/trade-grades")
    data = response.json()
    assert len(data["trades"]) == 2


async def test_trade_grades_excludes_non_trades(client, db_session):
    """Waiver and free agent transactions should not appear."""
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user = await create_user(db_session)
    await create_roster(db_session, season, user, roster_id=1)

    await create_transaction(
        db_session, season, id="txn_waiver", type="waiver",
        status="complete", roster_ids=[1], status_updated=1700000001000,
    )
    await create_transaction(
        db_session, season, id="txn_fa", type="free_agent",
        status="complete", roster_ids=[1], status_updated=1700000002000,
    )
    await db_session.flush()

    response = await client.get("/api/trade-grades")
    assert response.status_code == 200
    assert response.json()["trades"] == []
