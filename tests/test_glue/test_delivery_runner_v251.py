"""v2.5.1 B1 — DeliveryRunner must not ship fake Henry audit / stub briefs.

Audit finding: through v2.5.0 the runner returned a hardcoded
``{"status": "pass", "gates_run": 28}`` payload + 4-line markdown stub briefs.
The fix wires Henry + the real Wave 5 templates, and refuses to ship if the
upstream wave-artifact corpus is missing.

These tests are the failing-first contract.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from opl_cancer.glue.delivery_runner import (
    DeliveryArtifactsMissing,
    DeliveryFailure,
    DeliveryRunner,
)


def _build_complete_wave_corpus(run_root: Path) -> None:
    """Drop the minimum set of upstream artifacts a real delivery requires."""
    run_root.mkdir(parents=True, exist_ok=True)
    # Wave 1: at least one expert report.
    w1 = run_root / "tasks" / "w1_rosa_pathology"
    w1.mkdir(parents=True, exist_ok=True)
    (w1 / "report.md").write_text(
        "# Wave 1 — rosa / pathology\n\n"
        "Per Awad et al. (PMID:34750504), ORR was 23.2% (n=142).\n",
        encoding="utf-8",
    )
    # Plan, profile, wave artifacts the brief refers to. v2.6.0 B5-semantic:
    # these must carry REAL (non-empty) content or the hollow-gate refuses them.
    (run_root / "plan.json").write_text(
        '{"goal": "next-line options", "tasks": ["t1"]}', encoding="utf-8"
    )
    (run_root / "wave2_hypotheses.json").write_text(
        '{"hypotheses": [{"id": "h1", "text": "x"}], "top_k": ["h1"]}', encoding="utf-8"
    )
    (run_root / "wave3_data_evidence.json").write_text(
        '{"analysis_runs": [{"id": "a1"}], "validations": []}', encoding="utf-8"
    )
    (run_root / "wave4_validation.json").write_text(
        '{"validations": [{"id": "v1", "verdict": "inconclusive"}]}', encoding="utf-8"
    )


def test_delivery_runner_without_upstream_artifacts_refuses(tmp_path: Path) -> None:
    """B1+B5: with no Wave 1-4 outputs the runner MUST raise
    DeliveryArtifactsMissing — no fake 'pass' Henry audit, no stub brief."""
    out_dir = tmp_path / "patient" / "triggers" / "run-x" / "delivery"
    runner = DeliveryRunner(out_dir=out_dir)
    with pytest.raises(DeliveryArtifactsMissing):
        runner.run()
    # Absolutely nothing must be written.
    assert not (out_dir / "HENRY_AUDIT.json").exists()
    assert not (out_dir / "patient_plain_brief.md").exists()
    assert not (out_dir / "patient_pi_brief.md").exists()


def test_delivery_runner_real_henry_audit_uses_validator(tmp_path: Path) -> None:
    """v2.6.0 corrected contract: the v2.5.1 fix STILL never ran a real audit —
    it emitted henry_real_audit=true + status=pass for a scaffold. The honest
    contract: the default (scaffold) path declares henry_real_audit=False and a
    non-pass status; the auditor is still constructed (fail-loud on missing
    catalogue) and the payload carries no hardcoded magic gates number."""
    run_root = tmp_path / "patient" / "triggers" / "run-x"
    _build_complete_wave_corpus(run_root)
    out_dir = run_root / "delivery"

    result = DeliveryRunner(out_dir=out_dir).run()
    # The scaffold is NOT a finished, audited deliverable — say so honestly.
    assert result["status"] == "scaffold_pending_fill"
    assert result["henry_real_audit"] is False

    import json

    audit = json.loads((out_dir / "HENRY_AUDIT.json").read_text(encoding="utf-8"))
    assert audit.get("audit_version", "").startswith("v2."), audit
    # No hardcoded "gates_run: 28" magic number, and no claim was audited yet.
    assert audit.get("gates_run") == 0, audit
    assert audit.get("claims_audited") == 0, audit
    assert audit.get("henry_real_audit") is False
    assert audit.get("status") != "pass"
    # ADR-0021 Inv-3: the placeholder language in the scaffold is surfaced.
    assert audit.get("placeholder_findings"), audit
    assert isinstance(audit.get("pending_acks"), list)
    assert isinstance(audit.get("upstream_artifacts"), dict)


def test_plain_brief_is_not_4_line_stub(tmp_path: Path) -> None:
    """B1: the plain brief must not be the v2.5.0 4-line stub. The real
    template-driven brief carries the patient-facing Section headers from
    prompts/tasks/patient_plain_brief_rendering.md."""
    run_root = tmp_path / "patient" / "triggers" / "run-x"
    _build_complete_wave_corpus(run_root)
    out_dir = run_root / "delivery"

    DeliveryRunner(out_dir=out_dir).run()
    md = (out_dir / "patient_plain_brief.md").read_text(encoding="utf-8")
    # The stub was 4 lines; real rendering carries the 5 mandatory sections
    # from the template (Section 0 / 1 / 2 / 3 / 4 in zh).
    assert "一句话答案" in md or "The bottom line" in md, md[:400]
    assert "问医生" in md or "questions" in md.lower(), md[:400]
    # ≥ 30 lines is a reasonable floor for the real template (v2.5.0 stub
    # was 4); we keep the floor low to avoid coupling to exact prose.
    assert len(md.splitlines()) >= 30, (
        f"plain brief looks like a stub ({len(md.splitlines())} lines)"
    )


def test_pi_brief_is_not_4_line_stub(tmp_path: Path) -> None:
    """B1: the PI brief must be the real pi_delivery rendering, not a 4-line stub."""
    run_root = tmp_path / "patient" / "triggers" / "run-x"
    _build_complete_wave_corpus(run_root)
    out_dir = run_root / "delivery"

    DeliveryRunner(out_dir=out_dir).run()
    md = (out_dir / "patient_pi_brief.md").read_text(encoding="utf-8")
    # Real PI brief carries Henry verdict + per-claim layer + ack table.
    assert "Henry" in md or "henry" in md, md[:400]
    assert "PI" in md or "clinician" in md.lower(), md[:400]
    assert len(md.splitlines()) >= 20, (
        f"PI brief looks like a stub ({len(md.splitlines())} lines)"
    )


def test_delivery_failure_when_henry_catalogue_missing(tmp_path: Path) -> None:
    """B1: if the serious_risks catalogue cannot be found, the runner must
    surface that as a DeliveryFailure — not silently fall through to a
    hardcoded pass."""
    run_root = tmp_path / "patient" / "triggers" / "run-x"
    _build_complete_wave_corpus(run_root)
    out_dir = run_root / "delivery"

    runner = DeliveryRunner(
        out_dir=out_dir,
        serious_risks_path=tmp_path / "does_not_exist.json",
    )
    with pytest.raises(DeliveryFailure):
        runner.run()
