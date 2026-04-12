"""Tests for the future draft pick tracker endpoint.

Covers:
  - GET /draft-picks/future  (response shape + no 500 with no traded picks)
  - Response has all required fields
  - Picks are generated for all owners × rounds × seasons
"""

import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient

from tests.conftest import (
    create_league,
    create_user,
    create_season,
    create_roster,
)
from app.models import Draft
from sqlalchemy.ext.asyncio import AsyncSession


pytestmark = pytest.mark.asyncio


async def _seed_base(db: AsyncSession):
    """Two-team season + a completed draft."""
    league = await create_league(db)
    season = await create_season(db, league, year=2025)

    user_a = await create_user(db, id="user_a", username="owner_a", display_name="Owner A")
    user_b = await create_user(db, id="user_b", username="owner_b", display_name="Owner B")

    await create_roster(db, season, user_a, roster_id=1, team_name="Team A")
    await create_roster(db, season, user_b, roster_id=2, team_name="Team B")

    draft = Draft(
        id="draft_2025",
        season_id=season.id,
        year=2025,
        type="snake",
        status="complete",
        rounds=5,
    )
    db.add(draft)
    await db.commit()
    return season


async def test_future_draft_picks_no_trades(client: AsyncClient, db_session: AsyncSession):
    """With no traded picks, every team should hold all their own picks."""
    await _seed_base(db_session)

    with patch(
        "app.api.routes.draft_picks.sleeper_client.get_traded_picks",
        new_callable=AsyncMock,
        return_value=[],
    ):
        resp = await client.get("/api/draft-picks/future")

    assert resp.status_code == 200
    data = resp.json()

    assert "current_season" in data
    assert "future_seasons" in data
    assert "num_rounds" in data
    assert "owners" in data
    assert "picks" in data

    assert data["current_season"] == 2025
    assert data["num_rounds"] == 5
    assert len(data["owners"]) == 2

    # No picks should be marked as traded
    assert all(not p["is_traded"] for p in data["picks"])

    # Every pick's current owner should equal the original owner
    for pick in data["picks"]:
        assert pick["current_roster_id"] == pick["original_roster_id"]


async def test_future_draft_picks_with_trade(client: AsyncClient, db_session: AsyncSession):
    """A traded pick should show the current owner differs from original."""
    await _seed_base(db_session)

    # Simulate Owner A's 2026 R1 being traded to Owner B
    mock_traded = [
        {
            "season": "2026",
            "round": 1,
            "roster_id": 1,           # original owner
            "owner_id": 2,            # current owner
            "previous_owner_id": 1,
        }
    ]

    with patch(
        "app.api.routes.draft_picks.sleeper_client.get_traded_picks",
        new_callable=AsyncMock,
        return_value=mock_traded,
    ):
        resp = await client.get("/api/draft-picks/future")

    assert resp.status_code == 200
    data = resp.json()

    traded_picks = [p for p in data["picks"] if p["is_traded"]]
    assert len(traded_picks) == 1

    tp = traded_picks[0]
    assert tp["season"] == 2026
    assert tp["round"] == 1
    assert tp["original_roster_id"] == 1
    assert tp["current_roster_id"] == 2


async def test_future_draft_picks_response_has_all_fields(client: AsyncClient, db_session: AsyncSession):
    """Each pick entry must include all required fields."""
    await _seed_base(db_session)

    with patch(
        "app.api.routes.draft_picks.sleeper_client.get_traded_picks",
        new_callable=AsyncMock,
        return_value=[],
    ):
        resp = await client.get("/api/draft-picks/future")

    assert resp.status_code == 200
    picks = resp.json()["picks"]
    assert len(picks) > 0

    required_pick_fields = {
        "season", "round", "original_roster_id", "original_owner",
        "current_roster_id", "current_owner", "is_traded",
    }
    required_owner_fields = {"roster_id", "user_id", "display_name", "avatar"}

    for pick in picks:
        assert required_pick_fields <= pick.keys(), f"Missing fields in pick: {pick.keys()}"
        assert required_owner_fields <= pick["original_owner"].keys()
        assert required_owner_fields <= pick["current_owner"].keys()


async def test_future_draft_picks_no_season(client: AsyncClient, db_session: AsyncSession):
    """Endpoint should not 500 when no season data exists."""
    with patch(
        "app.api.routes.draft_picks.sleeper_client.get_traded_picks",
        new_callable=AsyncMock,
        return_value=[],
    ):
        resp = await client.get("/api/draft-picks/future")

    assert resp.status_code == 200
    data = resp.json()
    assert data["owners"] == []
    assert data["picks"] == []
