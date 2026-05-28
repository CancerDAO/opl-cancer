"""v2.1 P0-#1+#2: `opl run --wave 3 --mode native` invokes NativeAnalysisRunner."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from opl_cancer.cli import main


def test_opl_run_wave3_native_invokes_runner(tmp_path):
    """opl run --wave 3 --mode native must call NativeAnalysisRunner.run_notebook."""
    patient_dir = tmp_path / "patient"
    run_dir = patient_dir / "triggers" / "test_run"
    (run_dir / "tasks").mkdir(parents=True)
    (run_dir / "plan.json").write_text('{"tasks":[]}')

    with patch("opl_cancer.cli.NativeAnalysisRunner") as MockRunner:
        instance = MockRunner.return_value
        instance.is_available.return_value = True
        # run_notebook returns a BixbenchRunResult-like object with to_dict
        rr = MagicMock()
        rr.to_dict.return_value = {"status": "ok", "mode": "native-test"}
        rr.mode = "native-test"
        instance.run_notebook = MagicMock(return_value=rr)

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "run",
                "--wave",
                "3",
                "--patient-dir",
                str(patient_dir),
                "--run-id",
                "test_run",
                "--mode",
                "native",
            ],
        )
        assert result.exit_code == 0, result.output
        instance.run_notebook.assert_called()
