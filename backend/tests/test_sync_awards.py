"""Tests for season awards sync logic."""
from app.services.sync_service import SyncService


def test_get_bracket_winner_with_p1_match():
    """Champion is the winner of the p=1 match in the highest round."""
    bracket = [
        {"r": 1, "m": 1, "t1": 1, "t2": 8, "w": 1, "l": 8},
        {"r": 1, "m": 2, "t1": 4, "t2": 5, "w": 5, "l": 4},
        {"r": 2, "m": 3, "t1": 1, "t2": 5, "w": 5, "l": 1},
        {"p": 1, "r": 3, "m": 4, "t1": 5, "t2": 3, "w": 5, "l": 3},
        {"p": 3, "r": 3, "m": 5, "t1": 1, "t2": 7, "w": 1, "l": 7},
    ]
    assert SyncService._get_bracket_winner(bracket) == 5


def test_get_bracket_winner_single_final_match():
    """If no p field, fallback to the only match in the final round."""
    bracket = [
        {"r": 1, "m": 1, "t1": 1, "t2": 2, "w": 1, "l": 2},
        {"r": 2, "m": 2, "t1": 1, "t2": 3, "w": 3, "l": 1},
    ]
    assert SyncService._get_bracket_winner(bracket) == 3


def test_get_bracket_winner_no_winner_yet():
    """Return None if the final match has no winner yet."""
    bracket = [
        {"r": 1, "m": 1, "t1": 1, "t2": 2, "w": 1, "l": 2},
        {"p": 1, "r": 2, "m": 2, "t1": None, "t2": None, "w": None, "l": None},
    ]
    assert SyncService._get_bracket_winner(bracket) is None


def test_get_bracket_winner_empty_bracket():
    """Return None for empty bracket."""
    assert SyncService._get_bracket_winner([]) is None
    assert SyncService._get_bracket_winner(None) is None
