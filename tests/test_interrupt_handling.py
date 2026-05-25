"""Tests for v1.5.2-3 interrupt protocol contracts.

The interrupt protocol is mostly a documented contract that lives in
SKILL.md + prompts/tasks/interrupt_handling.md. These tests assert
the structural pieces a downstream implementation MUST honor:

- SKILL.md has the protocol section with the 7 canonical actions
- The task prompt advertises the JSON envelope shape
- The 7 canonical actions are enumerated consistently across the two
  documents
- Hard rules #1..5 are mirrored between SKILL.md and the task prompt
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_MD = REPO_ROOT / "SKILL.md"
INTERRUPT_PROMPT = REPO_ROOT / "prompts" / "tasks" / "interrupt_handling.md"


def test_skill_md_has_interrupt_protocol_section() -> None:
    content = SKILL_MD.read_text(encoding="utf-8")
    assert "Interrupt protocol" in content
    assert "v1.5.2-3" in content


def test_skill_md_lists_seven_canonical_actions() -> None:
    content = SKILL_MD.read_text(encoding="utf-8")
    for action in (
        "SKIP-STAGE",
        "SIMPLIFY-STAGE",
        "PAUSE-AND-SHOW-PARTIAL",
        "PARTIAL-DELIVERY",
        "CANCEL",
        "REPLAN",
        "STATUS+ETA",
    ):
        assert action in content, f"SKILL.md missing canonical action {action!r}"


def test_skill_md_pattern_table_covers_zh_and_en() -> None:
    content = SKILL_MD.read_text(encoding="utf-8")
    # zh patterns
    for pat in ("跳过", "简化", "停一下", "算了", "取消", "换一下专家"):
        assert pat in content, f"SKILL.md missing zh pattern {pat!r}"
    # en patterns
    for pat in ("skip", "simplify", "pause", "cancel", "swap experts"):
        assert pat in content, f"SKILL.md missing en pattern {pat!r}"


def test_skill_md_hard_rules_listed() -> None:
    content = SKILL_MD.read_text(encoding="utf-8")
    assert "Hard rules" in content
    assert "Acknowledge within 5 seconds" in content
    assert "Never silently change scope" in content
    assert "Skip is gate-aware" in content
    assert "Cancel always preserves artifacts" in content
    assert "Replan re-runs comorbid expansion" in content


def test_interrupt_prompt_exists() -> None:
    assert INTERRUPT_PROMPT.exists(), f"missing prompt at {INTERRUPT_PROMPT}"


def test_interrupt_prompt_advertises_json_envelope() -> None:
    content = INTERRUPT_PROMPT.read_text(encoding="utf-8")
    for required_field in (
        "parsed_intent",
        "stage_at_interrupt",
        "ack_message_to_user",
        "safety_warnings",
        "plan_modification",
        "needs_user_confirm",
        "next_assistant_action",
    ):
        assert required_field in content, (
            f"interrupt prompt envelope missing field {required_field!r}"
        )


def test_interrupt_prompt_enumerates_seven_canonical_intents() -> None:
    content = INTERRUPT_PROMPT.read_text(encoding="utf-8")
    for intent in (
        "SKIP_STAGE",
        "SIMPLIFY_STAGE",
        "PAUSE",
        "PARTIAL_DELIVERY",
        "CANCEL",
        "REPLAN",
        "STATUS_ETA",
        "UNKNOWN",
    ):
        assert intent in content, (
            f"interrupt prompt missing intent label {intent!r}"
        )


def test_interrupt_prompt_documents_g25_safety_surface() -> None:
    """Skip Wave 3 → Henry G25 BLOCK → must surface 2-option choice."""
    content = INTERRUPT_PROMPT.read_text(encoding="utf-8")
    assert "G25" in content
    assert "henry_gates_armed" in content


def test_interrupt_prompt_documents_cancel_preserves_artifacts() -> None:
    content = INTERRUPT_PROMPT.read_text(encoding="utf-8")
    assert "canceled.json" in content
    assert "resumable_via" in content
    assert "feedback_no_false_completion" in content


def test_interrupt_prompt_references_reporter_block_method() -> None:
    """The PAUSE / interrupt path calls ProgressReporter.block(...)
    (v1.5.1). The contract must say so explicitly so future authors
    don't reinvent."""
    content = INTERRUPT_PROMPT.read_text(encoding="utf-8")
    assert "ProgressReporter.block" in content


def test_interrupt_prompt_mirrors_skill_md_hard_rules() -> None:
    """The two documents must agree on the 5 hard rules."""
    skill_content = SKILL_MD.read_text(encoding="utf-8")
    prompt_content = INTERRUPT_PROMPT.read_text(encoding="utf-8")
    for hard_rule_marker in (
        "Acknowledge",
        "silently change scope",
        "gate-aware",
        "preserves artifacts",
        "Replan",
    ):
        assert hard_rule_marker.lower() in skill_content.lower()
        assert hard_rule_marker.lower() in prompt_content.lower()


def test_skill_md_provides_three_worked_examples() -> None:
    """SKILL.md gives 3 concrete dialog examples (skip with safety,
    simplify with echo, cancel with partial-delivery)."""
    content = SKILL_MD.read_text(encoding="utf-8")
    # At least 3 *User:* dialog turns in the Interrupt section
    interrupt_section_start = content.find("Interrupt protocol")
    interrupt_section_end = content.find("**Step 2 —")
    section = content[interrupt_section_start:interrupt_section_end]
    user_turns = section.count("*User:*")
    assert user_turns >= 3, f"expected ≥3 worked examples, got {user_turns}"
