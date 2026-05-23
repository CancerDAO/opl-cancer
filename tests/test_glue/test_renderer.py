"""Test PatientBriefRenderer — Wave 1 outputs → HTML + Markdown."""
from pathlib import Path
from typing import Any

from opl_cancer.glue.renderer import PatientBriefRenderer


def _ctx() -> dict[str, Any]:
    return {
        "patient_code": "anon_001",
        "run_id": "run_test",
        "created_at": "2026-05-24T00:00:00Z",
        "language": "zh-CN",
        "sid_summary": "Team identified actionable EGFR L858R.",
        "risk_cards": [
            {"level": 2, "message": "Off-label combination considered.", "requires_ack": False},
        ],
        "experts": [
            {
                "name": "bert",
                "role": "Geneticist",
                "claims": [
                    {
                        "layer": "established",
                        "text": "EGFR L858R is actionable.",
                        "evidence": [
                            {"type": "pmid", "id": "31157963", "quote": "Osimertinib 1L OS benefit."},
                        ],
                        "reviewer_challenges": [],
                        "provenance_hash": "sha256:" + "a" * 64,
                    },
                ],
            },
        ],
    }


def test_renderer_writes_html_and_md(tmp_path: Path) -> None:
    r = PatientBriefRenderer()
    out_html = tmp_path / "brief.html"
    out_md = tmp_path / "brief.md"
    r.render_html(_ctx(), out_html)
    r.render_md(_ctx(), out_md)
    assert out_html.exists() and "EGFR L858R" in out_html.read_text(encoding="utf-8")
    assert out_md.exists() and "PMID:31157963" in out_md.read_text(encoding="utf-8")


def test_renderer_includes_risk_card_at_top(tmp_path: Path) -> None:
    r = PatientBriefRenderer()
    out = tmp_path / "brief.html"
    r.render_html(_ctx(), out)
    text = out.read_text(encoding="utf-8")
    assert text.index("Risk Disclosure") < text.index("Summary"), "risk card must precede summary"


def test_renderer_includes_three_tier_styling(tmp_path: Path) -> None:
    r = PatientBriefRenderer()
    out = tmp_path / "brief.html"
    r.render_html(_ctx(), out)
    text = out.read_text(encoding="utf-8")
    assert "tier established" in text
    assert ".speculative" in text
    assert ".exploratory" in text


def test_renderer_includes_pmid_link(tmp_path: Path) -> None:
    r = PatientBriefRenderer()
    out = tmp_path / "brief.html"
    r.render_html(_ctx(), out)
    text = out.read_text(encoding="utf-8")
    assert "pubmed.ncbi.nlm.nih.gov/31157963" in text


def test_renderer_includes_provenance_hash(tmp_path: Path) -> None:
    r = PatientBriefRenderer()
    out_html = tmp_path / "brief.html"
    out_md = tmp_path / "brief.md"
    r.render_html(_ctx(), out_html)
    r.render_md(_ctx(), out_md)
    expected_hash = "sha256:" + "a" * 64
    assert expected_hash in out_html.read_text(encoding="utf-8")
    assert expected_hash in out_md.read_text(encoding="utf-8")


def test_renderer_includes_reviewer_challenges(tmp_path: Path) -> None:
    ctx = _ctx()
    ctx["experts"][0]["claims"][0]["reviewer_challenges"] = [
        "PMID 31157963 quote does not appear in abstract",
        "Brand 'Tagrisso' should be INN osimertinib",
    ]
    r = PatientBriefRenderer()
    out = tmp_path / "brief.html"
    r.render_html(ctx, out)
    text = out.read_text(encoding="utf-8")
    assert "Reviewer challenges" in text
    assert "Tagrisso" in text


def test_renderer_creates_parent_dirs(tmp_path: Path) -> None:
    r = PatientBriefRenderer()
    nested = tmp_path / "deeply" / "nested" / "out" / "brief.html"
    r.render_html(_ctx(), nested)
    assert nested.exists()
