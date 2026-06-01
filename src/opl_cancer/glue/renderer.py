"""Patient brief HTML + Markdown renderer. Spec §4 Wave 5.

Wave 1 outputs (per-claim {layer, text, evidence, reviewer_challenges,
provenance_hash}) → ``patient_brief.html`` + ``patient_brief.md`` via
Jinja2 templates at ``prompts/delivery/patient_brief.{html,md}.j2``.

Each claim renders with a three-tier badge (established/exploratory/
speculative), PMID hyperlinks where ``evidence.type == "pmid"``, the
canonical SHA-256 provenance hash, and any reviewer-challenge list.
L3-L4 risks render as a red-bordered ``risk-card`` block placed BEFORE
the Summary section (acknowledgment requirement preserved per
:class:`opl_cancer.validators.permission_levels` semantics).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from opl_cancer.prompts_loader import PromptTemplate, find_prompts_root


class PatientBriefRenderer:
    def __init__(self) -> None:
        root = find_prompts_root()
        self.html_tpl = PromptTemplate.load(
            root / "delivery" / "patient_brief.html.j2",
            version="patient_brief_html@v0.1.0",
        )
        self.md_tpl = PromptTemplate.load(
            root / "delivery" / "patient_brief.md.j2",
            version="patient_brief_md@v0.1.0",
        )

    def render_html(self, context: dict[str, Any], out_path: Path) -> None:
        text = self.html_tpl.render(**context)
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(text, encoding="utf-8")

    def render_md(self, context: dict[str, Any], out_path: Path) -> None:
        text = self.md_tpl.render(**context)
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(text, encoding="utf-8")
