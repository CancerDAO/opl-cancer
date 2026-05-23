"""P6 acceptance — v1.0.0 release gates.

Covers:
- T1 multi-case E2E expansion (4 cancer types parametrised — sibling test
  ``test_wave1_e2e.py::test_wave1_e2e_two_patients`` enumerates them; we
  assert the parametrisation is wider than P5's 2-patient baseline.)
- T3 NOTICE + DISCLAIMER present + non-empty + minimum content
- T4 ``tools/sign_contributor_agreement.py`` importable + dry-run signs
- T5 ``docs/landing/founder_mode_against_cancer.md`` present + non-empty
- T6 pyproject version == 1.0.0
- 18 experts roster intact
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# T3 — Legal artifacts
# ---------------------------------------------------------------------------


def test_notice_present_and_attributes_third_parties() -> None:
    notice = REPO_ROOT / "NOTICE"
    assert notice.exists(), "NOTICE missing"
    txt = notice.read_text(encoding="utf-8")
    assert "Apache" in txt
    # Acknowledge model providers used by spec
    assert "Anthropic" in txt or "Claude" in txt
    assert "MiniMax" in txt
    # Acknowledge open data sources we reference
    assert "PubMed" in txt
    assert "ClinicalTrials.gov" in txt


def test_disclaimer_present_and_explicit_boundaries() -> None:
    disc = REPO_ROOT / "DISCLAIMER.md"
    assert disc.exists(), "DISCLAIMER.md missing"
    txt = disc.read_text(encoding="utf-8")
    # spec §17.6 — explicit boundaries
    assert "not a substitute" in txt.lower() or "not a doctor" in txt.lower()
    assert "not clinical decision support" in txt.lower()
    # patient decision authority
    assert "sole decision" in txt.lower() or "patient" in txt.lower()
    # safety pathway
    assert "safety@cancerdao.org" in txt or "issues" in txt.lower()


# ---------------------------------------------------------------------------
# T4 — CONTRIBUTOR_AGREEMENT signing tool
# ---------------------------------------------------------------------------


def _load_sign_tool() -> object:
    path = REPO_ROOT / "tools" / "sign_contributor_agreement.py"
    spec = importlib.util.spec_from_file_location("sign_contrib", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["sign_contrib"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_sign_contributor_agreement_module_importable() -> None:
    mod = _load_sign_tool()
    assert hasattr(mod, "load_agreement")
    assert hasattr(mod, "make_signature")
    assert hasattr(mod, "write_signature")


def test_sign_contributor_agreement_dry_run(capsys: pytest.CaptureFixture[str]) -> None:
    mod = _load_sign_tool()
    rc = mod.main(  # type: ignore[attr-defined]
        [
            "--name",
            "Test User",
            "--email",
            "test@example.com",
            "--gh-handle",
            "testuser",
            "--dry-run",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "DRY-RUN" in out
    assert "test@example.com" in out
    # ensure no signature file created in dry-run
    assert not (REPO_ROOT / "governance" / "contributors" / "testuser.json").exists()


def test_sign_contributor_agreement_persists_and_idempotent(tmp_path: Path) -> None:
    mod = _load_sign_tool()
    text, digest = mod.load_agreement()  # type: ignore[attr-defined]
    assert digest and len(digest) == 64
    sig = mod.make_signature(  # type: ignore[attr-defined]
        name="A",
        email="a@b.c",
        gh_handle="alice_p6_test",
        agreement_sha256=digest,
    )
    assert sig["agreement_sha256"] == digest
    assert sig["gh_handle"] == "alice_p6_test"
    # write_signature lands a JSON in governance/contributors/
    out = mod.write_signature(sig, force=True)  # type: ignore[attr-defined]
    try:
        assert out.exists()
        loaded = json.loads(out.read_text(encoding="utf-8"))
        assert loaded["email"] == "a@b.c"
        # idempotency: second write without force should fail
        with pytest.raises(FileExistsError):
            mod.write_signature(sig, force=False)  # type: ignore[attr-defined]
    finally:
        if out.exists():
            out.unlink()


# ---------------------------------------------------------------------------
# T5 — Landing copy
# ---------------------------------------------------------------------------


def test_landing_copy_present() -> None:
    p = REPO_ROOT / "docs" / "landing" / "founder_mode_against_cancer.md"
    assert p.exists(), "landing copy missing"
    txt = p.read_text(encoding="utf-8")
    assert "Founder Mode" in txt or "founder mode" in txt.lower()
    # founder-mode discipline keywords
    assert "patient" in txt.lower()
    assert "open-source" in txt.lower() or "open source" in txt.lower() or "Apache" in txt
    # warm reference back to disclaimer
    assert "DISCLAIMER" in txt or "Disclaimer" in txt


# ---------------------------------------------------------------------------
# T1 — multi-case E2E parametrisation widened to 4 patients
# ---------------------------------------------------------------------------


def test_wave1_e2e_parametrisation_covers_four_cancer_types() -> None:
    """The wave1 E2E test must enumerate ≥4 patient codes (HCC/NSCLC/CRC/BRCA)."""
    src_path = REPO_ROOT / "tests" / "test_e2e" / "test_wave1_e2e.py"
    src = src_path.read_text(encoding="utf-8")
    for code in ("anon_hcc_001", "anon_nsclc_001", "anon_crc_001", "anon_brca_001"):
        assert code in src, f"{code} not in wave1 E2E parametrisation"


# ---------------------------------------------------------------------------
# T6 — Release prep
# ---------------------------------------------------------------------------


def test_pyproject_version_is_v1() -> None:
    py = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    # Accept any v1.0.x patch — P6 baseline 1.0.0; Iter-9+ bumps patch level
    assert 'version = "1.0.' in py, "pyproject not on v1.0.x line"


def test_changelog_has_1_0_0_section() -> None:
    cl = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "1.0.0-p6" in cl or "[1.0.0]" in cl, "CHANGELOG missing v1.0.0 entry"


# ---------------------------------------------------------------------------
# Sanity — 18 experts still routable
# ---------------------------------------------------------------------------


def test_eighteen_experts_in_roster() -> None:
    from opl_cancer.experts.roster import ROSTER

    assert len(ROSTER) == 18, f"expected 18 experts, found {len(ROSTER)}"
    for needed in (
        "rosa",
        "bert",
        "vince",
        "rick",
        "heddy",
        "mary",
        "aviv",
        "tyler",
        "iain",
        "ted",
        "riad",
        "jen",
        "kieren",
        "mark",
        "hong",
        "frances",
        "dennis",
        "steve",
    ):
        assert needed in ROSTER


# ---------------------------------------------------------------------------
# Sanity — synthetic patients golden subset covers ≥4 cancer types
# ---------------------------------------------------------------------------


def test_golden_set_has_four_cancer_types() -> None:
    gs = REPO_ROOT / "validators" / "golden_set" / "synthetic_patients"
    children = sorted(p.name for p in gs.iterdir() if p.is_dir())
    for needed in ("anon_hcc_001", "anon_nsclc_001", "anon_crc_001", "anon_brca_001"):
        assert needed in children, f"{needed} missing from golden_set/synthetic_patients"
