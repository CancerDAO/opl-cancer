#!/usr/bin/env python3
"""Live v2 paradigm E2E test with MiniMax-M2.7.

Validates the wired path from v2.0.1 with REAL LLM calls (not mocks):
  1. Load PT-EE62321353 patient profile.
  2. For each of the 6 v2 generation strategies, call MiniMax-M2.7 to
     produce a real hypothesis. Specifically:
       - 2 v2 strategies (target_synergy_emergent + undrugged_target_design)
         are the load-bearing test — these must produce concrete
         testability_path values.
  3. Write a wave2_hypotheses.json to the synthetic run dir.
  4. Build render context using render_bridge (the new wiring fix).
  5. Render patient_brief.html + .md.
  6. Save artefacts for multi-perspective subagent review.

Honest disclosure: this is a focused Wave 2 + Wave 5 test, NOT a full
5-wave run (which requires ~$10-30 + 20-40 min per patient). Wave 1 / 3 / 4
runners are unchanged from v1.5.7 and exercised by existing tests.

Usage:
    MINIMAX_API_KEY=sk-cp-... python3 scripts/live_v2_e2e_minimax.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from opl_cancer.glue.render_bridge import load_world_unknown_candidates
from opl_cancer.glue.renderer import PatientBriefRenderer
from opl_cancer.llm.base import LLMRequest
from opl_cancer.llm.minimax_client import MiniMaxClient
from opl_cancer.orchestrator.generation import (
    STRATEGIES,
    _STRATEGY_GUIDANCE,
)


PATIENT_DIR = Path("/Users/baozhiwei/cancerdao/patients/PT-EE62321353")
OUT_DIR = REPO_ROOT / "tmp_live_v2_e2e"


SYSTEM_PROMPT = """You are a generation slot inside OPL for Cancer's Wave 2
hypothesis tournament. You are NOT giving treatment advice; you are
producing one structured hypothesis card per call.

Boundaries:
- patient is the sole decision authority.
- claim_layer MUST be "speculative" for v2 strategies (target_synergy_emergent
  + undrugged_target_design).
- testability_path MUST be concrete (≥ 20 chars, reference a real dataset /
  assay / pipeline like DepMap, GEO, CRISPR PDX, BLI, ctDNA, scRNA-seq,
  ESMFold + DiffDock, organoid).
- For undrugged_target_design: include candidate_smiles only if you can
  cite the chemical scaffold rationale. LLM-self-reported lipinski / PAINS
  flags will be overridden by the mechanical chemistry gate.
- Cite evidence_refs (pmid / kg_edge / dataset). For v2 strategies an
  empty pmid list is acceptable; provide kg_edge anchors instead.
"""


def build_user_prompt(strategy: str, profile: dict) -> str:
    return f"""Strategy: {strategy}

Strategy guidance:
{_STRATEGY_GUIDANCE[strategy]}

Patient profile (JSON, partial):
```json
{json.dumps(profile, ensure_ascii=False)[:4000]}
```

Return strict JSON:
{{
  "id": "hyp_<8-char>",
  "text": "<one-sentence statement>",
  "rationale": "<2-4 sentences>",
  "generation_strategy": "{strategy}",
  "claim_layer": "speculative",
  "testability_path": "<concrete next-step>",
  "evidence_refs": [{{"type": "kg_edge|pmid|dataset", "id": "<id>"}}]
}}
"""


import re

_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_LAST_OBJ = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)


def _extract_json(text: str) -> dict:
    """MiniMax-M2.7 is a reasoning model — it emits thinking + JSON in the
    same content string. Strip markdown fences first, then fall back to the
    last balanced object."""
    if not text:
        raise ValueError("empty content")
    m = _JSON_FENCE.search(text)
    if m:
        return json.loads(m.group(1))
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Find the last balanced top-level object
    matches = list(_LAST_OBJ.finditer(text))
    for m in reversed(matches):
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    raise ValueError(f"no JSON object found in content[:200]={text[:200]!r}")


async def generate_one(client: MiniMaxClient, strategy: str, profile: dict) -> dict:
    # Per memory:reference_minimax_llm — M2.7 is a reasoning model; allow 96K
    # max_tokens so reasoning + JSON fit. response_format=json_object hints
    # but MiniMax doesn't strictly enforce; we parse defensively.
    req = LLMRequest(
        model="MiniMax-M2.7",
        messages=[{"role": "user", "content": build_user_prompt(strategy, profile)}],
        system=SYSTEM_PROMPT,
        max_tokens=96000,
        response_format={"type": "json_object"},
        temperature=0.4,
    )
    resp = await client.complete(req)
    parsed = _extract_json(resp.content)
    parsed["generation_strategy"] = strategy
    parsed["claim_layer"] = parsed.get("claim_layer", "speculative")
    return parsed


async def main() -> int:
    if not os.environ.get("MINIMAX_API_KEY"):
        print("MINIMAX_API_KEY not set", file=sys.stderr)
        return 2

    profile_path = PATIENT_DIR / "profile.json"
    if not profile_path.exists():
        print(f"profile.json missing at {profile_path}", file=sys.stderr)
        return 2

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(exist_ok=True)
    run_dir = OUT_DIR / f"live-v2-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    run_dir.mkdir()

    client = MiniMaxClient()
    print(f"[live-e2e] starting 6-strategy generation with MiniMax-M2.7 on {profile.get('patient_code')}")
    t0 = time.monotonic()

    hypotheses = []
    for strat in STRATEGIES:
        print(f"[live-e2e] generating {strat} ...")
        try:
            h = await generate_one(client, strat, profile)
            hypotheses.append(h)
            print(f"[live-e2e]   {strat} OK — {len(h.get('text',''))} chars text")
        except Exception as exc:  # noqa: BLE001
            print(f"[live-e2e]   {strat} FAIL: {type(exc).__name__}: {exc}")
            hypotheses.append({
                "id": f"hyp_{strat}_fail",
                "text": f"(generation failed: {exc})",
                "generation_strategy": strat,
                "claim_layer": "speculative",
                "rationale": "live LLM call failed; logged for review",
                "evidence_refs": [],
            })

    wall = time.monotonic() - t0

    wave2_path = run_dir / "wave2_hypotheses.json"
    wave2_path.write_text(
        json.dumps(
            {
                "run_id": run_dir.name,
                "patient_text": "PT-EE62321353 KRAS G12C MSS mCRC L4+",
                "hypotheses": hypotheses,
                "wall_time_seconds": round(wall, 2),
                "model": "MiniMax-M2.7",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[live-e2e] wrote {wave2_path}")

    # v2.0.1 wiring fix: render_bridge populates world_unknown_candidates
    world_unknown = load_world_unknown_candidates(run_dir)
    print(f"[live-e2e] render_bridge surfaced {len(world_unknown)} world-unknown candidates")

    renderer = PatientBriefRenderer()
    delivery_dir = run_dir / "delivery"
    delivery_dir.mkdir()
    ctx = {
        "language": "zh",
        "patient_code": profile.get("patient_code", "UNKNOWN"),
        "run_id": run_dir.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sid_summary": (
            "本次 run 仅作为 v2.0.2 范式验证 — Wave 2 + Wave 5 已跑，"
            "Wave 1/3/4 未运行；评估完整治疗方案请等待真实 5-wave 输出。"
        ),
        "run_incomplete_notice": (
            "Wave 1 (临床检索) / Wave 3 (数据证据生成) / Wave 4 (假设验证) "
            "在本次 run 中未运行。下方 Findings by Expert 为空，World-Unknown "
            "Candidates 仅基于 Wave 2 的 LLM 推测，未经 Wave 3 数据反向验证。"
        ),
        "experts": [],  # not exercised in this focused test
        "risk_cards": [],
        "world_unknown_candidates": world_unknown,
    }
    renderer.render_html(ctx, delivery_dir / "patient_brief.html")
    renderer.render_md(ctx, delivery_dir / "patient_brief.md")
    print(f"[live-e2e] rendered {delivery_dir / 'patient_brief.html'}")

    print(f"[live-e2e] DONE — wall time {wall:.1f}s, run_dir={run_dir}")
    print(f"[live-e2e] inspect: cat {delivery_dir}/patient_brief.md")
    print(f"[live-e2e] inspect: open {delivery_dir}/patient_brief.html")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
