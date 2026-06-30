"""Tests for v2.5 IntegratorABC + entry-point discovery — RFC 0001 §2.4."""
from __future__ import annotations

import pytest

from opl_cancer.integrators._abc import (
    IntegratorABC,
    IntegratorRegistry,
)


EXPECTED_ENTRY_POINT_INTEGRATORS = {
    "pubmed",
    "opentargets",
    "clinicaltrials",
    "cbioportal",
    "oncokb",
}


def test_five_entry_point_integrators_registered() -> None:
    """pyproject.toml [project.entry-points.\"opl_cancer.integrators\"] declares
    the 5 v2.5 entry-point integrators (pubmed, opentargets, clinicaltrials,
    cbioportal, oncokb). Remaining 39 are tagged for M3 migration."""
    reg = IntegratorRegistry.discover()
    discovered = set(reg.keys())
    assert EXPECTED_ENTRY_POINT_INTEGRATORS <= discovered, (
        f"missing entry points: {EXPECTED_ENTRY_POINT_INTEGRATORS - discovered}"
    )


def test_clinicaltrials_inherits_from_integrator_abc() -> None:
    """v2.5 picks ≥ 1 existing integrator to ALSO inherit IntegratorABC as
    proof-of-protocol. ClinicalTrialsGovIntegrator is one of those."""
    from opl_cancer.integrators.clinicaltrials import ClinicalTrialsGovIntegrator

    assert issubclass(ClinicalTrialsGovIntegrator, IntegratorABC)


def test_opentargets_inherits_from_integrator_abc() -> None:
    """OpenTargetsIntegrator is the second proof-of-protocol inheritor."""
    from opl_cancer.integrators.open_targets import OpenTargetsIntegrator

    assert issubclass(OpenTargetsIntegrator, IntegratorABC)


def test_unknown_entry_point_raises() -> None:
    reg = IntegratorRegistry.discover()
    with pytest.raises(KeyError):
        reg.get("not_a_real_integrator_xyz")


def test_registry_describe_returns_machine_inventory() -> None:
    reg = IntegratorRegistry.discover()
    rows = {row["name"]: row for row in reg.describe()}
    assert rows["clinicaltrials"]["ok"] is True
    assert rows["clinicaltrials"]["implements_integrator_abc"] is True
    assert rows["pubmed"]["module"].startswith("opl_cancer.integrators.")


def test_integrator_abc_protocol_methods() -> None:
    """IntegratorABC declares id / query / normalize / provenance."""
    abc_attrs = dir(IntegratorABC)
    for method in ("query", "normalize", "provenance"):
        assert method in abc_attrs, f"IntegratorABC missing {method}"
    # 'id' is a class attribute (string), not a method
    assert hasattr(IntegratorABC, "id")


def test_existing_integrators_remain_importable_backward_compat() -> None:
    """v2.5 BC invariant — all 44 v2.4 integrators still importable."""
    import importlib
    from pathlib import Path

    integrators_dir = Path(__file__).resolve().parent.parent.parent / "src" / "opl_cancer" / "integrators"
    py_files = [
        p.stem
        for p in integrators_dir.glob("*.py")
        if not p.stem.startswith("_") and p.stem != "base" and p.stem != "cache"
    ]
    # ≥ 30 (v2.4 had 44; some are helpers — confirm a reasonable lower bound)
    assert len(py_files) >= 30
    failures: list[str] = []
    for stem in py_files:
        try:
            importlib.import_module(f"opl_cancer.integrators.{stem}")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{stem}: {exc}")
    assert not failures, f"import failures: {failures}"
