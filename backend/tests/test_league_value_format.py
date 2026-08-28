"""Tests for resolving which KTC value column a league should read.

Two independent axes: superflex (from roster_positions) and TE premium (from
scoring_settings.bonus_rec_te). All three configured leagues turned on TE
premium for 2026, and two of them already run SUPER_FLEX, so the wrong column
silently misprices whole position groups.
"""
import pytest
from sqlalchemy import select

from app.models.player_value import PlayerValue
from app.services.league_value_format import (
    LeagueValueFormat,
    get_league_value_format,
    te_premium_from_scoring,
)
from tests.conftest import create_league, create_season

SUPERFLEX_POSITIONS = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "SUPER_FLEX"]
ONE_QB_POSITIONS = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "FLEX", "DEF"]


# --- te_premium_from_scoring -------------------------------------------------

def test_te_premium_detected_from_bonus_rec_te():
    assert te_premium_from_scoring({"rec": 1.0, "bonus_rec_te": 0.5}) is True


def test_te_premium_false_without_the_bonus():
    assert te_premium_from_scoring({"rec": 1.0}) is False


def test_te_premium_false_for_zero_bonus():
    """Sleeper can carry the key at 0.0 when the setting was turned back off."""
    assert te_premium_from_scoring({"bonus_rec_te": 0.0}) is False


def test_te_premium_true_above_half_point():
    """KTC's tepp/teppp saturate at the 9999 ceiling, so every premium league
    reads the tep column; larger bonuses are still TE premium."""
    assert te_premium_from_scoring({"bonus_rec_te": 1.0}) is True


def test_te_premium_handles_missing_settings():
    assert te_premium_from_scoring(None) is False
    assert te_premium_from_scoring({}) is False


# --- column selection --------------------------------------------------------

def test_one_qb_no_premium_reads_base_columns():
    fmt = LeagueValueFormat(scoring_format="1qb", te_premium=False)
    assert fmt.value_column is PlayerValue.value
    assert fmt.rank_column is PlayerValue.rank


@pytest.mark.parametrize(
    "scoring_format,te_premium,expected",
    [
        ("1qb", True, "tep_value"),
        ("superflex", False, "superflex_value"),
        ("superflex", True, "superflex_tep_value"),
    ],
)
def test_specialised_formats_read_their_own_column(scoring_format, te_premium, expected):
    fmt = LeagueValueFormat(scoring_format=scoring_format, te_premium=te_premium)
    # Non-base columns coalesce down to a fallback, so assert the preferred
    # column leads the expression rather than comparing object identity.
    assert expected in str(fmt.value_column)


def test_superflex_tep_falls_back_through_superflex_to_base():
    """KTC omits values for fringe players; a null must not read as zero."""
    expr = str(LeagueValueFormat("superflex", True).value_column)
    assert expr.index("superflex_tep_value") < expr.index("superflex_value")
    assert expr.index("superflex_value") < expr.index("player_values.value")


# --- get_league_value_format -------------------------------------------------

@pytest.mark.asyncio
async def test_resolves_one_qb_te_premium_league(db_session):
    """Insight2Dynasty in 2026: 1QB, TE premium on."""
    league = await create_league(
        db_session,
        id="i2d",
        roster_positions=ONE_QB_POSITIONS,
        scoring_settings={"rec": 1.0, "bonus_rec_te": 0.5},
    )
    await create_season(db_session, league, year=2026)

    fmt = await get_league_value_format(db_session, "i2d")

    assert fmt == LeagueValueFormat(scoring_format="1qb", te_premium=True)


@pytest.mark.asyncio
async def test_resolves_superflex_te_premium_league(db_session):
    """Couch Crusaders / Double Domination in 2026."""
    league = await create_league(
        db_session,
        id="cc",
        roster_positions=SUPERFLEX_POSITIONS,
        scoring_settings={"bonus_rec_te": 0.5},
    )
    await create_season(db_session, league, year=2026)

    fmt = await get_league_value_format(db_session, "cc")

    assert fmt == LeagueValueFormat(scoring_format="superflex", te_premium=True)


@pytest.mark.asyncio
async def test_uses_the_latest_season(db_session):
    """A league that adds SUPER_FLEX must switch on the newest season's config,
    not the oldest — this is how I2D flips over automatically in 2027."""
    old = await create_league(
        db_session, id="old", roster_positions=ONE_QB_POSITIONS, scoring_settings={}
    )
    new = await create_league(
        db_session,
        id="new",
        roster_positions=SUPERFLEX_POSITIONS,
        scoring_settings={"bonus_rec_te": 0.5},
    )
    # Both seasons belong to the same league group.
    await create_season(db_session, old, year=2026, group_id="grp")
    await create_season(db_session, new, year=2027, group_id="grp")

    fmt = await get_league_value_format(db_session, "grp")

    assert fmt == LeagueValueFormat(scoring_format="superflex", te_premium=True)


@pytest.mark.asyncio
async def test_unknown_league_falls_back_to_base(db_session):
    """An unsynced league must not crash the pages that call this."""
    fmt = await get_league_value_format(db_session, "does-not-exist")

    assert fmt == LeagueValueFormat(scoring_format="1qb", te_premium=False)


# --- the column actually selects the stored number ---------------------------

@pytest.mark.asyncio
async def test_selected_column_returns_the_matching_stored_value(db_session):
    """End-to-end: the expression must read the right number out of the row."""
    db_session.add(
        PlayerValue(
            player_id="te1",
            ktc_name="Brock Bowers",
            position="TE",
            value=8280,
            superflex_value=8222,
            tep_value=9161,
            superflex_tep_value=9098,
        )
    )
    await db_session.flush()

    expected = {
        ("1qb", False): 8280,
        ("1qb", True): 9161,
        ("superflex", False): 8222,
        ("superflex", True): 9098,
    }
    for (scoring_format, te_premium), want in expected.items():
        fmt = LeagueValueFormat(scoring_format, te_premium)
        got = await db_session.execute(
            select(fmt.value_column).where(PlayerValue.player_id == "te1")
        )
        assert got.scalar() == want, f"{scoring_format} te_premium={te_premium}"


@pytest.mark.asyncio
async def test_missing_premium_value_falls_back_to_base(db_session):
    """KTC ranks only ~500 players; the rest have no tep row to read."""
    db_session.add(
        PlayerValue(player_id="deep", ktc_name="Deep Bench", value=400)
    )
    await db_session.flush()

    fmt = LeagueValueFormat("superflex", True)
    got = await db_session.execute(
        select(fmt.value_column).where(PlayerValue.player_id == "deep")
    )
    assert got.scalar() == 400


# --- draft picks -------------------------------------------------------------

def test_without_te_premium_keeps_the_format_and_drops_the_bonus():
    """Draft picks have no position yet, so a TE bonus cannot apply to them —
    but superflex still does."""
    fmt = LeagueValueFormat("superflex", te_premium=True).without_te_premium

    assert fmt == LeagueValueFormat("superflex", te_premium=False)
    assert "tep" not in str(fmt.value_column)
    assert "superflex_value" in str(fmt.value_column)


def test_without_te_premium_is_a_no_op_when_already_off():
    fmt = LeagueValueFormat("1qb", te_premium=False)
    assert fmt.without_te_premium == fmt
