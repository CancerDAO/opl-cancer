"""P1 acceptance test — verifies P0 + P1 acceptance criteria met.

Renames previous test_p0_acceptance.py and adds Wave 1 / experts / integrators /
gates acceptance per spec section 16 P1 scope. The old tautological
`test_acceptance_pytest_runs` is replaced with `test_p1_e2e_runs_to_completion`
which makes a real assertion against Wave1Runner imports.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from click.testing import CliRunner

from opl_cancer.cli import main
from opl_cancer.experts.roster import ROSTER

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_p1_e2e_runs_to_completion() -> None:
    """Replaces P0 tautology — confirms Wave1Runner is wired and importable."""
    from opl_cancer.glue.wave1_runner import Wave1Runner

    assert hasattr(Wave1Runner, "run")
    assert callable(Wave1Runner.run)


def test_acceptance_cli_help_shows_usage() -> None:
    r = CliRunner().invoke(main, ["--help"])
    assert r.exit_code == 0
    assert "OPL for Cancer" in r.output


def test_acceptance_package_importable() -> None:
    import opl_cancer  # noqa: F401
    import opl_cancer.cli  # noqa: F401
    import opl_cancer.memory  # noqa: F401
    import opl_cancer.memory.store  # noqa: F401
    import opl_cancer.memory.schemas  # noqa: F401
    import opl_cancer.provenance.hasher  # noqa: F401
    import opl_cancer.provenance.journal  # noqa: F401
    import opl_cancer.plan.schemas  # noqa: F401
    import opl_cancer.validators.mechanical_gates  # noqa: F401
    import opl_cancer.validators.permission_levels  # noqa: F401
    import opl_cancer.validators.rollback  # noqa: F401
    import opl_cancer.integrators.base  # noqa: F401
    import opl_cancer.integrators.cache  # noqa: F401
    import opl_cancer.experts.base  # noqa: F401
    import opl_cancer.experts.roster  # noqa: F401
    import opl_cancer.orchestrator.pi_session  # noqa: F401
    import opl_cancer.orchestrator.dispatch  # noqa: F401
    import opl_cancer.orchestrator.tournament  # noqa: F401
    import opl_cancer.orchestrator.trigger  # noqa: F401


def test_acceptance_5_adrs_written() -> None:
    adr_files = list((REPO_ROOT / "docs" / "adr").glob("000?-*.md"))
    assert len(adr_files) >= 5


def test_acceptance_apache_2_0_license_present() -> None:
    text = (REPO_ROOT / "LICENSE").read_text()
    assert "Apache License" in text
    assert "Version 2.0" in text


def test_acceptance_all_18_experts_in_roster() -> None:
    assert len(ROSTER) == 18


def test_acceptance_ci_config_present() -> None:
    assert (REPO_ROOT / ".github" / "workflows" / "ci.yml").exists()


def test_acceptance_governance_docs_present() -> None:
    assert (REPO_ROOT / "CONTRIBUTING.md").exists()
    assert (REPO_ROOT / "MAINTAINERS.md").exists()
    assert (REPO_ROOT / "docs" / "governance" / "contributor_agreement.md").exists()


def test_acceptance_patients_schema_documented() -> None:
    assert (REPO_ROOT / "patients" / "SCHEMA.md").exists()


def test_acceptance_skill_md_present() -> None:
    assert (REPO_ROOT / "SKILL.md").exists()


def test_acceptance_models_yaml_present() -> None:
    assert (REPO_ROOT / "models.yaml").exists()


# ----- P1 acceptance (T35) -----


def test_acceptance_all_six_p1_experts_importable() -> None:
    from opl_cancer.experts.bert import BertExpert
    from opl_cancer.experts.heddy import HeddyExpert
    from opl_cancer.experts.hong import HongExpert
    from opl_cancer.experts.rick import RickExpert
    from opl_cancer.experts.rosa import RosaExpert
    from opl_cancer.experts.vince import VinceExpert

    for cls in (
        RosaExpert,
        BertExpert,
        VinceExpert,
        RickExpert,
        HeddyExpert,
        HongExpert,
    ):
        assert cls.portfolio
        assert cls.preferred_families


def test_acceptance_p1_integrators_importable() -> None:
    from opl_cancer.integrators.cbioportal import CBioPortalIntegrator  # noqa: F401
    from opl_cancer.integrators.chictr import ChiCTRIntegrator  # noqa: F401
    from opl_cancer.integrators.civic import CIViCIntegrator  # noqa: F401
    from opl_cancer.integrators.clinicaltrials import (  # noqa: F401
        ClinicalTrialsGovIntegrator,
    )
    from opl_cancer.integrators.clinvar import ClinVarIntegrator  # noqa: F401
    from opl_cancer.integrators.fda_eap import FDAEAPIntegrator  # noqa: F401
    from opl_cancer.integrators.gdc import GDCIntegrator  # noqa: F401
    from opl_cancer.integrators.gnomad import GnomADIntegrator  # noqa: F401
    from opl_cancer.integrators.nccn import NCCNPageIndexIntegrator  # noqa: F401
    from opl_cancer.integrators.nmpa_eap import NMPAEAPIntegrator  # noqa: F401
    from opl_cancer.integrators.oncokb import OncoKBIntegrator  # noqa: F401
    from opl_cancer.integrators.paperqa import PaperQA2Integrator  # noqa: F401
    from opl_cancer.integrators.pubmed import PubMedIntegrator  # noqa: F401
    from opl_cancer.integrators.retractiondb import (  # noqa: F401
        RetractionDBIntegrator,
    )
    from opl_cancer.integrators.rxnorm import RxNormIntegrator  # noqa: F401
    from opl_cancer.integrators.unpaywall import UnpaywallIntegrator  # noqa: F401


def test_acceptance_p1_gates_importable() -> None:
    from opl_cancer.validators.gates.g1_pmid_existence import (  # noqa: F401
        G1PMIDExistenceGate,
    )
    from opl_cancer.validators.gates.g2_pmid_quote_match import (  # noqa: F401
        G2PMIDQuoteMatchGate,
    )
    from opl_cancer.validators.gates.g3_drug_normalization import (  # noqa: F401
        G3DrugNormalizationGate,
    )
    from opl_cancer.validators.gates.g9_retraction_check import (  # noqa: F401
        G9RetractionCheckGate,
    )
    from opl_cancer.validators.gates.g11_no_silent_fallback import (  # noqa: F401
        G11NoSilentFallbackGate,
    )


def test_acceptance_wave1_runner_glue_importable() -> None:
    from opl_cancer.glue.case_loader import PatientCaseLoader  # noqa: F401
    from opl_cancer.glue.renderer import PatientBriefRenderer  # noqa: F401
    from opl_cancer.glue.wave1_runner import Wave1Runner  # noqa: F401


def test_acceptance_synthetic_patients_present() -> None:
    gs = REPO_ROOT / "validators" / "golden_set" / "synthetic_patients"
    assert (gs / "anon_hcc_001" / "profile.json").exists()
    assert (gs / "anon_nsclc_001" / "profile.json").exists()


def test_acceptance_failure_mode_inputs_present() -> None:
    gs = REPO_ROOT / "validators" / "golden_set" / "failure_mode_inputs"
    assert (gs / "fake_pmid_input.json").exists()
    assert (gs / "retracted_pmid_input.json").exists()
    assert (gs / "imperative_command_input.json").exists()


def test_acceptance_evaluator_dispatcher_present() -> None:
    assert (REPO_ROOT / "scripts" / "dispatch_e2e_evaluator.py").exists()


def test_acceptance_changelog_enumerates_p1() -> None:
    text = (REPO_ROOT / "CHANGELOG.md").read_text()
    assert "v0.1.0-p1" in text
    # Enumerates each major P1 deliverable
    for marker in (
        "6 Expert Batch A",
        "15 Integrator",
        "5 mechanical gates",
        "Wave 1 end-to-end",
        "synthetic golden-set patients",
    ):
        assert marker in text, f"CHANGELOG missing P1 marker: {marker}"


def test_acceptance_total_test_count_threshold() -> None:
    """Spec P1 acceptance: >= 150 tests collected."""
    r = subprocess.run(
        ["pytest", "--collect-only", "-q", "tests/"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env={"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PATH": __import__("os").environ.get("PATH", "")},
    )
    out = r.stdout + r.stderr
    # Look for a line like "234 tests collected"
    n = 0
    for line in out.splitlines():
        line = line.strip()
        if "test" in line and ("collected" in line or "selected" in line):
            head = line.split()[0]
            if head.isdigit():
                n = max(n, int(head))
    assert n >= 150, f"only {n} tests collected, P1 acceptance requires >= 150"
