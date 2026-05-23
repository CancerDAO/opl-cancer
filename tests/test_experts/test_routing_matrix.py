"""Routing-matrix golden test — 18 experts × 4 patients (HCC/NSCLC/CRC/BRCA).

Verifies the static expert→task_package portfolio is consistent and exhaustive,
and that each canonical patient cancer-type maps to a stable set of *candidate*
expert task-packages. This is a structural check, not an LLM call (memory:
feedback_default_prompt_over_script — routing remains LLM-driven at runtime,
but the *catalog* the planner picks from must be auditable + stable).

Per Iter 9 task #2: all 18 experts route per task package; 4 patient
cancer-types covered (HCC/NSCLC/CRC/BRCA).
"""
from __future__ import annotations

import importlib
import inspect
from pathlib import Path

import pytest

EXPERTS_PKG = "opl_cancer.experts"

# Canonical expert → task_package portfolio (golden snapshot).
EXPECTED_ROSTER: dict[str, tuple[str, ...]] = {
    "aviv": (
        "hypothesis_generation",
        "pathway_enrichment",
        "single_cell_reanalysis",
        "dataset_acquisition",
        "bioinformatics_data_analysis",
        "hypothesis_validation",  # shared with tyler (in-silico vs wet-lab split)
    ),
    "bert": ("molecular_ngs_interpretation",),
    "dennis": ("cross_border_navigation",),
    "frances": ("expanded_access_navigation",),
    "heddy": ("recist_progression",),
    "hong": ("tcm_oncology",),
    "iain": ("meta_analysis", "cross_source_consistency"),
    "jen": ("palliative_symptom_qol",),
    "kieren": ("neutropenic_fever_management",),
    "mark": ("ici_endocrine_irae",),
    "mary": ("ddi_adme_dosing",),
    "riad": ("interventional_oncology",),
    "rick": ("trial_matching",),
    "rosa": ("pathology_interpretation",),
    "steve": ("oncology_nutrition",),
    "ted": ("radiation_planning",),
    "tyler": ("hypothesis_validation", "in_silico_experiment_design"),
    "vince": ("treatment_line_recommendation",),
}

# Per-cancer expected candidate task-packages (planner is free to pick a subset).
# These represent the *minimum mandatory* candidate set per cancer.
PATIENT_EXPECTED_CANDIDATES: dict[str, set[str]] = {
    # HCC — molecular + path + imaging + intervention + trial + treatment
    "anon_hcc_001": {
        "molecular_ngs_interpretation",
        "pathology_interpretation",
        "recist_progression",
        "interventional_oncology",
        "trial_matching",
        "treatment_line_recommendation",
    },
    # NSCLC — molecular (EGFR/ALK) + imaging + irAE + trial + treatment
    "anon_nsclc_001": {
        "molecular_ngs_interpretation",
        "pathology_interpretation",
        "recist_progression",
        "ici_endocrine_irae",
        "trial_matching",
        "treatment_line_recommendation",
    },
    # CRC — molecular (KRAS/MSI) + path + treatment + trial + radiation
    "anon_crc_001": {
        "molecular_ngs_interpretation",
        "pathology_interpretation",
        "treatment_line_recommendation",
        "trial_matching",
        "radiation_planning",
    },
    # BRCA — molecular (HER2) + path + treatment + trial + ddi (cardiotoxicity)
    "anon_brca_001": {
        "molecular_ngs_interpretation",
        "pathology_interpretation",
        "treatment_line_recommendation",
        "trial_matching",
        "ddi_adme_dosing",
    },
}


def _expert_modules() -> list[str]:
    pkg_root = Path(__file__).resolve().parents[2] / "src" / "opl_cancer" / "experts"
    return sorted(
        p.stem
        for p in pkg_root.glob("*.py")
        if p.stem not in {"__init__", "base", "_common", "roster"}
    )


def _load_expert_class(name: str) -> type:
    mod = importlib.import_module(f"{EXPERTS_PKG}.{name}")
    # Find the class with portfolio attribute
    for _, obj in inspect.getmembers(mod, inspect.isclass):
        portfolio = getattr(obj, "portfolio", None)
        if portfolio is not None and obj.__module__.endswith(name):
            return obj
    raise AssertionError(f"no Expert class with portfolio in {name}")


# ----------------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------------


def test_all_18_experts_present() -> None:
    """Roster has exactly 18 expert modules (spec §2.2.X)."""
    mods = _expert_modules()
    assert len(mods) == 18, f"expected 18 expert modules, got {len(mods)}: {mods}"
    assert set(mods) == set(EXPECTED_ROSTER), (
        f"expert modules diverge: extra={set(mods)-set(EXPECTED_ROSTER)} "
        f"missing={set(EXPECTED_ROSTER)-set(mods)}"
    )


@pytest.mark.parametrize("expert_name", sorted(EXPECTED_ROSTER))
def test_expert_portfolio_matches_golden(expert_name: str) -> None:
    """Each expert's static portfolio matches the canonical snapshot."""
    cls = _load_expert_class(expert_name)
    actual = tuple(cls.portfolio)
    expected = EXPECTED_ROSTER[expert_name]
    assert actual == expected, (
        f"{expert_name} portfolio drift: expected={expected} actual={actual}"
    )


# Intentionally shared task_packages (documented routing flexibility).
SHARED_PACKAGES: dict[str, set[str]] = {
    "hypothesis_validation": {"aviv", "tyler"},  # in-silico (aviv) vs wet-lab (tyler)
}


def test_task_packages_unique_or_intentional_overlap() -> None:
    """task_package overlap is allowed only if registered in SHARED_PACKAGES."""
    seen: dict[str, str] = {}
    for expert_name, packages in EXPECTED_ROSTER.items():
        for pkg in packages:
            if pkg in seen:
                allowed = SHARED_PACKAGES.get(pkg, set())
                if {seen[pkg], expert_name} != allowed:
                    raise AssertionError(
                        f"task_package {pkg!r} owned by both "
                        f"{seen[pkg]} and {expert_name} but not in SHARED_PACKAGES"
                    )
            else:
                seen[pkg] = expert_name


@pytest.mark.parametrize("patient_code", sorted(PATIENT_EXPECTED_CANDIDATES))
def test_patient_candidate_packages_coverable(patient_code: str) -> None:
    """Every candidate task_package for a patient has a registered owner."""
    expected = PATIENT_EXPECTED_CANDIDATES[patient_code]
    all_packages = {pkg for pkgs in EXPECTED_ROSTER.values() for pkg in pkgs}
    missing = expected - all_packages
    assert not missing, (
        f"patient {patient_code} requires uncoverable packages: {missing}"
    )


def test_four_canonical_cancer_types_covered() -> None:
    """Exactly the four canonical cancer-type patient codes are validated."""
    assert set(PATIENT_EXPECTED_CANDIDATES) == {
        "anon_hcc_001",
        "anon_nsclc_001",
        "anon_crc_001",
        "anon_brca_001",
    }


def test_every_expert_has_at_least_one_routing_target() -> None:
    """No silent dead experts in the roster."""
    for expert_name, packages in EXPECTED_ROSTER.items():
        assert len(packages) >= 1, f"{expert_name} has empty portfolio"
