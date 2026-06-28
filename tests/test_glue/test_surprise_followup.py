"""D3 — follow-the-surprise policy (the deterministic discipline guard).

The host (LLM) judges WHETHER a Wave-3 result contradicts the pre-registered
forecast or surfaces an anomaly; this pure policy enforces the discipline: a
chased surprise MUST carry a testability_path (no manufactured novelty), and a
genuine surprise must not be silently ignored. The orchestrator replan RUNTIME
is separate (mid-extraction, founder-gated); this is the verifiable core.
"""
from __future__ import annotations

from opl_cancer.glue.surprise_followup import decide_surprise_followup


def test_no_surprise_means_no_chase():
    d = decide_surprise_followup(contradicted=False, anomaly=False, testability_path=None)
    assert d["should_chase"] is False
    assert d["is_surprise"] is False


def test_contradicted_with_testability_chases():
    d = decide_surprise_followup(
        contradicted=True, anomaly=False, testability_path="DepMap co-essentiality re-query + PDO assay"
    )
    assert d["is_surprise"] is True
    assert d["should_chase"] is True


def test_anomaly_with_testability_chases():
    d = decide_surprise_followup(contradicted=False, anomaly=True, testability_path="single-cell re-cluster")
    assert d["should_chase"] is True


def test_surprise_without_testability_is_blocked_not_chased():
    d = decide_surprise_followup(contradicted=True, anomaly=False, testability_path="")
    assert d["is_surprise"] is True
    assert d["should_chase"] is False
    assert "testability" in d["blocked_reason"].lower()
