"""Tests for v1.5.1 ProgressReporter."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from opl_cancer.glue.progress_reporter import (
    STAGE_LABELS,
    ProgressEvent,
    ProgressReporter,
)


def test_stage_labels_cover_5_stages() -> None:
    assert set(STAGE_LABELS.keys()) == {1, 2, 3, 4, 5}
    for stage in (1, 2, 3, 4, 5):
        assert "zh" in STAGE_LABELS[stage]
        assert "en" in STAGE_LABELS[stage]


def test_no_internal_wave_names_in_labels() -> None:
    """Stage labels must never use 'Wave 1' etc. — pure plain language."""
    for stage in (1, 2, 3, 4, 5):
        for lang_label in STAGE_LABELS[stage].values():
            assert "wave" not in lang_label.lower()


def test_start_stage_emits_bilingual_label() -> None:
    r = ProgressReporter()
    e = r.start_stage(1)
    assert "准备" in e.user_message
    assert "Getting ready" in e.user_message
    assert e.phase == "start"
    assert e.eta_min == (5, 8)


def test_start_stage_eta_range_visible() -> None:
    """ETA must be a range, never a single number."""
    r = ProgressReporter()
    e = r.start_stage(3)
    # default zh template includes "{lo}-{hi} 分钟"
    assert "-" in e.user_message
    assert "分钟" in e.user_message


def test_heartbeat_respects_interval_default() -> None:
    r = ProgressReporter(heartbeat_interval_s=60)
    r.start_stage(1)
    # immediate heartbeat suppressed
    out = r.heartbeat(1, "in flight")
    assert out is None


def test_heartbeat_force_overrides_interval() -> None:
    r = ProgressReporter(heartbeat_interval_s=60)
    r.start_stage(1)
    out = r.heartbeat(1, "in flight", force=True)
    assert out is not None
    assert out.phase == "heartbeat"
    assert "in flight" in out.user_message


def test_heartbeat_fires_after_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    r = ProgressReporter(heartbeat_interval_s=0.001)
    r.start_stage(2)
    time.sleep(0.005)
    out = r.heartbeat(2, "第 2 轮 PK 进行中")
    assert out is not None


def test_end_stage_marks_done_with_summary() -> None:
    r = ProgressReporter()
    r.start_stage(1)
    e = r.end_stage(1, "病历整理好了, 找到 5 个试验", next_stage_preview_zh="想办法")
    assert "✓" in e.user_message
    assert "病历整理" in e.user_message
    assert "下一步" in e.user_message
    assert "想办法" in e.user_message


def test_end_stage_skip_next_for_final_stage() -> None:
    r = ProgressReporter()
    r.start_stage(5)
    e = r.end_stage(5, "两份报告都好了")
    assert "✓" in e.user_message
    assert "下一步" not in e.user_message


def test_delay_message_invites_skip() -> None:
    r = ProgressReporter()
    r.start_stage(3)
    e = r.delay(3, "ClinicalTrials.gov 现在响应慢", new_eta_min=8)
    assert "慢" in e.user_message
    assert "跳过" in e.user_message or "简化" in e.user_message


def test_block_message_lists_options_with_letters() -> None:
    r = ProgressReporter()
    r.start_stage(4)
    e = r.block(
        4,
        "审核发现一条关键结论的数据缺位",
        options_zh=[
            "等我重新拿数据 (10 分钟)",
            "把这条退到附录, 其他结论继续",
        ],
    )
    assert "暂停" in e.user_message
    assert "(a)" in e.user_message
    assert "(b)" in e.user_message


def test_jargon_scrub_flags_leaks() -> None:
    """If a stage-summary leaks 'Wave 3' or 'Elo tournament' or 'G25',
    the message gets a [jargon-leak:...] tag appended so the
    orchestrator + tests can catch the regression."""
    r = ProgressReporter()
    r.start_stage(3)
    e = r.end_stage(3, "Wave 3 找到 70 个 hits, G25 audit passed")
    assert "jargon-leak" in e.user_message


def test_no_jargon_in_well_formed_default_messages() -> None:
    """The default templates must be jargon-free."""
    r = ProgressReporter()
    for s in (1, 2, 3, 4, 5):
        e = r.start_stage(s)
        assert "jargon-leak" not in e.user_message, e.user_message


def test_jsonl_audit_trail_persisted(tmp_path: Path) -> None:
    log = tmp_path / "progress.jsonl"
    r = ProgressReporter(log_path=log)
    r.start_stage(1)
    r.end_stage(1, "好了", next_stage_preview_zh="想办法")
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    events = [json.loads(l) for l in lines]
    assert events[0]["phase"] == "start"
    assert events[1]["phase"] == "end"
    assert events[1]["stage_label_zh"] == "准备"


def test_on_emit_callback_invoked() -> None:
    captured: list[str] = []
    r = ProgressReporter(on_emit=captured.append)
    r.start_stage(1)
    r.start_stage(2)
    assert len(captured) == 2
    assert all("[" in m for m in captured)


def test_unknown_stage_raises() -> None:
    r = ProgressReporter()
    with pytest.raises(ValueError, match="unknown stage"):
        r.start_stage(99)
    with pytest.raises(ValueError, match="unknown stage"):
        r.heartbeat(99, "x", force=True)


def test_zh_only_language_drops_english() -> None:
    r = ProgressReporter(language="zh")
    e = r.start_stage(1)
    assert "准备" in e.user_message
    assert "Getting ready" not in e.user_message


def test_en_only_language_drops_chinese() -> None:
    r = ProgressReporter(language="en")
    e = r.start_stage(2)
    assert "Brainstorming" in e.user_message
    assert "想办法" not in e.user_message


def test_eta_override_per_stage() -> None:
    r = ProgressReporter(eta_overrides={3: (1, 2)})
    e = r.start_stage(3)
    assert "1-2" in e.user_message


def test_progress_message_rendering_prompt_present() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    p = repo_root / "prompts" / "tasks" / "progress_message_rendering.md"
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    # Five canonical stage labels referenced
    for label in ("准备", "想办法", "查数据", "审核", "写报告"):
        assert label in content
    # ETA range mandate
    assert "ETA must be a range" in content
    # Never silent past 60s
    assert "60s" in content or "60 s" in content or "60秒" in content
    # Internal-code leakage banned
    assert "Never reveal internal codes" in content
