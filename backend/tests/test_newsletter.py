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
        "week", "season", "is_regular_season", "high_score", "low_score", "league_median",
        "top_players", "season_leaders", "rookie_report",
        "standings", "playoff_odds", "playoff_picture", "potential_points", "recaps", "upcoming_matchups",
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
async def test_newsletter_is_regular_season_flag(client: AsyncClient, base_data):
    # Week 5 is within regular season (14 weeks), so should be True
    resp = await client.get("/api/newsletter/5")
    data = resp.json()
    assert data["is_regular_season"] is True

    # Week 15 is beyond regular season (14 weeks), so should be False
    resp = await client.get("/api/newsletter/15")
    data = resp.json()
    assert data["is_regular_season"] is False


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
async def test_newsletter_playoff_odds_regular_season(client: AsyncClient, base_data):
    # Week 5 is regular season — playoff_odds should be a list (possibly empty if no played matchups)
    resp = await client.get("/api/newsletter/5")
    data = resp.json()
    # playoff_odds is a list during regular season (simulation ran), None otherwise
    assert data["playoff_odds"] is None or isinstance(data["playoff_odds"], list)


@pytest.mark.anyio
async def test_newsletter_playoff_odds_null_in_playoffs(client: AsyncClient, base_data):
    # Week 15 is beyond regular season — playoff_odds should be None
    resp = await client.get("/api/newsletter/15")
    data = resp.json()
    assert data["playoff_odds"] is None


@pytest.mark.anyio
async def test_newsletter_standings(client: AsyncClient, base_data):
    resp = await client.get("/api/newsletter/5")
    data = resp.json()
    standings = data["standings"]
    assert len(standings) == 2
    # Alice has more wins so she should be ranked #1
    assert standings[0]["rank"] == 1
    assert standings[0]["team_name"] == "Alice's Team"
    assert standings[0]["wins"] == 8
    assert standings[0]["losses"] == 4
    assert standings[0]["points_for"] == 1200.0
    assert standings[1]["team_name"] == "Bob's Team"
    assert "division" in standings[0]


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


@pytest.mark.anyio
async def test_rookie_report_excludes_zero_point_rookies(client: AsyncClient, db_session):
    """Rookies with 0 points should not appear in the rookie report."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user1 = await create_user(db_session, id="u1", username="alice", display_name="Alice")
    user2 = await create_user(db_session, id="u2", username="bob", display_name="Bob")
    roster1 = await create_roster(db_session, season, user1, roster_id=1, division=1)
    roster2 = await create_roster(db_session, season, user2, roster_id=2, division=2)
    matchup = await create_matchup(db_session, season, roster1, roster2, week=3)

    active_rookie = await create_player(
        db_session, id="rb_active", full_name="Active Rookie", position="RB",
        team="KC", years_exp=0, rookie_year=2024,
    )
    zero_rookie = await create_player(
        db_session, id="rb_zero", full_name="Zero Rookie", position="RB",
        team="SF", years_exp=0, rookie_year=2024,
    )

    await create_matchup_player_point(db_session, matchup, roster1, active_rookie, points=18.5, is_starter=True)
    await create_matchup_player_point(db_session, matchup, roster2, zero_rookie, points=0.0, is_starter=True)
    await db_session.commit()

    resp = await client.get("/api/newsletter/3")
    data = resp.json()
    rb_rookies = data["rookie_report"]["RB"]
    names = [r["player_name"] for r in rb_rookies]
    assert "Active Rookie" in names
    assert "Zero Rookie" not in names
