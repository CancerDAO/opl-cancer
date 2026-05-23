"""Test PromptTemplate — Jinja2 load from prompts/ tree + variable injection."""
from __future__ import annotations

from pathlib import Path

import pytest

from opl_cancer.llm.prompts import PromptTemplate, find_prompts_root


def test_find_prompts_root_returns_repo_prompts() -> None:
    # Use the repo's actual prompts/ directory
    root = find_prompts_root()
    assert root.exists()
    assert root.name == "prompts"


def test_prompt_render_variables(tmp_path: Path) -> None:
    (tmp_path / "greet.md").write_text("Hello {{ name }}, layer={{ layer }}.")
    pt = PromptTemplate.load(tmp_path / "greet.md", version="greet@v0.1.0")
    out = pt.render(name="Sid", layer="established")
    assert out == "Hello Sid, layer=established."


def test_prompt_version_string(tmp_path: Path) -> None:
    (tmp_path / "x.md").write_text("body")
    pt = PromptTemplate.load(tmp_path / "x.md", version="x@v0.1.0")
    assert pt.version == "x@v0.1.0"


def test_prompt_missing_var_raises(tmp_path: Path) -> None:
    (tmp_path / "x.md").write_text("Hi {{ who }}")
    pt = PromptTemplate.load(tmp_path / "x.md", version="x@v0.1.0")
    with pytest.raises(Exception):
        pt.render()  # 'who' not provided
