from tests.conftest import LEAGUE_PREFIX
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
    create_draft,
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
    resp = await client.get(f"{LEAGUE_PREFIX}/trade-calculator/owners")
    assert resp.status_code == 200
    data = resp.json()
    assert "owners" in data
    assert isinstance(data["owners"], list)
    assert len(data["owners"]) == 2


async def test_get_owners_response_has_required_fields(client: AsyncClient, db_session: AsyncSession):
    await _seed_base(db_session)
    resp = await client.get(f"{LEAGUE_PREFIX}/trade-calculator/owners")
    assert resp.status_code == 200
    owner = resp.json()["owners"][0]
    for field in ("user_id", "display_name", "team_name", "roster_id", "classification", "avg_age"):
        assert field in owner, f"Missing field: {field}"


async def test_get_owners_classification_is_string_or_none(client: AsyncClient, db_session: AsyncSession):
    """Regression: AttributeError 'PlayerPowerScore' object has no attribute 'score' (should be power_score)."""
    await _seed_base(db_session)
    resp = await client.get(f"{LEAGUE_PREFIX}/trade-calculator/owners")
    assert resp.status_code == 200
    for owner in resp.json()["owners"]:
        assert owner["classification"] is None or isinstance(owner["classification"], str)


async def test_get_owners_empty_when_no_season(client: AsyncClient):
    resp = await client.get(f"{LEAGUE_PREFIX}/trade-calculator/owners")
    assert resp.status_code == 200
    assert resp.json()["owners"] == []


# ---------------------------------------------------------------------------
# /trade-calculator/roster/{user_id}
# ---------------------------------------------------------------------------

async def test_get_roster_response_shape(client: AsyncClient, db_session: AsyncSession):
    await _seed_base(db_session)
    resp = await client.get(f"{LEAGUE_PREFIX}/trade-calculator/roster/user_a")
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

    resp = await client.get(f"{LEAGUE_PREFIX}/trade-calculator/roster/user_a")
    assert resp.status_code == 200
    players = resp.json()["players"]
    assert len(players) == 1
    p = players[0]
    for field in ("player_id", "full_name", "position", "ktc_value"):
        assert field in p, f"Missing field: {field}"
    assert p["ktc_value"] == 8500


async def test_get_roster_404_unknown_user(client: AsyncClient, db_session: AsyncSession):
    await _seed_base(db_session)
    resp = await client.get(f"{LEAGUE_PREFIX}/trade-calculator/roster/no_such_user")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /trade-calculator/pick-values
# ---------------------------------------------------------------------------

async def test_get_pick_values_empty(client: AsyncClient):
    resp = await client.get(f"{LEAGUE_PREFIX}/trade-calculator/pick-values")
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

    resp = await client.get(f"{LEAGUE_PREFIX}/trade-calculator/pick-values")
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
    resp = await client.get(f"{LEAGUE_PREFIX}/trade-calculator/h2h-trades/user_a/user_b")
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "trades" in data
    assert isinstance(data["trades"], list)


async def test_h2h_trades_unknown_user_returns_empty(client: AsyncClient, db_session: AsyncSession):
    await _seed_base(db_session)
    resp = await client.get(f"{LEAGUE_PREFIX}/trade-calculator/h2h-trades/user_a/ghost_user")
    # Unknown user gracefully returns empty history (no 500)
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "trades" in data
        assert data["trades"] == []


# ---------------------------------------------------------------------------
# Classification consistency with the Roster Analysis page
# ---------------------------------------------------------------------------

async def test_owners_classification_matches_roster_analysis(client, db_session):
    """A team's classification must be identical on the trade calculator and
    the roster analysis page (same scoring inputs incl. KTC + position avg)."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)

    # Three teams with players that have KTC values, so the KTC component
    # (previously ignored by the owners endpoint) actually affects scores.
    for i in range(1, 4):
        u = await create_user(db_session, id=f"u{i}", username=f"o{i}", display_name=f"O{i}")
        await create_roster(db_session, season, u, roster_id=i, players=[f"p{i}"])
        pl = await create_player(db_session, id=f"p{i}", full_name=f"P{i}", position="QB", age=24 + i)
        db_session.add(PlayerValue(player_id=pl.id, value=9000 - i * 3000, superflex_value=9000 - i * 3000,
                                   position="QB", source="ktc", ktc_name=f"P{i}"))
    await db_session.commit()

    owners_resp = await client.get(f"{LEAGUE_PREFIX}/trade-calculator/owners")
    ra_resp = await client.get(f"{LEAGUE_PREFIX}/roster-analysis")
    assert owners_resp.status_code == 200 and ra_resp.status_code == 200

    owners_cls = {o["roster_id"]: o["classification"] for o in owners_resp.json()["owners"]}
    ra_cls = {t["roster_id"]: t["classification"] for t in ra_resp.json()["teams"]}
    assert owners_cls == ra_cls


# ---------------------------------------------------------------------------
# Preseason pick tiers fall back to prior-season standings
# ---------------------------------------------------------------------------

async def test_roster_picks_preseason_uses_prior_standings(client, db_session, monkeypatch):
    """In the preseason (all records 0-0), pick tiers derive from the prior
    season's final standings, not the empty current records."""
    from app.services.sleeper_client import sleeper_client

    league = await create_league(db_session)
    prior = await create_season(db_session, league, year=2025)
    current = await create_season(db_session, league, year=2026)

    # Prior season: roster 1 was worst (2-12), roster 2 was best (12-2)
    u1 = await create_user(db_session, id="u1", username="o1", display_name="Worst Last Year")
    u2 = await create_user(db_session, id="u2", username="o2", display_name="Best Last Year")
    await create_roster(db_session, prior, u1, roster_id=1, wins=2, losses=12)
    await create_roster(db_session, prior, u2, roster_id=2, wins=12, losses=2)
    # Current season: both 0-0 (preseason)
    await create_roster(db_session, current, u1, roster_id=1, wins=0, losses=0)
    await create_roster(db_session, current, u2, roster_id=2, wins=0, losses=0)
    await db_session.commit()

    async def _no_traded_picks(league_id=None):
        return []

    async def _no_drafts(league_id=None):
        return []

    monkeypatch.setattr(sleeper_client, "get_traded_picks", _no_traded_picks)
    monkeypatch.setattr(sleeper_client, "get_drafts", _no_drafts)

    # Worst prior record -> earliest pick slot; record shown reflects last
    # season (2-12), not the current 0-0.
    resp = await client.get(f"{LEAGUE_PREFIX}/trade-calculator/roster-picks/u1")
    assert resp.status_code == 200
    own1 = [p for p in resp.json()["picks"] if p["own_pick"]]
    assert own1, "expected the owner's own future picks"
    assert all(p["original_record"] == "2-12" for p in own1)
    assert all(p["estimated_pick_slot"] == 1 for p in own1)  # worst -> picks first

    # Best prior record -> latest pick slot (2 of 2)
    resp2 = await client.get(f"{LEAGUE_PREFIX}/trade-calculator/roster-picks/u2")
    own2 = [p for p in resp2.json()["picks"] if p["own_pick"]]
    assert all(p["original_record"] == "12-2" for p in own2)
    assert all(p["estimated_pick_slot"] == 2 for p in own2)


# ---------------------------------------------------------------------------
# Picks from an already-completed rookie draft are not tradeable
# ---------------------------------------------------------------------------

async def _seed_two_team_2026(db_session, draft_status: str | None):
    """Current season 2026 with two rosters and an optional 2026 draft row."""
    league = await create_league(db_session)
    current = await create_season(db_session, league, year=2026)
    u1 = await create_user(db_session, id="u1", username="o1", display_name="O1")
    u2 = await create_user(db_session, id="u2", username="o2", display_name="O2")
    await create_roster(db_session, current, u1, roster_id=1, wins=4, losses=10)
    await create_roster(db_session, current, u2, roster_id=2, wins=10, losses=4)
    if draft_status is not None:
        await create_draft(db_session, current, id="d2026", status=draft_status)
    await db_session.commit()


def _patch_sleeper(monkeypatch, traded_picks):
    from app.services.sleeper_client import sleeper_client

    async def _traded(league_id=None):
        return traded_picks

    async def _drafts(league_id=None):
        return [{"season": "2026", "status": "complete", "settings": {"rounds": 4}}]

    monkeypatch.setattr(sleeper_client, "get_traded_picks", _traded)
    monkeypatch.setattr(sleeper_client, "get_drafts", _drafts)


async def test_roster_picks_excludes_years_whose_draft_is_complete(
    client, db_session, monkeypatch
):
    """Sleeper keeps returning traded picks for a season after that season's
    rookie draft has been held. Those picks have already been used and must
    not be offered by the trade calculator."""
    await _seed_two_team_2026(db_session, draft_status="complete")

    _patch_sleeper(monkeypatch, traded_picks=[
        # A 2026 pick that was already used in the completed draft
        {"season": "2026", "round": 1, "roster_id": 2,
         "owner_id": 1, "previous_owner_id": 2},
        # A genuine future pick
        {"season": "2027", "round": 1, "roster_id": 2,
         "owner_id": 1, "previous_owner_id": 2},
    ])

    resp = await client.get(f"{LEAGUE_PREFIX}/trade-calculator/roster-picks/u1")
    assert resp.status_code == 200
    years = {p["year"] for p in resp.json()["picks"]}
    assert 2026 not in years, "2026 draft is complete; its picks no longer exist"
    assert 2027 in years


async def test_roster_picks_includes_current_year_before_its_draft(
    client, db_session, monkeypatch
):
    """Before the rookie draft is held, the current season's picks are still
    real assets and must remain tradeable."""
    await _seed_two_team_2026(db_session, draft_status="pre_draft")

    _patch_sleeper(monkeypatch, traded_picks=[
        {"season": "2026", "round": 1, "roster_id": 2,
         "owner_id": 1, "previous_owner_id": 2},
    ])

    resp = await client.get(f"{LEAGUE_PREFIX}/trade-calculator/roster-picks/u1")
    assert resp.status_code == 200
    years = {p["year"] for p in resp.json()["picks"]}
    assert 2026 in years, "2026 draft has not been held; its picks are still assets"


async def test_pick_values_excludes_years_whose_draft_is_complete(
    client, db_session
):
    """The pick list shown before an owner is selected comes from cached KTC
    rows, which linger after a draft. It must hide dead years too, or the two
    halves of the trade calculator disagree."""
    await _seed_two_team_2026(db_session, draft_status="complete")
    db_session.add(PlayerValue(
        pick_key="2026_1_early", ktc_name="2026 Early 1st",
        value=6165, source="ktc", position="RDP",
    ))
    db_session.add(PlayerValue(
        pick_key="2027_1_early", ktc_name="2027 Early 1st",
        value=7275, source="ktc", position="RDP",
    ))
    await db_session.commit()

    resp = await client.get(f"{LEAGUE_PREFIX}/trade-calculator/pick-values")
    assert resp.status_code == 200
    years = {p["year"] for p in resp.json()["picks"]}
    assert years == {2027}


async def test_pick_values_keeps_current_year_before_its_draft(
    client, db_session
):
    """Mirror of the above: pre-draft, the current year's pick values stay."""
    await _seed_two_team_2026(db_session, draft_status="pre_draft")
    db_session.add(PlayerValue(
        pick_key="2026_1_early", ktc_name="2026 Early 1st",
        value=6165, source="ktc", position="RDP",
    ))
    await db_session.commit()

    resp = await client.get(f"{LEAGUE_PREFIX}/trade-calculator/pick-values")
    assert resp.status_code == 200
    years = {p["year"] for p in resp.json()["picks"]}
    assert years == {2026}
