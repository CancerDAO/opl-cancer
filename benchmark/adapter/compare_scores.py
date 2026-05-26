#!/usr/bin/env python3
"""Compare baseline vs MTB-lite arms from a benchmark scoring run.

Reads ``summary.json`` from ``score_model_outputs.py`` output and emits a
markdown comparison report.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


KEY_METRICS = [
    ("CRC therapy F1@3 (full denom)", ("crc", "therapy_f1_at3_full_denominator")),
    ("CRC therapy F1@3 (scorable only)", ("crc", "therapy_f1_at3_scorable_only")),
    ("CRC strict therapy F1@3", ("crc", "strict_therapy_f1_at3")),
    ("CRC class-level F1@3", ("crc", "class_therapy_f1_at3")),
    ("CRC therapy coverage F1", ("crc", "therapy_coverage_f1")),
    ("CRC nDCG@3", ("crc", "ndcg_at3")),
    ("CRC off-gold rate (lower=better)", ("crc", "off_gold_recommendation_rate")),
    ("CRC unsupported rate (lower=better)", ("crc", "unsupported_recommendation_rate")),
    ("CRC contraindicated rate (lower=better)", ("crc", "contraindicated_recommendation_rate")),
    ("CRC treatment-intent match", ("crc", "treatment_intent_match_rate")),
    ("CRC molecular-context-error (lower=better)", ("crc", "molecular_context_error_rate")),
    ("CRC missing-info F1", ("crc", "missing_info_f1")),
    ("JSON parse rate", (None, "json_parse_rate")),
    ("Schema-valid rate", (None, "schema_valid_rate")),
    ("Raw schema-valid rate", (None, "raw_schema_valid_rate")),
]

LOWER_IS_BETTER = {
    "CRC off-gold rate (lower=better)",
    "CRC unsupported rate (lower=better)",
    "CRC contraindicated rate (lower=better)",
    "CRC molecular-context-error (lower=better)",
}


def fmt(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def get_metric(data: dict, path: tuple[str | None, str]) -> object:
    section, key = path
    if section is None:
        return data.get(key)
    bucket = data.get(section) or {}
    return bucket.get(key)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--arms",
        default="baseline::,mtb-lite::",
        help="Comma-separated list of model-prefix tags to compare, in column order.",
    )
    args = parser.parse_args()

    summary = json.loads((args.scores_dir / "summary.json").read_text())
    by_model: dict[str, dict] = summary.get("by_model") or {}

    arm_prefixes = [a.strip() for a in args.arms.split(",") if a.strip()]
    arms: list[tuple[str, str | None]] = []
    for prefix in arm_prefixes:
        model_id = next((m for m in by_model if m.startswith(prefix)), None)
        arms.append((prefix.rstrip(":"), model_id))

    lines: list[str] = []
    lines.append("# CRC Benchmark — N-way arm comparison")
    lines.append("")
    lines.append(f"Scorer version: `{summary.get('scorer_version')}`")
    lines.append("")
    for tag, model_id in arms:
        lines.append(f"- **{tag} arm:** `{model_id or '(missing)'}`")
    lines.append("")
    n_line_parts: list[str] = []
    for tag, model_id in arms:
        if model_id:
            n_line_parts.append(f"{tag}={by_model[model_id].get('n_total')}")
    if n_line_parts:
        lines.append("- N items per arm: " + ", ".join(n_line_parts))
    lines.append("")

    lines.append("## Metric comparison")
    lines.append("")
    header_cols = ["Metric"] + [tag for tag, _ in arms]
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("| --- | " + " | ".join("---:" for _ in arms) + " |")
    arm_data = [(tag, by_model.get(mid or "", {})) for tag, mid in arms]
    for label, path in KEY_METRICS:
        vals = [get_metric(d, path) for _, d in arm_data]
        cells = [fmt(v) for v in vals]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    lines.append("")
    lines.append("## Failure-label distribution")
    lines.append("")
    lines.append("| Label | " + " | ".join(tag for tag, _ in arms) + " |")
    lines.append("| --- | " + " | ".join("---:" for _ in arms) + " |")
    all_labels: set[str] = set()
    for _, d in arm_data:
        all_labels.update((d.get("failure_labels") or {}).keys())
    for label in sorted(all_labels):
        counts = [(d.get("failure_labels") or {}).get(label, 0) for _, d in arm_data]
        lines.append(f"| {label} | " + " | ".join(str(c) for c in counts) + " |")
    if not all_labels:
        lines.append("| (no failure labels recorded) | " + " | ".join("—" for _ in arms) + " |")

    lines.append("")
    lines.append("## Raw summary blocks")
    lines.append("")
    for tag, model_id in arms:
        if not model_id:
            continue
        lines.append(f"### {tag} (`{model_id}`)")
        lines.append("```json")
        lines.append(json.dumps(by_model.get(model_id, {}), ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")

    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written to {args.out}")
    print("Top-line metric values:")
    print(f"  {'metric':40s}  " + "  ".join(f"{tag:>15s}" for tag, _ in arms))
    for label, path in KEY_METRICS:
        vals = [get_metric(d, path) for _, d in arm_data]
        line = f"  {label:40s}  "
        line += "  ".join(f"{v:15.3f}" if isinstance(v, float) else f"{str(v if v is not None else '-'):>15s}" for v in vals)
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
