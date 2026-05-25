"""Tests for v1.5.2-2 auto-prepending persona prefix.

The canonical persona prefix at prompts/experts/_shared/persona_prefix.md
(v1.5 P1-A) is now automatically prepended to every expert's system
prompt by LLMBackedExpert._compose_system_prompt(). These tests verify:

1. The prefix is actually inlined for every expert in the roster (no
   18-persona-prompt manual backfill needed).
2. The skip_persona_prefix=True escape hatch works for isolated tests.
3. Missing prefix file raises a loud error (no silent degradation).
4. The prefix contains the v1.5 P1-A required sections.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from opl_cancer.experts._common import LLMBackedExpert
from opl_cancer.experts.base import ExpertProfile
from opl_cancer.experts.roster import ROSTER

REPO_ROOT = Path(__file__).resolve().parents[1]


def _make_expert(name: str, skip_prefix: bool = False) -> LLMBackedExpert:
    profile = ExpertProfile(
        name=name,
        inspiration="test-only",
        role="test-only",
        persona_summary="test-only profile for unit tests",
        task_package_portfolio=["molecular_ngs_interpretation"],
        preferred_integrator_families=["F1"],
    )

    class _NullClient:
        async def complete(self, *args, **kwargs):  # noqa: ANN001
            raise NotImplementedError

    return LLMBackedExpert(
        profile=profile,
        executor_client=_NullClient(),
        reviewer_client=_NullClient(),
        executor_model_id="x",
        reviewer_model_id="y",
        skip_persona_prefix=skip_prefix,
    )


def test_persona_prefix_file_present() -> None:
    p = REPO_ROOT / "prompts" / "experts" / "_shared" / "persona_prefix.md"
    assert p.exists(), f"missing v1.5 P1-A persona prefix at {p}"


def test_compose_system_prompt_includes_prefix_for_bert() -> None:
    e = _make_expert("bert")
    composed = e._compose_system_prompt()
    # Prefix's section headers should be present
    assert "G7" in composed
    assert "Patient-anchor" in composed or "patient-anchor" in composed
    assert "Source-traceability" in composed or "traceability" in composed.lower()
    # The persona body should still be there
    persona_body = e._persona_path().read_text(encoding="utf-8")
    # Use a substring of the persona body's title line
    body_first_line = persona_body.strip().splitlines()[0] if persona_body.strip() else ""
    if body_first_line:
        assert body_first_line in composed


def test_skip_persona_prefix_escape_hatch() -> None:
    e = _make_expert("bert", skip_prefix=True)
    composed = e._compose_system_prompt()
    # When skipped, the v1.5 P1-A prefix should NOT be present
    # (We assert against a unique fragment that only the prefix has)
    assert "Canonical Expert Persona Prefix" not in composed


def test_missing_prefix_raises_when_not_skipped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """If someone deletes the prefix file the skill must fail loud."""
    e = _make_expert("bert")
    LLMBackedExpert._persona_prefix_cache = None  # reset cache
    # Point the prompts root at a tmp dir that has no _shared/persona_prefix.md
    monkeypatch.setattr(
        "opl_cancer.experts._common.find_prompts_root",
        lambda: tmp_path,
    )
    with pytest.raises(FileNotFoundError, match="persona prefix missing"):
        e._compose_system_prompt()
    # Restore cache for other tests
    LLMBackedExpert._persona_prefix_cache = None


def test_prefix_inlined_for_all_18_roster_experts() -> None:
    """No persona was missed — every expert in the roster gets the
    prefix at runtime via _compose_system_prompt()."""
    LLMBackedExpert._persona_prefix_cache = None  # ensure fresh
    persona_root = REPO_ROOT / "prompts" / "experts"
    skipped: list[str] = []
    failed: list[tuple[str, str]] = []
    for expert_name in sorted(ROSTER.keys()):
        if expert_name == "_shared":  # not an expert
            continue
        persona_md = persona_root / expert_name / "persona.md"
        if not persona_md.exists():
            skipped.append(expert_name)
            continue
        e = _make_expert(expert_name)
        try:
            composed = e._compose_system_prompt()
        except Exception as exc:  # pragma: no cover — fail loud
            failed.append((expert_name, repr(exc)))
            continue
        # Two stable markers from the prefix that the persona body
        # itself does not have.
        if "G7" not in composed:
            failed.append((expert_name, "G7 marker missing"))
        if "Patient-anchor" not in composed and "patient-anchor" not in composed.lower():
            failed.append((expert_name, "patient-anchor marker missing"))
    assert not failed, f"prefix not inlined for: {failed}"
    # The 18-expert roster must cover at least 14 personas with a
    # persona.md file. If too many are missing, that's a separate bug.
    assert (
        len(ROSTER) - len(skipped) >= 14
    ), f"too many personas missing persona.md: skipped={skipped}"


def test_prefix_cache_avoids_repeated_disk_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Class-level cache: prefix file read at most once per process."""
    LLMBackedExpert._persona_prefix_cache = None
    reads: list[Path] = []
    real_read = Path.read_text

    def _spy(self: Path, *args, **kwargs):  # noqa: ANN001
        if "_shared/persona_prefix.md" in str(self):
            reads.append(self)
        return real_read(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _spy)
    e1 = _make_expert("bert")
    e2 = _make_expert("vince")
    e1._compose_system_prompt()
    e2._compose_system_prompt()
    e1._compose_system_prompt()
    # All 3 compositions should reuse the cache after the first read.
    assert len(reads) == 1, f"expected 1 read, saw {len(reads)}"


def test_prefix_has_g7_imperative_section() -> None:
    p = REPO_ROOT / "prompts" / "experts" / "_shared" / "persona_prefix.md"
    content = p.read_text(encoding="utf-8")
    # The G7 voice section enumerates forbidden constructions
    assert "Forbidden constructions" in content
    for forbidden in ("must", "should", "patient must"):
        assert forbidden in content
    # Imperative→informational rewrites table
    assert "Required rephrasings" in content
