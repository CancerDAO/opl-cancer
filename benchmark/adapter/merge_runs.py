#!/usr/bin/env python3
"""Merge raw_outputs.jsonl files from multiple runs, renaming model tags.

Usage:
    python merge_runs.py \
        --out merged.jsonl \
        path1.jsonl:keep \
        path2.jsonl:baseline=>baseline-v1,mtb-lite=>mtb-anchor \
        path3.jsonl:mtb-lite=>mtb-pageindex

Each input spec is `<path>:<rename1>,<rename2>,...` where each rename is
`<old_prefix>=><new_prefix>`. The model field starts with `<old_prefix>::<llm>`;
the prefix is swapped to `<new_prefix>` keeping the `::<llm>` suffix intact.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_spec(spec: str) -> tuple[Path, dict[str, str]]:
    if ":" not in spec:
        return Path(spec), {}
    path_part, rules_part = spec.split(":", 1)
    rules: dict[str, str] = {}
    if rules_part and rules_part != "keep":
        for rule in rules_part.split(","):
            if "=>" not in rule:
                continue
            old, new = rule.split("=>", 1)
            rules[old.strip()] = new.strip()
    return Path(path_part), rules


def rename_model(model: str, rules: dict[str, str]) -> str:
    if not rules or "::" not in model:
        return model
    prefix, suffix = model.split("::", 1)
    if prefix in rules:
        return f"{rules[prefix]}::{suffix}"
    return model


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("specs", nargs="+", help="path:rename1,rename2 or path:keep")
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    counts: dict[str, int] = {}
    with args.out.open("w", encoding="utf-8") as out_handle:
        for spec in args.specs:
            path, rules = parse_spec(spec)
            with path.open(encoding="utf-8") as in_handle:
                for line in in_handle:
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    record["model"] = rename_model(record.get("model", ""), rules)
                    out_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                    counts[record["model"]] = counts.get(record["model"], 0) + 1
                    written += 1
    print(f"Merged {written} records → {args.out}")
    for model, n in sorted(counts.items()):
        print(f"  {n:4d}  {model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
