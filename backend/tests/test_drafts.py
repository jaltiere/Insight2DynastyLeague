from tests.conftest import LEAGUE_PREFIX
from datetime import datetime
from unittest.mock import AsyncMock, patch
from tests.conftest import (
    create_league, create_season, create_user, create_roster,
    create_draft, create_draft_pick, create_player,
)

# Patch sleeper_client.get_traded_picks for all /drafts/current tests
TRADED_PICKS_PATH = "app.api.routes.drafts.sleeper_client.get_traded_picks"


async def test_get_all_drafts_success(client, db_session):
    league = await create_league(db_session)
    s2023 = await create_season(db_session, league, year=2023)
    s2024 = await create_season(db_session, league, year=2024)
    await create_draft(db_session, s2023, id="d2023", year=2023)
    await create_draft(db_session, s2024, id="d2024", year=2024)

    response = await client.get(f"{LEAGUE_PREFIX}/drafts")
    assert response.status_code == 200
    data = response.json()
    assert data["total_drafts"] == 2
    # Ordered by year desc
    assert data["drafts"][0]["year"] == 2024
    assert data["drafts"][1]["year"] == 2023


async def test_get_all_drafts_empty(client):
    response = await client.get(f"{LEAGUE_PREFIX}/drafts")
    assert response.status_code == 200
    data = response.json()
    assert data["total_drafts"] == 0
    assert data["drafts"] == []


async def test_get_draft_by_year_success(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user = await create_user(db_session, id="u1", display_name="Owner One", avatar="abc123")
    roster = await create_roster(db_session, season, user, roster_id=1, team_name="Team Alpha")
    player = await create_player(db_session, id="p1", full_name="Patrick Mahomes", position="QB", team="KC")
    draft = await create_draft(db_session, season, draft_order={"1": 1})
    await create_draft_pick(db_session, draft, pick_no=1, round=1, pick_in_round=1, roster_id=roster.roster_id, player_id=player.id)

    response = await client.get(f"{LEAGUE_PREFIX}/drafts/2024")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2024
    assert data["total_picks"] == 1
    assert data["draft_order"] == {"1": 1}
    assert "slot_owners" in data
    assert data["slot_owners"]["1"]["display_name"] == "Team Alpha"
    assert data["slot_owners"]["1"]["avatar"] == "abc123"
    pick = data["picks"][0]
    assert pick["pick_no"] == 1
    assert pick["player_name"] == "Patrick Mahomes"
    assert pick["position"] == "QB"
    assert pick["owner_display_name"] == "Team Alpha"


async def test_get_draft_by_year_not_found(client):
    response = await client.get(f"{LEAGUE_PREFIX}/drafts/2020")
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

    response = await client.get(f"{LEAGUE_PREFIX}/drafts/2024")
    assert response.status_code == 200
    picks = response.json()["picks"]
    assert [p["pick_no"] for p in picks] == [1, 2, 3]


async def test_draft_pick_without_player(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    draft = await create_draft(db_session, season)
    await create_draft_pick(db_session, draft, pick_no=1, round=1, pick_in_round=1, player_id=None)

    response = await client.get(f"{LEAGUE_PREFIX}/drafts/2024")
    assert response.status_code == 200
    pick = response.json()["picks"][0]
    assert pick["player_id"] is None
    assert "player_name" not in pick


async def test_slot_owners_fallback_for_unknown_roster(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    draft = await create_draft(db_session, season, draft_order={"1": 1, "2": 999})
    user = await create_user(db_session, id="u1", display_name="Owner One")
    await create_roster(db_session, season, user, roster_id=1, team_name="Team Alpha")

    response = await client.get(f"{LEAGUE_PREFIX}/drafts/2024")
    assert response.status_code == 200
    data = response.json()
    # Slot 1 has a known owner (team_name takes priority)
    assert data["slot_owners"]["1"]["display_name"] == "Team Alpha"
    # Slot 2 has unknown roster, falls back to "Team 2"
    assert data["slot_owners"]["2"]["display_name"] == "Team 2"
    assert data["slot_owners"]["2"]["user_id"] is None


async def test_draft_pick_without_roster_user(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    draft = await create_draft(db_session, season)
    # roster_id 999 does not match any roster
    await create_draft_pick(db_session, draft, pick_no=1, round=1, pick_in_round=1, roster_id=999)

    response = await client.get(f"{LEAGUE_PREFIX}/drafts/2024")
    assert response.status_code == 200
    pick = response.json()["picks"][0]
    assert "owner_user_id" not in pick
    assert "owner_display_name" not in pick


@patch(TRADED_PICKS_PATH, new_callable=AsyncMock, return_value=[])
async def test_get_current_draft_returns_latest(mock_tp, client, db_session):
    league = await create_league(db_session)
    s2023 = await create_season(db_session, league, year=2023)
    s2024 = await create_season(db_session, league, year=2024)
    await create_draft(db_session, s2023, id="d2023", year=2023, status="complete")
    await create_draft(
        db_session, s2024, id="d2024", year=2024, status="pre_draft",
        start_time=datetime(2024, 8, 25, 19, 0, 0)
    )

    response = await client.get(f"{LEAGUE_PREFIX}/drafts/current")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2024
    assert data["status"] == "pre_draft"
    assert data["start_time"] == "2024-08-25T19:00:00"


@patch(TRADED_PICKS_PATH, new_callable=AsyncMock, return_value=[])
async def test_get_current_draft_no_start_time(mock_tp, client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    await create_draft(db_session, season, id="d2025", year=2025, status="pre_draft")

    response = await client.get(f"{LEAGUE_PREFIX}/drafts/current")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2025
    assert data["status"] == "pre_draft"
    assert data["start_time"] is None


@patch(TRADED_PICKS_PATH, new_callable=AsyncMock, return_value=[])
async def test_get_current_draft_empty(mock_tp, client):
    response = await client.get(f"{LEAGUE_PREFIX}/drafts/current")
    assert response.status_code == 200
    assert response.json() is None


async def test_get_all_drafts_includes_start_time(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    await create_draft(
        db_session, season, id="d2024", year=2024,
        start_time=datetime(2024, 8, 25, 19, 0, 0)
    )

    response = await client.get(f"{LEAGUE_PREFIX}/drafts")
    assert response.status_code == 200
    draft = response.json()["drafts"][0]
    assert draft["start_time"] == "2024-08-25T19:00:00"


@patch(TRADED_PICKS_PATH, new_callable=AsyncMock, return_value=[])
async def test_get_current_draft_with_draft_order(mock_tp, client, db_session):
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

    response = await client.get(f"{LEAGUE_PREFIX}/drafts/current")
    assert response.status_code == 200
    data = response.json()
    order = data["draft_order"]
    assert len(order) == 2
    # Slot 1 â†’ roster 2 â†’ Bob (not traded)
    assert order[0]["slot"] == 1
    assert order[0]["display_name"] == "Bob"
    assert order[0]["avatar"] == "av2"
    assert order[0]["is_traded"] is False
    assert order[0]["original_owner_name"] is None
    # Slot 2 â†’ roster 1 â†’ Team Alpha (team_name takes priority)
    assert order[1]["slot"] == 2
    assert order[1]["display_name"] == "Team Alpha"
    assert order[1]["is_traded"] is False


@patch(TRADED_PICKS_PATH, new_callable=AsyncMock, return_value=[])
async def test_get_current_draft_empty_draft_order(mock_tp, client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    await create_draft(db_session, season, id="d2025", year=2025, status="pre_draft")

    response = await client.get(f"{LEAGUE_PREFIX}/drafts/current")
    assert response.status_code == 200
    assert response.json()["draft_order"] == []


@patch(TRADED_PICKS_PATH, new_callable=AsyncMock)
async def test_get_current_draft_traded_pick(mock_tp, client, db_session):
    """When a first-round pick is traded, show the new owner with original owner noted."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    u1 = await create_user(db_session, id="u1", display_name="Alice", avatar="av1")
    u2 = await create_user(db_session, id="u2", display_name="Bob", avatar="av2")
    u3 = await create_user(db_session, id="u3", display_name="Charlie", avatar="av3")
    await create_roster(db_session, season, u1, roster_id=1)
    await create_roster(db_session, season, u2, roster_id=2)
    await create_roster(db_session, season, u3, roster_id=3)
    # Draft order: slot 1 = roster 1 (Alice), slot 2 = roster 2 (Bob), slot 3 = roster 3 (Charlie)
    await create_draft(
        db_session, season, id="d2025", year=2025, status="pre_draft",
        draft_order={"1": 1, "2": 2, "3": 3}
    )

    # Simulate: roster 2 (Bob) traded their 1st round pick to roster 3 (Charlie)
    mock_tp.return_value = [
        {"season": "2025", "round": 1, "roster_id": 2, "previous_owner_id": 2, "owner_id": 3},
    ]

    response = await client.get(f"{LEAGUE_PREFIX}/drafts/current")
    assert response.status_code == 200
    order = response.json()["draft_order"]
    assert len(order) == 3

    # Slot 1: Alice's pick, not traded
    assert order[0]["display_name"] == "Test Team"  # roster team_name default
    assert order[0]["is_traded"] is False
    assert order[0]["original_owner_name"] is None

    # Slot 2: Originally Bob's pick, traded to Charlie
    assert order[1]["display_name"] == "Test Team"  # Charlie's team_name
    assert order[1]["is_traded"] is True
    assert order[1]["original_owner_name"] == "Test Team"  # Bob's team_name

    # Slot 3: Charlie's own pick, not traded
    assert order[2]["is_traded"] is False


@patch(TRADED_PICKS_PATH, new_callable=AsyncMock)
async def test_get_current_draft_traded_pick_with_distinct_names(mock_tp, client, db_session):
    """Verify traded pick shows correct owner names when team_name differs."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    u1 = await create_user(db_session, id="u1", display_name="Alice", avatar="av1")
    u2 = await create_user(db_session, id="u2", display_name="Bob", avatar="av2")
    await create_roster(db_session, season, u1, roster_id=1, team_name="Team Alpha")
    await create_roster(db_session, season, u2, roster_id=2, team_name="Team Beta")
    await create_draft(
        db_session, season, id="d2025", year=2025, status="pre_draft",
        draft_order={"1": 1, "2": 2}
    )

    # Alice traded her pick to Bob
    mock_tp.return_value = [
        {"season": "2025", "round": 1, "roster_id": 1, "previous_owner_id": 1, "owner_id": 2},
    ]

    response = await client.get(f"{LEAGUE_PREFIX}/drafts/current")
    assert response.status_code == 200
    order = response.json()["draft_order"]

    # Slot 1: Originally Alice's, now Bob's
    assert order[0]["slot"] == 1
    assert order[0]["display_name"] == "Team Beta"
    assert order[0]["avatar"] == "av2"
    assert order[0]["is_traded"] is True
    assert order[0]["original_owner_name"] == "Team Alpha"

    # Slot 2: Bob's own pick, not traded
    assert order[1]["slot"] == 2
    assert order[1]["display_name"] == "Team Beta"
    assert order[1]["is_traded"] is False


@patch(TRADED_PICKS_PATH, new_callable=AsyncMock)
async def test_get_draft_by_year_incomplete_shows_current_owners_in_boxes(mock_tp, client, db_session):
    """For incomplete drafts, slot_owners show original owners, current_pick_owners show traded owners."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2025)
    u1 = await create_user(db_session, id="u1", display_name="Alice", avatar="av1")
    u2 = await create_user(db_session, id="u2", display_name="Bob", avatar="av2")
    u3 = await create_user(db_session, id="u3", display_name="Charlie", avatar="av3")
    await create_roster(db_session, season, u1, roster_id=1, team_name="Team Alpha")
    await create_roster(db_session, season, u2, roster_id=2, team_name="Team Beta")
    await create_roster(db_session, season, u3, roster_id=3, team_name="Team Gamma")

    # Draft order: slot 1 = roster 1 (Alice), slot 2 = roster 2 (Bob), slot 3 = roster 3 (Charlie)
    draft = await create_draft(
        db_session, season, id="d2025", year=2025, status="pre_draft",
        draft_order={"1": 1, "2": 2, "3": 3}, rounds=3
    )

    # Simulate: Alice (roster 1) traded her round 1 pick to Bob (roster 2)
    mock_tp.return_value = [
        {"season": "2025", "round": 1, "roster_id": 1, "previous_owner_id": 1, "owner_id": 2},
    ]

    response = await client.get(f"{LEAGUE_PREFIX}/drafts/2025")
    assert response.status_code == 200
    data = response.json()

    # slot_owners should ALWAYS show ORIGINAL owners (column headers)
    assert data["slot_owners"]["1"]["display_name"] == "Team Alpha"
    assert data["slot_owners"]["1"]["avatar"] == "av1"
    assert data["slot_owners"]["2"]["display_name"] == "Team Beta"
    assert data["slot_owners"]["3"]["display_name"] == "Team Gamma"

    # current_pick_owners should show who actually owns each pick
    assert "current_pick_owners" in data
    assert data["current_pick_owners"] is not None
    # Slot 1, Round 1: Traded to Bob
    assert data["current_pick_owners"]["1_1"]["display_name"] == "Team Beta"
    # Slot 1, Round 2: Not traded, still Alice
    assert data["current_pick_owners"]["1_2"]["display_name"] == "Team Alpha"
    # Slot 2, Round 1: Bob's own pick
    assert data["current_pick_owners"]["2_1"]["display_name"] == "Team Beta"


async def test_draft_slot_owners_isolated_from_other_leagues(client, db_session):
    """Rosters from other leagues with the same roster_id must not bleed into slot_owners."""
    # Target league (the one the client is scoped to)
    league_a = await create_league(db_session, id="test_league_001")
    season_a = await create_season(db_session, league_a, year=2024, group_id="test_league_001")
    user_a = await create_user(db_session, id="ua1", display_name="Alice")
    await create_roster(db_session, season_a, user_a, roster_id=1, team_name="Alice's Team")
    draft_a = await create_draft(db_session, season_a, id="da2024", year=2024, draft_order={"1": 1})
    player = await create_player(db_session, id="p1", full_name="Patrick Mahomes", position="QB", team="KC")
    await create_draft_pick(db_session, draft_a, pick_no=1, round=1, pick_in_round=1, roster_id=1, player_id=player.id)

    # Other league — same year, same roster_id=1, but different team
    league_b = await create_league(db_session, id="other_league_002", name="Other League")
    season_b = await create_season(db_session, league_b, year=2024, group_id="other_league_002")
    user_b = await create_user(db_session, id="ub1", display_name="Bob")
    await create_roster(db_session, season_b, user_b, roster_id=1, team_name="Bob's Team")

    response = await client.get(f"{LEAGUE_PREFIX}/drafts/2024")
    assert response.status_code == 200
    data = response.json()
    # Slot 1 must resolve to Alice's team, not Bob's from the other league
    assert data["slot_owners"]["1"]["display_name"] == "Alice's Team"
    assert data["picks"][0]["owner_display_name"] == "Alice's Team"


@patch(TRADED_PICKS_PATH, new_callable=AsyncMock)
async def test_get_draft_by_year_complete_no_current_pick_owners(mock_tp, client, db_session):
    """For complete drafts, slot_owners show original owners and no current_pick_owners returned."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    u1 = await create_user(db_session, id="u1", display_name="Alice", avatar="av1")
    u2 = await create_user(db_session, id="u2", display_name="Bob", avatar="av2")
    await create_roster(db_session, season, u1, roster_id=1, team_name="Team Alpha")
    await create_roster(db_session, season, u2, roster_id=2, team_name="Team Beta")

    draft = await create_draft(
        db_session, season, id="d2024", year=2024, status="complete",
        draft_order={"1": 1, "2": 2}
    )

    # Even if traded picks exist, they should be ignored for complete drafts
    mock_tp.return_value = [
        {"season": "2024", "round": 1, "roster_id": 1, "previous_owner_id": 1, "owner_id": 2},
    ]

    response = await client.get(f"{LEAGUE_PREFIX}/drafts/2024")
    assert response.status_code == 200
    data = response.json()

    # slot_owners should show ORIGINAL owners
    assert data["slot_owners"]["1"]["display_name"] == "Team Alpha"
    assert data["slot_owners"]["1"]["avatar"] == "av1"
    assert data["slot_owners"]["2"]["display_name"] == "Team Beta"

    # Complete drafts should not have current_pick_owners
    assert data["current_pick_owners"] is None
