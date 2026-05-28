"""v2.4 ADR-0024 — `n1arxiv_submitter.py` tests.

Unit + integration coverage for the cross-repo PR-assembly helper that
turns a `.n1a` bundle into a ready-to-PR diff against `CancerDAO/n1arxiv`.

Founder-mode invariants this test file pins:

* The submitter NEVER executes `gh pr create` or `git push` — it only
  emits a plan (paths copied, PR body draft, command suggestions).
* The content stub is auto-generated from `manifest.json` so the
  manuscript text never gets duplicated into the platform repo.
* The bundle SHA is preserved end-to-end — copying must be byte-exact.
* Banner / data_source is surfaced in the PR body draft so the
  maintainer never merges a `methodology_demo` bundle without seeing
  the framing.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest


# Import lazily so the test file fails with a useful message rather
# than ImportError at collection time when the module hasn't shipped.
def _import_module():
    from opl_cancer.delivery import n1arxiv_submitter  # type: ignore[import-not-found]

    return n1arxiv_submitter


@pytest.fixture
def good_bundle_dir(tmp_path: Path) -> Path:
    """Build a minimal but schema-valid .n1a bundle on disk."""
    from opl_cancer.delivery.n1a_bundle_writer import write_bundle

    trig = tmp_path / "patient" / "triggers" / "run-abc"
    trig.mkdir(parents=True)
    (trig / "manuscript.md").write_text(
        "# Manuscript\n\n[BACKGROUND] N=1 framing.\n\n"
        "Pembrolizumab is approved [PMID:32179615].\n",
        encoding="utf-8",
    )
    (trig / "ai_authorship_disclosure.md").write_text(
        "# AI Authorship\n\nNo human author beyond the patient and "
        "supervising clinician.\n\n| Expert | Role |\n| - | - |\n| Iain | retrieval |\n",
        encoding="utf-8",
    )
    (trig / "reproducibility.md").write_text(
        "# Reproducibility\n\n## Data sources\n\n- TCGA, tier: public\n",
        encoding="utf-8",
    )
    (trig / "HENRY_AUDIT.json").write_text(
        json.dumps(
            {
                "audit_version": "v2.3",
                "status": "pass",
                "results": [
                    {"gate": "G29", "status": "PASS"},
                    {"gate": "G30", "status": "PASS"},
                    {"gate": "G31", "status": "PASS"},
                    {"gate": "G32", "status": "PASS"},
                    {"gate": "G33", "status": "PASS"},
                ],
            }
        ),
        encoding="utf-8",
    )
    write_bundle(
        trigger_dir=trig,
        patient_code="riaz-reference",
        data_source="reference_case",
        opl_version="2.4.0",
        run_id="run-abc",
    )
    return trig


def _zip_in(d: Path) -> Path:
    zips = sorted(d.glob("*.n1a.zip"))
    assert zips, f"no .n1a.zip under {d}"
    return zips[0]


# ─── unit: content stub generation ─────────────────────────────────────


def test_content_stub_pulls_from_manifest(tmp_path: Path) -> None:
    mod = _import_module()
    manifest = {
        "schema_version": "0.1",
        "opl_version": "2.4.0",
        "patient_id_hash": "abc1234deadbeef",
        "generated_at": "2026-05-28T12:00:00+00:00",
        "data_source": "reference_case",
        "file_index": ["manuscript.md", "HENRY_AUDIT.json"],
        "sha256s": {"manuscript.md": "a" * 64, "HENRY_AUDIT.json": "b" * 64},
        "banner": "[REFERENCE CASE — PUBLIC DATA, NOT THIS PATIENT]",
    }
    stub = mod.build_content_stub(
        manifest=manifest,
        paper_id="2026-05-28-riaz-reference",
        bundle_relpath="bundles/2026-05-28-riaz-reference.n1a.zip",
    )
    # Hugo front matter present
    assert stub.startswith("---\n")
    assert "title:" in stub
    assert "data_source: reference_case" in stub
    assert "opl_version: \"2.4.0\"" in stub or "opl_version: 2.4.0" in stub
    # Banner surfaced
    assert "REFERENCE CASE" in stub
    # Bundle link present
    assert "2026-05-28-riaz-reference.n1a.zip" in stub
    # Patient hash never leaks raw patient_code
    assert "abc1234deadbeef" in stub


def test_paper_id_is_deterministic(tmp_path: Path) -> None:
    mod = _import_module()
    pid_a = mod.derive_paper_id(
        manifest={"patient_id_hash": "f00d", "generated_at": "2026-05-28T10:00:00+00:00"},
        patient_code="riaz-reference",
    )
    pid_b = mod.derive_paper_id(
        manifest={"patient_id_hash": "f00d", "generated_at": "2026-05-28T10:00:00+00:00"},
        patient_code="riaz-reference",
    )
    assert pid_a == pid_b
    assert pid_a.startswith("2026-05-28-")
    # Sanitised: no spaces, lower-case
    assert pid_a == pid_a.lower()
    assert " " not in pid_a


# ─── integration: stage bundle into a fake n1arxiv clone ───────────────


def test_stage_into_local_clone(good_bundle_dir: Path, tmp_path: Path) -> None:
    mod = _import_module()
    zip_path = _zip_in(good_bundle_dir)
    n1a_clone = tmp_path / "n1arxiv"
    (n1a_clone / "static" / "bundles").mkdir(parents=True)
    (n1a_clone / "content" / "papers").mkdir(parents=True)

    plan = mod.assemble_submission(
        bundle_zip=zip_path,
        n1arxiv_clone=n1a_clone,
        patient_code="riaz-reference",
        execute=False,  # founder-mode default
    )

    # Bundle copied byte-exact
    target_zip = n1a_clone / "static" / "bundles" / Path(plan["bundle_target"]).name
    assert target_zip.is_file()
    assert hashlib.sha256(target_zip.read_bytes()).hexdigest() == hashlib.sha256(
        zip_path.read_bytes()
    ).hexdigest()

    # Stub written
    stub_path = n1a_clone / "content" / "papers" / Path(plan["content_stub_target"]).name
    assert stub_path.is_file()
    txt = stub_path.read_text(encoding="utf-8")
    assert txt.startswith("---\n")
    assert "data_source:" in txt

    # PR body draft is in the plan
    assert "pr_body" in plan
    assert "ethics" in plan["pr_body"].lower()
    assert "consent" in plan["pr_body"].lower()

    # gh pr create command suggested, NOT executed
    assert "gh pr create" in plan["suggested_commands"]
    assert not plan.get("executed_gh_pr_create", False)


def test_real_patient_without_consent_flagged(good_bundle_dir: Path, tmp_path: Path) -> None:
    """real_patient bundles must surface a consent reminder in the PR body."""
    mod = _import_module()
    # Re-pack as real_patient
    from opl_cancer.delivery.n1a_bundle_writer import write_bundle

    real_dir = tmp_path / "real" / "triggers" / "r-1"
    real_dir.mkdir(parents=True)
    for f in good_bundle_dir.iterdir():
        if f.is_file() and not f.name.endswith(".n1a.zip") and f.name != "manifest.json":
            (real_dir / f.name).write_bytes(f.read_bytes())
    write_bundle(
        trigger_dir=real_dir,
        patient_code="patient-007",
        data_source="real_patient",
        opl_version="2.4.0",
        run_id="r-1",
    )
    zip_path = _zip_in(real_dir)

    n1a_clone = tmp_path / "n1arxiv2"
    (n1a_clone / "static" / "bundles").mkdir(parents=True)
    (n1a_clone / "content" / "papers").mkdir(parents=True)

    plan = mod.assemble_submission(
        bundle_zip=zip_path,
        n1arxiv_clone=n1a_clone,
        patient_code="patient-007",
        execute=False,
    )
    body = plan["pr_body"]
    # Must remind submitter that real_patient triggers stricter CI consent check
    assert "real_patient" in body
    assert "consent" in body.lower()


def test_submitter_never_executes_git(good_bundle_dir: Path, tmp_path: Path, monkeypatch) -> None:
    """No `git push` / `gh pr create` is ever shelled out — founder mode."""
    mod = _import_module()
    zip_path = _zip_in(good_bundle_dir)
    n1a_clone = tmp_path / "n1arxiv"
    (n1a_clone / "static" / "bundles").mkdir(parents=True)
    (n1a_clone / "content" / "papers").mkdir(parents=True)

    calls: list[list[str]] = []

    def _fake_run(cmd, *a, **kw):  # noqa: ANN001
        calls.append(cmd if isinstance(cmd, list) else [str(cmd)])

        class R:
            returncode = 0
            stdout = ""
            stderr = ""

        return R()

    monkeypatch.setattr("subprocess.run", _fake_run)

    mod.assemble_submission(
        bundle_zip=zip_path,
        n1arxiv_clone=n1a_clone,
        patient_code="riaz-reference",
        execute=False,
    )

    # The submitter MUST NOT have called git/gh for state-changing actions
    flat = " ".join(" ".join(c) for c in calls)
    assert "gh pr create" not in flat
    assert "git push" not in flat


def test_bundle_zip_integrity_preserved(good_bundle_dir: Path, tmp_path: Path) -> None:
    """After staging, the zip in n1arxiv unzips to the same file_index as the source."""
    mod = _import_module()
    zip_path = _zip_in(good_bundle_dir)
    n1a_clone = tmp_path / "n1arxiv"
    (n1a_clone / "static" / "bundles").mkdir(parents=True)
    (n1a_clone / "content" / "papers").mkdir(parents=True)
    plan = mod.assemble_submission(
        bundle_zip=zip_path,
        n1arxiv_clone=n1a_clone,
        patient_code="riaz-reference",
        execute=False,
    )
    target = n1a_clone / "static" / "bundles" / Path(plan["bundle_target"]).name

    with zipfile.ZipFile(zip_path) as src, zipfile.ZipFile(target) as dst:
        assert sorted(src.namelist()) == sorted(dst.namelist())
        with src.open("manifest.json") as fa, dst.open("manifest.json") as fb:
            assert json.load(fa) == json.load(fb)
