"""P4.5 acceptance — closeout items present + wired correctly."""
from __future__ import annotations

import importlib

from opl_cancer.experts.roster import ROSTER


def test_all_experts_in_roster() -> None:
    # v2.0.0 (ADR-0010): 18 v1 + 2 v2 (maya, julius) = 20
    assert len(ROSTER) == 20


def test_three_new_experts_modules_importable() -> None:
    for mod_name, cls_name in (
        ("opl_cancer.experts.kieren", "KierenExpert"),
        ("opl_cancer.experts.mark", "MarkExpert"),
        ("opl_cancer.experts.dennis", "DennisExpert"),
    ):
        mod = importlib.import_module(mod_name)
        assert hasattr(mod, cls_name), f"{mod_name} missing {cls_name}"


def test_g7_imperative_detector_importable() -> None:
    mod = importlib.import_module(
        "opl_cancer.validators.gates.g7_imperative_detector"
    )
    assert hasattr(mod, "G7ImperativeDetectorGate")
    gate = mod.G7ImperativeDetectorGate()
    assert gate.failure_mode_code == "C1"


def test_wave4_runner_importable() -> None:
    mod = importlib.import_module("opl_cancer.glue.wave4_runner")
    assert hasattr(mod, "Wave4Runner")


def test_three_new_task_prompts_exist() -> None:
    from opl_cancer.llm.prompts import find_prompts_root

    root = find_prompts_root() / "tasks"
    for task in (
        "neutropenic_fever_management",
        "ici_endocrine_irae",
        "cross_border_navigation",
    ):
        p = root / f"{task}.md"
        assert p.exists(), f"task prompt missing: {p}"
        body = p.read_text(encoding="utf-8")
        assert "JSON" in body or "json" in body


def test_three_new_personas_exist() -> None:
    from opl_cancer.llm.prompts import find_prompts_root

    root = find_prompts_root() / "experts"
    for name in ("kieren", "mark", "dennis"):
        p = root / name / "persona.md"
        assert p.exists(), f"persona missing: {p}"
        body = p.read_text(encoding="utf-8")
        assert "Anti-patterns" in body
