from tests.conftest import LEAGUE_PREFIX
from tests.conftest import (
    create_league,
    create_season,
    create_user,
    create_roster,
    create_player,
    create_matchup,
    create_matchup_player_point,
    create_draft,
    create_draft_pick,
)


# ---------------------------------------------------------------------------
# Helper to set up a basic draft scenario
# ---------------------------------------------------------------------------


async def _setup_basic_draft(db, year=2020, draft_type="linear", rounds=3):
    """Create a basic draft scenario with 2 owners.
    Returns (draft, season, roster1, roster2, user1, user2)."""
    league = await create_league(db)
    season = await create_season(
        db, league, year=year, regular_season_weeks=14
    )
    user1 = await create_user(
        db, id="user1", username="owner1", display_name="Owner One"
    )
    user2 = await create_user(
        db, id="user2", username="owner2", display_name="Owner Two"
    )
    roster1 = await create_roster(db, season, user1, roster_id=1)
    roster2 = await create_roster(db, season, user2, roster_id=2)

    # Create draft
    draft = await create_draft(
        db,
        season,
        id=f"draft_{year}",
        year=year,
        type=draft_type,
        status="complete",
        rounds=rounds,
        draft_order={"1": 1, "2": 2},  # slot: roster_id
    )
    await db.flush()
    return draft, season, roster1, roster2, user1, user2


async def _add_draft_pick(
    db, draft, round_num, pick_in_round, roster_id, player
):
    """Helper: add a draft pick."""
    pick_no = (round_num - 1) * 2 + pick_in_round  # 2 teams
    await create_draft_pick(
        db,
        draft,
        pick_no=pick_no,
        round=round_num,
        pick_in_round=pick_in_round,
        roster_id=roster_id,
        player_id=player.id,
    )


async def _add_player_points(
    db, season, roster, player, week, points, is_starter=True
):
    """Helper: create a matchup + player point entry for a given week."""
    matchup = await create_matchup(
        db,
        season,
        roster,
        roster,
        week=week,
        matchup_id=week * 100 + roster.id,
        home_points=points,
        away_points=0.0,
    )
    await create_matchup_player_point(
        db, matchup, roster, player, points=points, is_starter=is_starter
    )
    return matchup


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_draft_grades_empty(client):
    """No drafts should return an empty list."""
    response = await client.get(f"{LEAGUE_PREFIX}/draft-grades")
    assert response.status_code == 200
    assert response.json()["drafts"] == []


async def test_draft_grades_basic_draft(client, db_session):
    """A basic 2-owner draft with known scoring should produce grades."""
    draft, season, r1, r2, u1, u2 = await _setup_basic_draft(
        db_session, year=2020
    )

    # Create players
    p1 = await create_player(
        db_session, id="p1", full_name="Player 1", position="WR", team="KC"
    )
    p2 = await create_player(
        db_session, id="p2", full_name="Player 2", position="RB", team="SF"
    )
    p3 = await create_player(
        db_session, id="p3", full_name="Player 3", position="WR", team="BUF"
    )
    p4 = await create_player(
        db_session, id="p4", full_name="Player 4", position="QB", team="KC"
    )

    # Draft picks: user1 picks p1, p4; user2 picks p2, p3
    await _add_draft_pick(db_session, draft, 1, 1, 1, p1)  # r1: user1 -> p1
    await _add_draft_pick(db_session, draft, 1, 2, 2, p2)  # r1: user2 -> p2
    await _add_draft_pick(db_session, draft, 2, 1, 2, p3)  # r2: user2 -> p3
    await _add_draft_pick(db_session, draft, 2, 2, 1, p4)  # r2: user1 -> p4

    # Add points for drafted players
    # Player 1 scores well for user1 (weeks 1-3)
    for wk in [1, 2, 3]:
        await _add_player_points(
            db_session, season, r1, p1, wk, 20.0, is_starter=True
        )

    # Player 2 scores moderately for user2
    for wk in [1, 2, 3]:
        await _add_player_points(
            db_session, season, r2, p2, wk, 12.0, is_starter=True
        )

    # Player 3 scores well for user2
    for wk in [1, 2, 3]:
        await _add_player_points(
            db_session, season, r2, p3, wk, 15.0, is_starter=True
        )

    # Player 4 scores poorly for user1
    for wk in [1, 2, 3]:
        await _add_player_points(
            db_session, season, r1, p4, wk, 8.0, is_starter=True
        )

    await db_session.flush()

    response = await client.get(f"{LEAGUE_PREFIX}/draft-grades")
    assert response.status_code == 200
    data = response.json()
    assert len(data["drafts"]) == 1

    draft_result = data["drafts"][0]
    assert draft_result["draft_id"] == "draft_2020"
    assert draft_result["year"] == 2020
    assert len(draft_result["owners"]) == 2

    # User2 should have higher total value (p2 + p3 > p1 + p4)
    owners_sorted = draft_result["owners"]
    assert owners_sorted[0]["total_value"] > owners_sorted[1]["total_value"]


async def test_draft_grades_filter_by_type(client, db_session):
    """Should be able to filter by draft type (startup vs rookie).

    Startup draft = 20+ rounds
    Rookie drafts = <20 rounds (typically 3-5 rounds)
    """
    # Create league and users once
    league = await create_league(db_session)
    u1 = await create_user(
        db_session, id="user1", username="owner1", display_name="Owner One"
    )
    u2 = await create_user(
        db_session, id="user2", username="owner2", display_name="Owner Two"
    )

    # Create startup draft (25 rounds)
    season1 = await create_season(
        db_session, league, year=2020, regular_season_weeks=14
    )
    r1 = await create_roster(db_session, season1, u1, roster_id=1)
    r2 = await create_roster(db_session, season1, u2, roster_id=2)
    draft1 = await create_draft(
        db_session,
        season1,
        id="draft_2020",
        year=2020,
        type="linear",
        status="complete",
        rounds=25,  # startup draft has 20+ rounds
        draft_order={"1": 1, "2": 2},
    )
    p1 = await create_player(
        db_session, id="p1", full_name="Player 1", position="WR"
    )
    await _add_draft_pick(db_session, draft1, 1, 1, 1, p1)

    # Create rookie draft (3 rounds)
    season2 = await create_season(
        db_session, league, year=2021, regular_season_weeks=14
    )
    r3 = await create_roster(db_session, season2, u1, roster_id=1)
    r4 = await create_roster(db_session, season2, u2, roster_id=2)
    draft2 = await create_draft(
        db_session,
        season2,
        id="draft_2021",
        year=2021,
        type="snake",
        status="complete",
        rounds=3,  # rookie drafts have <20 rounds
        draft_order={"1": 1, "2": 2},
    )
    p2 = await create_player(
        db_session, id="p2", full_name="Player 2", position="RB"
    )
    await _add_draft_pick(db_session, draft2, 1, 1, 1, p2)

    await db_session.flush()

    # Test filter by startup (20+ rounds)
    response = await client.get(f"{LEAGUE_PREFIX}/draft-grades?draft_type=startup")
    assert response.status_code == 200
    data = response.json()
    assert len(data["drafts"]) == 1
    assert data["drafts"][0]["year"] == 2020
    assert data["drafts"][0]["rounds"] == 25

    # Test filter by rookie (<20 rounds)
    response = await client.get(f"{LEAGUE_PREFIX}/draft-grades?draft_type=rookie")
    assert response.status_code == 200
    data = response.json()
    assert len(data["drafts"]) == 1
    assert data["drafts"][0]["year"] == 2021
    assert data["drafts"][0]["rounds"] == 3

    # Test no filter (all drafts)
    response = await client.get(f"{LEAGUE_PREFIX}/draft-grades")
    assert response.status_code == 200
    data = response.json()
    assert len(data["drafts"]) == 2


async def test_draft_grades_filter_by_owner(client, db_session):
    """Should be able to filter by owner."""
    draft, season, r1, r2, u1, u2 = await _setup_basic_draft(
        db_session, year=2020
    )

    p1 = await create_player(
        db_session, id="p1", full_name="Player 1", position="WR"
    )
    p2 = await create_player(
        db_session, id="p2", full_name="Player 2", position="RB"
    )

    await _add_draft_pick(db_session, draft, 1, 1, 1, p1)
    await _add_draft_pick(db_session, draft, 1, 2, 2, p2)

    await db_session.flush()

    # Filter by user1
    response = await client.get(f"{LEAGUE_PREFIX}/draft-grades?owner_id=user1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["drafts"]) == 1
    # Verify user1 is in the draft
    owners = data["drafts"][0]["owners"]
    assert any(o["user_id"] == "user1" for o in owners)


async def test_draft_grades_bench_weighting(client, db_session):
    """Bench points should be weighted at 0.1 (much less than starter 1.5)."""
    draft, season, r1, r2, u1, u2 = await _setup_basic_draft(
        db_session, year=2020
    )

    p1 = await create_player(
        db_session, id="p1", full_name="Player 1", position="WR"
    )
    p2 = await create_player(
        db_session, id="p2", full_name="Player 2", position="RB"
    )

    await _add_draft_pick(db_session, draft, 1, 1, 1, p1)
    await _add_draft_pick(db_session, draft, 1, 2, 2, p2)

    # p1 scores 20 pts as starter for 3 weeks
    # weighted: 20 * 1.5 * 3 = 90
    for wk in [1, 2, 3]:
        await _add_player_points(
            db_session, season, r1, p1, wk, 20.0, is_starter=True
        )

    # p2 scores 20 pts on bench for 3 weeks
    # weighted: 20 * 0.1 * 3 = 6
    for wk in [1, 2, 3]:
        await _add_player_points(
            db_session, season, r2, p2, wk, 20.0, is_starter=False
        )

    await db_session.flush()

    response = await client.get(f"{LEAGUE_PREFIX}/draft-grades")
    data = response.json()
    draft_result = data["drafts"][0]

    # Find each owner
    owner1 = next(o for o in draft_result["owners"] if o["user_id"] == "user1")
    owner2 = next(o for o in draft_result["owners"] if o["user_id"] == "user2")

    # owner1 should have much higher value (90 vs 6)
    assert owner1["total_value"] > owner2["total_value"] * 10


async def test_draft_grades_single_draft_endpoint(client, db_session):
    """Should be able to get a single draft by ID."""
    draft, season, r1, r2, u1, u2 = await _setup_basic_draft(
        db_session, year=2020
    )

    p1 = await create_player(
        db_session, id="p1", full_name="Player 1", position="WR"
    )
    await _add_draft_pick(db_session, draft, 1, 1, 1, p1)

    await db_session.flush()

    response = await client.get(f"{LEAGUE_PREFIX}/draft-grades/{draft.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["draft_id"] == draft.id
    assert data["year"] == 2020


async def test_draft_grades_single_draft_not_found(client):
    """Should return 404 for non-existent draft."""
    response = await client.get(f"{LEAGUE_PREFIX}/draft-grades/nonexistent")
    assert response.status_code == 404


async def test_draft_grades_response_has_all_fields(client, db_session):
    """Verify the response has all expected fields."""
    draft, season, r1, r2, u1, u2 = await _setup_basic_draft(
        db_session, year=2020
    )

    p1 = await create_player(
        db_session, id="p1", full_name="Player 1", position="WR", team="KC"
    )
    await _add_draft_pick(db_session, draft, 1, 1, 1, p1)
    await _add_player_points(
        db_session, season, r1, p1, 1, 15.0, is_starter=True
    )

    await db_session.flush()

    response = await client.get(f"{LEAGUE_PREFIX}/draft-grades")
    data = response.json()
    draft_result = data["drafts"][0]

    # Verify draft-level fields
    assert "draft_id" in draft_result
    assert "year" in draft_result
    assert "type" in draft_result
    assert "rounds" in draft_result
    assert "weeks_of_data" in draft_result
    assert "avg_value" in draft_result
    assert "total_picks" in draft_result
    assert "owners" in draft_result

    # Verify owner-level fields
    owner = draft_result["owners"][0]
    assert "user_id" in owner
    assert "username" in owner
    assert "avatar" in owner
    assert "total_value" in owner
    assert "num_picks" in owner
    assert "avg_value_per_pick" in owner
    assert "value_vs_average" in owner
    assert "grade" in owner
    assert "picks" in owner

    # Verify pick-level fields
    pick = owner["picks"][0]
    assert "pick_no" in pick
    assert "round" in pick
    assert "player_id" in pick
    assert "player_name" in pick
    assert "position" in pick
    assert "team" in pick
    assert "weighted_points" in pick
    assert "expected_points" in pick
    assert "starter_weeks" in pick
    assert "bench_weeks" in pick
    assert "total_weeks" in pick


async def test_draft_grade_measures_actual_vs_expected(client, db_session):
    """Grades reflect production relative to the per-round baseline for the
    picks an owner held, not raw total value.

    Two owners each hold one round-1 pick and one round-4 pick, so their
    expected values are identical. The owner whose picks outscore the other's
    must grade higher, and the round-1 baseline (avg of both R1 picks) is
    reflected in each pick's expected_points.
    """
    draft, season, r1, r2, u1, u2 = await _setup_basic_draft(
        db_session, year=2023, rounds=4
    )

    # user1's picks (roster 1): a strong R1, weak R4
    p1 = await create_player(db_session, id="p1", full_name="Strong R1", position="WR", team="KC")
    p2 = await create_player(db_session, id="p2", full_name="Weak R4", position="RB", team="SF")
    # user2's picks (roster 2): weak R1, weak R4
    p3 = await create_player(db_session, id="p3", full_name="Weak R1", position="WR", team="BUF")
    p4 = await create_player(db_session, id="p4", full_name="Weak R4b", position="WR", team="DAL")

    await _add_draft_pick(db_session, draft, 1, 1, 1, p1)   # user1 R1
    await _add_draft_pick(db_session, draft, 1, 2, 2, p3)   # user2 R1
    await _add_draft_pick(db_session, draft, 4, 1, 2, p4)   # user2 R4
    await _add_draft_pick(db_session, draft, 4, 2, 1, p2)   # user1 R4

    # p1 scores big; p2/p3/p4 score little
    for wk in [1, 2, 3]:
        await _add_player_points(db_session, season, r1, p1, wk, 20.0, is_starter=True)
        await _add_player_points(db_session, season, r1, p2, wk, 2.0, is_starter=True)
        await _add_player_points(db_session, season, r2, p3, wk, 2.0, is_starter=True)
        await _add_player_points(db_session, season, r2, p4, wk, 2.0, is_starter=True)

    await db_session.flush()

    response = await client.get(f"{LEAGUE_PREFIX}/draft-grades?draft_type=rookie")
    assert response.status_code == 200
    owners = {o["user_id"]: o for o in response.json()["drafts"][0]["owners"]}

    # user1 held a strong R1 → beats expected; user2's identical slots lag
    assert owners["user1"]["value_vs_average"] > 1.0
    assert owners["user2"]["value_vs_average"] < 1.0
    assert owners["user1"]["grade"] != owners["user2"]["grade"]

    # No round multipliers anymore
    for o in owners.values():
        for pick in o["picks"]:
            assert "round_multiplier" not in pick
            assert "expected_points" in pick

    # R1 baseline = avg of p1 (20*1.5*3=90) and p3 (2*1.5*3=9) = 49.5;
    # both R1 picks carry that as their expected_points.
    u1_r1 = next(p for p in owners["user1"]["picks"] if p["round"] == 1)
    assert abs(u1_r1["expected_points"] - 49.5) < 0.01


async def test_draft_grade_ignores_pick_volume(client, db_session):
    """More picks doesn't inflate the grade when per-pick production is equal.

    user1 holds 4 picks and user2 holds 1, but every pick produces the same.
    Both should grade equally (share ~1.0) even though user1's total value is
    4x user2's — the exact scenario the old total-vs-average method got wrong.
    """
    draft, season, r1, r2, u1, u2 = await _setup_basic_draft(
        db_session, year=2023, rounds=4
    )

    # user1: one pick in each of rounds 1-4, all scoring 10 pts/wk
    for rnd in [1, 2, 3, 4]:
        p = await create_player(db_session, id=f"a{rnd}", full_name=f"A{rnd}", position="WR", team="KC")
        await _add_draft_pick(db_session, draft, rnd, 1, 1, p)
        for wk in [1, 2, 3]:
            await _add_player_points(db_session, season, r1, p, wk, 10.0, is_starter=True)

    # user2: a single round-1 pick scoring the same 10 pts/wk
    b1 = await create_player(db_session, id="b1", full_name="B1", position="WR", team="SF")
    await _add_draft_pick(db_session, draft, 1, 2, 2, b1)
    for wk in [1, 2, 3]:
        await _add_player_points(db_session, season, r2, b1, wk, 10.0, is_starter=True)

    await db_session.flush()

    response = await client.get(f"{LEAGUE_PREFIX}/draft-grades?draft_type=rookie")
    assert response.status_code == 200
    owners = {o["user_id"]: o for o in response.json()["drafts"][0]["owners"]}

    # user1 has 4x the total value (4 picks vs 1) ...
    assert owners["user1"]["total_value"] > owners["user2"]["total_value"] * 3
    # ... but both drafted exactly to expectation for their slots -> same grade
    assert owners["user1"]["grade"] == owners["user2"]["grade"]
    assert abs(owners["user1"]["value_vs_average"] - 1.0) < 0.01
    assert abs(owners["user2"]["value_vs_average"] - 1.0) < 0.01


async def test_draft_grades_skips_empty_draft(client, db_session):
    """Phantom/abandoned drafts with no picks (status=complete, 0 picks) must not appear."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)

    # Real draft with picks
    real_draft = await create_draft(
        db_session, season, id="real_draft", year=2024, status="complete", rounds=3,
    )
    user = await create_user(db_session, id="u1", display_name="Alice")
    roster = await create_roster(db_session, season, user, roster_id=1)
    player = await create_player(db_session, id="p1", full_name="CeeDee Lamb", position="WR", team="DAL")
    await create_draft_pick(db_session, real_draft, pick_no=1, round=1, pick_in_round=1, roster_id=1, player_id=player.id)

    # Phantom draft — same year, status=complete, no picks
    await create_draft(
        db_session, season, id="phantom_draft", year=2024, status="complete", rounds=3,
    )
    await db_session.flush()

    response = await client.get(f"{LEAGUE_PREFIX}/draft-grades")
    assert response.status_code == 200
    data = response.json()
    # Only the real draft with picks should appear
    assert data["total"] == 1
    assert data["drafts"][0]["draft_id"] == "real_draft"
