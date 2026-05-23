"""Top-level smoke test — package importable + CLI invokable."""
from click.testing import CliRunner

from opl_cancer import __version__
from opl_cancer.cli import main


def test_package_version_string() -> None:
    assert isinstance(__version__, str)
    assert __version__.count(".") >= 1


def test_cli_help_runs() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "OPL for Cancer" in result.output
