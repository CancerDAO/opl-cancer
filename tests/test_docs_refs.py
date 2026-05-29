"""v2.7.0 ADR-0026 — every doc/reference SKILL.md points at must exist.

RC-5 (docs/ANTI_PATTERNS_v1.4.md) and RC-6 (references/patient-data-layout.md)
were dangling citations — SKILL.md described them as authoritative while the
files did not exist. This test makes that class of drift fail CI.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SKILL = _REPO / "SKILL.md"
_REF_RE = re.compile(r"(?:references|docs)/[A-Za-z0-9_./-]+\.md")


def _referenced_paths() -> list[str]:
    text = _SKILL.read_text(encoding="utf-8")
    # de-dupe, preserve determinism
    return sorted(set(_REF_RE.findall(text)))


@pytest.mark.parametrize("rel", _referenced_paths())
def test_skill_md_reference_exists(rel: str) -> None:
    assert (_REPO / rel).is_file(), (
        f"SKILL.md references {rel!r} but it does not exist in the repo "
        "(dangling citation — see ADR-0026 RC-5/RC-6)."
    )


def test_no_stale_anti_patterns_v14_reference() -> None:
    """The dangling ANTI_PATTERNS_v1.4.md ref must be gone (redirected to ANTI_PATTERNS.md)."""
    assert "ANTI_PATTERNS_v1.4.md" not in _SKILL.read_text(encoding="utf-8")
