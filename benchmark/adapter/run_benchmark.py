#!/usr/bin/env python3
"""Run SBT benchmark CRC items through baseline (direct LLM) and MTB-lite arms.

Writes raw_outputs.jsonl in the format expected by
``SBT_Benchmark/scripts/score_model_outputs.py``.

Usage:
    OPENROUTER_API_KEY=sk-... \
    python run_benchmark.py \
        --benchmark-root ../SBT_Benchmark \
        --out-dir ../runs/crc_pilot \
        --model openai/gpt-4o-mini \
        --n 20 \
        --arms baseline,mtb
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mtb_lite
import mtb_full
import opl_full


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            items.append(json.loads(line))
            if limit is not None and len(items) >= limit:
                break
    return items


def select_crc_items(benchmark_root: Path, n: int) -> list[dict[str, Any]]:
    return read_jsonl(benchmark_root / "tmp" / "Case_version" / "input.jsonl", limit=n)


def select_nccn_crc_items(benchmark_root: Path, n: int) -> list[dict[str, Any]]:
    """Pick the n NCCN-sourced CRC items (workspace_id in 结肠癌 / 直肠癌).

    Returns up to ``n`` items, balanced across the two CRC workspaces.
    """
    items = read_jsonl(benchmark_root / "tmp" / "NCCN_version" / "input.jsonl")
    crc_kw = ("结肠", "直肠", "结直肠")
    crc_items = [it for it in items if any(kw in (it.get("workspace_id") or "") for kw in crc_kw)]
    by_ws: dict[str, list[dict[str, Any]]] = {}
    for it in crc_items:
        by_ws.setdefault(it.get("workspace_id") or "?", []).append(it)
    # Balance: round-robin across workspaces until n.
    selected: list[dict[str, Any]] = []
    idx = 0
    while len(selected) < n:
        added_this_round = False
        for ws in sorted(by_ws.keys()):
            if idx < len(by_ws[ws]):
                selected.append(by_ws[ws][idx])
                added_this_round = True
                if len(selected) >= n:
                    break
        if not added_this_round:
            break
        idx += 1
    return selected[:n]


def build_case_facts(item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    payload = dict(item.get("input", {}))
    payload.pop("source", None)
    case_id = item.get("case_id") or payload.get("case_id") or item.get("package_item_id")
    return str(case_id), payload


def build_nccn_facts(item: dict[str, Any]) -> tuple[str, str, list[dict[str, Any]], str]:
    """Returns (item_id, scenario_label, patient_facts, cancer_type_hint)."""
    item_id = item.get("item_id") or item.get("canonical_item_id") or item.get("package_item_id")
    inp = item.get("input") or {}
    doctor_input = inp.get("doctor_facing_input") or {}
    scenario_label = (inp.get("decision_frontier") or {}).get("scenario_label") or ""
    patient_facts = doctor_input.get("patient_facts") or []
    ws = (item.get("workspace_id") or "").lower()
    if "直肠" in ws:
        cancer = "RECTAL_CANCER"
    elif "结直肠" in ws:
        cancer = "COLORECTAL_CANCER"
    else:
        cancer = "COLON_CANCER"
    return str(item_id), str(scenario_label), patient_facts, cancer


def run_one(arm: str, model: str, case_id: str, case_facts: dict[str, Any], surface: str = "crc_case") -> dict[str, Any]:
    try:
        if surface == "crc_case":
            if arm == "baseline":
                result = mtb_lite.run_baseline(model, case_id, case_facts)
                model_tag = f"baseline::{model}"
            elif arm == "mtb":
                result = mtb_lite.run_mtb(model, case_id, case_facts)
                model_tag = f"mtb-lite::{model}"
            elif arm == "mtb-full":
                result = mtb_full.run_full_mtb(model, case_id, case_facts)
                model_tag = f"mtb-full::{model}"
            elif arm == "opl-anchor":
                result = opl_full.run_opl_anchor(model, case_id, case_facts)
                model_tag = f"opl-anchor::{model}"
            elif arm == "opl-full":
                result = opl_full.run_opl_full(model, case_id, case_facts)
                model_tag = f"opl-full::{model}"
            else:
                raise ValueError(f"Unknown arm for crc_case: {arm}")
        elif surface == "nccn_structured":
            scenario_label = case_facts.get("__scenario_label", "")
            patient_facts = case_facts.get("__patient_facts", [])
            cancer_hint = case_facts.get("__cancer_type_hint", "COLON_CANCER")
            if arm == "baseline":
                result = mtb_lite.run_baseline_nccn(model, case_id, scenario_label, patient_facts)
                model_tag = f"baseline::{model}"
            elif arm == "mtb":
                result = mtb_lite.run_mtb_nccn(model, case_id, scenario_label, patient_facts, cancer_type_hint=cancer_hint)
                model_tag = f"mtb-lite::{model}"
            elif arm == "mtb-full":
                result = mtb_full.run_full_mtb_nccn(model, case_id, scenario_label, patient_facts, cancer_type_hint=cancer_hint)
                model_tag = f"mtb-full::{model}"
            elif arm == "opl-anchor":
                result = opl_full.run_opl_anchor_nccn(model, case_id, scenario_label, patient_facts, cancer_type_hint=cancer_hint)
                model_tag = f"opl-anchor::{model}"
            elif arm == "opl-full":
                result = opl_full.run_opl_full_nccn(model, case_id, scenario_label, patient_facts, cancer_type_hint=cancer_hint)
                model_tag = f"opl-full::{model}"
            else:
                raise ValueError(f"Unknown arm for nccn_structured: {arm}")
        else:
            raise ValueError(f"Unknown surface: {surface}")
    except Exception as exc:  # noqa: BLE001
        return {
            "model": f"{arm}::{model}",
            "surface": surface,
            "item_id": case_id,
            "ok": False,
            "elapsed_seconds": None,
            "finish_reason": None,
            "content_present": False,
            "json_parse_ok": False,
            "parsed_json": None,
            "raw_response": None,
            "error": {"error_type": type(exc).__name__, "error": str(exc)},
            "intermediate": None,
        }
    return {
        "model": model_tag,
        "surface": surface,
        "item_id": case_id,
        "ok": result["ok"],
        "elapsed_seconds": result["elapsed_seconds"],
        "finish_reason": result.get("finish_reason"),
        "content_present": result["content_present"],
        "json_parse_ok": result["json_parse_ok"],
        "parsed_json": result["parsed_json"],
        "raw_response": result.get("raw_response"),
        "error": result.get("error"),
        "intermediate": result.get("intermediate"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-root", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--model", default=os.environ.get("BENCH_MODEL", "openai/gpt-4o-mini"))
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--arms", default="baseline,mtb")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--surface", default="crc_case", choices=["crc_case", "nccn_structured"])
    args = parser.parse_args()

    if not os.environ.get("OPENROUTER_API_KEY"):
        raise SystemExit("OPENROUTER_API_KEY env var is required.")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = args.out_dir / "raw_outputs.jsonl"

    arms = [a.strip() for a in args.arms.split(",") if a.strip()]

    tasks: list[dict[str, Any]] = []
    if args.surface == "crc_case":
        items = select_crc_items(args.benchmark_root, args.n)
        for item in items:
            case_id, case_facts = build_case_facts(item)
            for arm in arms:
                tasks.append({"arm": arm, "case_id": case_id, "case_facts": case_facts})
    else:  # nccn_structured
        items = select_nccn_crc_items(args.benchmark_root, args.n)
        for item in items:
            item_id, scenario_label, patient_facts, cancer_hint = build_nccn_facts(item)
            facts_bundle = {
                "__scenario_label": scenario_label,
                "__patient_facts": patient_facts,
                "__cancer_type_hint": cancer_hint,
            }
            for arm in arms:
                tasks.append({"arm": arm, "case_id": item_id, "case_facts": facts_bundle})

    manifest = {
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "model": args.model,
        "arms": arms,
        "surface": args.surface,
        "n_items": len(items),
        "n_tasks": len(tasks),
        "concurrency": args.concurrency,
        "benchmark_root": str(args.benchmark_root.resolve()),
        "raw_outputs": str(raw_path.resolve()),
    }
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[manifest] {json.dumps(manifest, ensure_ascii=False)}")

    lock = threading.Lock()
    completed = 0
    started_at = time.time()
    with raw_path.open("w", encoding="utf-8") as handle, ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(run_one, t["arm"], args.model, t["case_id"], t["case_facts"], args.surface) for t in tasks]
        for fut in as_completed(futures):
            record = fut.result()
            with lock:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
                completed += 1
                elapsed = round(time.time() - started_at, 1)
                print(
                    f"{completed}/{len(tasks)} t={elapsed}s",
                    "OK" if record["ok"] else "FAIL",
                    record["model"],
                    record["item_id"],
                    f"json={record['json_parse_ok']}",
                    flush=True,
                )

    print(f"OUTPUT_DIR={args.out_dir}")
    print(f"RAW_OUTPUTS={raw_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
