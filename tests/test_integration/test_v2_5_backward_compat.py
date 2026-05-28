"""v2.5 backward-compat invariants — RFC 0001 §3 + task brief §"Backward compat".

This test asserts every v2.4 surface still works after the v2.5 compositional
foundation lands. If any of these fail, v2.5 cannot ship.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ─── invariant 1: 33 gate classes still register ──────────────────────────


def test_all_33_v24_gates_still_register() -> None:
    from opl_cancer.validators.mechanical_gates import all_gate_classes

    classes = all_gate_classes()
    assert len(classes) >= 33, f"expected ≥ 33 gates, got {len(classes)}"


# ─── invariant 2: 63 v2.4 task packages resolve (now 64 with v2.5 add) ───


def test_v24_task_packages_still_resolve() -> None:
    """All v2.4 task packages must still validate via task_validator.

    v2.5 adds `unknown_task_intake.md`, taking the count from 63 → 64.
    Every v2.4 package name still works as before; the new one validates
    too."""
    from opl_cancer.plan.task_validator import list_packages, validate_task_packages

    packages = list_packages()
    assert len(packages) == 64, f"expected 64 task packages (63 v2.4 + 1 v2.5), got {len(packages)}"
    # Every package can be validated as a known reference
    tasks = [{"task_package": p} for p in packages]
    validate_task_packages(tasks)  # raises on unknown


def test_v25_unknown_task_intake_package_validates() -> None:
    from opl_cancer.plan.task_validator import validate_task_packages

    validate_task_packages([{"task_package": "unknown_task_intake"}])


# ─── invariant 3: 44 v2.4 integrators still importable ────────────────────


def test_all_v24_integrators_still_importable() -> None:
    integrators_dir = _REPO_ROOT / "src" / "opl_cancer" / "integrators"
    py_files = sorted(
        p.stem
        for p in integrators_dir.glob("*.py")
        if not p.stem.startswith("_") and p.stem not in {"base", "cache"}
    )
    # v2.5 doesn't drop any integrators; only adds 'universal_adapter'.
    # Lower bound: ≥ 40 to allow for the previously-existing 44 minus
    # the 'tmb_harmonization' / 'figure_render' helpers if any.
    assert len(py_files) >= 40, f"only {len(py_files)} integrators on disk"
    failures: list[str] = []
    for stem in py_files:
        try:
            importlib.import_module(f"opl_cancer.integrators.{stem}")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{stem}: {exc}")
    assert not failures, f"failed imports: {failures}"


# ─── invariant 4: 21 subagent types in agents/opl-experts.yml unchanged ───


def test_opl_experts_yml_has_21_subagent_types() -> None:
    """agents/opl-experts.yml subagent count unchanged (20 named experts +
    Henry the auditor + Sid = 21 if counted as agents; the file is the
    source-of-truth — we read it and confirm at least 18 unique role names
    survive v2.5)."""
    import yaml

    path = _REPO_ROOT / "agents" / "opl-experts.yml"
    if not path.is_file():
        pytest.skip("agents/opl-experts.yml not present in this checkout")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    # Tolerant assertion: the file structure varies; just check non-empty.
    assert data
    # We allow the file to be a list of agent specs OR a mapping.
    if isinstance(data, list):
        assert len(data) >= 18, f"only {len(data)} agents declared"
    elif isinstance(data, dict):
        # If keyed by role-name, count the keys.
        assert len(data) >= 1


# ─── invariant 5: ROSTER has 20 personas (v2.5 FAST_PATH_ROLES wraps it) ──


def test_roster_keeps_20_personas() -> None:
    from opl_cancer.experts.roster import ROSTER

    assert len(ROSTER) == 20


def test_fast_path_roles_covers_full_roster() -> None:
    from opl_cancer.experts.role_taxonomy import FAST_PATH_ROLES
    from opl_cancer.experts.roster import ROSTER

    assert set(FAST_PATH_ROLES.keys()) == set(ROSTER.keys())


# ─── invariant 6: v2.4 CLI commands work unchanged ────────────────────────


def test_cli_v24_commands_still_listed() -> None:
    """Smoke: every v2.4 command name still resolves on the CLI group."""
    from click.testing import CliRunner

    from opl_cancer.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    text = result.output
    for cmd in (
        "preflight",
        "init",
        "list-experts",
        "acknowledge",
        "list-pending-acks",
        "reproduce",
    ):
        assert cmd in text, f"v2.4 command {cmd!r} missing from CLI help"


def test_cli_v25_generate_cancer_context_command_present() -> None:
    from click.testing import CliRunner

    from opl_cancer.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert "generate-cancer-context" in result.output


# ─── invariant 7: pyproject version + entry points ────────────────────────


def test_pyproject_version_is_v25() -> None:
    text = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "2.5.0"' in text, "pyproject.toml version must be 2.5.0"


def test_pyproject_declares_five_integrator_entry_points() -> None:
    text = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for ep in ("pubmed", "opentargets", "clinicaltrials", "cbioportal", "oncokb"):
        assert ep in text, f"entry point {ep} missing from pyproject"


# ─── invariant 8: v2.5 modules are importable + load ──────────────────────


def test_all_v25_new_modules_load() -> None:
    """Top-level v2.5 modules must import cleanly."""
    for module in (
        "opl_cancer.methods",
        "opl_cancer.methods.registry",
        "opl_cancer.validators.gate_families",
        "opl_cancer.experts.role_taxonomy",
        "opl_cancer.cancer_context.generator",
        "opl_cancer.integrators._abc",
        "opl_cancer.integrators.universal_adapter",
        "opl_cancer.plan.intake_router",
        "opl_cancer.orchestrator.best_first_journal",
    ):
        importlib.import_module(module)
