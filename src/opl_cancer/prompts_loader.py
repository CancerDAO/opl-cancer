"""Jinja2-backed prompt template loader (pure file I/O — NO LLM calls).

Moved out of the deleted ``opl_cancer.llm`` package during the harness split
(docs/iteration/HARNESS_SPLIT_PRD.md). The patient-delivery path (experts/,
glue/) only needs to *load* prompt files from the ``prompts/`` tree and render
them with Jinja2 — it never calls an LLM internally. This module therefore
carries the deterministic file-loading helper with zero provider/network deps.

Prompt files live in prompts/<scope>/<name>.md (scope = pi/experts/tasks/reviewer/auditor).
Each template tagged with a semver-ish version string (recorded in produced_by.prompt_version).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, StrictUndefined


def find_prompts_root() -> Path:
    """Walk up from this file until we find a sibling 'prompts/' directory."""
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / "prompts"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("prompts/ directory not found in any parent")


@dataclass
class PromptVersion:
    name: str       # e.g. "molecular_ngs_interpretation"
    semver: str     # e.g. "v0.1.0"

    def __str__(self) -> str:
        return f"{self.name}@{self.semver}"


class PromptTemplate:
    """Single Jinja2 template + version tag (recorded in provenance)."""

    _env = Environment(
        undefined=StrictUndefined,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    def __init__(self, source: str, version: str, path: Path | None = None) -> None:
        self.source = source
        self.version = version
        self.path = path
        self._template = self._env.from_string(source)

    @classmethod
    def load(cls, path: Path, version: str) -> PromptTemplate:
        return cls(
            source=Path(path).read_text(encoding="utf-8"),
            version=version,
            path=Path(path),
        )

    def render(self, **vars: object) -> str:
        return self._template.render(**vars)
