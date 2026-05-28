"""G31 — figure_reproducible unit tests."""
from __future__ import annotations

from pathlib import Path

from opl_cancer.validators.gates import G31FigureReproducibleGate
from opl_cancer.validators.mechanical_gates import GateStatus


GATE = G31FigureReproducibleGate()


def _make_pair(d: Path, ident: str, py_body: str = "# deterministic\n") -> None:
    (d / f"fig_{ident}.png").write_bytes(b"\x89PNG\r\n")
    (d / f"fig_{ident}.py").write_text(py_body, encoding="utf-8")


def test_g31_pass_matched_pair(tmp_path: Path) -> None:
    fdir = tmp_path / "figures"
    fdir.mkdir()
    _make_pair(fdir, "1")
    _make_pair(fdir, "2")
    res = GATE.check({"figures_dir": str(fdir), "run_stage": "wave6"})
    assert res.status == GateStatus.PASS, res.message
    assert set(res.evidence["figures"]) == {"1", "2"}


def test_g31_fail_orphan_png(tmp_path: Path) -> None:
    fdir = tmp_path / "figures"
    fdir.mkdir()
    (fdir / "fig_1.png").write_bytes(b"png")
    res = GATE.check({"figures_dir": str(fdir), "run_stage": "wave6"})
    assert res.status == GateStatus.FAIL
    assert res.block
    assert "1" in res.evidence["orphan_png"]


def test_g31_fail_orphan_py(tmp_path: Path) -> None:
    fdir = tmp_path / "figures"
    fdir.mkdir()
    (fdir / "fig_2.py").write_text("# orphan\n", encoding="utf-8")
    res = GATE.check({"figures_dir": str(fdir), "run_stage": "wave6"})
    assert res.status == GateStatus.FAIL
    assert res.block
    assert "2" in res.evidence["orphan_py"]


def test_g31_warns_on_stochastic_unseeded(tmp_path: Path) -> None:
    fdir = tmp_path / "figures"
    fdir.mkdir()
    _make_pair(fdir, "1", py_body="import numpy as np\nnp.random.seed = None\nx = np.random.rand(10)\n")
    res = GATE.check({"figures_dir": str(fdir), "run_stage": "wave6"})
    # Stochasticity warning, not a fail.
    assert res.status == GateStatus.PASS
    assert "1" in res.evidence["stochastic_unseeded"]


def test_g31_seed_extracted(tmp_path: Path) -> None:
    fdir = tmp_path / "figures"
    fdir.mkdir()
    _make_pair(fdir, "1", py_body="random_seed = 42\nimport numpy as np\nnp.random.seed(random_seed)\n")
    res = GATE.check({"figures_dir": str(fdir), "run_stage": "wave6"})
    assert res.status == GateStatus.PASS
    assert res.evidence["seeds"]["1"] == 42


def test_g31_skip_no_figures_dir() -> None:
    res = GATE.check({"run_stage": "wave6"})
    assert res.status == GateStatus.SKIP


def test_g31_skip_empty_figures_dir(tmp_path: Path) -> None:
    fdir = tmp_path / "figures"
    fdir.mkdir()
    res = GATE.check({"figures_dir": str(fdir), "run_stage": "wave6"})
    assert res.status == GateStatus.SKIP


def test_g31_skip_non_wave6_stage(tmp_path: Path) -> None:
    fdir = tmp_path / "figures"
    fdir.mkdir()
    res = GATE.check({"figures_dir": str(fdir), "run_stage": "wave3"})
    assert res.status == GateStatus.SKIP


def test_g31_resolves_from_bundle_root(tmp_path: Path) -> None:
    fdir = tmp_path / "figures"
    fdir.mkdir()
    _make_pair(fdir, "1")
    res = GATE.check({"bundle_root": str(tmp_path), "run_stage": "wave6"})
    assert res.status == GateStatus.PASS
