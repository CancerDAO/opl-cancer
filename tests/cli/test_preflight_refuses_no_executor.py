"""v2.1 P0-#2: preflight refuses patient runs when no Wave-3 executor is available."""
from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from opl_cancer.cli import main


def test_preflight_refuses_when_no_executor():
    """If both NativeAnalysisRunner.is_available() and docker daemon are missing,
    preflight exits non-zero with a clear message."""
    with patch("opl_cancer.cli.shutil.which") as which_mock, \
         patch("opl_cancer.cli.NativeAnalysisRunner") as native_mock:
        # Neither jupyter nor docker on PATH
        which_mock.return_value = None
        native_mock.return_value.is_available.return_value = False
        runner = CliRunner(env={"MINIMAX_API_KEY": "stub"})
        result = runner.invoke(main, ["preflight"])
        assert result.exit_code != 0
        # Output should include the wave-3-compute block message
        assert "wave 3" in result.output.lower() or "executor" in result.output.lower() \
            or "neither" in result.output.lower()
