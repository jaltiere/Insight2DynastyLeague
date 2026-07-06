"""Tests for team records endpoint."""
from tests.conftest import LEAGUE_PREFIX
from tests.conftest import (
    create_league, create_season, create_user, create_roster, create_matchup,
)


async def test_team_records_basic(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    u1 = await create_user(db_session, id="u1", display_name="Alice")
    u2 = await create_user(db_session, id="u2", display_name="Bob")
    r1 = await create_roster(db_session, season, u1, roster_id=1)
    r2 = await create_roster(db_session, season, u2, roster_id=2)
    await create_matchup(db_session, season, r1, r2, week=1, matchup_id=1,
                         home_points=120.0, away_points=100.0, match_type="regular")

    response = await client.get(f"{LEAGUE_PREFIX}/team-records")
    assert response.status_code == 200
    data = response.json()
    assert "streaks" in data


async def test_streaks_ignore_unplayed_matchups(client, db_session):
    """0-0 future-week matchups must not break win streaks as phantom ties.

    Alice wins week 1 and week 5 with unplayed 0-0 matchups between; the
    streak must be 2, not 1-broken-by-phantom-ties.
    """
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    u1 = await create_user(db_session, id="u1", display_name="Alice")
    u2 = await create_user(db_session, id="u2", display_name="Bob")
    r1 = await create_roster(db_session, season, u1, roster_id=1)
    r2 = await create_roster(db_session, season, u2, roster_id=2)

    await create_matchup(db_session, season, r1, r2, week=1, matchup_id=1,
                         home_points=120.0, away_points=100.0, match_type="regular")
    for week in (2, 3, 4):
        await create_matchup(db_session, season, r1, r2, week=week, matchup_id=1,
                             home_points=0, away_points=0, winner_roster_id=None,
                             match_type="regular")
    await create_matchup(db_session, season, r1, r2, week=5, matchup_id=1,
                         home_points=110.0, away_points=90.0, match_type="regular")

    response = await client.get(f"{LEAGUE_PREFIX}/team-records")
    assert response.status_code == 200
    reg_win = response.json()["streaks"]["reg_win"]
    alice = next(s for s in reg_win if "Alice" in s["owner_name"])
    assert alice["streak"] == 2
