from datetime import datetime
from tests.conftest import (
    create_league, create_season, create_user, create_roster,
    create_draft, create_draft_pick, create_player,
)


async def test_get_all_drafts_success(client, db_session):
    league = await create_league(db_session)
    s2023 = await create_season(db_session, league, year=2023)
    s2024 = await create_season(db_session, league, year=2024)
    await create_draft(db_session, s2023, id="d2023", year=2023)
    await create_draft(db_session, s2024, id="d2024", year=2024)

    response = await client.get("/api/drafts")
    assert response.status_code == 200
    data = response.json()
    assert data["total_drafts"] == 2
    # Ordered by year desc
    assert data["drafts"][0]["year"] == 2024
    assert data["drafts"][1]["year"] == 2023


async def test_get_all_drafts_empty(client):
    response = await client.get("/api/drafts")
    assert response.status_code == 200
    data = response.json()
    assert data["total_drafts"] == 0
    assert data["drafts"] == []


async def test_get_draft_by_year_success(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user = await create_user(db_session, id="u1", display_name="Owner One", avatar="abc123")
    roster = await create_roster(db_session, season, user, roster_id=1)
    player = await create_player(db_session, id="p1", full_name="Patrick Mahomes", position="QB", team="KC")
    draft = await create_draft(db_session, season, draft_order={"1": 1})
    await create_draft_pick(db_session, draft, pick_no=1, round=1, pick_in_round=1, roster_id=roster.roster_id, player_id=player.id)

    response = await client.get("/api/drafts/2024")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2024
    assert data["total_picks"] == 1
    assert data["draft_order"] == {"1": 1}
    assert "slot_owners" in data
    assert data["slot_owners"]["1"]["display_name"] == "Owner One"
    assert data["slot_owners"]["1"]["avatar"] == "abc123"
    pick = data["picks"][0]
    assert pick["pick_no"] == 1
    assert pick["player_name"] == "Patrick Mahomes"
    assert pick["position"] == "QB"
    assert pick["owner_display_name"] == "Owner One"


async def test_get_draft_by_year_not_found(client):
    response = await client.get("/api/drafts/2020")
    assert response.status_code == 404
    assert "Draft for year 2020 not found" in response.json()["detail"]


async def test_draft_picks_ordered_by_pick_number(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    draft = await create_draft(db_session, season)
    # Create picks out of order
    await create_draft_pick(db_session, draft, pick_no=3, round=1, pick_in_round=3)
    await create_draft_pick(db_session, draft, pick_no=1, round=1, pick_in_round=1)
    await create_draft_pick(db_session, draft, pick_no=2, round=1, pick_in_round=2)

    response = await client.get("/api/drafts/2024")
    assert response.status_code == 200
    picks = response.json()["picks"]
    assert [p["pick_no"] for p in picks] == [1, 2, 3]


async def test_draft_pick_without_player(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    draft = await create_draft(db_session, season)
    await create_draft_pick(db_session, draft, pick_no=1, round=1, pick_in_round=1, player_id=None)

    response = await client.get("/api/drafts/2024")
    assert response.status_code == 200
    pick = response.json()["picks"][0]
    assert pick["player_id"] is None
    assert "player_name" not in pick


async def test_slot_owners_fallback_for_unknown_roster(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    draft = await create_draft(db_session, season, draft_order={"1": 1, "2": 999})
    user = await create_user(db_session, id="u1", display_name="Owner One")
    await create_roster(db_session, season, user, roster_id=1)

    response = await client.get("/api/drafts/2024")
    assert response.status_code == 200
    data = response.json()
    # Slot 1 has a known owner
    assert data["slot_owners"]["1"]["display_name"] == "Owner One"
    # Slot 2 has unknown roster, falls back to "Team 2"
    assert data["slot_owners"]["2"]["display_name"] == "Team 2"
    assert data["slot_owners"]["2"]["user_id"] is None


async def test_draft_pick_without_roster_user(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    draft = await create_draft(db_session, season)
    # roster_id 999 does not match any roster
    await create_draft_pick(db_session, draft, pick_no=1, round=1, pick_in_round=1, roster_id=999)

    response = await client.get("/api/drafts/2024")
    assert response.status_code == 200
    pick = response.json()["picks"][0]
    assert "owner_user_id" not in pick
    assert "owner_display_name" not in pick


async def test_get_current_draft_returns_latest(client, db_session):
    league = await create_league(db_session)
    s2023 = await create_season(db_session, league, year=2023)
    s2024 = await create_season(db_session, league, year=2024)
    await create_draft(db_session, s2023, id="d2023", year=2023, status="complete")
    await create_draft(
        db_session, s2024, id="d2024", year=2024, status="pre_draft",
        start_time=datetime(2024, 8, 25, 19, 0, 0)
    )

    response = await client.get("/api/drafts/current")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2024
    assert data["status"] == "pre_draft"
    assert data["start_time"] == "2024-08-25T19:00:00"


async def test_get_current_draft_no_start_time(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    await create_draft(db_session, season, id="d2025", year=2025, status="pre_draft")

    response = await client.get("/api/drafts/current")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2025
    assert data["status"] == "pre_draft"
    assert data["start_time"] is None


async def test_get_current_draft_empty(client):
    response = await client.get("/api/drafts/current")
    assert response.status_code == 200
    assert response.json() is None


async def test_get_all_drafts_includes_start_time(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    await create_draft(
        db_session, season, id="d2024", year=2024,
        start_time=datetime(2024, 8, 25, 19, 0, 0)
    )

    response = await client.get("/api/drafts")
    assert response.status_code == 200
    draft = response.json()["drafts"][0]
    assert draft["start_time"] == "2024-08-25T19:00:00"


async def test_get_current_draft_with_draft_order(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    u1 = await create_user(db_session, id="u1", display_name="Alice", avatar="av1")
    u2 = await create_user(db_session, id="u2", display_name="Bob", avatar="av2")
    await create_roster(db_session, season, u1, roster_id=1, team_name="Team Alpha")
    await create_roster(db_session, season, u2, roster_id=2, team_name=None)
    await create_draft(
        db_session, season, id="d2025", year=2025, status="pre_draft",
        draft_order={"1": 2, "2": 1}
    )

    response = await client.get("/api/drafts/current")
    assert response.status_code == 200
    data = response.json()
    order = data["draft_order"]
    assert len(order) == 2
    # Slot 1 → roster 2 → Bob
    assert order[0]["slot"] == 1
    assert order[0]["display_name"] == "Bob"
    assert order[0]["avatar"] == "av2"
    # Slot 2 → roster 1 → Team Alpha (team_name takes priority)
    assert order[1]["slot"] == 2
    assert order[1]["display_name"] == "Team Alpha"


async def test_get_current_draft_empty_draft_order(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    await create_draft(db_session, season, id="d2025", year=2025, status="pre_draft")

    response = await client.get("/api/drafts/current")
    assert response.status_code == 200
    assert response.json()["draft_order"] == []
