#!/usr/bin/env python3
"""Render the MTB vs OPL n-way comparison report from two scored surfaces.

Takes two ``summary.json`` paths (one per surface) plus the corresponding
raw_outputs.jsonl files for wall-time + LLM-call counts, and emits a single
``REPORT_MTB_vs_OPL.md`` covering both CRC and NCCN.

Usage:
    python render_mtb_vs_opl_report.py \\
        --crc-scores  runs/mtb_vs_opl_n30_crc/scores  \\
        --nccn-scores runs/mtb_vs_opl_n30_nccn/scores \\
        --crc-raw     runs/mtb_vs_opl_n30_crc/raw_outputs.jsonl  \\
        --nccn-raw    runs/mtb_vs_opl_n30_nccn/raw_outputs.jsonl \\
        --out         reports/REPORT_MTB_vs_OPL.md
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ARM_ORDER = ["baseline", "mtb-lite", "mtb-full", "opl-anchor", "opl-full"]
ARM_LABEL = {
    "baseline":    "baseline (1 call)",
    "mtb-lite":    "mtb-anchor (vMTB plan+retrieve+synth)",
    "mtb-full":    "mtb-full (vMTB multi-agent + 3 verifiers)",
    "opl-anchor":  "opl-anchor (OPL Sid plan+retrieve+synth)",
    "opl-full":    "opl-full (OPL Rosa∥Bert+Vince+Sid+Henry-L1)",
}


CRC_METRICS = [
    ("therapy_f1_at3_full_denominator",      False, "CRC therapy F1@3 (full denom)"),
    ("therapy_f1_at3_scorable_only",         False, "CRC therapy F1@3 (scorable only)"),
    ("strict_therapy_f1_at3",                False, "CRC strict therapy F1@3"),
    ("class_therapy_f1_at3",                 False, "CRC class-level F1@3"),
    ("therapy_coverage_f1",                  False, "CRC therapy coverage F1"),
    ("ndcg_at3",                             False, "CRC nDCG@3"),
    ("treatment_intent_match_rate",          False, "CRC treatment-intent match"),
    ("off_gold_recommendation_rate",         True,  "CRC off-gold rate (lower=better)"),
    ("unsupported_recommendation_rate",      True,  "CRC unsupported rate (lower=better)"),
    ("contraindicated_recommendation_rate",  True,  "CRC contraindicated rate (lower=better)"),
    ("molecular_context_error_rate",         True,  "CRC molecular-context error (lower=better)"),
    ("missing_info_f1",                      False, "CRC missing-info F1"),
]


NCCN_METRICS = [
    # NCCN-section metrics are emitted at the top level of by_model[model], not nested.
    ("nccn_structured_decision_concordance_full",     False, "NCCN decision concordance (full denom)"),
    ("nccn_structured_decision_concordance_scorable", False, "NCCN decision concordance (scorable)"),
    ("nccn_structured_decision_concordance_strict",   False, "NCCN decision concordance (strict)"),
    ("nccn_strict_unsafe_overreach_rate",             True,  "NCCN unsafe overreach (lower=better)"),
    ("nccn_false_stop_rate",                          True,  "NCCN false-stop rate (lower=better)"),
    ("nccn_true_false_stop_rate",                     True,  "NCCN true false-stop rate (lower=better)"),
    ("nccn_premature_downstream_commitment_rate",     True,  "NCCN premature commitment (lower=better)"),
    ("nccn_route_label_text_mismatch_rate",           True,  "NCCN route mismatch (lower=better)"),
]


COMMON_METRICS = [
    ("json_parse_rate",        False, "JSON parse rate"),
    ("schema_valid_rate",      False, "Schema-valid rate"),
    ("raw_schema_valid_rate",  False, "Raw schema-valid rate"),
]


def find_arm(by_model: dict, prefix: str) -> tuple[str | None, dict]:
    """Return (full model tag, summary dict) for the arm prefix, or (None, {})."""
    for tag, body in by_model.items():
        if tag.startswith(prefix + "::"):
            return tag, body
    return None, {}


def fmt(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def best(values: list[float | None], lower_better: bool) -> int | None:
    candidates = [(i, v) for i, v in enumerate(values) if isinstance(v, (int, float))]
    if not candidates:
        return None
    pick = min(candidates, key=lambda iv: iv[1]) if lower_better else max(candidates, key=lambda iv: iv[1])
    return pick[0]


def get_metric(body: dict, key: str, surface_section: str) -> Any:
    # NCCN metrics live at top level (`body[key]`). CRC metrics live under `body["crc"]`.
    if key.startswith("nccn_"):
        return body.get(key)
    bucket = body.get(surface_section) or {}
    return bucket.get(key)


def wall_time_stats(raw_path: Path) -> dict[str, dict[str, float]]:
    """Read raw_outputs.jsonl and aggregate elapsed_seconds per arm prefix."""
    by_arm: dict[str, list[float]] = defaultdict(list)
    by_arm_ok: dict[str, int] = defaultdict(int)
    by_arm_total: dict[str, int] = defaultdict(int)
    by_arm_jsonok: dict[str, int] = defaultdict(int)
    with raw_path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            tag = (rec.get("model") or "").split("::")[0]
            by_arm_total[tag] += 1
            if rec.get("ok"):
                by_arm_ok[tag] += 1
            if rec.get("json_parse_ok"):
                by_arm_jsonok[tag] += 1
            elapsed = rec.get("elapsed_seconds")
            if isinstance(elapsed, (int, float)):
                by_arm[tag].append(float(elapsed))
    out: dict[str, dict[str, float]] = {}
    for tag, vals in by_arm.items():
        out[tag] = {
            "n_total": float(by_arm_total[tag]),
            "n_ok": float(by_arm_ok[tag]),
            "n_json_ok": float(by_arm_jsonok[tag]),
            "wall_mean": statistics.mean(vals) if vals else 0.0,
            "wall_median": statistics.median(vals) if vals else 0.0,
            "wall_max": max(vals) if vals else 0.0,
            "wall_total": sum(vals),
        }
    return out


def render_metric_table(by_model: dict, surface_section: str, metrics: list[tuple], headers: list[str]) -> list[str]:
    rows: list[str] = []
    rows.append("| Metric | " + " | ".join(headers) + " |")
    rows.append("| --- | " + " | ".join("---:" for _ in headers) + " |")
    arm_bodies = [find_arm(by_model, arm)[1] for arm in ARM_ORDER]
    for key, lower_better, label in metrics:
        vals = [get_metric(b, key, surface_section) for b in arm_bodies]
        best_idx = best(vals, lower_better)
        cells = []
        for i, v in enumerate(vals):
            txt = fmt(v)
            if i == best_idx and v is not None:
                txt = f"**{txt}**"
            cells.append(txt)
        rows.append(f"| {label} | " + " | ".join(cells) + " |")
    return rows


def render_failure_distribution(by_model: dict) -> list[str]:
    rows: list[str] = []
    headers = [ARM_LABEL[a] for a in ARM_ORDER]
    rows.append("| Failure label | " + " | ".join(headers) + " |")
    rows.append("| --- | " + " | ".join("---:" for _ in headers) + " |")
    arm_bodies = [find_arm(by_model, arm)[1] for arm in ARM_ORDER]
    all_labels: set[str] = set()
    for body in arm_bodies:
        all_labels.update((body.get("failure_labels") or {}).keys())
    if not all_labels:
        rows.append("| (no failure labels recorded) | " + " | ".join("—" for _ in headers) + " |")
    else:
        for label in sorted(all_labels):
            counts = [(body.get("failure_labels") or {}).get(label, 0) for body in arm_bodies]
            rows.append(f"| {label} | " + " | ".join(str(c) for c in counts) + " |")
    return rows


def render_walltime_table(wall: dict[str, dict[str, float]]) -> list[str]:
    rows: list[str] = []
    headers = ["mean wall (s/case)", "median wall (s)", "max wall (s)", "total wall (s)", "n_total", "n_ok", "n_json_ok"]
    rows.append("| Arm | " + " | ".join(headers) + " |")
    rows.append("| --- | " + " | ".join("---:" for _ in headers) + " |")
    for arm in ARM_ORDER:
        body = wall.get(arm, {})
        row = [
            f"{body.get('wall_mean', 0.0):.1f}",
            f"{body.get('wall_median', 0.0):.1f}",
            f"{body.get('wall_max', 0.0):.1f}",
            f"{body.get('wall_total', 0.0):.0f}",
            str(int(body.get('n_total', 0))),
            str(int(body.get('n_ok', 0))),
            str(int(body.get('n_json_ok', 0))),
        ]
        rows.append(f"| {ARM_LABEL[arm]} | " + " | ".join(row) + " |")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crc-scores", type=Path, required=True)
    parser.add_argument("--nccn-scores", type=Path, required=True)
    parser.add_argument("--crc-raw", type=Path, required=True)
    parser.add_argument("--nccn-raw", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    crc_summary = json.loads((args.crc_scores / "summary.json").read_text())
    nccn_summary = json.loads((args.nccn_scores / "summary.json").read_text())
    crc_by_model = crc_summary.get("by_model") or {}
    nccn_by_model = nccn_summary.get("by_model") or {}

    crc_wall = wall_time_stats(args.crc_raw)
    nccn_wall = wall_time_stats(args.nccn_raw)

    lines: list[str] = []
    lines.append("# MTB vs OPL — quantitative comparison on SBT_Benchmark")
    lines.append("")
    lines.append(f"Scorer: `{crc_summary.get('scorer_version')}` (CRC) / `{nccn_summary.get('scorer_version')}` (NCCN)")
    lines.append("")
    lines.append("## Arm legend")
    lines.append("")
    for arm in ARM_ORDER:
        lines.append(f"- **{arm}** — {ARM_LABEL[arm]}")
    lines.append("")

    headers = [arm for arm in ARM_ORDER]

    # ----- CRC surface
    lines.append("## CRC surface (`tmp/Case_version/`)")
    lines.append("")
    sample = next(iter(crc_by_model.values()), {})
    lines.append(f"N items per arm: {sample.get('n_total')}")
    lines.append("")
    lines.append("### Wall-time & success counts")
    lines.append("")
    lines.extend(render_walltime_table(crc_wall))
    lines.append("")
    lines.append("### Technical health")
    lines.append("")
    lines.extend(render_metric_table(crc_by_model, "crc", COMMON_METRICS, headers))
    lines.append("")
    lines.append("### CRC clinical metrics (bold = best in row)")
    lines.append("")
    lines.extend(render_metric_table(crc_by_model, "crc", CRC_METRICS, headers))
    lines.append("")
    lines.append("### Failure-label distribution (CRC)")
    lines.append("")
    lines.extend(render_failure_distribution(crc_by_model))
    lines.append("")

    # ----- NCCN surface
    lines.append("## NCCN surface (`tmp/NCCN_version/`, CRC subset)")
    lines.append("")
    sample = next(iter(nccn_by_model.values()), {})
    lines.append(f"N items per arm: {sample.get('n_total')}")
    lines.append("")
    lines.append("### Wall-time & success counts")
    lines.append("")
    lines.extend(render_walltime_table(nccn_wall))
    lines.append("")
    lines.append("### Technical health")
    lines.append("")
    lines.extend(render_metric_table(nccn_by_model, "nccn_structured", COMMON_METRICS, headers))
    lines.append("")
    lines.append("### NCCN clinical metrics (bold = best in row)")
    lines.append("")
    lines.extend(render_metric_table(nccn_by_model, "nccn_structured", NCCN_METRICS, headers))
    lines.append("")
    lines.append("### Failure-label distribution (NCCN)")
    lines.append("")
    lines.extend(render_failure_distribution(nccn_by_model))
    lines.append("")

    # ----- Raw blocks
    lines.append("## Raw `by_model` blocks")
    lines.append("")
    for surface, by_model in (("CRC", crc_by_model), ("NCCN", nccn_by_model)):
        lines.append(f"### {surface}")
        lines.append("")
        for arm in ARM_ORDER:
            tag, body = find_arm(by_model, arm)
            lines.append(f"#### {arm} (`{tag or '(missing)'}`)")
            lines.append("```json")
            lines.append(json.dumps(body, ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
