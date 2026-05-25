"""NativeAnalysisRunner tests — v1.5 P0-1.

Covers the Docker-free compute path. Mirrors test_runner.py shape so the two
runners stay behaviorally consistent.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from opl_cancer.compute import (
    NATIVE_IMAGE_TAG,
    BixbenchRunner,
    NativeAnalysisRunner,
    NativeAnalysisRunnerError,
    select_compute_runner,
)


def test_image_tag_constant() -> None:
    assert "native" in NATIVE_IMAGE_TAG
    assert "v1.5" in NATIVE_IMAGE_TAG


def test_dry_run_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPL_NATIVE_LIVE", raising=False)
    nb = tmp_path / "analysis.ipynb"
    nb.write_text("{}", encoding="utf-8")
    runner = NativeAnalysisRunner()
    result = runner.run_notebook(notebook_path=nb, workdir=tmp_path, timeout_s=120)
    assert result.mode == "native-dry-run"
    assert result.image == NATIVE_IMAGE_TAG
    assert "jupyter" in result.docker_cmd[0]  # field reused for cross-runner compat
    assert "nbconvert" in result.docker_cmd
    assert "--execute" in result.docker_cmd
    assert result.extra.get("runner") == "native"


def test_command_includes_notebook_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPL_NATIVE_LIVE", raising=False)
    nb = tmp_path / "ctdna_montecarlo.ipynb"
    nb.write_text("{}", encoding="utf-8")
    runner = NativeAnalysisRunner()
    result = runner.run_notebook(notebook_path=nb, workdir=tmp_path)
    assert str(nb) in result.docker_cmd


def test_live_raises_when_jupyter_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPL_NATIVE_LIVE", "1")
    runner = NativeAnalysisRunner(jupyter_binary="jupyter_does_not_exist_xyz")
    nb = tmp_path / "x.ipynb"
    nb.write_text("{}", encoding="utf-8")
    with pytest.raises(NativeAnalysisRunnerError, match="not on PATH"):
        runner.run_notebook(notebook_path=nb, workdir=tmp_path)


def test_live_raises_when_notebook_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPL_NATIVE_LIVE", "1")
    runner = NativeAnalysisRunner()
    if not runner.is_available():
        pytest.skip("jupyter not on PATH; cannot exercise live path")
    nb = tmp_path / "does_not_exist.ipynb"
    with pytest.raises(NativeAnalysisRunnerError, match="notebook not found"):
        runner.run_notebook(notebook_path=nb, workdir=tmp_path)


def test_is_available_reports_jupyter_presence() -> None:
    runner = NativeAnalysisRunner()
    expected = shutil.which("jupyter") is not None
    assert runner.is_available() is expected


def test_select_compute_runner_prefers_native_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeNative:
        def is_available(self) -> bool:
            return True

    class FakeBix:
        docker_binary = "docker"

    runner = select_compute_runner(prefer="auto", bixbench=FakeBix(), native=FakeNative())
    assert isinstance(runner, FakeNative)


def test_select_compute_runner_falls_back_to_bixbench(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeNative:
        def is_available(self) -> bool:
            return False

    class FakeBix:
        docker_binary = "/bin/sh"  # always exists on macOS / linux

    runner = select_compute_runner(prefer="auto", bixbench=FakeBix(), native=FakeNative())
    assert isinstance(runner, FakeBix)


def test_select_compute_runner_raises_when_both_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeNative:
        def is_available(self) -> bool:
            return False

    class FakeBix:
        docker_binary = "definitely_not_a_real_binary_xyz123"

    with pytest.raises(RuntimeError, match="Wave 3 cannot proceed"):
        select_compute_runner(
            prefer="auto", bixbench=FakeBix(), native=FakeNative()
        )


def test_select_compute_runner_explicit_native_raises_when_unavailable() -> None:
    class FakeNative:
        def is_available(self) -> bool:
            return False

    class FakeBix:
        docker_binary = "/bin/sh"

    with pytest.raises(RuntimeError, match="jupyter not on PATH"):
        select_compute_runner(prefer="native", bixbench=FakeBix(), native=FakeNative())


def test_wave3_runner_accepts_native(tmp_path: Path) -> None:
    """Wave3Runner.bixbench param accepts NativeAnalysisRunner (v1.5 widening)."""
    from opl_cancer.glue.wave3_runner import Wave3Runner

    class StubExpert:
        async def execute(self, **kwargs):  # noqa: ANN003
            return {}

    runner = Wave3Runner(
        out_dir=tmp_path,
        aviv=StubExpert(),
        bixbench=NativeAnalysisRunner(),  # type: ignore[arg-type]
    )
    assert isinstance(runner.bixbench, NativeAnalysisRunner)


def test_kernel_requirements_file_present() -> None:
    """Sanity check the file the Dockerfile expects exists (AP-14 fix)."""
    repo_root = Path(__file__).resolve().parents[2]
    req_file = repo_root / "src" / "opl_cancer" / "compute" / "kernel_requirements.txt"
    assert req_file.exists(), f"kernel_requirements.txt missing at {req_file}"
    content = req_file.read_text(encoding="utf-8")
    assert "pandas" in content
    assert "scipy" in content
    assert "scanpy" in content


def test_dockerfile_copies_kernel_requirements_only_once() -> None:
    """The Dockerfile must reference kernel_requirements.txt (build sanity)."""
    repo_root = Path(__file__).resolve().parents[2]
    dockerfile = repo_root / "src" / "opl_cancer" / "compute" / "bixbench.Dockerfile"
    content = dockerfile.read_text(encoding="utf-8")
    assert "COPY kernel_requirements.txt" in content
