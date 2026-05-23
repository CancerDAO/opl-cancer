"""P2-T15: ExperimentalInsightsFeedback (Robin EXPERIMENTAL_INSIGHTS appendage)."""
from __future__ import annotations

from opl_cancer.memory.schemas import Hypothesis
from opl_cancer.orchestrator.experimental_insights import (
    ExperimentalInsightsFeedback,
    experimental_insights_appendage,
)


def test_append_empty() -> None:
    assert ExperimentalInsightsFeedback.append([], []) == ""


def test_append_includes_top_hypotheses() -> None:
    hyps = [
        Hypothesis(id="h1", text="alpha", elo_rating=1300.0),
        Hypothesis(id="h2", text="beta", elo_rating=1100.0),
    ]
    out = ExperimentalInsightsFeedback.append([], hyps)
    assert "Top hypotheses by Elo" in out
    assert "alpha" in out
    assert "beta" in out


def test_append_includes_pair_outcomes() -> None:
    hyps = [
        Hypothesis(id="h1", text="alpha", elo_rating=1300.0),
        Hypothesis(id="h2", text="beta", elo_rating=1200.0),
    ]
    outcomes = [{"a": "h1", "b": "h2", "winner": "A", "reason": "stronger mechanism"}]
    out = ExperimentalInsightsFeedback.append(outcomes, hyps)
    assert "stronger mechanism" in out
    assert "winner=A" in out


def test_module_shortcut() -> None:
    hyps = [Hypothesis(id="h1", text="x", elo_rating=1200.0)]
    out = experimental_insights_appendage([], hyps)
    assert "x" in out
