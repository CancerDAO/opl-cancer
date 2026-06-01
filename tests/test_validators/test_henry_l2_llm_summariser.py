"""Henry L2 axis-naming hand-off (harness-split).

The in-Python LLM call ``summarise_disagreement_axes`` was removed; axis-naming
is now an OPTIONAL host-agent prompt (``prompts/auditor/henry_axis_naming.md``).
Henry only builds the scaffold (cleaned verbatim challenges + prompt reference)
and preserves the empty-input short-circuit. This test asserts that new
deterministic behavior — no LLM client, no network.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from opl_cancer.validators.henry import HenryAuditor

REPO_ROOT = Path(__file__).resolve().parents[2]
SERIOUS_RISKS_PATH = REPO_ROOT / "knowledge" / "serious_risks_per_drug.json"


@pytest.fixture()
def auditor(tmp_path: Path) -> HenryAuditor:
    return HenryAuditor(
        serious_risks_path=SERIOUS_RISKS_PATH,
        outstanding_dir=tmp_path / "outstanding",
    )


def test_axis_naming_scaffold_returns_cleaned_challenges_and_prompt(
    auditor: HenryAuditor,
) -> None:
    scaffold = auditor.build_axis_naming_scaffold(
        ["No phase III for this combo", "  Dose 200mg may exceed safe ceiling  "]
    )
    # The host-agent prompt is referenced (Henry no longer reasons in-process).
    assert scaffold["host_prompt"] == "auditor/henry_axis_naming.md"
    # Verbatim challenges are cleaned (stripped) but never invented/edited.
    assert scaffold["reviewer_challenges"] == [
        "No phase III for this combo",
        "Dose 200mg may exceed safe ceiling",
    ]


def test_axis_naming_scaffold_empty_challenges_short_circuits(
    auditor: HenryAuditor,
) -> None:
    scaffold = auditor.build_axis_naming_scaffold([])
    # Engine short-circuit preserved: empty result, no host call.
    assert scaffold == {"axes": [], "summary": "", "host_prompt": None}


def test_henry_has_no_llm_call(auditor: HenryAuditor) -> None:
    """Regression: the LLM summariser method is gone (harness-split)."""
    assert not hasattr(auditor, "summarise_disagreement_axes")
