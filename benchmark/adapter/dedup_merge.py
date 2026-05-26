#!/usr/bin/env python3
"""Dedup-merge raw_outputs.jsonl files for resumed benchmark runs.

For each (item_id, arm-prefix-of-model) pair across all inputs, pick the best
record using this preference order:

  1. json_parse_ok = True wins over json_parse_ok = False.
  2. If tie, the *last* input file wins (later inputs supersede earlier).

Usage:
    python dedup_merge.py --out merged.jsonl run1.jsonl run2.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def arm_of(model_tag: str) -> str:
    return (model_tag or "").split("::")[0]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("inputs", nargs="+", type=Path)
    args = p.parse_args()

    best: dict[tuple[str, str], dict[str, Any]] = {}
    for src_idx, src in enumerate(args.inputs):
        if not src.exists():
            print(f"[warn] {src} not found, skipping")
            continue
        n_seen = 0
        with src.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                rec = json.loads(line)
                n_seen += 1
                key = (str(rec.get("item_id") or ""), arm_of(rec.get("model") or ""))
                prev = best.get(key)
                if prev is None:
                    best[key] = rec
                    continue
                # Prefer json_parse_ok=True
                prev_json = bool(prev.get("json_parse_ok"))
                new_json = bool(rec.get("json_parse_ok"))
                if new_json and not prev_json:
                    best[key] = rec
                elif new_json == prev_json:
                    # Tie — later input wins
                    best[key] = rec
        print(f"[input {src_idx}] {src.name}: {n_seen} records")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for key in sorted(best.keys()):
            fh.write(json.dumps(best[key], ensure_ascii=False) + "\n")
    n_json = sum(1 for r in best.values() if r.get("json_parse_ok"))
    print(f"[merged] {len(best)} unique (item, arm) pairs → {args.out}")
    print(f"[merged] {n_json} have json_parse_ok=True ({100 * n_json / max(1, len(best)):.1f}%)")
    # Per-arm breakdown
    by_arm: dict[str, list[bool]] = {}
    for rec in best.values():
        arm = arm_of(rec.get("model") or "")
        by_arm.setdefault(arm, []).append(bool(rec.get("json_parse_ok")))
    print("[merged] per-arm json_parse_ok rate:")
    for arm in sorted(by_arm.keys()):
        flags = by_arm[arm]
        rate = sum(flags) / max(1, len(flags))
        print(f"  {arm:14s} : {sum(flags):3d}/{len(flags):3d} = {rate:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
