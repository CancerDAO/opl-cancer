"""v2.3 Wave 6 task package shape tests.

8 new task packages must exist under prompts/tasks/ with:
- wave: 6 in frontmatter
- owning_expert in frontmatter
- henry_gates_invoked list in frontmatter
- length ≥ 120 lines (per spec §5.2)

This is a structural test — it does not exercise the prompts themselves
(those are LLM-driven and tested via the E2E suite).
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pytest


TASK_PACKAGES_DIR = Path("prompts/tasks")

WAVE6_PACKAGES: dict[str, tuple[str, Sequence[str]]] = {
    "manuscript_introduction.md": ("iain", ["G29", "G30"]),
    "manuscript_methods.md":      ("aviv", ["G29", "G30", "G32", "G33"]),
    "manuscript_results.md":      ("aviv", ["G29", "G30", "G31"]),
    "manuscript_discussion.md":   ("vince", ["G29", "G30", "G33"]),
    "manuscript_limitations.md":  ("henry", ["G29", "G30", "G33"]),
    "manuscript_abstract.md":     ("iain", ["G29", "G30", "G33"]),
    "citation_assembly.md":       ("henry-adjacent", ["G1", "G2", "G30"]),
    "figure_caption.md":          ("aviv", ["G30", "G31"]),
}


@pytest.mark.parametrize("filename", list(WAVE6_PACKAGES.keys()))
def test_wave6_package_exists(filename: str) -> None:
    p = TASK_PACKAGES_DIR / filename
    assert p.is_file(), f"{p} missing"


@pytest.mark.parametrize("filename", list(WAVE6_PACKAGES.keys()))
def test_wave6_package_has_frontmatter_wave_6(filename: str) -> None:
    text = (TASK_PACKAGES_DIR / filename).read_text(encoding="utf-8")
    # Frontmatter is between the first --- and second --- lines
    assert text.startswith("---\n"), f"{filename} missing frontmatter"
    end = text.find("\n---\n", 4)
    assert end > 0, f"{filename} unterminated frontmatter"
    fm = text[:end]
    assert "wave: 6" in fm, f"{filename} missing wave: 6 in frontmatter"


@pytest.mark.parametrize(
    "filename,expected_expert", [(k, v[0]) for k, v in WAVE6_PACKAGES.items()]
)
def test_wave6_package_declares_owning_expert(
    filename: str, expected_expert: str
) -> None:
    text = (TASK_PACKAGES_DIR / filename).read_text(encoding="utf-8")
    end = text.find("\n---\n", 4)
    fm = text[:end]
    assert f"owning_expert: {expected_expert}" in fm, (
        f"{filename} expected owning_expert={expected_expert}; "
        f"frontmatter:\n{fm}"
    )


@pytest.mark.parametrize(
    "filename,gates", [(k, v[1]) for k, v in WAVE6_PACKAGES.items()]
)
def test_wave6_package_declares_henry_gates(
    filename: str, gates: Sequence[str]
) -> None:
    text = (TASK_PACKAGES_DIR / filename).read_text(encoding="utf-8")
    end = text.find("\n---\n", 4)
    fm = text[:end]
    assert "henry_gates_invoked" in fm, (
        f"{filename} missing henry_gates_invoked in frontmatter"
    )
    for gate in gates:
        assert gate in fm, f"{filename} missing gate {gate}"


@pytest.mark.parametrize("filename", list(WAVE6_PACKAGES.keys()))
def test_wave6_package_length_minimum(filename: str) -> None:
    text = (TASK_PACKAGES_DIR / filename).read_text(encoding="utf-8")
    lines = text.count("\n") + 1
    assert lines >= 120, (
        f"{filename} has only {lines} lines; spec §5.2 requires ≥ 120."
    )


def test_total_task_package_count_is_62() -> None:
    """v2.2 had 54 task packages. v2.3 adds 8 = 62. v2.4 adds 1
    (`n1arxiv_pr_assembly.md`) = 63."""
    count = sum(
        1 for _ in TASK_PACKAGES_DIR.iterdir() if _.suffix == ".md"
    )
    assert count == 63, f"expected 63 task packages, got {count}"
