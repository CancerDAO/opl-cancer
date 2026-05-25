"""Tests for v1.5.2 ProgressReporter wiring into wave1/wave3 runners."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from opl_cancer.compute.native_runner import NativeAnalysisRunner
from opl_cancer.glue.progress_reporter import ProgressReporter
from opl_cancer.glue.wave3_runner import Wave3Runner


class _StubExpert:
    """Minimal expert stub for Wave3Runner integration test."""

    class _Profile:
        name = "aviv"

    profile = _Profile()

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        return {"stub": True, "task": kwargs.get("task_package")}

    async def review(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"verdict": "ok"}


@pytest.mark.asyncio
async def test_wave3_runner_emits_stage_3_start_and_end(tmp_path: Path) -> None:
    captured: list[str] = []
    reporter = ProgressReporter(
        on_emit=captured.append,
        heartbeat_interval_s=0,  # allow every heartbeat through
    )
    runner = Wave3Runner(
        out_dir=tmp_path,
        aviv=_StubExpert(),
        bixbench=NativeAnalysisRunner(),
        reporter=reporter,
    )
    result = await runner.run(
        patient_text="test",
        patient_context={"profile_json": "{}"},
        wave2_outputs={
            "hypotheses": [
                {"id": "H01", "text": "test hypothesis"},
            ],
            "top_k": [("H01", 1500)],
        },
    )
    assert result["run_id"].startswith("wave3_")
    # At minimum: start + end of stage 3
    starts = [m for m in captured if "[3/5" in m and "查数据" in m and "✓" not in m]
    ends = [m for m in captured if "[3/5" in m and "✓" in m]
    assert starts, f"no stage-3 start in {captured!r}"
    assert ends, f"no stage-3 end in {captured!r}"


@pytest.mark.asyncio
async def test_wave3_runner_back_compat_without_reporter(tmp_path: Path) -> None:
    """Default reporter=None should preserve v1.5 behavior — no crash."""
    runner = Wave3Runner(
        out_dir=tmp_path,
        aviv=_StubExpert(),
        bixbench=NativeAnalysisRunner(),
    )
    result = await runner.run(
        patient_text="test",
        patient_context={"profile_json": "{}"},
        wave2_outputs={"hypotheses": [], "top_k": []},
    )
    assert result["run_id"].startswith("wave3_")


@pytest.mark.asyncio
async def test_wave3_runner_stage_3_summary_mentions_next_stage(
    tmp_path: Path,
) -> None:
    captured: list[str] = []
    reporter = ProgressReporter(
        on_emit=captured.append, heartbeat_interval_s=0
    )
    runner = Wave3Runner(
        out_dir=tmp_path,
        aviv=_StubExpert(),
        bixbench=NativeAnalysisRunner(),
        reporter=reporter,
    )
    await runner.run(
        patient_text="t",
        patient_context={"profile_json": "{}"},
        wave2_outputs={
            "hypotheses": [{"id": "H01", "text": "x"}],
            "top_k": [("H01", 1500)],
        },
    )
    end_msg = next(m for m in captured if "[3/5" in m and "✓" in m)
    assert "审核" in end_msg
    assert "下一步" in end_msg


@pytest.mark.asyncio
async def test_wave3_runner_no_jargon_leak_in_default_emissions(
    tmp_path: Path,
) -> None:
    captured: list[str] = []
    reporter = ProgressReporter(
        on_emit=captured.append, heartbeat_interval_s=0
    )
    runner = Wave3Runner(
        out_dir=tmp_path,
        aviv=_StubExpert(),
        bixbench=NativeAnalysisRunner(),
        reporter=reporter,
    )
    await runner.run(
        patient_text="t",
        patient_context={"profile_json": "{}"},
        wave2_outputs={
            "hypotheses": [{"id": "H01", "text": "x"}],
            "top_k": [("H01", 1500)],
        },
    )
    # None of the emitted user-facing messages should trip the
    # jargon-scrub trip wire ([jargon-leak:...]).
    for msg in captured:
        assert "[jargon-leak" not in msg, f"jargon leaked in: {msg!r}"


def test_wave1_runner_signature_accepts_reporter() -> None:
    """Wave1Runner exposes reporter as keyword-only kwarg with None default."""
    import inspect

    from opl_cancer.glue.wave1_runner import Wave1Runner

    sig = inspect.signature(Wave1Runner.__init__)
    assert "reporter" in sig.parameters
    p = sig.parameters["reporter"]
    assert p.default is None
    assert p.kind is inspect.Parameter.KEYWORD_ONLY


def test_wave3_runner_signature_accepts_reporter() -> None:
    import inspect

    sig = inspect.signature(Wave3Runner.__init__)
    assert "reporter" in sig.parameters
    p = sig.parameters["reporter"]
    assert p.default is None
    assert p.kind is inspect.Parameter.KEYWORD_ONLY
