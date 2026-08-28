"""Tests for KTC value service player matching."""
from app.services.ktc_service import (
    _build_player_lookup,
    _value_fields,
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


# --- TE-premium value extraction ---------------------------------------------

def _entry(**tiers):
    """A KTC playersArray entry; each tier is {"value": v, "rank": r}."""
    def block(base, tep):
        out = {"value": base[0], "rank": base[1]}
        if tep is not None:
            out["tep"] = {"value": tep[0], "rank": tep[1]}
        return out
    return {
        "oneQBValues": block(tiers["one_qb"], tiers.get("one_qb_tep")),
        "superflexValues": block(tiers["superflex"], tiers.get("superflex_tep")),
    }


def test_value_fields_reads_all_four_tiers():
    """KTC ships tep alongside the base values in the same payload."""
    fields = _value_fields(_entry(
        one_qb=(8280, 6), one_qb_tep=(9161, 5),
        superflex=(8222, 9), superflex_tep=(9098, 7),
    ))

    assert fields["value"] == 8280
    assert fields["rank"] == 6
    assert fields["tep_value"] == 9161
    assert fields["tep_rank"] == 5
    assert fields["superflex_value"] == 8222
    assert fields["superflex_rank"] == 9
    assert fields["superflex_tep_value"] == 9098
    assert fields["superflex_tep_rank"] == 7


def test_value_fields_leaves_premium_null_when_ktc_omits_it():
    """Unranked players carry no tep block; null lets reads fall back to base
    instead of pricing the player at zero."""
    fields = _value_fields(_entry(one_qb=(400, None), superflex=(0, None)))

    assert fields["value"] == 400
    assert fields["tep_value"] is None
    assert fields["superflex_tep_value"] is None


def test_value_fields_treats_zero_premium_as_missing():
    """A 0 from KTC is absence of data, not a real valuation."""
    fields = _value_fields(_entry(
        one_qb=(400, None), one_qb_tep=(0, None), superflex=(0, None),
    ))

    assert fields["tep_value"] is None


def test_non_tight_ends_get_identical_premium_values():
    """Only TEs move between tiers, so a WR's premium value equals its base —
    the column swap must be a no-op for every other position."""
    fields = _value_fields(_entry(
        one_qb=(7542, 10), one_qb_tep=(7542, 12),
        superflex=(7100, 20), superflex_tep=(7100, 24),
    ))

    assert fields["tep_value"] == fields["value"]
    assert fields["superflex_tep_value"] == fields["superflex_value"]
