"""Test GitHub Actions CI config presence + required steps."""
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_ci_yaml_exists() -> None:
    assert (REPO_ROOT / ".github" / "workflows" / "ci.yml").exists()


def test_ci_runs_pytest_ruff_mypy() -> None:
    cfg = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text())
    steps_text = yaml.dump(cfg)
    assert "pytest" in steps_text
    assert "ruff" in steps_text
    assert "mypy" in steps_text


def test_ci_matrix_includes_python_311() -> None:
    cfg = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text())
    matrix_text = yaml.dump(cfg.get("jobs", {}))
    assert "3.11" in matrix_text or "'3.11'" in matrix_text
