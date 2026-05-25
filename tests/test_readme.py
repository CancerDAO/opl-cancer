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
        "One Person Lab",  # v1.5.3 paradigm framing
        "AI 科研团队",  # the v1.5.3 plain-language framing
        "Apache-2.0",
        # Mandatory top-level sections (v1.5.3 README)
        "什么是 OPL",
        "遇见您的实验室",
        "实验室在做什么",
        "安装",
        "使用",
        "运行示例",
        "设计哲学",
        "技术实现",
        "贡献",
        "免责声明",
        # Named roles + paradigm framing
        "Sid",
        "Henry",
        "founder mode against cancer",
        # OPC → OPL paradigm explicitly explained
        "One Person Company",
    ]
    for r in required:
        assert r in text, f"README missing {r!r}"


def test_readme_introduces_all_18_named_experts() -> None:
    """README must surface all 18 named scientists by name so the user
    can see what the team looks like (per v1.5.3 user feedback)."""
    text = (REPO_ROOT / "README.md").read_text()
    for name in (
        "Rosa", "Bert", "Vince", "Rick", "Heddy", "Mary", "Aviv", "Tyler",
        "Iain", "Ted", "Riad", "Jen", "Kieren", "Mark", "Hong", "Frances",
        "Dennis", "Steve",
    ):
        assert name in text, f"README missing expert name {name!r}"


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


def test_readme_does_not_use_real_case_codes() -> None:
    """README must not contain a real-format patient code (PT- prefix
    followed by mixed letters+digits resembling an institutional code).
    Pseudonyms like PT-EXAMPLE-A are fine; a real-looking PT-XX12345678
    is not. Runtime PII enforcement is G27
    (validators/gates/g27_privacy_scrub.py); this is the doc-layer
    sanity check.

    Note: we do NOT enumerate any historical leak token here — listing
    it as a string literal would re-introduce it into source.
    """
    import re

    text = (REPO_ROOT / "README.md").read_text()
    # A "real-looking" code matches PT-<letters><digits...> with enough
    # entropy to look institutional (e.g. PT-XX12345678). EXAMPLE codes
    # are explicitly allowed.
    candidates = re.findall(r"\bPT-[A-Z]{0,4}\d{4,}[A-Z0-9]*\b", text)
    real_looking = [c for c in candidates if "EXAMPLE" not in c]
    assert not real_looking, f"real-looking patient codes in README: {real_looking}"


def test_disclaimer_has_v1_release_and_emergency_notice() -> None:
    """Iter 16: DISCLAIMER carries v1.x scope + emergency-number guidance + jurisdictional notice."""
    text = (REPO_ROOT / "DISCLAIMER.md").read_text()
    assert "v1.x" in text
    assert "120" in text and "911" in text  # CN + US emergency numbers
    assert "WITHOUT WARRANTY" in text
    assert "Jurisdictional notice" in text
