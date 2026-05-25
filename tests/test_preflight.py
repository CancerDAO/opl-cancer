"""Preflight tests — v1.5 P0-3 + P0-10.

Verifies G13 reviewer-distinct hard-fail and Wave 3 non-skippable gating.
"""
from __future__ import annotations

import json
import shutil

import pytest
from click.testing import CliRunner

from opl_cancer.cli import main


def _invoke_preflight(*args: str, env: dict[str, str] | None = None):
    runner = CliRunner()
    return runner.invoke(main, ["preflight", "--json", *args], env=env or {})


@pytest.fixture
def clean_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip all LLM env vars so G13 paths fire deterministically."""
    for k in (
        "ANTHROPIC_API_KEY",
        "MINIMAX_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
    ):
        monkeypatch.delenv(k, raising=False)


def test_preflight_blocks_when_no_reviewer_key(
    clean_llm_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G13 hard-fail: missing reviewer pool keys → exit_code != 0."""
    # Make sure Wave 3 compute is OK so the only blocker is G13.
    monkeypatch.setenv("PATH", shutil.which("python3").rsplit("/", 1)[0])
    r = _invoke_preflight()
    payload = json.loads(r.output.split("\n", 0)[0] if r.output.startswith("{") else r.output)
    assert payload["ok"] is False
    blocks = [i for i in payload["issues"] if "[block]" in i and "G13" in i]
    assert blocks, f"expected G13 block message, got issues={payload['issues']}"
    assert r.exit_code != 0


def test_preflight_allow_single_model_bypasses_g13(
    clean_llm_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--allow-single-model bypass: warn instead of block."""
    r = _invoke_preflight("--allow-single-model")
    payload = json.loads(r.output)
    assert payload["checks"]["llm"]["g13_reviewer_distinct_ok"] is True
    assert payload["checks"]["llm"]["allow_single_model_override"] is True
    warns = [i for i in payload["issues"] if "[warn]" in i and "single-model" in i]
    assert warns, f"expected warn about single-model bypass, got {payload['issues']}"


def test_preflight_minimax_key_satisfies_g13(
    clean_llm_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-cp-fake-for-test")
    r = _invoke_preflight()
    payload = json.loads(r.output)
    assert payload["checks"]["llm"]["g13_reviewer_distinct_ok"] is True
    assert "minimax-m2-7" in payload["checks"]["llm"]["reviewer_pool_keys_present"]
    blocks = [i for i in payload["issues"] if "G13" in i and "[block]" in i]
    assert not blocks


def test_preflight_reports_wave3_compute_field(
    clean_llm_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """wave3_compute replaces docker; key always present."""
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-cp-fake")
    r = _invoke_preflight("--allow-single-model")
    payload = json.loads(r.output)
    w3 = payload["checks"].get("wave3_compute")
    assert w3 is not None
    assert "native_runner_ready" in w3
    assert "bixbench_runner_ready" in w3
    assert "default_runner" in w3


def test_preflight_blocks_when_neither_native_nor_bixbench(
    clean_llm_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If neither jupyter nor docker is on PATH, Wave 3 cannot proceed."""
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-cp-fake")
    monkeypatch.setattr(
        shutil, "which", lambda binary: None  # type: ignore[arg-type]
    )
    r = _invoke_preflight()
    payload = json.loads(r.output)
    w3 = payload["checks"]["wave3_compute"]
    assert w3["ok"] is False
    assert w3["native_runner_ready"] is False
    assert w3["bixbench_runner_ready"] is False
    assert payload["ok"] is False
    assert any("Wave 3 compute unavailable" in i for i in payload["issues"])


def test_preflight_passes_when_jupyter_only(
    clean_llm_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Native-only path is sufficient — Docker not required."""
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-cp-fake")

    def which_native_only(binary: str) -> str | None:
        if binary == "jupyter":
            return "/usr/local/bin/jupyter"
        if binary == "docker":
            return None
        return shutil.which.__wrapped__(binary) if hasattr(shutil.which, "__wrapped__") else "/usr/bin/x"

    monkeypatch.setattr(shutil, "which", which_native_only)
    r = _invoke_preflight()
    payload = json.loads(r.output)
    w3 = payload["checks"]["wave3_compute"]
    assert w3["native_runner_ready"] is True
    assert w3["bixbench_runner_ready"] is False
    assert w3["default_runner"] == "native"
    assert w3["ok"] is True
