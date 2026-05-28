"""Tests for figure_render integrator (v2.2 P1-#14).

matplotlib-backed renderer for the three Wave-3 figure types required by
P1-#14: KM curve, forest plot, Monte Carlo trajectory. Each render writes a
PNG to a caller-supplied path and returns {path, sha256, size_bytes}.
"""
from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import pytest

from opl_cancer.integrators.figure_render import (
    FigureRenderIntegrator,
    render_forest_plot,
    render_km_curve,
    render_monte_carlo_trajectory,
)


def test_render_km_curve_writes_png(tmp_path: Path) -> None:
    out_path = tmp_path / "km.png"
    res = render_km_curve(
        out_path=out_path,
        arms=[
            {"label": "control",  "durations": [3, 5, 7, 9, 11, 13],
             "events": [1, 1, 1, 1, 1, 1]},
            {"label": "treatment","durations": [10, 12, 14, 16, 18, 20],
             "events": [1, 1, 1, 1, 1, 1]},
        ],
        title="KM curve test",
    )
    assert out_path.exists()
    assert res["size_bytes"] > 100
    assert res["path"] == str(out_path)
    assert len(res["sha256"]) == 64


def test_render_forest_plot_writes_png(tmp_path: Path) -> None:
    out_path = tmp_path / "forest.png"
    res = render_forest_plot(
        out_path=out_path,
        rows=[
            {"label": "Overall",       "hr": 0.65, "ci_low": 0.45, "ci_high": 0.95},
            {"label": "KRAS G12C",     "hr": 0.42, "ci_low": 0.21, "ci_high": 0.85},
            {"label": "KRAS WT",       "hr": 0.80, "ci_low": 0.55, "ci_high": 1.15},
            {"label": "L1",            "hr": 0.62, "ci_low": 0.40, "ci_high": 0.94},
            {"label": "L3+",           "hr": 0.71, "ci_low": 0.43, "ci_high": 1.18},
        ],
        title="Forest test",
    )
    assert out_path.exists()
    assert res["size_bytes"] > 100


def test_render_monte_carlo_trajectory_writes_png(tmp_path: Path) -> None:
    out_path = tmp_path / "mc.png"
    res = render_monte_carlo_trajectory(
        out_path=out_path,
        timepoints=list(range(0, 13)),
        trajectories=[
            [100, 90, 80, 70, 60, 50, 45, 42, 40, 38, 36, 34, 33],
            [100, 95, 88, 80, 70, 62, 55, 50, 48, 45, 42, 40, 38],
            [100, 85, 70, 55, 45, 38, 32, 28, 25, 22, 20, 18, 17],
        ],
        title="Monte Carlo ctDNA trajectory",
    )
    assert out_path.exists()
    assert res["size_bytes"] > 100


def test_integrator_dispatches_kind(tmp_path: Path) -> None:
    integ = FigureRenderIntegrator()
    out_path = tmp_path / "km2.png"
    payload = {
        "kind": "km",
        "out_path": str(out_path),
        "arms": [
            {"label": "A", "durations": [3, 5, 7, 9, 11, 13],
             "events": [1, 1, 1, 1, 1, 1]},
            {"label": "B", "durations": [10, 12, 14, 16, 18, 20],
             "events": [1, 1, 1, 1, 1, 1]},
        ],
        "title": "via integrator",
    }
    out = asyncio.run(integ.render(payload))
    assert out_path.exists()
    assert out["sha256"]


def test_integrator_rejects_unknown_kind(tmp_path: Path) -> None:
    integ = FigureRenderIntegrator()
    with pytest.raises(ValueError):
        asyncio.run(integ.render({"kind": "garbage", "out_path": str(tmp_path / "x.png")}))


def test_sha256_matches_file_content(tmp_path: Path) -> None:
    out_path = tmp_path / "km3.png"
    res = render_km_curve(
        out_path=out_path,
        arms=[
            {"label": "A", "durations": [3, 5, 7], "events": [1, 1, 1]},
            {"label": "B", "durations": [9, 11, 13], "events": [1, 1, 1]},
        ],
        title="sha test",
    )
    body = out_path.read_bytes()
    assert hashlib.sha256(body).hexdigest() == res["sha256"]
