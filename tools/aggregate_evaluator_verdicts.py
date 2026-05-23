"""tools/aggregate_evaluator_verdicts.py — Iter 11: merge quad verdicts → HTML.

Reads `<workspace>/verdicts/<dim>.json` (4 files), validates against
`<workspace>/schema.json`, and writes `<workspace>/evaluator_report.html`.

Aggregation rule:
- overall_verdict = "fail" if any dim==fail
                    else "conditional" if any dim==conditional
                    else "pass"
- overall_score = mean of per-dim scores (rounded to 2 decimals)

memory:feedback_third_party_lens — does not echo "looks good" by default; if
any dim is missing, surfaces as `missing`.
"""
from __future__ import annotations

import argparse
import html
import json
import statistics
import sys
from pathlib import Path
from typing import Any

DIMENSIONS: tuple[str, ...] = ("architecture", "safety", "code_quality", "ux")


def _load_verdict(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _validate_verdict(v: dict[str, Any], dim: str) -> list[str]:
    """Lightweight schema check (avoid jsonschema dep). Returns list of errors."""
    errs: list[str] = []
    required = {"dimension", "verdict", "score", "findings", "evaluator_id"}
    missing = required - set(v.keys())
    if missing:
        errs.append(f"missing keys: {sorted(missing)}")
    if v.get("dimension") != dim:
        errs.append(f"dimension mismatch: file says {v.get('dimension')!r}, expected {dim!r}")
    if v.get("verdict") not in {"pass", "conditional", "fail"}:
        errs.append(f"verdict invalid: {v.get('verdict')!r}")
    score = v.get("score")
    if not isinstance(score, (int, float)) or not 0 <= score <= 10:
        errs.append(f"score invalid: {score!r}")
    if not isinstance(v.get("findings"), list):
        errs.append("findings must be list")
    return errs


def aggregate(verdicts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Compute overall verdict + score from per-dim verdicts.

    Missing dimensions count as conditional (per memory:feedback_third_party_lens —
    don't silently pass when evidence is missing).
    """
    per_dim_verdict: dict[str, str] = {}
    per_dim_score: dict[str, float] = {}
    missing: list[str] = []
    for dim in DIMENSIONS:
        if dim not in verdicts:
            missing.append(dim)
            per_dim_verdict[dim] = "missing"
            continue
        v = verdicts[dim]
        per_dim_verdict[dim] = v["verdict"]
        per_dim_score[dim] = float(v["score"])
    if missing:
        overall = "conditional"
    elif any(s == "fail" for s in per_dim_verdict.values()):
        overall = "fail"
    elif any(s == "conditional" for s in per_dim_verdict.values()):
        overall = "conditional"
    else:
        overall = "pass"
    score = round(statistics.mean(per_dim_score.values()), 2) if per_dim_score else 0.0
    return {
        "overall_verdict": overall,
        "overall_score": score,
        "per_dim_verdict": per_dim_verdict,
        "per_dim_score": per_dim_score,
        "missing": missing,
    }


def render_html(agg: dict[str, Any], verdicts: dict[str, dict[str, Any]]) -> str:
    rows: list[str] = []
    for dim in DIMENSIONS:
        v = verdicts.get(dim)
        if v is None:
            rows.append(
                f"<tr><td>{dim}</td><td class='missing'>missing</td>"
                f"<td>-</td><td>-</td><td>-</td></tr>"
            )
            continue
        findings_html = "<br>".join(
            f"[{html.escape(str(f.get('severity', '?')))}] "
            f"{html.escape(str(f.get('message', '')))}"
            for f in v.get("findings", [])[:5]
        ) or "(none)"
        rows.append(
            "<tr>"
            f"<td>{html.escape(dim)}</td>"
            f"<td class='{html.escape(v['verdict'])}'>{html.escape(v['verdict'])}</td>"
            f"<td>{html.escape(str(v['score']))}</td>"
            f"<td>{html.escape(str(v.get('evaluator_id', '?')))}</td>"
            f"<td>{findings_html}</td>"
            "</tr>"
        )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>OPL Cancer — Quad Evaluator Report</title>"
        "<style>"
        "body{font-family:-apple-system,sans-serif;max-width:920px;margin:2rem auto;padding:0 1rem}"
        "table{width:100%;border-collapse:collapse}"
        "th,td{border:1px solid #ccc;padding:.5rem;text-align:left;vertical-align:top}"
        "th{background:#f5f5f5}"
        ".pass{background:#d4f4dd}.fail{background:#f4d4d4}"
        ".conditional{background:#fff4cc}.missing{background:#eee;color:#888}"
        f".overall-{html.escape(agg['overall_verdict'])}"
        "{padding:.5rem;border-radius:.25rem}"
        "</style></head><body>"
        "<h1>OPL Cancer — Quad Independent Evaluator Report</h1>"
        f"<p>Overall verdict: <strong class='{html.escape(agg['overall_verdict'])}'>"
        f"{html.escape(agg['overall_verdict'])}</strong></p>"
        f"<p>Mean score: <strong>{agg['overall_score']}</strong> / 10</p>"
        + (
            f"<p class='missing'>Missing dimensions: "
            f"{html.escape(', '.join(agg['missing']))}</p>"
            if agg["missing"]
            else ""
        )
        + "<table>"
        "<thead><tr><th>Dimension</th><th>Verdict</th><th>Score</th>"
        "<th>Evaluator</th><th>Top findings</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        "</body></html>"
    )


def run(workspace: Path) -> tuple[Path, dict[str, Any]]:
    verdicts_dir = workspace / "verdicts"
    verdicts: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    if verdicts_dir.exists():
        for dim in DIMENSIONS:
            p = verdicts_dir / f"{dim}.json"
            if not p.exists():
                continue
            v = _load_verdict(p)
            errs = _validate_verdict(v, dim)
            if errs:
                errors.extend(f"{dim}: {e}" for e in errs)
                continue
            verdicts[dim] = v
    if errors:
        raise ValueError("verdict validation failed: " + "; ".join(errors))
    agg = aggregate(verdicts)
    html_str = render_html(agg, verdicts)
    report = workspace / "evaluator_report.html"
    report.write_text(html_str, encoding="utf-8")
    return report, agg


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", type=Path, default=Path("evaluator_workspace"))
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report, agg = run(args.workspace)
    print(f"wrote {report}")
    print(f"overall: {agg['overall_verdict']} (score {agg['overall_score']})")
    return 0 if agg["overall_verdict"] != "fail" else 2


if __name__ == "__main__":
    sys.exit(main())
