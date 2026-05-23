"""BixbenchRunner tests — P3-T10."""
from __future__ import annotations

from pathlib import Path

import pytest

from opl_cancer.compute import BIXBENCH_IMAGE_TAG, BixbenchRunner
from opl_cancer.compute.runner import BixbenchRunnerError


def test_image_tag_constant() -> None:
    assert "bixbench" in BIXBENCH_IMAGE_TAG
    assert "v0.3.0" in BIXBENCH_IMAGE_TAG


def test_dry_run_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPL_BIXBENCH_LIVE", raising=False)
    nb = tmp_path / "analysis.ipynb"
    nb.write_text("{}", encoding="utf-8")
    runner = BixbenchRunner()
    result = runner.run_notebook(notebook_path=nb, workdir=tmp_path, timeout_s=120)
    assert result.mode == "dry-run"
    assert result.image == BIXBENCH_IMAGE_TAG
    assert "docker" in result.docker_cmd[0]
    assert "run" in result.docker_cmd
    assert "--rm" in result.docker_cmd
    assert any("/workspace" in p for p in result.docker_cmd)


def test_command_includes_notebook_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPL_BIXBENCH_LIVE", raising=False)
    nb = tmp_path / "deseq2_run.ipynb"
    nb.write_text("{}", encoding="utf-8")
    runner = BixbenchRunner()
    result = runner.run_notebook(notebook_path=nb, workdir=tmp_path)
    assert "/workspace/deseq2_run.ipynb" in result.docker_cmd
    assert "jupyter" in result.docker_cmd


def test_live_mode_missing_docker_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPL_BIXBENCH_LIVE", "1")
    nb = tmp_path / "x.ipynb"
    nb.write_text("{}", encoding="utf-8")
    # Use a binary name that definitely isn't on PATH
    runner = BixbenchRunner(docker_binary="docker_does_not_exist_xyz")
    with pytest.raises(BixbenchRunnerError):
        runner.run_notebook(notebook_path=nb, workdir=tmp_path)


def test_is_live_reflects_env(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = BixbenchRunner()
    monkeypatch.delenv("OPL_BIXBENCH_LIVE", raising=False)
    assert not runner.is_live()
    monkeypatch.setenv("OPL_BIXBENCH_LIVE", "1")
    assert runner.is_live()
    monkeypatch.setenv("OPL_BIXBENCH_LIVE", "0")
    assert not runner.is_live()


def test_result_to_dict_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPL_BIXBENCH_LIVE", raising=False)
    nb = tmp_path / "x.ipynb"
    nb.write_text("{}", encoding="utf-8")
    runner = BixbenchRunner()
    d = runner.run_notebook(notebook_path=nb, workdir=tmp_path, timeout_s=99).to_dict()
    assert d["mode"] == "dry-run"
    assert d["timeout_s"] == 99
    assert "docker_cmd" in d


def test_dockerfile_present() -> None:
    df = Path(__file__).resolve().parents[2] / "src/opl_cancer/compute/bixbench.Dockerfile"
    assert df.exists(), f"bixbench Dockerfile missing at {df}"
    content = df.read_text(encoding="utf-8")
    assert "FROM continuumio/miniconda3" in content
    assert "jupyter" in content.lower() or "ipykernel" in content
    assert "WORKDIR /workspace" in content
