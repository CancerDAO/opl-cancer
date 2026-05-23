"""P5 acceptance — Validation Stack completeness.

Covers:
- T1 risk-disclosure-card model + render
- T2 Henry 4-layer auditor
- T3 serious-risks knowledge file
- T4 CLI acknowledge + list-pending-acks
- T5 models.yaml reviewer_pairings populated
- T6 tools/reproduce.py + tools/verify_provenance.py
- T7 golden_set expansion (synthetic patients, failure modes, regression anchors, boundary cases)
- T8 (smoke) integrator-aware experts still importable
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parent.parent
SERIOUS_RISKS_PATH = REPO_ROOT / "knowledge" / "serious_risks_per_drug.json"
GOLDEN_ROOT = REPO_ROOT / "validators" / "golden_set"


# -----------------------------------------------------------------------------
# T3 — serious-risks knowledge file
# -----------------------------------------------------------------------------


def test_serious_risks_catalogue_exists() -> None:
    assert SERIOUS_RISKS_PATH.exists()
    data = json.loads(SERIOUS_RISKS_PATH.read_text(encoding="utf-8"))
    assert "_meta" in data
    # at least 5 drugs catalogued
    drug_keys = [k for k in data if not k.startswith("_")]
    assert len(drug_keys) >= 5


def test_serious_risks_catalogue_each_entry_has_risks() -> None:
    data = json.loads(SERIOUS_RISKS_PATH.read_text(encoding="utf-8"))
    for k, v in data.items():
        if k.startswith("_"):
            continue
        assert "known_serious_risks" in v
        assert len(v["known_serious_risks"]) >= 1
        assert "inn" in v


# -----------------------------------------------------------------------------
# T1 — risk-disclosure-card
# -----------------------------------------------------------------------------


def test_risk_card_requires_risks_or_gaps() -> None:
    from pydantic import ValidationError as PydValErr

    from opl_cancer.delivery.risk_card import RiskDisclosureCard, RiskDisclosureCardError

    # Pydantic wraps the custom ValueError subclass into a ValidationError.
    with pytest.raises((RiskDisclosureCardError, PydValErr)):
        RiskDisclosureCard(
            card_id="card-1",
            claim_text="some claim",
            level=3,
            known_serious_risks=[],
            epistemic_gaps=[],
        )


def test_risk_card_with_risks_constructs() -> None:
    from opl_cancer.delivery.risk_card import RiskDisclosureCard

    card = RiskDisclosureCard(
        card_id="card-1",
        claim_text="off-label X",
        level=4,
        known_serious_risks=["hepatotoxicity"],
        epistemic_gaps=["unknown long-term safety"],
    )
    assert card.requires_patient_acknowledgment is True
    assert card.level == 4


def test_risk_card_content_hash_stable() -> None:
    from opl_cancer.delivery.risk_card import RiskDisclosureCard

    card1 = RiskDisclosureCard(
        card_id="c1", claim_text="x", level=3, known_serious_risks=["r1"]
    )
    card2 = RiskDisclosureCard(
        card_id="c1", claim_text="x", level=3, known_serious_risks=["r1"]
    )
    # content_hash excludes created_at + ack timestamp, so identical inputs -> identical hash
    assert card1.content_hash() == card2.content_hash()
    assert card1.content_hash().startswith("sha256:")


def test_risk_card_markdown_renders() -> None:
    from opl_cancer.delivery.risk_card import RiskDisclosureCard, render_risk_card_markdown

    card = RiskDisclosureCard(
        card_id="c1",
        claim_text="off-label atezolizumab in 3L HCC",
        level=4,
        known_serious_risks=["immune hepatitis"],
        epistemic_gaps=["small N"],
        alternatives=["best supportive care", "clinical trial enrolment"],
    )
    md = render_risk_card_markdown(card)
    assert "Level 4" in md
    assert "immune hepatitis" in md
    assert "awaiting patient acknowledgment" in md


def test_risk_card_html_renders_and_escapes() -> None:
    from opl_cancer.delivery.risk_card import RiskDisclosureCard, render_risk_card_html

    card = RiskDisclosureCard(
        card_id="c1",
        claim_text="<script>evil()</script>",
        level=3,
        known_serious_risks=["risk & one"],
    )
    html = render_risk_card_html(card)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "risk &amp; one" in html


# -----------------------------------------------------------------------------
# T2 — Henry 4-layer auditor
# -----------------------------------------------------------------------------


def _make_auditor(tmp_path: Path) -> object:
    from opl_cancer.validators.henry import HenryAuditor

    return HenryAuditor(
        serious_risks_path=SERIOUS_RISKS_PATH,
        outstanding_dir=tmp_path / "outstanding",
    )


def test_henry_missing_catalogue_raises(tmp_path: Path) -> None:
    from opl_cancer.validators.henry import HenryAuditError, HenryAuditor

    with pytest.raises(HenryAuditError):
        HenryAuditor(
            serious_risks_path=tmp_path / "nope.json",
            outstanding_dir=tmp_path / "outstanding",
        )


def test_henry_l0_l2_no_card_no_ack(tmp_path: Path) -> None:
    from opl_cancer.validators.permission_levels import Level

    auditor = _make_auditor(tmp_path)
    result = auditor.audit_claim(  # type: ignore[attr-defined]
        claim_id="c1",
        claim_text="general info about HCC staging",
        level=Level.L0_INFORMATION,
    )
    assert result.layer1_card is None
    assert result.layer4_ack_required is False


def test_henry_l3_emits_card_and_pending_ack(tmp_path: Path) -> None:
    from opl_cancer.validators.permission_levels import Level

    auditor = _make_auditor(tmp_path)
    result = auditor.audit_claim(  # type: ignore[attr-defined]
        claim_id="c1",
        claim_text="atezolizumab high-risk in HBV reactivation",
        level=Level.L3_HIGH_RISK,
        drugs_mentioned=["atezolizumab"],
        epistemic_gaps=["HBV+ cohort under-represented"],
    )
    assert result.layer1_card is not None
    assert result.layer4_ack_required is True
    assert result.layer4_ack_pending_path is not None
    # At least one catalogued risk surfaced
    assert any("atezolizumab" in r.lower() for r in result.layer3_serious_risks)


def test_henry_l4_uses_card_level_4(tmp_path: Path) -> None:
    from opl_cancer.validators.permission_levels import Level

    auditor = _make_auditor(tmp_path)
    result = auditor.audit_claim(  # type: ignore[attr-defined]
        claim_id="c2",
        claim_text="off-label use of trastuzumab in HER2-low",
        level=Level.L4_BOUNDARY,
        drugs_mentioned=["trastuzumab"],
        alternatives=["enroll in HER2-low trial"],
    )
    assert result.layer1_card is not None
    assert result.layer1_card.level == 4


def test_henry_unknown_drug_surfaces_warning(tmp_path: Path) -> None:
    from opl_cancer.validators.permission_levels import Level

    auditor = _make_auditor(tmp_path)
    result = auditor.audit_claim(  # type: ignore[attr-defined]
        claim_id="c3",
        claim_text="speculative",
        level=Level.L3_HIGH_RISK,
        drugs_mentioned=["unobtanium"],
    )
    assert any("unknown drug" in r.lower() for r in result.layer3_serious_risks)


def test_henry_layer2_passes_through_challenges(tmp_path: Path) -> None:
    from opl_cancer.validators.permission_levels import Level

    auditor = _make_auditor(tmp_path)
    result = auditor.audit_claim(  # type: ignore[attr-defined]
        claim_id="c4",
        claim_text="x",
        level=Level.L3_HIGH_RISK,
        drugs_mentioned=["atezolizumab"],
        reviewer_challenges=["disagrees on safety in HBV+", "  ", "alt MoA model"],
    )
    # Empty/whitespace challenges trimmed
    assert "disagrees on safety in HBV+" in result.layer2_disagreements
    assert "alt MoA model" in result.layer2_disagreements
    assert "" not in result.layer2_disagreements


def test_henry_ack_and_list_pending(tmp_path: Path) -> None:
    from opl_cancer.validators.permission_levels import Level

    auditor = _make_auditor(tmp_path)
    res = auditor.audit_claim(  # type: ignore[attr-defined]
        claim_id="c5",
        claim_text="x",
        level=Level.L3_HIGH_RISK,
        drugs_mentioned=["osimertinib"],
    )
    assert res.layer1_card is not None
    pending = auditor.list_pending()  # type: ignore[attr-defined]
    assert len(pending) == 1
    rec = auditor.acknowledge(  # type: ignore[attr-defined]
        res.layer1_card.card_id, acknowledged_at="2026-05-24T12:00:00+00:00"
    )
    assert rec["patient_acknowledged_at"] == "2026-05-24T12:00:00+00:00"
    assert auditor.list_pending() == []  # type: ignore[attr-defined]


def test_henry_ack_missing_card_raises(tmp_path: Path) -> None:
    from opl_cancer.validators.henry import HenryAuditError

    auditor = _make_auditor(tmp_path)
    with pytest.raises(HenryAuditError):
        auditor.acknowledge("nonexistent-id", acknowledged_at="2026-05-24T00:00:00Z")  # type: ignore[attr-defined]


# -----------------------------------------------------------------------------
# T4 — CLI acknowledge + list-pending-acks
# -----------------------------------------------------------------------------


def test_cli_acknowledge_and_list(tmp_path: Path) -> None:
    from opl_cancer.cli import main
    from opl_cancer.validators.henry import HenryAuditor
    from opl_cancer.validators.permission_levels import Level

    out_dir = tmp_path / "outstanding"
    auditor = HenryAuditor(
        serious_risks_path=SERIOUS_RISKS_PATH, outstanding_dir=out_dir
    )
    res = auditor.audit_claim(
        claim_id="cli-1",
        claim_text="cli test",
        level=Level.L3_HIGH_RISK,
        drugs_mentioned=["pembrolizumab"],
    )
    assert res.layer1_card is not None
    card_id = res.layer1_card.card_id

    runner = CliRunner()
    list_r = runner.invoke(
        main,
        [
            "list-pending-acks",
            "--outstanding-dir",
            str(out_dir),
            "--serious-risks",
            str(SERIOUS_RISKS_PATH),
        ],
    )
    assert list_r.exit_code == 0
    assert card_id in list_r.output

    ack_r = runner.invoke(
        main,
        [
            "acknowledge",
            card_id,
            "--outstanding-dir",
            str(out_dir),
            "--serious-risks",
            str(SERIOUS_RISKS_PATH),
        ],
    )
    assert ack_r.exit_code == 0
    assert "Acknowledged" in ack_r.output


def test_cli_list_pending_acks_when_empty(tmp_path: Path) -> None:
    from opl_cancer.cli import main

    runner = CliRunner()
    r = runner.invoke(
        main,
        [
            "list-pending-acks",
            "--outstanding-dir",
            str(tmp_path / "empty"),
            "--serious-risks",
            str(SERIOUS_RISKS_PATH),
        ],
    )
    assert r.exit_code == 0
    assert "No pending" in r.output


# -----------------------------------------------------------------------------
# T5 — models.yaml reviewer_pairings populated
# -----------------------------------------------------------------------------


def test_reviewer_pairings_populated() -> None:
    data = yaml.safe_load((REPO_ROOT / "models.yaml").read_text(encoding="utf-8"))
    pairings = data.get("reviewer_pairings") or {}
    # All 18 experts must have a pairing (15 LLM-backed + 3 specials checked below).
    # Minimum: at least 15 entries.
    assert len(pairings) >= 15


def test_reviewer_pairings_no_self_review() -> None:
    data = yaml.safe_load((REPO_ROOT / "models.yaml").read_text(encoding="utf-8"))
    pairings = data.get("reviewer_pairings") or {}
    for producer, reviewer in pairings.items():
        assert producer != reviewer, f"{producer!r} reviews itself — violates G13 spirit."


def test_reviewer_pairings_cover_key_experts() -> None:
    data = yaml.safe_load((REPO_ROOT / "models.yaml").read_text(encoding="utf-8"))
    pairings = data.get("reviewer_pairings") or {}
    for must_have in (
        "bert", "aviv", "mary", "rosa", "rick", "iain", "frances", "dennis"
    ):
        assert must_have in pairings, f"{must_have} missing from reviewer_pairings"


# -----------------------------------------------------------------------------
# T6 — tools/reproduce.py + tools/verify_provenance.py
# -----------------------------------------------------------------------------


def _load_tool(name: str) -> object:
    p = REPO_ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"tools.{name}", p)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"tools.{name}"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_reproduce_tool_loads_provenance(tmp_path: Path) -> None:
    mod = _load_tool("reproduce")
    pdir = tmp_path / "patient"
    run_dir = pdir / "triggers" / "run-1"
    run_dir.mkdir(parents=True)
    jl = run_dir / "provenance.jsonl"
    jl.write_text(
        json.dumps(
            {
                "id": "c1",
                "_meta": {"prompt_version": "v1@1", "model": "claude-opus-4-7"},
                "claim_hash": "sha256:abc",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    entries = mod.load_provenance(pdir, "run-1")  # type: ignore[attr-defined]
    assert len(entries) == 1
    report = mod.verify_recipe(entries)  # type: ignore[attr-defined]
    assert report["reproducible"] is True
    assert "claude-opus-4-7" in report["models_used"]


def test_reproduce_tool_flags_missing_prompt_version(tmp_path: Path) -> None:
    mod = _load_tool("reproduce")
    pdir = tmp_path / "patient"
    run_dir = pdir / "triggers" / "run-2"
    run_dir.mkdir(parents=True)
    jl = run_dir / "provenance.jsonl"
    jl.write_text(
        json.dumps({"id": "c1", "claim_hash": "sha256:abc"}) + "\n",
        encoding="utf-8",
    )
    entries = mod.load_provenance(pdir, "run-2")  # type: ignore[attr-defined]
    report = mod.verify_recipe(entries)  # type: ignore[attr-defined]
    assert report["reproducible"] is False
    assert report["missing_prompt_version"] >= 1


def test_reproduce_tool_main_exits_nonzero_on_missing_file(tmp_path: Path) -> None:
    mod = _load_tool("reproduce")
    rc = mod.main(["prog", str(tmp_path / "nope"), "run-x"])  # type: ignore[attr-defined]
    assert rc == 2


def test_verify_provenance_tool_match(tmp_path: Path) -> None:
    import hashlib

    mod = _load_tool("verify_provenance")
    pdir = tmp_path / "patient"
    run_dir = pdir / "triggers" / "run-v1"
    run_dir.mkdir(parents=True)
    rec = {"id": "c1", "payload": {"x": 1}}
    raw = json.dumps(rec, sort_keys=True, ensure_ascii=False).encode("utf-8")
    h = "sha256:" + hashlib.sha256(raw).hexdigest()
    rec["claim_hash"] = h
    (run_dir / "provenance.jsonl").write_text(
        json.dumps(rec) + "\n", encoding="utf-8"
    )
    report = mod.verify(pdir, "run-v1")  # type: ignore[attr-defined]
    assert report["ok"] is True
    assert report["matches"] == 1


def test_verify_provenance_tool_mismatch(tmp_path: Path) -> None:
    mod = _load_tool("verify_provenance")
    pdir = tmp_path / "patient"
    run_dir = pdir / "triggers" / "run-v2"
    run_dir.mkdir(parents=True)
    (run_dir / "provenance.jsonl").write_text(
        json.dumps({"id": "c1", "x": 1, "claim_hash": "sha256:wrong"}) + "\n",
        encoding="utf-8",
    )
    report = mod.verify(pdir, "run-v2")  # type: ignore[attr-defined]
    assert report["ok"] is False
    assert len(report["mismatches"]) == 1


def test_verify_provenance_tool_missing_file(tmp_path: Path) -> None:
    mod = _load_tool("verify_provenance")
    rc = mod.main(["prog", str(tmp_path / "nope"), "run-x"])  # type: ignore[attr-defined]
    assert rc == 2


# -----------------------------------------------------------------------------
# T7 — golden_set expansion
# -----------------------------------------------------------------------------


def test_golden_set_synthetic_patients_extended() -> None:
    sp = GOLDEN_ROOT / "synthetic_patients"
    cancer_types: set[str] = set()
    for d in sp.iterdir():
        if not d.is_dir():
            continue
        profile_p = d / "profile.json"
        assert profile_p.exists(), f"missing profile.json in {d}"
        data = json.loads(profile_p.read_text(encoding="utf-8"))
        site = data.get("diagnosis", {}).get("primary_site")
        if site:
            cancer_types.add(site)
    # P5: ≥4 patients across ≥4 distinct primary sites (HCC liver, NSCLC lung, CRC rectum, breast)
    assert len(cancer_types) >= 4, f"expected ≥4 cancer types, got {cancer_types}"


def test_golden_set_failure_modes_extended() -> None:
    fm = GOLDEN_ROOT / "failure_mode_inputs"
    inputs = list(fm.glob("*.json"))
    # P1 had 3; P5 adds ≥5 more = ≥8 total
    assert len(inputs) >= 8, f"expected ≥8 failure-mode inputs, got {len(inputs)}"
    for p in inputs:
        data = json.loads(p.read_text(encoding="utf-8"))
        assert "test_name" in data
        assert "expected_block_gate" in data
        # P5 fixtures use "rationale"; older P1 fixtures may use "note" or "p1_behavior".
        assert any(k in data for k in ("rationale", "note", "p1_behavior"))


def test_golden_set_regression_anchors_present() -> None:
    ra = GOLDEN_ROOT / "regression_anchors"
    assert ra.exists()
    anchors = list(ra.glob("*.json"))
    assert len(anchors) >= 2
    for p in anchors:
        data = json.loads(p.read_text(encoding="utf-8"))
        assert "anchor_name" in data
        assert "acceptance_criterion" in data


def test_golden_set_boundary_cases_present() -> None:
    bc = GOLDEN_ROOT / "boundary_cases"
    assert bc.exists()
    cases = list(bc.glob("*.json"))
    assert len(cases) >= 3
    for p in cases:
        data = json.loads(p.read_text(encoding="utf-8"))
        assert "case_name" in data
        assert "expected_behavior" in data
        assert isinstance(data["expected_behavior"], list)


def test_failure_mode_inputs_have_distinct_gates() -> None:
    fm = GOLDEN_ROOT / "failure_mode_inputs"
    gates: set[str] = set()
    for p in fm.glob("*.json"):
        data = json.loads(p.read_text(encoding="utf-8"))
        gates.add(data["expected_block_gate"])
    # At least 5 distinct gates exercised across failure modes
    assert len(gates) >= 5, f"only {len(gates)} distinct gates in golden set"


# -----------------------------------------------------------------------------
# T8 — integrator-aware experts (smoke)
# -----------------------------------------------------------------------------


def test_p5_experts_importable_and_have_portfolio() -> None:
    from opl_cancer.experts import dennis, frances, mary, rick

    for cls, expected_pkg in (
        (mary.MaryExpert, "ddi_adme_dosing"),
        (frances.FrancesExpert, "expanded_access_navigation"),
        (dennis.DennisExpert, "cross_border_navigation"),
        (rick.RickExpert, "trial_matching"),
    ):
        assert expected_pkg in cls.portfolio


# -----------------------------------------------------------------------------
# Acceptance — count + tag preparation
# -----------------------------------------------------------------------------


def test_p5_validation_stack_complete() -> None:
    """Roll-up assertion: P5 building blocks are all present."""
    assert (REPO_ROOT / "src" / "opl_cancer" / "delivery" / "risk_card.py").exists()
    assert (REPO_ROOT / "src" / "opl_cancer" / "validators" / "henry.py").exists()
    assert (REPO_ROOT / "knowledge" / "serious_risks_per_drug.json").exists()
    assert (REPO_ROOT / "tools" / "reproduce.py").exists()
    assert (REPO_ROOT / "tools" / "verify_provenance.py").exists()
    assert (GOLDEN_ROOT / "regression_anchors").exists()
    assert (GOLDEN_ROOT / "boundary_cases").exists()
