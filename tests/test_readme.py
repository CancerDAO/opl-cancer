"""README contract tests — v1.5.3 public-release format.

The v1.5.3 README was rewritten following the cancer-buddy-skill format
(plain-language opening, 5-step lifecycle, scenario examples, design
philosophy). These tests assert the structural contract — the sections
a public-facing README must carry — without locking the prose.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_readme_has_required_sections() -> None:
    text = (REPO_ROOT / "README.md").read_text()
    required = [
        # Branding + license + framing
        "OPL for Cancer",
        "AI 科研团队",  # the v1.5.3 plain-language framing
        "Apache-2.0",
        # Mandatory top-level sections
        "团队能做什么",
        "5 步流程",
        "安装",
        "使用",
        "运行示例",
        "设计哲学",
        "技术实现",
        "贡献",
        "免责声明",
        # Named roles still surfaced (just translated for lay audience)
        "Sid",
        "Henry",
    ]
    for r in required:
        assert r in text, f"README missing {r!r}"


def test_readme_has_install_command() -> None:
    """A public README must show the npx install command."""
    text = (REPO_ROOT / "README.md").read_text()
    assert "npx skills add CancerDAO/opl-cancer-skill" in text


def test_readme_lists_five_stage_lifecycle() -> None:
    """The 5 plain-language stage labels (v1.5.1 progress reporter) are
    the public-facing surface of the run lifecycle."""
    text = (REPO_ROOT / "README.md").read_text()
    for stage in ("准备", "想办法", "查数据", "审核", "写报告"):
        assert stage in text, f"README missing stage label {stage!r}"


def test_readme_includes_at_least_three_dialog_scenarios() -> None:
    """v1.5.3 follows cancer-buddy format: at least 3 concrete dialog
    examples so a reader can see what a run looks like."""
    text = (REPO_ROOT / "README.md").read_text()
    # Three "场景X:" headers per the format
    n_scenarios = text.count("### 场景")
    assert n_scenarios >= 3, f"expected ≥3 scenario blocks, got {n_scenarios}"


def test_readme_includes_emergency_routing() -> None:
    """Public-facing README must visibly route emergencies to local
    crisis numbers (per founder-mode safety floor)."""
    text = (REPO_ROOT / "README.md").read_text()
    assert "120" in text
    assert "911" in text


def test_readme_uses_pseudonym_for_case_studies() -> None:
    """README must reference case studies via pseudonymized identifiers
    (e.g. PT-EXAMPLE-A) only — never a real-format identifier. Runtime
    PII enforcement is G27 (validators/gates/g27_privacy_scrub.py);
    this is the doc-layer sanity check."""
    text = (REPO_ROOT / "README.md").read_text()
    # If a case study is referenced, the pseudonym form must be used.
    if "case study" in text.lower() or "案例" in text:
        # Either no specific case study identifier is named, or the
        # pseudonym pattern is used. We do NOT enumerate the historical
        # forbidden tokens in this file — listing them would re-leak.
        # G27 enforces at runtime; we just confirm the pseudonym
        # convention is visible.
        assert "PT-EXAMPLE" in text or "<patient_code>" in text or "patient_code" in text, (
            "case study referenced without pseudonym convention"
        )


def test_disclaimer_has_v1_release_and_emergency_notice() -> None:
    """Iter 16: DISCLAIMER carries v1.x scope + emergency-number guidance + jurisdictional notice."""
    text = (REPO_ROOT / "DISCLAIMER.md").read_text()
    assert "v1.x" in text
    assert "120" in text and "911" in text  # CN + US emergency numbers
    assert "WITHOUT WARRANTY" in text
    assert "Jurisdictional notice" in text
