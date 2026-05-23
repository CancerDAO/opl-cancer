"""P2-T5: EloTournament — pair rotation, batch update, top-k, convergence."""
from __future__ import annotations

import pytest

from opl_cancer.orchestrator.tournament import EloRater, EloTournament


def test_pair_rotation_n2() -> None:
    t = EloTournament()
    assert t.pair_rotation(["a", "b"]) == [("a", "b")]


def test_pair_rotation_n3_gives_3_pairs() -> None:
    t = EloTournament()
    pairs = t.pair_rotation(["a", "b", "c"])
    assert len(pairs) == 3
    assert set(pairs) == {("a", "b"), ("a", "c"), ("b", "c")}


def test_pair_rotation_n4_gives_6_pairs() -> None:
    t = EloTournament()
    assert len(t.pair_rotation(["a", "b", "c", "d"])) == 6


def test_apply_round_updates_ratings() -> None:
    t = EloTournament(k_factor=32.0)
    ratings = {"a": 1200.0, "b": 1200.0, "c": 1200.0}
    outcomes = [
        {"a": "a", "b": "b", "winner": "A"},
        {"a": "b", "b": "c", "winner": "B"},
    ]
    new_ratings, deltas = t.apply_round(ratings, outcomes)
    assert new_ratings["a"] > 1200.0  # a won
    assert new_ratings["c"] > 1200.0  # c won
    assert new_ratings["b"] < 1200.0  # b lost twice
    assert deltas["b"] < 0.0


def test_top_k_sorted_desc() -> None:
    t = EloTournament()
    ratings = {"a": 1180.0, "b": 1250.0, "c": 1200.0}
    top = t.top_k(ratings, k=2)
    assert top[0][0] == "b"
    assert top[1][0] == "c"
    assert len(top) == 2


def test_convergence_check_false_when_top1_changes() -> None:
    t = EloTournament()
    history = [
        {"a": 1200.0, "b": 1180.0},
        {"a": 1300.0, "b": 1100.0},  # a leads
        {"a": 1100.0, "b": 1300.0},  # b leads → not converged
    ]
    assert t.convergence_check(history) is False


def test_convergence_check_true_when_stable() -> None:
    t = EloTournament()
    history = [
        {"a": 1300.0, "b": 1100.0},
        {"a": 1302.0, "b": 1098.0},
        {"a": 1303.0, "b": 1097.0},
    ]
    assert t.convergence_check(history, window=2, threshold=5.0) is True


def test_elo_rater_alias_works() -> None:
    """P0 callers used EloRater — must still work."""
    assert EloRater is EloTournament
    r = EloRater()
    new_a, new_b, da, db = r.update(1200.0, 1200.0, "a")
    assert da > 0.0
    assert db < 0.0


def test_update_accepts_upper_and_lower() -> None:
    t = EloTournament()
    upper = t.update(1200.0, 1200.0, "A")
    lower = t.update(1200.0, 1200.0, "a")
    assert upper == lower
