"""Test tournament stub — full impl deferred to P2 (lift from open-coscientist)."""
from opl_cancer.orchestrator.tournament import EloRater


def test_elo_rater_initializes_with_default_rating() -> None:
    r = EloRater()
    assert r.initial_rating == 1200
    assert r.k_factor == 32


def test_elo_update_winner_gains_loser_loses() -> None:
    r = EloRater()
    new_a, new_b, delta_a, delta_b = r.update(1200, 1200, outcome="a")
    assert new_a > 1200
    assert new_b < 1200
    assert delta_a > 0
    assert delta_b < 0
    assert delta_a == -delta_b


def test_elo_update_draw_no_change_for_equal_rating() -> None:
    r = EloRater()
    new_a, new_b, _, _ = r.update(1200, 1200, outcome="draw")
    assert new_a == 1200
    assert new_b == 1200
