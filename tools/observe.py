"""tools/observe.py — Iter 14 (v1.0.6): Trigger run observability aggregator.

Per spec §10. Scans a root directory for trigger run subdirectories — each
expected to contain a `run_metadata.json` file with fields:

  - token_cost            (number)
  - wall_time_seconds     (number)
  - claims_produced       (int)
  - claims_withdrawn      (int)
  - reviewer_fail_rate    (number, 0-1)
  - mechanical_gate_blocks(int)

Outputs:
  - JSON aggregate (stdout or --out-json <path>)
  - Markdown summary (stdout or --out-md <path>)

Per-run rows are surfaced verbatim; aggregate row computes mean/sum where
appropriate. Missing fields per run are reported under `errors`.

memory:feedback_no_false_completion — explicit count of runs scanned,
runs accepted, runs skipped (with reasons).
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

METRIC_KEYS: tuple[str, ...] = (
    "token_cost",
    "wall_time_seconds",
    "claims_produced",
    "claims_withdrawn",
    "reviewer_fail_rate",
    "mechanical_gate_blocks",
)


def _load_run(meta_path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    errs: list[str] = []
    try:
        data: dict[str, Any] = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"unreadable: {exc}"]
    missing = [k for k in METRIC_KEYS if k not in data]
    if missing:
        errs.append(f"missing keys: {missing}")
    return data, errs


def collect_runs(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (accepted_runs, skipped_with_reasons).

    Each accepted run dict carries `run_id` (subdir name) + metric fields.
    """
    accepted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for meta_path in sorted(root.rglob("run_metadata.json")):
        data, errs = _load_run(meta_path)
        run_id = meta_path.parent.relative_to(root).as_posix()
        if data is None or errs:
            skipped.append({"run_id": run_id, "errors": errs})
            if data is None:
                continue
        row: dict[str, Any] = {"run_id": run_id}
        for k in METRIC_KEYS:
            row[k] = data.get(k)
        accepted.append(row)
    return accepted, skipped


def _mean(values: list[float]) -> float | None:
    nums = [v for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    return round(statistics.fmean(nums), 4)


def _sum(values: list[float]) -> float | None:
    nums = [v for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    return sum(nums)


def aggregate(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Return aggregate metrics across runs."""
    return {
        "runs_count": len(runs),
        "token_cost_total": _sum([r["token_cost"] for r in runs]),
        "wall_time_seconds_total": _sum([r["wall_time_seconds"] for r in runs]),
        "claims_produced_total": _sum([r["claims_produced"] for r in runs]),
        "claims_withdrawn_total": _sum([r["claims_withdrawn"] for r in runs]),
        "reviewer_fail_rate_mean": _mean([r["reviewer_fail_rate"] for r in runs]),
        "mechanical_gate_blocks_total": _sum(
            [r["mechanical_gate_blocks"] for r in runs]
        ),
    }


def build_report(root: Path) -> dict[str, Any]:
    accepted, skipped = collect_runs(root)
    return {
        "root": str(root),
        "runs": accepted,
        "skipped": skipped,
        "aggregate": aggregate(accepted),
    }


def render_markdown(report: dict[str, Any]) -> str:
    agg = report["aggregate"]
    lines: list[str] = [
        f"# OPL Trigger-Run Observability — `{report['root']}`",
        "",
        f"- Runs accepted: **{agg['runs_count']}**",
        f"- Runs skipped: **{len(report['skipped'])}**",
        "",
        "## Aggregate",
        "",
        f"- token_cost_total: {agg['token_cost_total']}",
        f"- wall_time_seconds_total: {agg['wall_time_seconds_total']}",
        f"- claims_produced_total: {agg['claims_produced_total']}",
        f"- claims_withdrawn_total: {agg['claims_withdrawn_total']}",
        f"- reviewer_fail_rate_mean: {agg['reviewer_fail_rate_mean']}",
        f"- mechanical_gate_blocks_total: {agg['mechanical_gate_blocks_total']}",
        "",
        "## Per-run",
        "",
        "| run_id | token_cost | wall_time_s | claims+ | claims- | rev_fail | mech_blk |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in report["runs"]:
        lines.append(
            f"| {r['run_id']} | {r['token_cost']} | {r['wall_time_seconds']} | "
            f"{r['claims_produced']} | {r['claims_withdrawn']} | "
            f"{r['reviewer_fail_rate']} | {r['mechanical_gate_blocks']} |"
        )
    if report["skipped"]:
        lines += ["", "## Skipped runs", ""]
        for s in report["skipped"]:
            lines.append(f"- `{s['run_id']}` — {s['errors']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True, help="trigger runs root dir")
    p.add_argument("--out-json", type=Path, default=None)
    p.add_argument("--out-md", type=Path, default=None)
    args = p.parse_args(argv)
    if not args.root.exists():
        print(f"error: root does not exist: {args.root}", file=sys.stderr)
        return 2
    report = build_report(args.root)
    md = render_markdown(report)
    json_blob = json.dumps(report, indent=2)
    if args.out_json:
        args.out_json.write_text(json_blob, encoding="utf-8")
    if args.out_md:
        args.out_md.write_text(md, encoding="utf-8")
    if not args.out_json and not args.out_md:
        sys.stdout.write(json_blob + "\n")
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
