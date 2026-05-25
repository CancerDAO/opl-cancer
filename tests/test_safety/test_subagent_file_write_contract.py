"""Tests for the v1.5 P0-7 subagent file-write contract."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = (
    REPO_ROOT / "prompts" / "safety" / "subagent_file_write_contract.md"
)


def test_contract_file_exists() -> None:
    assert CONTRACT_PATH.exists(), f"missing contract at {CONTRACT_PATH}"


def test_contract_has_canonical_sentinel() -> None:
    content = CONTRACT_PATH.read_text(encoding="utf-8")
    assert "OPL_REPORT_EOF" in content


def test_contract_has_write_then_bash_fallback_order() -> None:
    content = CONTRACT_PATH.read_text(encoding="utf-8")
    # PRIMARY must precede FALLBACK textually
    primary_idx = content.find("(PRIMARY)")
    fallback_idx = content.find("(FALLBACK)")
    confirm_idx = content.find("(CONFIRMATION)")
    assert primary_idx >= 0
    assert fallback_idx > primary_idx
    assert confirm_idx > fallback_idx


def test_contract_enumerates_five_wave_paths() -> None:
    content = CONTRACT_PATH.read_text(encoding="utf-8")
    for path_fragment in (
        "tasks/w1_",
        "tasks/w2_",
        "tasks/w3_",
        "tasks/w4_",
        "tasks/henry",
    ):
        assert path_fragment in content, f"missing path template {path_fragment}"


def test_contract_json_envelope_required_fields() -> None:
    content = CONTRACT_PATH.read_text(encoding="utf-8")
    for field in (
        "report_path",
        "report_bytes",
        "report_sha256_short",
        "status",
        "task",
        "expert",
    ):
        assert field in content, f"envelope field {field} not specified"


def test_contract_forbids_silent_skip() -> None:
    content = CONTRACT_PATH.read_text(encoding="utf-8")
    assert "silent skip" in content.lower() or "no silent skip" in content.lower()
    assert "feedback_no_offline_only" in content


def test_contract_forbids_inline_full_report() -> None:
    content = CONTRACT_PATH.read_text(encoding="utf-8")
    # The retro pattern was: subagents return the full report inline
    # instead of writing to file. The contract must explicitly forbid this.
    assert "DO NOT" in content
    assert "full report content" in content.lower() or "inline" in content.lower()


def test_contract_documents_orchestrator_validation() -> None:
    """The orchestrator must verify file presence + size + hash. This is
    the v1.5 anti-fabrication audit step (memory:feedback_no_false_completion)."""
    content = CONTRACT_PATH.read_text(encoding="utf-8")
    assert "sha256" in content.lower()
    assert "Validation by the orchestrator" in content


def test_contract_caps_redispatch_retry() -> None:
    """If the envelope mismatches the filesystem, the orchestrator should
    re-dispatch — but only 1 retry, to avoid infinite loops on broken
    harness configs."""
    content = CONTRACT_PATH.read_text(encoding="utf-8")
    assert "Cap re-dispatch at 1 retry" in content
