"""Test CLI subcommands skeleton."""
from pathlib import Path

from click.testing import CliRunner

from opl_cancer.cli import main


def test_cli_status_runs() -> None:
    r = CliRunner().invoke(main, ["status"])
    assert r.exit_code == 0
    # v1.2.0 audit-fix: dropped the P0 Skeleton fiction; status now reflects shipped capabilities.
    assert "OPL for Cancer" in r.output
    assert "v1.2.0" in r.output
    assert "Experts active: 18" in r.output


def test_cli_init_patient_runs(tmp_path: Path) -> None:
    r = CliRunner().invoke(
        main, ["init-patient", "anon_test", "--root", str(tmp_path)]
    )
    assert r.exit_code == 0
    assert (tmp_path / "anon_test" / "memory").exists()
    assert (tmp_path / "anon_test" / "pi_session").exists()
    assert (tmp_path / "anon_test" / "inbox").exists()
    assert (tmp_path / "anon_test" / "triggers").exists()


def test_cli_list_experts_runs() -> None:
    r = CliRunner().invoke(main, ["list-experts"])
    assert r.exit_code == 0
    for name in ("sid", "rosa", "bert", "vince"):
        assert name in r.output
