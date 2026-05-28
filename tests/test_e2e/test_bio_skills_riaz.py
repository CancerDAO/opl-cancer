"""E2E — exercise every v2.2 bio-skill task package integrator on
the Riaz reference case (public Riaz 2017 melanoma + nivolumab cohort).

This test runs in mock/offline mode by default — heavy network or
binary deps (MSIsensor live, SigProfilerAssignment live) are
exercised in dedicated live tests under `--live`.

The goal: per `feedback_multi_case_validation`, verify the v2.2
pipeline can drive all 7 (+1 optional) task packages end-to-end without
silent failures.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from opl_cancer.integrators.cosmic_sigprofiler import CosmicSigProfilerIntegrator
from opl_cancer.integrators.cpic import CpicIntegrator
from opl_cancer.integrators.lifelines_km import (
    LifelinesKMIntegrator,
    apply_subgroup_filter,
    require_lifelines,
)
from opl_cancer.integrators.msi_sensor import MSIsensorIntegrator
from opl_cancer.integrators.tmb_harmonization import TMBHarmonizationIntegrator
from opl_cancer.integrators.varsome_acmg import AcmgGermlineIntegrator
from opl_cancer.integrators.figure_render import (
    render_forest_plot,
    render_km_curve,
)


pytestmark = pytest.mark.skipif(
    not require_lifelines(strict=False),
    reason="lifelines required for the survival branch of the E2E",
)


# Synthetic Riaz-like cohort. Real Riaz 2017 has 65 melanoma patients with
# nivolumab; we use a 16-row subset that exercises every code path.
_RIAZ_LIKE_COHORT = [
    {"id": f"r{i}", "durations": d, "events": e, "msi_status": m, "tmb": t}
    for i, (d, e, m, t) in enumerate([
        (3, 1, "MSS", 4.2), (5, 1, "MSS", 6.1), (7, 1, "MSS", 5.0),
        (9, 1, "MSS", 3.8), (11, 0, "MSS", 4.5), (13, 1, "MSS", 5.2),
        (15, 0, "MSS", 6.8), (17, 1, "MSI-H", 22.4), (19, 0, "MSI-H", 28.5),
        (21, 1, "MSI-H", 19.2), (23, 0, "MSI-H", 31.0), (25, 0, "MSS", 7.5),
        (27, 1, "MSS", 8.0), (29, 0, "MSS", 5.5), (31, 0, "MSI-H", 25.0),
        (33, 0, "MSI-H", 20.8),
    ])
]


def test_msi_mock_runs() -> None:
    integ = MSIsensorIntegrator(mock_mode=True, mock_score=22.4, mock_sites=180)
    out = asyncio.run(integ.fetch("tumor:/tmp/t.bam:normal:/tmp/n.bam"))
    assert out["status"] == "MSI-H"
    assert out["n_sites_examined"] == 180


def test_tmb_harmonization_runs() -> None:
    integ = TMBHarmonizationIntegrator()
    out = asyncio.run(integ.fetch("panel:TSO500:n_mutations:25"))
    assert out["status"] == "TMB-H"
    assert out["effective_mb"] == 1.94


def test_cosmic_sigprofiler_mock_runs() -> None:
    integ = CosmicSigProfilerIntegrator(
        mock_mode=True,
        mock_signatures={"SBS7a": 0.55, "SBS7b": 0.25, "SBS1": 0.20},
    )
    out = asyncio.run(integ.fetch("vcf:/tmp/riaz.vcf"))
    assert out["dominant_signature"] == "SBS7a"  # UV — melanoma context


def test_acmg_mock_runs() -> None:
    integ = AcmgGermlineIntegrator(
        mock_mode=True,
        mock_criteria=["PVS1", "PS1", "PM2"],
    )
    out = asyncio.run(integ.fetch("variant:BRCA1:c.5266dupC"))
    assert out["classification"] == "Pathogenic"


def test_biostats_survival_runs() -> None:
    integ = LifelinesKMIntegrator(min_n_per_arm=5)
    msi_h = apply_subgroup_filter(_RIAZ_LIKE_COHORT, {"msi_status": "MSI-H"})
    mss = apply_subgroup_filter(_RIAZ_LIKE_COHORT, {"msi_status": "MSS"})
    assert len(msi_h) >= 5
    assert len(mss) >= 5
    out = asyncio.run(
        integ.fetch_logrank(
            arm_a={
                "durations": [r["durations"] for r in mss],
                "events": [r["events"] for r in mss],
                "label": "MSS",
            },
            arm_b={
                "durations": [r["durations"] for r in msi_h],
                "events": [r["events"] for r in msi_h],
                "label": "MSI-H",
            },
        )
    )
    assert "p_value" in out
    assert out["arm_a_n"] == len(mss)
    assert out["arm_b_n"] == len(msi_h)


def test_biostats_subgroup_forest_renders(tmp_path: Path) -> None:
    """Subgroup forest plot PNG renders with HR rows."""
    out_path = tmp_path / "riaz_forest.png"
    rec = render_forest_plot(
        out_path=out_path,
        rows=[
            {"label": "Overall",  "hr": 0.65, "ci_low": 0.50, "ci_high": 0.85},
            {"label": "MSI-H",    "hr": 0.32, "ci_low": 0.15, "ci_high": 0.68},
            {"label": "MSS",      "hr": 0.78, "ci_low": 0.55, "ci_high": 1.10},
            {"label": "TMB-H",    "hr": 0.40, "ci_low": 0.20, "ci_high": 0.75},
            {"label": "TMB-L",    "hr": 0.85, "ci_low": 0.60, "ci_high": 1.20},
        ],
        title="Riaz subgroup forest (synthetic)",
    )
    assert out_path.exists()
    assert rec["size_bytes"] > 100


def test_km_curve_renders(tmp_path: Path) -> None:
    out_path = tmp_path / "riaz_km.png"
    msi_h = apply_subgroup_filter(_RIAZ_LIKE_COHORT, {"msi_status": "MSI-H"})
    mss = apply_subgroup_filter(_RIAZ_LIKE_COHORT, {"msi_status": "MSS"})
    rec = render_km_curve(
        out_path=out_path,
        arms=[
            {"label": "MSS",
             "durations": [r["durations"] for r in mss],
             "events":    [r["events"] for r in mss]},
            {"label": "MSI-H",
             "durations": [r["durations"] for r in msi_h],
             "events":    [r["events"] for r in msi_h]},
        ],
        title="Riaz KM by MSI status (synthetic)",
    )
    assert out_path.exists()
    assert rec["size_bytes"] > 100


def test_cpic_lookup_runs() -> None:
    """DPYD × fluorouracil — typical Riaz follow-on chemo line."""
    integ = CpicIntegrator()
    out = asyncio.run(
        integ.fetch("gene:DPYD:drug:fluorouracil:phenotype:Intermediate Metabolizer")
    )
    assert out["recommendation_level"] == "A"


def test_all_7_required_packages_have_prompts_on_disk() -> None:
    """Sanity — every v2.2 task package is shipped under prompts/tasks/."""
    base = Path(__file__).resolve().parents[2] / "prompts" / "tasks"
    for pkg in (
        "msi_detection",
        "tmb_calculation",
        "cosmic_signature_extraction",
        "acmg_germline_classification",
        "opentargets_evidence",
        "biostats_survival",
        "biostats_subgroup",
        "pharmacogenomics_cpic",
    ):
        p = base / f"{pkg}.md"
        assert p.exists(), f"missing {p}"
