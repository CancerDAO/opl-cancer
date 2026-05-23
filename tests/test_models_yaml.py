"""Test models.yaml — production + reviewer model roster."""
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load() -> dict:
    return yaml.safe_load((REPO_ROOT / "models.yaml").read_text())


def test_models_yaml_exists() -> None:
    assert (REPO_ROOT / "models.yaml").exists()


def test_models_yaml_has_executor_and_reviewer_pools() -> None:
    cfg = _load()
    assert "executor_model" in cfg
    assert "reviewer_pool" in cfg
    assert isinstance(cfg["reviewer_pool"], list)


def test_reviewer_pool_excludes_executor_model() -> None:
    cfg = _load()
    assert cfg["executor_model"]["id"] not in [m["id"] for m in cfg["reviewer_pool"]]


def test_versions_are_locked() -> None:
    cfg = _load()
    assert cfg["executor_model"]["id"]
    assert "version_pinned" in cfg["executor_model"]
    assert cfg["executor_model"]["version_pinned"] is True
