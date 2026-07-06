"""Tests for KTC value service player matching."""
from app.services.ktc_service import (
    _build_player_lookup,
    _match_player_id,
    _normalize_name,
    _parse_pick_key,
)


def test_normalize_name_strips_suffixes_and_accents():
    assert _normalize_name("Kenneth Walker III") == "kenneth walker"
    assert _normalize_name("Amon-Ra St. Brown") == "amonra st brown"
    assert _normalize_name("Marvin Harrison Jr.") == "marvin harrison"


def test_parse_pick_key():
    assert _parse_pick_key("2026 Early 1st") == "2026_1_early"
    assert _parse_pick_key("2027 Mid 2nd") == "2027_2_mid"
    assert _parse_pick_key("not a pick") is None


def test_same_name_players_match_by_position():
    """Two players with the same name must resolve by position, not overwrite."""
    rows = [
        ("qb_id", "Josh Allen", "QB"),
        ("lb_id", "Josh Allen", "LB"),
        ("wr_id", "Puka Nacua", "WR"),
    ]
    by_name_pos, by_name = _build_player_lookup(rows)

    assert _match_player_id(by_name_pos, by_name, "Josh Allen", "QB") == "qb_id"
    assert _match_player_id(by_name_pos, by_name, "Josh Allen", "LB") == "lb_id"


def test_ambiguous_name_without_position_match_is_skipped():
    """If the position doesn't match and the name is ambiguous, return None."""
    rows = [
        ("qb_id", "Josh Allen", "QB"),
        ("lb_id", "Josh Allen", "LB"),
    ]
    by_name_pos, by_name = _build_player_lookup(rows)

    assert _match_player_id(by_name_pos, by_name, "Josh Allen", "RB") is None


def test_unambiguous_name_falls_back_without_position():
    """A unique name still matches when the position string differs."""
    rows = [("wr_id", "Puka Nacua", "WR")]
    by_name_pos, by_name = _build_player_lookup(rows)

    assert _match_player_id(by_name_pos, by_name, "Puka Nacua", "FLEX") == "wr_id"
