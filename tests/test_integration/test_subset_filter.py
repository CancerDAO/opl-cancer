"""Integration test: P1-#12 + P1-#13 — KM on filtered cohort.

The v2.1 failure mode: cBioPortal L3+ cohort KM ran against the FULL
denominator (which masked the subgroup effect). v2.2 narrows via
apply_subgroup_filter(...) BEFORE the lifelines KM fit.

This test simulates a 20-row cohort (10 L1 patients with good survival,
10 L3+ patients with poor survival) and verifies:
  * the unfiltered cohort median is materially different from the
    filtered cohort median
  * the filtered cohort hits the n_at_risk_start threshold
  * a KRAS G12C subset within the L3+ filter further narrows
"""
from __future__ import annotations

import asyncio

import pytest

from opl_cancer.integrators.lifelines_km import (
    LifelinesKMIntegrator,
    apply_subgroup_filter,
    require_lifelines,
)


pytestmark = pytest.mark.skipif(
    not require_lifelines(strict=False),
    reason="lifelines not installed",
)


_COHORT_20 = [
    # 10 L1 patients — long survival
    {"line": 1, "kras": "G12V", "durations": 36, "events": 0},
    {"line": 1, "kras": "G12V", "durations": 40, "events": 0},
    {"line": 1, "kras": "G12C", "durations": 30, "events": 1},
    {"line": 1, "kras": "WT",   "durations": 42, "events": 0},
    {"line": 1, "kras": "WT",   "durations": 38, "events": 1},
    {"line": 1, "kras": "G12C", "durations": 32, "events": 1},
    {"line": 1, "kras": "G12V", "durations": 45, "events": 0},
    {"line": 1, "kras": "G12C", "durations": 35, "events": 1},
    {"line": 1, "kras": "WT",   "durations": 50, "events": 0},
    {"line": 1, "kras": "G12C", "durations": 28, "events": 1},
    # 10 L3+ patients — short survival
    {"line": 3, "kras": "G12C", "durations": 5, "events": 1},
    {"line": 3, "kras": "G12C", "durations": 7, "events": 1},
    {"line": 4, "kras": "G12V", "durations": 4, "events": 1},
    {"line": 4, "kras": "G12C", "durations": 6, "events": 1},
    {"line": 3, "kras": "WT",   "durations": 10, "events": 1},
    {"line": 5, "kras": "G12C", "durations": 3, "events": 1},
    {"line": 3, "kras": "G12V", "durations": 8, "events": 1},
    {"line": 4, "kras": "WT",   "durations": 9, "events": 1},
    {"line": 5, "kras": "G12C", "durations": 4, "events": 1},
    {"line": 3, "kras": "G12C", "durations": 6, "events": 1},
]


def _km_for(integ, rows, label):
    durations = [r["durations"] for r in rows]
    events = [r["events"] for r in rows]
    return asyncio.run(integ.fetch_km(durations=durations, events=events, label=label))


def test_unfiltered_vs_l3plus_cohort_diverges() -> None:
    integ = LifelinesKMIntegrator(min_n_per_arm=5)
    unfiltered = _km_for(integ, _COHORT_20, "unfiltered")
    l3plus = apply_subgroup_filter(_COHORT_20, {"line": [3, 4, 5]})
    assert len(l3plus) == 10
    l3plus_km = _km_for(integ, l3plus, "L3+")
    # L3+ median should be materially shorter than the unfiltered median
    assert l3plus_km["median_months"] < unfiltered["median_months"]
    # And specifically <= 10 months (since all L3+ events are at 3-10)
    assert l3plus_km["median_months"] <= 10


def test_l3plus_kras_g12c_subset_filter() -> None:
    """Two-step filter: L3+ AND KRAS G12C — P1-#13 TROP2 KRAS G12C scenario."""
    g12c_l3 = apply_subgroup_filter(_COHORT_20, {"line": [3, 4, 5], "kras": "G12C"})
    assert len(g12c_l3) == 6
    integ = LifelinesKMIntegrator(min_n_per_arm=5)
    km = _km_for(integ, g12c_l3, "L3+_KRAS_G12C")
    assert km["n_at_risk_start"] == 6
    assert km["n_events"] == 6
    # All event-durations 3-7 so median ≈ 5
    assert 3 <= km["median_months"] <= 7


def test_filter_preserves_unfiltered_n() -> None:
    """After filtering, the integrator's `n_at_risk_start` must reflect the
    FILTERED cohort, but downstream task output also needs the unfiltered N
    for transparency (per biostats_survival task package spec)."""
    l3plus = apply_subgroup_filter(_COHORT_20, {"line": [3, 4, 5]})
    integ = LifelinesKMIntegrator(min_n_per_arm=5)
    km = _km_for(integ, l3plus, "L3+")
    assert km["n_at_risk_start"] == 10  # filtered
    assert len(_COHORT_20) == 20  # original preserved
