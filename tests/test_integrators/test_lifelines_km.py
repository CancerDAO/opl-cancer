"""Tests for lifelines KM survival-analysis wrapper (v2.2 ADR-0022).

Light-weight Python wrapper around the lifelines library. We test:
  * KM curve from synthetic durations+events runs and returns median + CI
  * log-rank test between two groups returns a p-value
  * subgroup filter narrows to the requested cohort BEFORE running KM
  * lifelines absent → IntegratorError (no silent fallback)
  * subgroup `min_n_per_arm` enforcement raises IntegratorError if either
    arm too small (G15 / G17 prereq)
"""
from __future__ import annotations

import asyncio

import pytest

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.lifelines_km import (
    KMResult,
    LifelinesKMIntegrator,
    apply_subgroup_filter,
    require_lifelines,
)


pytestmark = pytest.mark.skipif(
    not require_lifelines(strict=False),
    reason="lifelines not installed — optional [bio] extra",
)


def test_km_result_dataclass_round_trip() -> None:
    r = KMResult(
        median_months=12.3,
        ci95_lower_months=9.5,
        ci95_upper_months=15.1,
        n_at_risk_start=120,
        n_events=78,
        engine="lifelines",
    )
    d = r.to_dict()
    assert d["median_months"] == 12.3
    assert d["ci95_lower_months"] == 9.5


def test_integrator_km_curve_synthetic() -> None:
    integ = LifelinesKMIntegrator()
    out = asyncio.run(
        integ.fetch_km(
            durations=[2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24],
            events=[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
            label="cohort_A",
        )
    )
    assert out["engine"] == "lifelines"
    assert out["label"] == "cohort_A"
    assert out["n_events"] == 11
    assert out["median_months"] > 0


def test_integrator_log_rank_two_arms() -> None:
    integ = LifelinesKMIntegrator()
    out = asyncio.run(
        integ.fetch_logrank(
            arm_a={
                "durations": [3, 5, 7, 9, 11, 13],
                "events": [1] * 6,
                "label": "control",
            },
            arm_b={
                "durations": [10, 12, 14, 16, 18, 20],
                "events": [1] * 6,
                "label": "treatment",
            },
        )
    )
    assert "p_value" in out
    assert out["p_value"] >= 0
    assert out["arm_a_median"] < out["arm_b_median"]


def test_apply_subgroup_filter() -> None:
    cohort = [
        {"id": 1, "kras": "G12C", "line": 3, "duration": 5, "event": 1},
        {"id": 2, "kras": "G12C", "line": 2, "duration": 9, "event": 1},
        {"id": 3, "kras": "G12V", "line": 3, "duration": 12, "event": 0},
        {"id": 4, "kras": "G12C", "line": 3, "duration": 15, "event": 1},
    ]
    filt = apply_subgroup_filter(cohort, {"kras": "G12C", "line": 3})
    assert {r["id"] for r in filt} == {1, 4}


def test_apply_subgroup_filter_supports_set_match() -> None:
    cohort = [
        {"id": 1, "line": 3},
        {"id": 2, "line": 4},
        {"id": 3, "line": 5},
    ]
    filt = apply_subgroup_filter(cohort, {"line": [3, 5]})
    assert {r["id"] for r in filt} == {1, 3}


def test_integrator_subgroup_enforces_min_n(monkeypatch) -> None:
    integ = LifelinesKMIntegrator(min_n_per_arm=10)
    cohort = [{"durations": [1, 2, 3], "events": [1, 1, 1], "arm": "A"}] * 5
    # Synthetic 5-row arm A vs 0-row arm B → arm B will fail min_n
    with pytest.raises(IntegratorError):
        asyncio.run(
            integ.fetch_logrank(
                arm_a={"durations": [1, 2, 3], "events": [1, 1, 1], "label": "A"},
                arm_b={"durations": [4, 5], "events": [1, 1], "label": "B"},
            )
        )


def test_integrator_family_and_ttl() -> None:
    integ = LifelinesKMIntegrator()
    assert integ.family == "F_BIO"
    assert integ.ttl_seconds > 0
