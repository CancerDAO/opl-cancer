"""v2 paradigm tests — patient brief renderer surfaces a dedicated World-Unknown section."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from opl_cancer.glue.renderer import PatientBriefRenderer


FIXTURE = json.loads(
    Path("tests/fixtures/v2/wave2_output_with_novelty.json").read_text(encoding="utf-8")
)


def _render(fmt: str) -> str:
    renderer = PatientBriefRenderer()
    ctx = {
        "language": "zh",
        "patient_code": "TEST-001",
        "run_id": "test-v2-fixture",
        "created_at": "2026-05-26T00:00:00Z",
        "sid_summary": "test summary",
        "experts": [],
        "risk_cards": [],
        "world_unknown_candidates": [
            h
            for h in FIXTURE["top_k_hypotheses"]
            if h["claim_layer"] == "speculative"
        ],
    }
    suffix = ".html" if fmt == "html" else ".md"
    with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False) as f:
        out = Path(f.name)
    if fmt == "html":
        renderer.render_html(ctx, out)
    else:
        renderer.render_md(ctx, out)
    return out.read_text(encoding="utf-8")


def test_html_renders_world_unknown_section():
    html = _render("html")
    assert "World-Unknown" in html
    assert "KRAS-SHP2" in html
    assert "DiffDock" in html
    assert "testability" in html.lower()


def test_md_renders_world_unknown_section():
    md = _render("md")
    assert "World-Unknown" in md
    assert "KRAS-SHP2" in md
    assert "DiffDock" in md


def test_world_unknown_section_renders_kg_edge_anchors():
    html = _render("html")
    assert "PrimeKG" in html
    assert "DepMap" in html


def test_world_unknown_section_framed_as_research_direction():
    html = _render("html")
    # Must explicitly frame as research direction, NOT as recommendation
    assert "未发表" in html
    assert "未验证" in html
    assert "research direction" in html.lower()
    assert "not a treatment recommendation" in html.lower()


def test_world_unknown_section_absent_when_no_candidates():
    """If the run produced 0 [S] hypotheses, the section should not render."""
    renderer = PatientBriefRenderer()
    ctx = {
        "language": "zh",
        "patient_code": "TEST-002",
        "run_id": "test-no-novelty",
        "created_at": "2026-05-26T00:00:00Z",
        "sid_summary": "test",
        "experts": [],
        "risk_cards": [],
        "world_unknown_candidates": [],
    }
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        out = Path(f.name)
    renderer.render_html(ctx, out)
    html = out.read_text(encoding="utf-8")
    assert "World-Unknown" not in html
