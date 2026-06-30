from __future__ import annotations

from opl_cancer.plan.task_capabilities import (
    build_task_capability_registry,
    owners_for_task,
    validate_task_capability_registry,
)


def test_task_capability_registry_links_static_portfolios_to_prompts() -> None:
    registry = build_task_capability_registry()

    assert registry["target_synergy_emergent"].prompt_exists is True
    assert registry["target_synergy_emergent"].owners == ["maya"]
    assert registry["undrugged_target_design"].prompt_exists is True
    assert registry["undrugged_target_design"].owners == ["julius"]
    assert registry["in_silico_experiment_design"].prompt_exists is True
    assert registry["in_silico_experiment_design"].owners == ["tyler"]


def test_task_capability_registry_includes_runtime_roster_portfolios() -> None:
    registry = build_task_capability_registry()

    assert "bert" in registry["msi_detection"].owners
    assert "aviv" in registry["biostats_survival"].owners
    assert "mary" in registry["pharmacogenomics_cpic"].owners
    assert "maya" in registry["opentargets_evidence"].owners


def test_task_capability_registry_validates_prompt_coverage() -> None:
    registry = build_task_capability_registry()
    validation = validate_task_capability_registry(registry)

    assert validation["ok"] is True
    assert validation["summary"]["missing_prompt"] == 0
    assert validation["summary"]["count"] == 78


def test_owners_for_task_returns_sorted_owner_names() -> None:
    assert owners_for_task("hypothesis_validation") == ["aviv", "tyler"]

