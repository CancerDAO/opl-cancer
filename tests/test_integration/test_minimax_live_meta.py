"""Meta-tests for the live MiniMax integration suite.

These tests run unconditionally — they verify the scaffolding is correct
(skip when env absent, module imports cleanly) without making network calls.
"""
from __future__ import annotations

import importlib
import os
from pathlib import Path


def test_live_test_module_imports_cleanly() -> None:
    """tests/test_integration/test_minimax_live.py imports without error."""
    mod = importlib.import_module("tests.test_integration.test_minimax_live")
    assert hasattr(mod, "test_minimax_live_simple_json_call")
    assert hasattr(mod, "test_minimax_live_max_tokens_ceiling_honoured")
    assert hasattr(mod, "test_minimax_live_errcode_2056_raised_if_quota")


def test_live_marker_declared_in_pyproject() -> None:
    """pyproject.toml declares the `live` marker (so pytest -m live works)."""
    py = (Path(__file__).resolve().parents[2] / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert "live:" in py, "pyproject missing live marker registration"


def test_verify_script_present_and_importable() -> None:
    """scripts/verify_minimax_setup.py exists and is syntactically importable."""
    p = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "verify_minimax_setup.py"
    )
    assert p.exists()
    src = p.read_text(encoding="utf-8")
    compile(src, str(p), "exec")  # raises SyntaxError if invalid


def test_live_tests_skip_when_env_not_set() -> None:
    """Without MINIMAX_API_KEY env, pytestmark must include skipif."""
    assert "MINIMAX_API_KEY" in os.environ or True  # tautological: skip is conditional
    mod = importlib.import_module("tests.test_integration.test_minimax_live")
    marks = getattr(mod, "pytestmark", [])
    # pytestmark is a list with skipif + live; just sanity-check structure
    assert any("skipif" in repr(m).lower() for m in marks)
    assert any("live" in repr(m).lower() for m in marks)
