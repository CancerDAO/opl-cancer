"""Test G18 meta-analysis search-strategy gate."""
from pathlib import Path

from opl_cancer.validators.gates.g18_meta_search_strategy import (
    G18MetaSearchStrategyGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


def _touch_artifacts(tmp_path: Path) -> dict[str, str]:
    paths = {}
    for name in ("forest.png", "funnel.png", "prisma.png"):
        p = tmp_path / name
        p.write_bytes(b"\x89PNG")
        paths[name] = str(p)
    return paths


def test_g18_skip_no_meta() -> None:
    gate = G18MetaSearchStrategyGate()
    r = gate.check({})
    assert r.status == GateStatus.SKIP


def test_g18_pass_complete(tmp_path: Path) -> None:
    arts = _touch_artifacts(tmp_path)
    gate = G18MetaSearchStrategyGate()
    claim = {
        "meta_analysis": {
            "search_strategy": {
                "databases": ["PubMed", "Cochrane"],
                "query": "atezolizumab AND HCC",
                "inclusion": "phase 3 RCTs",
                "exclusion": "case reports",
            },
            "forest_plot_path": arts["forest.png"],
            "funnel_plot_path": arts["funnel.png"],
            "prisma_flow_diagram_path": arts["prisma.png"],
        }
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g18_fail_missing_strategy_fields(tmp_path: Path) -> None:
    arts = _touch_artifacts(tmp_path)
    gate = G18MetaSearchStrategyGate()
    claim = {
        "meta_analysis": {
            "search_strategy": {"databases": ["PubMed"], "query": "x"},
            "forest_plot_path": arts["forest.png"],
            "funnel_plot_path": arts["funnel.png"],
            "prisma_flow_diagram_path": arts["prisma.png"],
        }
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


def test_g18_fail_missing_files() -> None:
    gate = G18MetaSearchStrategyGate()
    claim = {
        "meta_analysis": {
            "search_strategy": {
                "databases": ["PubMed"],
                "query": "x",
                "inclusion": "y",
                "exclusion": "z",
            },
            "forest_plot_path": "/nonexistent/forest.png",
            "funnel_plot_path": "/nonexistent/funnel.png",
            "prisma_flow_diagram_path": "/nonexistent/prisma.png",
        }
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
