"""ADR-0042 — hypothesis tree, re-entry/depth, abstraction, funnel.

Covers the four Arbor/HTR dynamics added to OPL:
  ① insight abstraction beat + G60 gate (WARN; rejects auto-fill)
  ② tree render in observe + deepen re-entry bounded by depth budget
  ③ informative-selection structural field surfaced in the funnel
  ④ deterministic explored→survived funnel + brief section
All are pure-read/scaffold harness pieces (judgment lives in prompts).
"""
from __future__ import annotations

import json

from click.testing import CliRunner

from opl_cancer.cli import abstract, deepen, funnel, main, observe, validate
from opl_cancer.plan.schemas import Plan, Task, WaveAssignment
from opl_cancer.validators.gates import G60InsightAbstractionWrittenGate
from opl_cancer.validators.mechanical_gates import GateStatus, all_gate_classes


def _run(tmp_path, *, max_depth=2, deepen_candidates=("H2",)):
    patient = tmp_path / "P"
    rid = "r1"
    rr = patient / "triggers" / rid
    rr.mkdir(parents=True)
    (rr / "plan.json").write_text(json.dumps({
        "goal": "二线后下一步", "max_depth": max_depth,
        "deepen_candidates": list(deepen_candidates),
        "waves": [{"wave_number": 1}], "tasks": [{"expert": "rick"}],
    }))
    (rr / "run_manifest.json").write_text(json.dumps({
        "run_token": "oplrun-x", "planned_waves": [1], "planned_experts": ["rick"],
    }))
    (rr / "wave2_hypotheses.json").write_text(json.dumps({"hypotheses": [
        {"id": "H1", "text": "anti-EGFR re-challenge", "elo_rating": 1260, "status": "active", "parent_chain": []},
        {"id": "H2", "text": "KRAS-G12C inhibitor + anti-EGFR", "elo_rating": 1255, "status": "active", "parent_chain": []},
        {"id": "H3", "text": "add SHP2 to the G12C combo", "elo_rating": 1240, "status": "active", "parent_chain": ["H2"]},
    ]}))
    (rr / "killed_candidates.jsonl").write_text('{"id":"H9"}\n{"id":"H8"}\n')
    (rr / "wave4_validation.json").write_text(json.dumps({
        "n_validated": 1, "n_falsified": 1, "n_inconclusive": 1, "validations": [
            {"hyp_id": "H1", "survival_status": "falsified"},
            {"hyp_id": "H2", "survival_status": "validated", "discrimination_target": ["H1", "H2"]},
            {"hyp_id": "H3", "survival_status": "inconclusive"},
        ]}))
    return patient, rid, rr


# ── G60 gate ────────────────────────────────────────────────────────────
def test_g60_registered_and_warn_only():
    assert "G60InsightAbstractionWrittenGate" in {g.__name__ for g in all_gate_classes()}


def test_g60_skip_warn_autofill_pass(tmp_path):
    patient, rid, rr = _run(tmp_path)
    g = G60InsightAbstractionWrittenGate()
    # owed → WARN (block=False, never withholds the brief)
    r = g.check({"run_root": str(rr), "run_id": rid})
    assert r.status == GateStatus.FAIL and r.block is False
    # verbatim copy of a source hypothesis → auto-fill WARN
    (rr / "abstraction.json").write_text(json.dumps({"abstracted_priors": [
        {"id": "a1", "lesson": "anti-EGFR re-challenge", "source_leaf_ids": ["H1"]}]}))
    assert "VERBATIM" in g.check({"run_root": str(rr), "run_id": rid}).message
    # real abstraction → PASS
    (rr / "abstraction.json").write_text(json.dumps({"abstracted_priors": [
        {"id": "a1", "lesson": "EGFR-axis monotherapy underperforms in this KRAS context",
         "source_leaf_ids": ["H1", "H2"]}]}))
    assert g.check({"run_root": str(rr), "run_id": rid}).status == GateStatus.PASS


def test_g60_skip_when_no_hypotheses(tmp_path):
    patient = tmp_path / "P"
    rr = patient / "triggers" / "r1"
    rr.mkdir(parents=True)
    g = G60InsightAbstractionWrittenGate()
    assert g.check({"run_root": str(rr), "run_id": "r1"}).status == GateStatus.SKIP


# ── ① abstract command ──────────────────────────────────────────────────
def test_abstract_scaffold_then_finalize(tmp_path):
    patient, rid, rr = _run(tmp_path)
    r = CliRunner()
    assert r.invoke(abstract, ["--patient", str(patient), "--run-id", rid]).exit_code == 0
    # reject auto-fill
    (rr / "abstraction.json").write_text(json.dumps({"abstracted_priors": [
        {"id": "a1", "lesson": "anti-EGFR re-challenge", "source_leaf_ids": ["H1"]}]}))
    bad = r.invoke(abstract, ["--patient", str(patient), "--run-id", rid, "--finalize"])
    assert bad.exit_code != 0 and "verbatim" in bad.output
    # accept real abstraction + persist
    (rr / "abstraction.json").write_text(json.dumps({"abstracted_priors": [
        {"id": "a1", "lesson": "EGFR-axis monotherapy underperforms here; G12C combos warrant a split",
         "source_leaf_ids": ["H1", "H2"], "directional": "supports"}]}))
    ok = r.invoke(abstract, ["--patient", str(patient), "--run-id", rid, "--finalize", "--json"])
    assert json.loads(ok.output)["persisted_priors"] == 1


def test_abstract_rejects_ungrounded_leaf(tmp_path):
    patient, rid, rr = _run(tmp_path)
    (rr / "abstraction.json").write_text(json.dumps({"abstracted_priors": [
        {"id": "a1", "lesson": "some general lesson", "source_leaf_ids": ["H_DOES_NOT_EXIST"]}]}))
    bad = CliRunner().invoke(abstract, ["--patient", str(patient), "--run-id", rid, "--finalize"])
    assert bad.exit_code != 0 and "no real hypothesis" in bad.output


# ── ② deepen / depth budget ─────────────────────────────────────────────
def test_deepen_frontier_selection(tmp_path):
    # _run: H1 is Wave-4 falsified (dead); H2 validated with child H3 inconclusive (pending).
    patient, rid, rr = _run(tmp_path, max_depth=2)
    r = CliRunner()
    # H1 falsified → refused as a dead target (false-hope guard)
    d1 = json.loads(r.invoke(deepen, ["--patient", str(patient), "--run-id", rid, "--target", "H1", "--json"]).output)
    assert d1["ok"] is False and d1["reason"] == "target_dead"
    # H2 has a pending (inconclusive) child → awaiting judgement, not a fresh spawn
    d2 = json.loads(r.invoke(deepen, ["--patient", str(patient), "--run-id", rid, "--target", "H2", "--json"]).output)
    assert d2["ok"] is False and d2["reason"] == "awaiting_judgement"


def test_deepen_unknown_target(tmp_path):
    patient, rid, rr = _run(tmp_path)
    bad = CliRunner().invoke(deepen, ["--patient", str(patient), "--run-id", rid, "--target", "NOPE"])
    assert bad.exit_code != 0


def test_plan_schema_accepts_depth_fields():
    p = Plan(run_id="r", patient_code="P", goal="g",
             waves=[WaveAssignment(wave_number=1, task_ids=["t1"])],
             tasks=[Task(id="t1", expert="rick", task_package="x", sub_goal="y")],
             max_depth=3, deepen_candidates=["H2"])
    assert p.max_depth == 3 and p.deepen_candidates == ["H2"]


# ── ④ funnel ────────────────────────────────────────────────────────────
def test_funnel_counts_and_emit(tmp_path):
    patient, rid, rr = _run(tmp_path)
    out = CliRunner().invoke(funnel, ["--patient", str(patient), "--run-id", rid, "--emit", "--json"])
    fn = json.loads(out.output)
    assert fn["explored"] == 3 and fn["killed_in_tournament"] == 2
    assert fn["validated"] == 1 and fn["falsified"] == 1 and fn["inconclusive"] == 1
    assert fn["ties_resolved_by_selection"] == 1 and fn["tree_depth_reached"] == 2
    assert (rr / "funnel.json").is_file()


# ── observe + validate integration ──────────────────────────────────────
def test_observe_renders_tree_funnel_and_owed_abstraction(tmp_path):
    patient, rid, rr = _run(tmp_path)
    out = CliRunner().invoke(observe, ["--patient", str(patient), "--run-id", rid])
    assert out.exit_code == 0
    assert "Hypothesis TREE" in out.output and "H3" in out.output and "depth 2/2" in out.output
    assert "FUNNEL" in out.output and "explored 3" in out.output
    assert "OWED" in out.output


def test_validate_warns_on_missing_abstraction_when_delivered(tmp_path):
    patient, rid, rr = _run(tmp_path)
    # mark delivered + ledger written so only the abstraction warning is novel
    (rr / "delivery").mkdir()
    (rr / "delivery" / "patient_plain_brief.md").write_text("brief")
    from opl_cancer.memory.store import ProjectMemoryStore, default_patient_memory_db
    from opl_cancer.memory.schemas import Hypothesis
    ProjectMemoryStore(default_patient_memory_db(rr)).save_hypothesis(
        Hypothesis(id="H1", text="t"), run_id=rid)
    out = CliRunner().invoke(validate, ["--patient", str(patient), "--run-id", rid, "--json"])
    codes = {p["code"] for p in json.loads(out.output)["problems"]}
    assert "DELIVERED_NO_ABSTRACTION" in codes


def test_cli_registers_new_commands():
    help_out = CliRunner().invoke(main, ["--help"]).output
    for cmd in ("abstract", "deepen", "funnel", "observe", "validate"):
        assert cmd in help_out


# ── review-found regressions (P1 + P2s) ─────────────────────────────────
def test_abstract_finalize_refuses_half_built_run(tmp_path):
    """P1: no wave2_hypotheses.json → fabricated source_leaf_ids must NOT persist."""
    patient = tmp_path / "P"
    rr = patient / "triggers" / "r1"
    rr.mkdir(parents=True)
    (rr / "abstraction.json").write_text(json.dumps({"abstracted_priors": [
        {"id": "a1", "lesson": "a totally fabricated prior", "source_leaf_ids": ["FAKE"]}]}))
    out = CliRunner().invoke(abstract, ["--patient", str(patient), "--run-id", "r1", "--finalize"])
    assert out.exit_code != 0 and "no hypotheses to ground against" in out.output
    # nothing persisted
    from opl_cancer.memory.store import ProjectMemoryStore, default_patient_memory_db
    db = default_patient_memory_db(rr)
    if db.exists():
        assert ProjectMemoryStore(db).query_abstractions() == []


def test_funnel_preserves_explicit_zero(tmp_path):
    """P2: explicit n_validated=0 must stay 0, not fall through to the tally."""
    patient = tmp_path / "P"
    rr = patient / "triggers" / "r1"
    rr.mkdir(parents=True)
    (rr / "wave2_hypotheses.json").write_text(json.dumps({"hypotheses": [{"id": "H1", "text": "t"}]}))
    (rr / "wave4_validation.json").write_text(json.dumps({
        "n_validated": 0, "n_falsified": 2,
        "validations": [{"hyp_id": "H1", "survival_status": "validated"}]}))  # tally would say 1
    out = CliRunner().invoke(funnel, ["--patient", str(patient), "--run-id", "r1", "--json"])
    assert json.loads(out.output)["validated"] == 0


def test_tree_cycle_does_not_drop_forest(tmp_path):
    """P2: a 2-cycle in parent_chain must not silently hide all hypotheses."""
    patient = tmp_path / "P"
    rr = patient / "triggers" / "r1"
    rr.mkdir(parents=True)
    (rr / "wave2_hypotheses.json").write_text(json.dumps({"hypotheses": [
        {"id": "A", "text": "a", "parent_chain": ["B"]},
        {"id": "B", "text": "b", "parent_chain": ["A"]}]}))
    out = CliRunner().invoke(observe, ["--patient", str(patient), "--run-id", "r1"])
    assert "A" in out.output and "B" in out.output and "no hypotheses yet" not in out.output


def test_dangling_parent_depth_is_consistent(tmp_path):
    """P2: a node whose parent is absent renders as a root (depth 1); the funnel
    depth must agree so it never trips DEPTH_BUDGET_EXCEEDED falsely."""
    patient = tmp_path / "P"
    rr = patient / "triggers" / "r1"
    rr.mkdir(parents=True)
    (rr / "plan.json").write_text(json.dumps({"max_depth": 1}))
    (rr / "wave2_hypotheses.json").write_text(json.dumps({"hypotheses": [
        {"id": "H1", "text": "t", "parent_chain": ["GHOST"]}]}))  # GHOST not present
    from opl_cancer.cli import _compute_funnel
    assert _compute_funnel(rr)["tree_depth_reached"] == 1
    out = CliRunner().invoke(validate, ["--patient", str(patient), "--run-id", "r1", "--json"])
    codes = {p["code"] for p in json.loads(out.output)["problems"]}
    assert "DEPTH_BUDGET_EXCEEDED" not in codes


# ── iteration-1: ✗① read-back · ✗③ enforce · ✗④ auto-emit ───────────────
def test_observe_surfaces_prior_content_not_just_count(tmp_path):
    """✗①: observe must show the abstracted lesson CONTENT so the planner can
    condition ideation on it (not just a count)."""
    patient, rid, rr = _run(tmp_path)
    from opl_cancer.memory.store import ProjectMemoryStore, default_patient_memory_db
    store = ProjectMemoryStore(default_patient_memory_db(rr))
    store.save_abstraction(
        {"id": "abs1", "lesson": "EGFR-axis monotherapy is futile in this KRAS context",
         "directional": "warns_against", "applies_to": "KRAS-G12C mCRC"},
        run_id="run_OLD")
    out = CliRunner().invoke(observe, ["--patient", str(patient), "--run-id", rid])
    assert "EGFR-axis monotherapy is futile" in out.output and "⊘" in out.output
    j = json.loads(CliRunner().invoke(observe, ["--patient", str(patient), "--run-id", rid, "--json"]).output)
    assert j["memory"]["cross_run_priors_list"][0]["directional"] == "warns_against"


def test_validate_flags_skipped_informative_selection(tmp_path):
    """✗③: near-tied survivors + no discrimination_target → WARN."""
    patient, rid, rr = _run(tmp_path)  # H1(1260)/H2(1255) are a near-tie, both active
    # overwrite wave4 so NO validation carries a discrimination_target
    (rr / "wave4_validation.json").write_text(json.dumps({"validations": [
        {"hyp_id": "H1", "survival_status": "validated"},
        {"hyp_id": "H2", "survival_status": "validated"}]}))
    out = CliRunner().invoke(validate, ["--patient", str(patient), "--run-id", rid, "--json"])
    codes = {p["code"] for p in json.loads(out.output)["problems"]}
    assert "INFORMATIVE_SELECTION_SKIPPED" in codes
    # and it clears once a discrimination_target is recorded
    (rr / "wave4_validation.json").write_text(json.dumps({"validations": [
        {"hyp_id": "H1", "survival_status": "validated", "discrimination_target": ["H1", "H2"]},
        {"hyp_id": "H2", "survival_status": "validated"}]}))
    out2 = CliRunner().invoke(validate, ["--patient", str(patient), "--run-id", rid, "--json"])
    assert "INFORMATIVE_SELECTION_SKIPPED" not in {p["code"] for p in json.loads(out2.output)["problems"]}


def test_informative_selection_no_warn_when_unscored(tmp_path):
    """review-P2: survivors with no elo_rating are not a 0-point tie → no WARN."""
    patient = tmp_path / "P"
    rid = "r1"
    rr = patient / "triggers" / rid
    rr.mkdir(parents=True)
    (rr / "wave2_hypotheses.json").write_text(json.dumps({"hypotheses": [
        {"id": "H1", "text": "a", "status": "active"},   # no elo_rating
        {"id": "H2", "text": "b", "status": "active"}]}))  # no elo_rating
    (rr / "wave4_validation.json").write_text(json.dumps({"validations": [
        {"hyp_id": "H1", "survival_status": "validated"},
        {"hyp_id": "H2", "survival_status": "validated"}]}))
    out = CliRunner().invoke(validate, ["--patient", str(patient), "--run-id", rid, "--json"])
    assert "INFORMATIVE_SELECTION_SKIPPED" not in {p["code"] for p in json.loads(out.output)["problems"]}


def test_emit_funnel_writes_file(tmp_path):
    """✗④: deterministic funnel.json emitter (called by delivery_runner)."""
    patient, rid, rr = _run(tmp_path)
    from opl_cancer.glue.funnel import emit_funnel
    fn = emit_funnel(rr)
    assert fn["run_id"] == rid and (rr / "funnel.json").is_file()
    assert json.loads((rr / "funnel.json").read_text())["explored"] == 3


# ── iteration-2/3: ✗② loop-until-dry convergence (single-source-of-truth) ──
def _run_children(tmp_path, kids, max_depth=3):
    """kids: list of (id, status, parent_chain). H1/H2 are root leads."""
    patient = tmp_path / "P"
    rid = "r1"
    rr = patient / "triggers" / rid
    rr.mkdir(parents=True)
    (rr / "plan.json").write_text(json.dumps({"max_depth": max_depth, "deepen_candidates": ["H2"]}))
    hyps = [
        {"id": "H1", "text": "a", "elo_rating": 1260, "status": "active", "parent_chain": []},
        {"id": "H2", "text": "b", "elo_rating": 1255, "status": "active", "parent_chain": []},
    ]
    for (hid, st, pc) in kids:
        h = {"id": hid, "text": hid, "elo_rating": 1230, "parent_chain": pc}
        if st is not None:
            h["status"] = st
        hyps.append(h)
    (rr / "wave2_hypotheses.json").write_text(json.dumps({"hypotheses": hyps}))
    return patient, rid, rr


def test_deepen_dry_is_advisory_exit_zero(tmp_path):
    """✗②: all direct children falsified → DRY, but it's an ADVISORY stop (exit 0)."""
    patient, rid, rr = _run_children(tmp_path, [("H2a", "falsified", ["H2"]), ("H2b", "falsified", ["H2"])])
    out = CliRunner().invoke(deepen, ["--patient", str(patient), "--run-id", rid, "--target", "H2", "--json"])
    d = json.loads(out.output)
    assert out.exit_code == 0 and d["ok"] is False and d["reason"] == "direction_dry" and d["children_explored"] == 2


def test_deepen_fresh_new_children_not_dry(tmp_path):
    """✗② review-P1: freshly scaffolded children (status 'new'/missing) are PENDING,
    not dead — the loop must NOT declare the direction it just created as dry."""
    for st in ("new", None):
        patient, rid, rr = _run_children(tmp_path / str(st), [("H2a", st, ["H2"])])
        out = CliRunner().invoke(deepen, ["--patient", str(patient), "--run-id", rid, "--target", "H2", "--json"])
        assert json.loads(out.output).get("reason") != "direction_dry", f"status={st} wrongly read as dry"


def test_deepen_inconclusive_child_not_dry(tmp_path):
    """✗② review-P1: an inconclusive Wave-4 verdict is PENDING (needs more), not dry."""
    patient, rid, rr = _run_children(tmp_path, [("H2a", "active", ["H2"])])
    (rr / "wave4_validation.json").write_text(json.dumps({"validations": [{"hyp_id": "H2a", "survival_status": "inconclusive"}]}))
    out = CliRunner().invoke(deepen, ["--patient", str(patient), "--run-id", rid, "--target", "H2", "--json"])
    assert json.loads(out.output).get("reason") != "direction_dry"


def test_saturated_and_retired_are_dead(tmp_path):
    """✗② review-P1: schema statuses 'saturated'/'retired' count as terminally dead."""
    patient, rid, rr = _run_children(tmp_path, [("H2a", "saturated", ["H2"]), ("H2b", "retired", ["H2"])])
    out = CliRunner().invoke(deepen, ["--patient", str(patient), "--run-id", rid, "--target", "H2", "--json"])
    assert json.loads(out.output)["reason"] == "direction_dry"


def test_deepen_grandchild_keeps_alive_not_masked(tmp_path):
    """✗② review-P1: a dead DIRECT child but a live GRANDCHILD → not dry; the
    frontier correctly advances to the live grandchild (max_depth=4 leaves room)."""
    patient, rid, rr = _run_children(
        tmp_path, [("H2a", "falsified", ["H2"]), ("H2a1", "active", ["H2a", "H2"])], max_depth=4)
    d = json.loads(CliRunner().invoke(deepen, ["--patient", str(patient), "--run-id", rid, "--target", "H2", "--json"]).output)
    assert d["ok"] is True and d["frontier"] == "H2a1" and d["frontier_depth"] == 3


def test_deepen_terminates_at_true_depth(tmp_path):
    """✗② review-P1: depth uses the forest walk, so a true depth-3 chain at
    max_depth=3 is budget_spent (len-based depth would have saturated at 2)."""
    patient, rid, rr = _run_children(
        tmp_path, [("H2a", "active", ["H2"]), ("H2a1", "active", ["H2a", "H2"])], max_depth=3)
    d = json.loads(CliRunner().invoke(deepen, ["--patient", str(patient), "--run-id", rid, "--target", "H2", "--json"]).output)
    assert d["ok"] is False and d["reason"] == "depth_budget_exhausted" and d["frontier_depth"] == 3


def test_observe_candidate_state_matches_deepen(tmp_path):
    """✗② review-P1: observe's candidate_states must not disagree with deepen's action."""
    patient, rid, rr = _run_children(tmp_path, [("H2a", "falsified", ["H2"]), ("H2b", "falsified", ["H2"])])
    j = json.loads(CliRunner().invoke(observe, ["--patient", str(patient), "--run-id", rid, "--json"]).output)
    assert j["depth"]["candidate_states"]["H2"] == "dry (converged)"
    assert "dry (converged)" in CliRunner().invoke(observe, ["--patient", str(patient), "--run-id", rid]).output


# ── iteration-4: review P0 (livelock) + P1 (dead target) ────────────────
def test_deepen_awaiting_judgement_breaks_livelock(tmp_path):
    """review-P0: a target whose children are all PENDING returns awaiting_judgement
    (advisory, exit 0) — the host must NOT spawn more, so an all-inconclusive loop
    cannot livelock. depth never advances on pending → this is the structural stop."""
    patient, rid, rr = _run_children(tmp_path, [("H2a", "new", ["H2"])])
    out = CliRunner().invoke(deepen, ["--patient", str(patient), "--run-id", rid, "--target", "H2", "--json"])
    d = json.loads(out.output)
    assert out.exit_code == 0 and d["ok"] is False and d["reason"] == "awaiting_judgement" and d["pending"] == 1
    # inconclusive (Wave-4) children behave identically
    patient2, rid2, rr2 = _run_children(tmp_path / "b", [("H2a", "active", ["H2"])])
    (rr2 / "wave4_validation.json").write_text(json.dumps({"validations": [{"hyp_id": "H2a", "survival_status": "inconclusive"}]}))
    d2 = json.loads(CliRunner().invoke(deepen, ["--patient", str(patient2), "--run-id", rid2, "--target", "H2", "--json"]).output)
    assert d2["reason"] == "awaiting_judgement"


def test_deepen_refuses_dead_target(tmp_path):
    """review-P1: a Wave-4-falsified lead is never recommended for deepening
    (false-hope guard), even if it has pending children."""
    patient, rid, rr = _run_children(tmp_path, [("H2a", "new", ["H2"])])
    (rr / "wave4_validation.json").write_text(json.dumps({"validations": [{"hyp_id": "H2", "survival_status": "falsified"}]}))
    d = json.loads(CliRunner().invoke(deepen, ["--patient", str(patient), "--run-id", rid, "--target", "H2", "--json"]).output)
    assert d["ok"] is False and d["reason"] == "target_dead"
    # and a schema-falsified target (no wave4) is also refused
    patient2, rid2, rr2 = _run_children(tmp_path / "b", [])
    import json as _j
    h = _j.loads((rr2 / "wave2_hypotheses.json").read_text())
    for x in h["hypotheses"]:
        if x["id"] == "H2":
            x["status"] = "falsified"
    (rr2 / "wave2_hypotheses.json").write_text(_j.dumps(h))
    d2 = _j.loads(CliRunner().invoke(deepen, ["--patient", str(patient2), "--run-id", rid2, "--target", "H2", "--json"]).output)
    assert d2["reason"] == "target_dead"
