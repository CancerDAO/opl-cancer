"""README contract tests — v2.5.1 public-release format.

v2.5.1 rewrites the README to the Apple-quality concise / world-class
open-source standard requested in the v2.5.1 hotfix spec:

* Hero line + 1-paragraph pitch
* Status badge row
* Honest "what this DOES / DOES NOT do" box
* 30-second quickstart with expected output snippets
* 5-Wave pipeline + RFC link
* Real example excerpt with PMID anchors + tier labels + drug-class redaction
* Why N=1 is hard (compositional intake + conformal honesty)
* Architecture diagram with compositional-layers callout
* Contributing + 6-milestone roadmap + 4 discipline rules
* Ethics & safety with founder-mode philosophy + emergency numbers
* Citation BibTeX
* Acknowledgements

These tests assert the v2.5.1 structural contract without locking the
prose. They replace the v1.5.3 contract which was tied to the old
all-Chinese 9-section layout.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_readme_has_required_sections() -> None:
    text = (REPO_ROOT / "README.md").read_text()
    required = [
        # Branding + license + framing
        "OPL for Cancer",
        "One Person Lab",
        "Apache-2.0",
        "research preview",
        # v2.5.1 mandatory top-level sections
        "What is this",
        "What this is / What this is not",
        "30-second quickstart",
        "The 5-Wave pipeline",
        "Example output",
        "Why N=1 is hard",
        "Architecture",
        "Contributing",
        "Ethics & safety",
        "Citation",
        "Acknowledgements",
        # Named roles + paradigm framing
        "Sid",
        "Henry",
        "founder mode against cancer",
        # OPC → OPL paradigm explicitly explained (preserved across rewrites)
        "OPC (One Person Company)",
        # Honest scope — patient as decision authority
        "patient is the sole decision authority"
        if "patient is the sole decision authority" in text
        else "Patient is sole decision authority",
        # Disclaimer link (replaces inline 免责声明 section)
        "DISCLAIMER.md",
    ]
    for r in required:
        assert r in text, f"README missing {r!r}"


def test_readme_introduces_all_20_named_experts() -> None:
    """README must surface all 20 named scientists by name (v1 18 + v2 Maya + Julius)."""
    text = (REPO_ROOT / "README.md").read_text()
    for name in (
        "Rosa", "Bert", "Vince", "Rick", "Heddy", "Mary", "Aviv", "Tyler",
        "Iain", "Ted", "Riad", "Jen", "Kieren", "Mark", "Hong", "Frances",
        "Dennis", "Steve",
        # v2.0.0 additions
        "Maya", "Julius",
    ):
        assert name in text, f"README missing expert name {name!r}"


def test_readme_has_install_command() -> None:
    """A public README must show install instructions: both `pip install -e .`
    for the CLI workflow AND the `npx skills add` command for the
    skill-installation workflow."""
    text = (REPO_ROOT / "README.md").read_text()
    assert "pip install" in text, "README must show pip install"
    assert "npx skills add CancerDAO/opl-cancer" in text, (
        "README must show npx skills add CancerDAO/opl-cancer"
    )


def test_readme_lists_five_stage_lifecycle() -> None:
    """The 5 plain-language stage labels surface in BOTH language READMEs:
    English in README.md, Chinese (the actual patient-facing UI strings) in
    README.zh-CN.md. v2.6.0 split the mixed-language README into English-default
    + a parallel Chinese version."""
    en = (REPO_ROOT / "README.md").read_text()
    for stage in ("Prepare", "Find-options", "Check-data", "Review", "Write-up"):
        assert stage in en, f"English README missing stage label {stage!r}"
    zh = (REPO_ROOT / "README.zh-CN.md").read_text()
    for stage in ("准备", "想办法", "查数据", "审核", "写报告"):
        assert stage in zh, f"Chinese README missing stage label {stage!r}"


def test_readme_includes_at_least_three_dialog_scenarios() -> None:
    """v1.5.3 cancer-buddy-style scenarios are preserved as a `## Run scenarios`
    block with ≥3 concrete examples — English `### Scenario` in README.md, Chinese
    `### 场景` in README.zh-CN.md."""
    en = (REPO_ROOT / "README.md").read_text()
    assert en.count("### Scenario") >= 3, (
        f"expected ≥3 English scenario blocks, got {en.count('### Scenario')}"
    )
    zh = (REPO_ROOT / "README.zh-CN.md").read_text()
    assert zh.count("### 场景") >= 3, (
        f"expected ≥3 Chinese scenario blocks, got {zh.count('### 场景')}"
    )


def test_readme_is_english_default_with_chinese_companion() -> None:
    """v2.6.0: README.md is English-default and must not mix in the old Chinese
    prose blocks; a parallel README.zh-CN.md exists and the two cross-link."""
    en = (REPO_ROOT / "README.md").read_text()
    zh_path = REPO_ROOT / "README.zh-CN.md"
    assert zh_path.exists(), "README.zh-CN.md (Chinese companion) must exist"
    zh = zh_path.read_text()
    # Cross-links both directions.
    assert "README.zh-CN.md" in en, "English README must link to the Chinese version"
    assert "README.md" in zh, "Chinese README must link back to the English version"
    # English README must not carry the old mixed-in Chinese scenario/label prose.
    assert "### 场景" not in en, "README.md must not contain Chinese scenario headers (use README.zh-CN.md)"
    assert "准备 / 想办法" not in en, "README.md must not contain the Chinese stage-label line"


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
    candidates = re.findall(r"\bPT-[A-Z]{0,4}\d{4,}[A-Z0-9]*\b", text)
    real_looking = [c for c in candidates if "EXAMPLE" not in c]
    assert not real_looking, f"real-looking patient codes in README: {real_looking}"


def test_readme_carries_v251_honesty_signals() -> None:
    """v2.5.1 BLOCKER fixes surface in the README: refuses-to-ship without
    upstream evidence, real Henry audit, drug-class redaction."""
    text = (REPO_ROOT / "README.md").read_text()
    assert "upstream_artifacts_missing" in text, (
        "README must show the v2.5.1 B5 structured-failure example"
    )
    assert "henry_real_audit" in text, "README must show v2.5.1 B1 audit field"
    assert "drug-class" in text or "drug class" in text.lower(), (
        "README must call out drug-class redaction"
    )


def test_readme_links_to_rfc_and_adr_ledger() -> None:
    """v2.5 compositional foundation should be explicitly linked from README."""
    text = (REPO_ROOT / "README.md").read_text()
    assert "docs/rfc/0001-compositional-paradigm.md" in text
    assert "docs/adr" in text


def test_disclaimer_has_v1_release_and_emergency_notice() -> None:
    """Iter 16 (v2.9: scope updated v1.x → v2.x): DISCLAIMER carries the current release scope + emergency-number guidance + jurisdictional notice."""
    text = (REPO_ROOT / "DISCLAIMER.md").read_text()
    assert "v2.x" in text
    assert "120" in text and "911" in text  # CN + US emergency numbers
    assert "WITHOUT WARRANTY" in text
    assert "Jurisdictional notice" in text
