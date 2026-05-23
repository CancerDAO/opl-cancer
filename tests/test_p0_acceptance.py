"""P0 acceptance test — verifies all stated P0 acceptance criteria met."""
from pathlib import Path

from click.testing import CliRunner

from opl_cancer.cli import main
from opl_cancer.experts.roster import ROSTER

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_acceptance_pytest_runs() -> None:
    assert True


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
