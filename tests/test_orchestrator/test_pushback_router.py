"""v2.1 P2-#19: patient_pushback_handling auto-triggered on keywords or sniffer halt."""
from __future__ import annotations

from pathlib import Path

from opl_cancer.orchestrator.pushback_router import (
    log_trigger,
    should_trigger_pushback,
)


def test_keyword_actually_triggers():
    assert should_trigger_pushback("Are you actually running it?")


def test_keyword_zhenzaipao_triggers():
    assert should_trigger_pushback("真的在跑吗？")


def test_neutral_message_no_trigger():
    assert not should_trigger_pushback("How is the weather?")


def test_log_trigger_appends_jsonl(tmp_path: Path):
    log_path = tmp_path / "pushback_trigger_log.jsonl"
    log_trigger(
        log_path,
        reason="keyword",
        excerpt="really hallucinating",
        source="user_message",
    )
    assert log_path.exists()
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 1
    assert "really hallucinating" in lines[0]


def test_log_trigger_appends_not_overwrites(tmp_path: Path):
    log_path = tmp_path / "pushback_trigger_log.jsonl"
    log_trigger(log_path, reason="k", excerpt="a", source="s1")
    log_trigger(log_path, reason="k", excerpt="b", source="s2")
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 2
