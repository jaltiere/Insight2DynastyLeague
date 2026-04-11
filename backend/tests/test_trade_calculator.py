"""Tests for the trade calculator endpoints.

Covers:
  - GET /trade-calculator/owners  (response shape + no 500 on classification logic)
  - GET /trade-calculator/roster/{user_id}  (response shape)
  - GET /trade-calculator/pick-values  (response shape)
  - GET /trade-calculator/h2h-trades/{uid_a}/{uid_b}  (response shape)
"""

import pytest
from httpx import AsyncClient

from tests.conftest import (
    create_league,
    create_user,
    create_season,
    create_roster,
    create_player,
    create_matchup,
    create_matchup_player_point,
    create_transaction,
)
from app.models.player_value import PlayerValue
from sqlalchemy.ext.asyncio import AsyncSession


pytestmark = pytest.mark.asyncio


async def _seed_base(db: AsyncSession):
    """Create a minimal two-team season used by multiple tests."""
    league = await create_league(db)
    season = await create_season(db, league)

    user_a = await create_user(db, id="user_a", username="owner_a", display_name="Owner A")
    user_b = await create_user(db, id="user_b", username="owner_b", display_name="Owner B")

    roster_a = await create_roster(
        db, season, user_a,
        roster_id=1, wins=8, losses=6, players=["player_001"],
        team_name="Team A",
    )
    roster_b = await create_roster(
        db, season, user_b,
        roster_id=2, wins=4, losses=10, players=[],
        team_name="Team B",
    )

    player = await create_player(db, id="player_001", position="QB", age=28)

    await db.commit()
    return league, season, user_a, user_b, roster_a, roster_b, player


# ---------------------------------------------------------------------------
# /trade-calculator/owners
# ---------------------------------------------------------------------------

async def test_get_owners_returns_list(client: AsyncClient, db_session: AsyncSession):
    await _seed_base(db_session)
    resp = await client.get("/api/trade-calculator/owners")
    assert resp.status_code == 200
    data = resp.json()
    assert "owners" in data
    assert isinstance(data["owners"], list)
    assert len(data["owners"]) == 2


async def test_get_owners_response_has_required_fields(client: AsyncClient, db_session: AsyncSession):
    await _seed_base(db_session)
    resp = await client.get("/api/trade-calculator/owners")
    assert resp.status_code == 200
    owner = resp.json()["owners"][0]
    for field in ("user_id", "display_name", "team_name", "roster_id", "classification", "avg_age"):
        assert field in owner, f"Missing field: {field}"


async def test_get_owners_classification_is_string_or_none(client: AsyncClient, db_session: AsyncSession):
    """Regression: AttributeError 'PlayerPowerScore' object has no attribute 'score' (should be power_score)."""
    await _seed_base(db_session)
    resp = await client.get("/api/trade-calculator/owners")
    assert resp.status_code == 200
    for owner in resp.json()["owners"]:
        assert owner["classification"] is None or isinstance(owner["classification"], str)


async def test_get_owners_empty_when_no_season(client: AsyncClient):
    resp = await client.get("/api/trade-calculator/owners")
    assert resp.status_code == 200
    assert resp.json()["owners"] == []


# ---------------------------------------------------------------------------
# /trade-calculator/roster/{user_id}
# ---------------------------------------------------------------------------

async def test_get_roster_response_shape(client: AsyncClient, db_session: AsyncSession):
    await _seed_base(db_session)
    resp = await client.get("/api/trade-calculator/roster/user_a")
    assert resp.status_code == 200
    data = resp.json()
    assert "user_id" in data
    assert "players" in data
    assert isinstance(data["players"], list)


async def test_get_roster_player_has_ktc_fields(client: AsyncClient, db_session: AsyncSession):
    await _seed_base(db_session)

    # Seed a KTC value for player_001
    pv = PlayerValue(
        player_id="player_001",
        ktc_name="Patrick Mahomes",
        value=8500,
        rank=1,
        source="ktc",
        position="QB",
    )
    db_session.add(pv)
    await db_session.commit()

    resp = await client.get("/api/trade-calculator/roster/user_a")
    assert resp.status_code == 200
    players = resp.json()["players"]
    assert len(players) == 1
    p = players[0]
    for field in ("player_id", "full_name", "position", "ktc_value"):
        assert field in p, f"Missing field: {field}"
    assert p["ktc_value"] == 8500


async def test_get_roster_404_unknown_user(client: AsyncClient, db_session: AsyncSession):
    await _seed_base(db_session)
    resp = await client.get("/api/trade-calculator/roster/no_such_user")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /trade-calculator/pick-values
# ---------------------------------------------------------------------------

async def test_get_pick_values_empty(client: AsyncClient):
    resp = await client.get("/api/trade-calculator/pick-values")
    assert resp.status_code == 200
    data = resp.json()
    assert "picks" in data
    assert data["picks"] == []


async def test_get_pick_values_returns_rdp_rows(client: AsyncClient, db_session: AsyncSession):
    pv = PlayerValue(
        pick_key="2026_1_early",
        ktc_name="2026 Early 1st",
        value=7500,
        source="ktc",
        position="RDP",
    )
    db_session.add(pv)
    await db_session.commit()

    resp = await client.get("/api/trade-calculator/pick-values")
    assert resp.status_code == 200
    picks = resp.json()["picks"]
    assert len(picks) == 1
    pick = picks[0]
    for field in ("pick_key", "ktc_name", "value"):
        assert field in pick, f"Missing field: {field}"
    assert pick["value"] == 7500


# ---------------------------------------------------------------------------
# /trade-calculator/h2h-trades/{uid_a}/{uid_b}
# ---------------------------------------------------------------------------

async def test_h2h_trades_no_history(client: AsyncClient, db_session: AsyncSession):
    await _seed_base(db_session)
    resp = await client.get("/api/trade-calculator/h2h-trades/user_a/user_b")
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "trades" in data
    assert isinstance(data["trades"], list)


async def test_h2h_trades_unknown_user_returns_empty(client: AsyncClient, db_session: AsyncSession):
    await _seed_base(db_session)
    resp = await client.get("/api/trade-calculator/h2h-trades/user_a/ghost_user")
    # Unknown user gracefully returns empty history (no 500)
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "trades" in data
        assert data["trades"] == []
