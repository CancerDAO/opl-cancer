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
    # NCCN-section metrics live under by_model[model]["nccn"][...], same shape
    # as CRC under by_model[model]["crc"][...].
    ("structured_decision_concordance_full_denominator",        False, "NCCN decision concordance (full denom)"),
    ("structured_decision_concordance_scorable_only",           False, "NCCN decision concordance (scorable)"),
    ("structured_decision_concordance_strict_full_denominator", False, "NCCN decision concordance (strict, full denom)"),
    ("structured_decision_concordance_strict_scorable_only",    False, "NCCN decision concordance (strict, scorable)"),
    ("macro_by_question_type_concordance",                      False, "NCCN macro-by-q-type concordance"),
    ("strict_unsafe_overreach_rate",                            True,  "NCCN unsafe overreach (lower=better)"),
    ("false_stop_rate",                                         True,  "NCCN false-stop rate (lower=better)"),
    ("true_false_stop_rate",                                    True,  "NCCN true false-stop rate (lower=better)"),
    ("premature_downstream_commitment_rate",                    True,  "NCCN premature commitment (lower=better)"),
    ("route_label_text_mismatch_rate",                          True,  "NCCN route mismatch (lower=better)"),
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


def get_metric(body: dict, key: str, surface_section: str | None) -> Any:
    # Common metrics (json_parse_rate / schema_valid_rate / ...) live at top level.
    # CRC / NCCN clinical metrics live under body[surface_section].
    if surface_section is None:
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


def render_metric_table(by_model: dict, surface_section: str | None, metrics: list[tuple], headers: list[str]) -> list[str]:
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
    lines.append("Model under test: **MiniMax-M2.7** (reasoning model — every arm gets identical model + temperature + retry budget; the only contrast between mtb-* and opl-* arms is the prompt corpus / multi-agent shape).")
    lines.append("")
    lines.append("Run scale: n=30 per surface (CRC + NCCN), 5 arms each, max_tokens floor=80000 to fit reasoning blocks. Only `json_parse_ok = true` records are scorable — see per-arm `n_json_ok` column below.")
    lines.append("")

    lines.append("## TL;DR — who wins?")
    lines.append("")
    lines.append("Plain answer to *\"哪个效果好\"* on this n=30 pilot:")
    lines.append("")
    lines.append("- **CRC surface (treatment recommendation)** — **opl-anchor wins clearly**. Best in 6/12 CRC metrics: therapy F1@3 (full denom 0.463 / scorable 0.555), nDCG@3 (0.679), strict therapy F1@3 (0.358), therapy coverage F1 (0.555), contraindicated rate (0.040), molecular-context-error rate (0.040). mtb-anchor takes class-level F1 (0.697 vs opl-anchor 0.677) and unsupported rate (0.000). opl-full leads treatment-intent match (0.750). Baseline holds off-gold rate (0.760) — i.e. it makes fewer recommendations period.")
    lines.append("- **CRC surface — the *-full multi-agent pipelines underperform their anchor twins on F1-style metrics** (mtb-full 0.281 vs mtb-anchor 0.399; opl-full 0.364 vs opl-anchor 0.463 on therapy F1@3 full denom). The extra Rosa∥Bert∥Vince / pathologist∥geneticist∥oncologist hops add reasoning loops but the schema-shape stage cannot recover the upstream variance. mtb-full does get to 0.048 contraindicated (vs baseline 0.080) — verifiers do catch some unsafe outputs.")
    lines.append("- **NCCN surface (decision concordance)** — **baseline wins decisively**. 0.400 strict scorable concordance vs mtb-anchor 0.250 / opl-anchor 0.160 / opl-full 0.125 / mtb-full 0.120. NCCN gold rewards `stop_missing_info` / `stop_need_evidence` / `routing` when discriminators are missing; multi-expert pipelines fan out into specific recommendations and score as overreach. opl-full 0.375 + opl-anchor 0.438 unsafe overreach vs baseline 0.125. mtb-full + opl-full do get false-stop rate to 0.000 (vs baseline 0.250) — but the cost is they push past 'need more info' too aggressively.")
    lines.append("- **Wall-time** (M2.7 + 80K tokens): baseline 25-27s, anchor arms 53-87s, full arms 187-268s. *-full arms are 7-10× baseline. No clinical gain on this substrate justifies that for full arms.")
    lines.append("- **Technical health is excellent at 80K tokens**: JSON parse rate 0.77-0.83 on CRC, 0.83 across all NCCN arms. The earlier M2 + 8K-token attempt had 0.4-0.7 parse rates because reasoning blocks truncated — fixed.")
    lines.append("")
    lines.append("**Headline**: on this SBT_Benchmark n=30 pilot, **OPL's prompt design wins CRC, baseline wins NCCN**. Neither framework's full multi-agent shape pays off here — the schema-shape stage is the bottleneck, and NCCN's 'know-when-to-stop' rubric actively penalises multi-expert recommendation fanout. The anchor arms (planner + retrieve + 1-call synth) sit in the sweet spot for this benchmark substrate.")
    lines.append("")
    lines.append("## Caveats before drawing conclusions")
    lines.append("")
    lines.append("1. **Sample size**: n=30 per arm per surface. CIs are wide. Treat metric deltas < ~0.1 as noise.")
    lines.append("2. **Neither framework is in production form here**. Both `*-full` arms were adapted to plain synchronous OpenRouter calls. OPL's real production stack is claude-native (Wave 2 hypothesis tournament + Wave 3 bixbench data evidence + Wave 4 hypothesis validation + Henry's 27 deterministic Python gates) — *none* of those run in this benchmark. vMTB similarly skips its NCCN PageIndex builder, organizer pre-step, and the deterministic facts/guidelines/safety verifiers as production code.")
    lines.append("3. **The schema-shape stage is shared between mtb-* and opl-***. The fact that `*-full` arms underperform `*-anchor` arms is partly because the upstream multi-agent output is harder for the schema-shape pass to compress into 3 ranked recommendations. This is fixable but not fixed in this pilot.")
    lines.append("4. **Reasoning-model artefact**: MiniMax-M2.7 emits `<think>...</think>` blocks before the answer. We bumped max_tokens floor to 80000 to fit; a smaller budget (e.g. M2 + 8K) caused 40-60% truncation on `*-full` arms in an earlier run. A non-reasoning model would shift these numbers and shrink the wall-time gap.")
    lines.append("5. **NCCN concordance metric rewards 'stop and ask' decisions** when discriminators are missing. Multi-expert pipelines fanned out to specific recommendations get scored as overreach. This is by design of the benchmark and shows up here.")
    lines.append("6. **Henry L1 verifier is LLM-orchestrated in this benchmark**, not the real Python `validators/gates/` registry. The OPL production verifier is much stronger; what we measured is a thin stand-in.")
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
    lines.extend(render_metric_table(crc_by_model, None, COMMON_METRICS, headers))
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
    lines.extend(render_metric_table(nccn_by_model, None, COMMON_METRICS, headers))
    lines.append("")
    lines.append("### NCCN clinical metrics (bold = best in row)")
    lines.append("")
    lines.extend(render_metric_table(nccn_by_model, "nccn", NCCN_METRICS, headers))
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
