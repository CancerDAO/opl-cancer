"""Test the independent-evaluator dispatcher (T34)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from dispatch_e2e_evaluator import (  # noqa: E402  type: ignore[import-not-found]
    EVAL_DIMS,
    VERDICT_SCHEMA,
    build_evaluator_prompt,
    write_artifacts,
)


def test_prompt_includes_all_six_dimensions() -> None:
    prompt = build_evaluator_prompt("<html>test</html>", "anon_x")
    for dim in EVAL_DIMS:
        assert dim in prompt


def test_prompt_states_third_party_lens() -> None:
    prompt = build_evaluator_prompt("<html>x</html>", "anon_p")
    assert "INDEPENDENT" in prompt
    assert "do NOT know" in prompt


def test_prompt_embeds_patient_code() -> None:
    prompt = build_evaluator_prompt("<html>x</html>", "anon_hcc_001")
    assert "anon_hcc_001" in prompt


def test_schema_lists_all_six_dimensions() -> None:
    props = VERDICT_SCHEMA["properties"]  # type: ignore[index]
    dims_props = props["dimensions"]["properties"]  # type: ignore[index]
    for dim in EVAL_DIMS:
        assert dim in dims_props


def test_write_artifacts_creates_prompt_and_schema(tmp_path: Path) -> None:
    brief_dir = tmp_path / "run"
    delivery = brief_dir / "delivery"
    delivery.mkdir(parents=True)
    (delivery / "patient_brief.html").write_text("<html>brief content</html>")

    prompt_path, schema_path = write_artifacts(brief_dir, "anon_test")

    assert prompt_path.exists()
    assert schema_path.exists()
    assert "anon_test" in prompt_path.read_text()
    schema = json.loads(schema_path.read_text())
    assert "dimensions" in schema["properties"]


def test_write_artifacts_raises_when_brief_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        write_artifacts(tmp_path / "nonexistent", "anon_x")
