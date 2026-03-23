"""Tests for the newsletter endpoint."""
import pytest
from httpx import AsyncClient

from tests.conftest import (
    create_league, create_user, create_season, create_roster,
    create_matchup, create_player, create_matchup_player_point,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def base_data(db_session):
    """Create a minimal two-team, one-matchup setup."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)

    user1 = await create_user(db_session, id="u1", username="alice", display_name="Alice")
    user2 = await create_user(db_session, id="u2", username="bob", display_name="Bob")

    roster1 = await create_roster(
        db_session, season, user1,
        roster_id=1, team_name="Alice's Team", division=1, wins=8, losses=4, points_for=1200.0,
    )
    roster2 = await create_roster(
        db_session, season, user2,
        roster_id=2, team_name="Bob's Team", division=2, wins=5, losses=7, points_for=1000.0,
    )

    matchup = await create_matchup(
        db_session, season, roster1, roster2,
        week=5, home_points=154.4, away_points=99.0,
        home_max_potential_points=170.0, away_max_potential_points=140.0,
    )

    # Players
    qb = await create_player(
        db_session, id="qb1", full_name="Patrick Mahomes", position="QB",
        team="KC", years_exp=7, rookie_year=2017,
    )
    rb = await create_player(
        db_session, id="rb1", full_name="Ashton Jeanty", position="RB",
        team="LV", years_exp=0, rookie_year=2024,
    )

    # Player points
    await create_matchup_player_point(
        db_session, matchup, roster1, qb, points=32.5, is_starter=True,
    )
    await create_matchup_player_point(
        db_session, matchup, roster2, rb, points=24.0, is_starter=True,
    )

    await db_session.commit()

    return {
        "season": season,
        "roster1": roster1,
        "roster2": roster2,
        "matchup": matchup,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_newsletter_returns_200(client: AsyncClient, base_data):
    resp = await client.get("/api/newsletter/5")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_newsletter_response_has_all_fields(client: AsyncClient, base_data):
    resp = await client.get("/api/newsletter/5")
    data = resp.json()

    required_keys = [
        "week", "season", "high_score", "low_score", "league_median",
        "top_players", "season_leaders", "rookie_report",
        "playoff_picture", "potential_points", "recaps", "upcoming_matchups",
    ]
    for key in required_keys:
        assert key in data, f"Missing key: {key}"


@pytest.mark.anyio
async def test_newsletter_week_and_season(client: AsyncClient, base_data):
    resp = await client.get("/api/newsletter/5")
    data = resp.json()
    assert data["week"] == 5
    assert data["season"] == 2024


@pytest.mark.anyio
async def test_newsletter_high_score(client: AsyncClient, base_data):
    resp = await client.get("/api/newsletter/5")
    data = resp.json()
    assert data["high_score"]["points"] == 154.4
    assert data["high_score"]["team_name"] == "Alice's Team"


@pytest.mark.anyio
async def test_newsletter_low_score(client: AsyncClient, base_data):
    resp = await client.get("/api/newsletter/5")
    data = resp.json()
    assert data["low_score"]["points"] == 99.0
    assert data["low_score"]["team_name"] == "Bob's Team"


@pytest.mark.anyio
async def test_newsletter_league_median(client: AsyncClient, base_data):
    resp = await client.get("/api/newsletter/5")
    data = resp.json()
    median_data = data["league_median"]
    assert "median" in median_data
    assert "teams" in median_data
    # With scores 154.4 and 99.0, median is 126.7
    assert median_data["median"] == pytest.approx(126.7, abs=0.1)
    # Higher score team beats median
    above = [t for t in median_data["teams"] if t["beat_median"]]
    below = [t for t in median_data["teams"] if not t["beat_median"]]
    assert len(above) == 1
    assert len(below) == 1
    assert above[0]["points"] == 154.4


@pytest.mark.anyio
async def test_newsletter_top_players_has_positions(client: AsyncClient, base_data):
    resp = await client.get("/api/newsletter/5")
    data = resp.json()
    top = data["top_players"]
    assert "QB" in top
    assert "RB" in top
    assert top["QB"] is not None
    assert top["QB"]["player_name"] == "Patrick Mahomes"
    assert top["QB"]["points"] == 32.5


@pytest.mark.anyio
async def test_newsletter_season_leaders(client: AsyncClient, base_data):
    resp = await client.get("/api/newsletter/5")
    data = resp.json()
    leaders = data["season_leaders"]
    assert "QB" in leaders
    assert "RB" in leaders
    # QB has Mahomes with 32.5 pts
    assert len(leaders["QB"]) >= 1
    assert leaders["QB"][0]["player_name"] == "Patrick Mahomes"
    assert leaders["QB"][0]["total_points"] == 32.5


@pytest.mark.anyio
async def test_newsletter_rookie_report(client: AsyncClient, base_data):
    resp = await client.get("/api/newsletter/5")
    data = resp.json()
    report = data["rookie_report"]
    assert "RB" in report
    # Jeanty is a rookie (years_exp=0)
    assert len(report["RB"]) >= 1
    assert report["RB"][0]["player_name"] == "Ashton Jeanty"
    assert "position_label" in report["RB"][0]


@pytest.mark.anyio
async def test_newsletter_playoff_picture(client: AsyncClient, base_data):
    resp = await client.get("/api/newsletter/5")
    data = resp.json()
    picture = data["playoff_picture"]
    assert "playoff" in picture
    assert "consolation" in picture
    # 2 teams total: both go into playoff (we only have 2)
    total = len(picture["playoff"]) + len(picture["consolation"])
    assert total == 2


@pytest.mark.anyio
async def test_newsletter_potential_points(client: AsyncClient, base_data):
    resp = await client.get("/api/newsletter/5")
    data = resp.json()
    pp = data["potential_points"]
    assert len(pp) == 2
    assert pp[0]["rank"] == 1
    # Alice has 170.0 max potential, Bob has 140.0
    assert pp[0]["max_potential_points"] == 170.0
    assert pp[1]["max_potential_points"] == 140.0


@pytest.mark.anyio
async def test_newsletter_season_query_param(client: AsyncClient, base_data):
    resp = await client.get("/api/newsletter/5?season=2024")
    assert resp.status_code == 200
    data = resp.json()
    assert data["season"] == 2024


@pytest.mark.anyio
async def test_newsletter_404_for_bad_season(client: AsyncClient, base_data):
    resp = await client.get("/api/newsletter/5?season=1999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_newsletter_empty_recaps(client: AsyncClient, base_data):
    """Recaps array should be empty when no recaps are stored."""
    resp = await client.get("/api/newsletter/5")
    data = resp.json()
    assert data["recaps"] == []
    assert data["upcoming_matchups"] == []
