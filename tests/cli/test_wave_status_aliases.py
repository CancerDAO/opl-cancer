"""v2.1 P0-#1: wave1-4 commands are clearly marked as state-check only."""
from __future__ import annotations

from click.testing import CliRunner

from opl_cancer.cli import main


def test_wave1_help_marks_it_state_check():
    runner = CliRunner()
    result = runner.invoke(main, ["wave1", "--help"])
    assert "state-check" in result.output.lower() or "does not execute" in result.output.lower()


def test_wave2_help_marks_it_state_check():
    runner = CliRunner()
    result = runner.invoke(main, ["wave2", "--help"])
    assert "state-check" in result.output.lower() or "does not execute" in result.output.lower()


def test_wave3_help_marks_it_state_check():
    runner = CliRunner()
    result = runner.invoke(main, ["wave3", "--help"])
    assert "state-check" in result.output.lower() or "does not execute" in result.output.lower()


def test_wave4_help_marks_it_state_check():
    runner = CliRunner()
    result = runner.invoke(main, ["wave4", "--help"])
    assert "state-check" in result.output.lower() or "does not execute" in result.output.lower()
