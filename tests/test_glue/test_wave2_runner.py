"""P2-T16: Wave2Runner end-to-end (hypothesis generation + tournament + reflection)."""
from __future__ import annotations

import json
from pathlib import Path

from opl_cancer.glue.wave2_runner import (
    Wave2Runner,
    lock_top_k_forecasts,
    write_tournament_audit,
)
from opl_cancer._llm_contract import LLMRequest, LLMResponse
from opl_cancer.memory.schemas import Hypothesis
from opl_cancer.orchestrator.debate import DebateJudge
from opl_cancer.orchestrator.evolution import EvolutionStrategist
from opl_cancer.orchestrator.generation import HypothesisGenerator
from opl_cancer.orchestrator.meta_critique import MetaCritiqueAggregator
from opl_cancer.orchestrator.reflection import Reflector
from opl_cancer.validators.gates.g49_forecast_pre_registration import (
    G49ForecastPreRegistrationGate,
    forecast_payload_hash,
)
from opl_cancer.validators.gates.g50_tournament_kill_recorded import (
    G50TournamentKillRecordedGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


class _SeqClient:
    """Cycles through canned responses keyed by call index."""

    provider = "fake"

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.idx = 0

    async def complete(self, request: LLMRequest) -> LLMResponse:
        body = self.responses[self.idx % len(self.responses)]
        self.idx += 1
        return LLMResponse(content=body, model=request.model)


_GEN_JSON = (
    '{"text":"H novel direction","rationale":"r","evidence_refs":[{"type":"pmid","id":"123"}],'
    '"prior_expectation":{"predicted_wave3_result":"signal X up","confidence_0_1":0.6}}'
)
_EVOLVE_JSON = '{"text":"H evolved","rationale":"r2","evidence_refs":[]}'
_JUDGE_JSON = '{"winner":"A","reason":"stronger"}'
_META_JSON = '{"meta_critique":"Round critique"}'
_REFLECT_JSON = '{"verdict":"passes","rationale":"clean"}'


def _make_runner(tmp_path: Path) -> Wave2Runner:
    # Each component gets its own seq client (they consume from different streams)
    gen_client = _SeqClient([_GEN_JSON] * 4)
    evo_client = _SeqClient([_EVOLVE_JSON] * 2)
    judge_client = _SeqClient([_JUDGE_JSON] * 50)
    meta_client = _SeqClient([_META_JSON] * 10)
    refl_client = _SeqClient([_REFLECT_JSON] * 10)

    return Wave2Runner(
        out_dir=tmp_path / "out",
        hypothesis_generator=HypothesisGenerator(gen_client, executor_model_id="claude-opus-4-7"),
        evolution_strategist=EvolutionStrategist(evo_client, executor_model_id="claude-opus-4-7"),
        reflector=Reflector(refl_client, reviewer_model_id="minimax-m2-7"),
        judge=DebateJudge(judge_client, reviewer_model_id="minimax-m2-7"),
        aggregator=MetaCritiqueAggregator(meta_client, reviewer_model_id="minimax-m2-7"),
        max_tournament_rounds=1,
    )


async def test_wave2_runner_produces_hypotheses(tmp_path: Path) -> None:
    runner = _make_runner(tmp_path)
    out = await runner.run("What novel directions exist?", patient_context={"cancer": "HCC"})
    # v2.0.0 (ADR-0010): 6 from generation (was 4) + 2 from evolution = 8
    assert len(out["hypotheses"]) == 8
    assert len(out["top_k"]) <= 5


async def test_wave2_runner_writes_json(tmp_path: Path) -> None:
    runner = _make_runner(tmp_path)
    out = await runner.run("?", patient_context={})
    run_dir = tmp_path / "out" / out["run_id"]
    assert (run_dir / "wave2_hypotheses.json").exists()
    payload = json.loads((run_dir / "wave2_hypotheses.json").read_text())
    assert "hypotheses" in payload
    assert "rounds" in payload
    assert "reflections" in payload


async def test_wave2_runner_provenance_written(tmp_path: Path) -> None:
    runner = _make_runner(tmp_path)
    out = await runner.run("?", patient_context={})
    prov = tmp_path / "out" / out["run_id"] / "provenance.jsonl"
    assert prov.exists()
    lines = prov.read_text().strip().splitlines()
    assert len(lines) >= 6  # one per hypothesis


async def test_wave2_runner_reflections_per_top_hypothesis(tmp_path: Path) -> None:
    runner = _make_runner(tmp_path)
    out = await runner.run("?", patient_context={})
    assert len(out["reflections"]) <= 3
    for r in out["reflections"]:
        assert "basic" in r
        assert "falsification" in r


async def test_wave2_runner_records_tournament_kills(tmp_path: Path) -> None:
    """C1/ADR-0031: an 8-candidate tournament must record its discard decision
    (the discard-the-wrong half of the loop) — kills, or an explicit all-survived
    justification — so G50 passes on the produced run dir end to end."""
    runner = _make_runner(tmp_path)
    out = await runner.run("?", patient_context={})
    run_dir = tmp_path / "out" / out["run_id"]

    res = G50TournamentKillRecordedGate().check({"run_root": str(run_dir)})
    assert res.status == GateStatus.PASS, res.message
    # exactly one audit artifact records the decision (never silently missing)
    assert (
        (run_dir / "killed_candidates.jsonl").is_file()
        or (run_dir / "tournament_all_survived.json").is_file()
    ), "a >=4-candidate tournament must persist its discard decision"


# ── C1 producer helper: the discard-record writer (deterministic, both branches) ──

def _seed_wave2(run_dir: Path, n: int) -> None:
    """Mirror what the runner writes before write_tournament_audit — G50 reads
    the candidate count from wave2_hypotheses.json."""
    (run_dir / "wave2_hypotheses.json").write_text(
        json.dumps({"hypotheses": [{"id": f"h{i}"} for i in range(n)]}), encoding="utf-8"
    )


def test_write_tournament_audit_records_kills(tmp_path: Path) -> None:
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    _seed_wave2(run_dir, 8)
    write_tournament_audit(
        run_dir,
        killed_candidates=[
            {"hyp_id": "h7", "final_elo": 1150.0, "kill_reason": "dominated"},
            {"hyp_id": "h6", "final_elo": 1170.0, "kill_reason": "dominated"},
        ],
        n_candidates=8,
    )
    p = run_dir / "killed_candidates.jsonl"
    assert p.is_file()
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
    rec = json.loads(lines[0])
    assert {"hyp_id", "final_elo", "kill_reason"} <= set(rec), rec
    # the kill record makes a 8-candidate tournament pass G50
    assert G50TournamentKillRecordedGate().check({"run_root": str(run_dir)}).status == GateStatus.PASS
    # the runner did not also leave a contradictory all-survived file
    assert not (run_dir / "tournament_all_survived.json").exists()


def test_write_tournament_audit_all_survived(tmp_path: Path) -> None:
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    _seed_wave2(run_dir, 8)
    write_tournament_audit(run_dir, killed_candidates=[], n_candidates=8)
    p = run_dir / "tournament_all_survived.json"
    assert p.is_file()
    payload = json.loads(p.read_text(encoding="utf-8"))
    assert payload["candidates"] == 8 and payload["killed"] == 0 and payload["justification"]
    # an explicit all-survived justification also passes G50
    assert G50TournamentKillRecordedGate().check({"run_root": str(run_dir)}).status == GateStatus.PASS
    assert not (run_dir / "killed_candidates.jsonl").exists()


def test_write_tournament_audit_small_field_is_noop(tmp_path: Path) -> None:
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    write_tournament_audit(run_dir, killed_candidates=[], n_candidates=2)  # <4 → not required
    assert not (run_dir / "killed_candidates.jsonl").exists()
    assert not (run_dir / "tournament_all_survived.json").exists()


# ── C2/ADR-0032 producer: lock the top-k forecasts before Wave 3 ──

def test_lock_top_k_forecasts_locks_only_forecasted() -> None:
    h1 = Hypothesis(
        id="h1", text="t1",
        prior_expectation={"predicted_wave3_result": "x", "confidence_0_1": 0.6},
    )
    h2 = Hypothesis(id="h2", text="t2")  # carries no pre-data forecast
    by_id = {"h1": h1, "h2": h2}
    n = lock_top_k_forecasts(by_id, ["h1", "h2"], locked_at="2026-06-01T00:00:00+00:00")
    assert n == 1
    assert h1.forecast_locked_at == "2026-06-01T00:00:00+00:00"
    assert h1.forecast_hash == forecast_payload_hash(h1.prior_expectation)
    # a forecast-less hypothesis is left untouched (never fabricated)
    assert h2.forecast_locked_at is None and h2.forecast_hash is None


def test_lock_top_k_forecasts_result_passes_g49() -> None:
    h1 = Hypothesis(
        id="h1", text="t1",
        prior_expectation={"predicted_wave3_result": "x", "confidence_0_1": 0.6},
    )
    lock_top_k_forecasts({"h1": h1}, ["h1"], locked_at="2026-06-01T00:00:00+00:00")
    res = G49ForecastPreRegistrationGate().check({
        "hypothesis_id": "h1",
        "prior_expectation": h1.prior_expectation,
        "forecast_locked_at": h1.forecast_locked_at,
        "forecast_hash": h1.forecast_hash,
        "wave3_data_at": None,  # no Wave-3 data yet (non-Docker path)
    })
    assert res.status == GateStatus.PASS, res.message


async def test_wave2_runner_locks_top_k_forecasts(tmp_path: Path) -> None:
    """C2/ADR-0032: top-k hypotheses carrying a pre-data forecast are locked at
    Wave 2 (timestamp + tamper hash) before any Wave-3 data, end to end."""
    runner = _make_runner(tmp_path)
    out = await runner.run("?", patient_context={})
    locked = [h for h in out["hypotheses"] if h.get("forecast_locked_at")]
    assert locked, "at least one top-k forecasted hypothesis must be locked"
    for h in locked:
        assert h["forecast_hash"] == forecast_payload_hash(h["prior_expectation"])
