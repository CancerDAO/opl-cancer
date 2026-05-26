"""Collect a TraceDigest from a completed run dir. ADR-0020 §What we copy #1.

Read-only — never modifies run_dir. Bounded output (~100KB).
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .models import HypothesisStrategyCount, TraceDigest, WaveSummary


_MAX_NOTABLE_ISSUES = 20
_MAX_ARTIFACT_PATHS_PER_WAVE = 30


def collect_trace_digest(run_dir: Path) -> TraceDigest:
    """Build a bounded TraceDigest from a completed run dir.

    Expected layout (any subset may be missing — collector is tolerant):
        <run_dir>/
            plan.json
            tasks/w{1,2,3,4,5}_*/report.md
            wave2_hypotheses.json
            wave3_data_evidence.json
            henry/verdict.json
            delivery/patient_brief.html
    """
    run_dir = Path(run_dir)
    if not run_dir.exists():
        raise FileNotFoundError(f"run_dir does not exist: {run_dir}")

    run_id = run_dir.name
    digest = TraceDigest(
        run_id=run_id,
        patient_code_scrubbed=run_dir.parent.parent.name if "patients" in str(run_dir) else "[SCRUBBED]",
    )

    # ---- Wave summaries ----
    tasks_dir = run_dir / "tasks"
    if tasks_dir.exists():
        for wave_n in (1, 2, 3, 4, 5):
            wave_tasks = sorted(tasks_dir.glob(f"w{wave_n}_*"))
            paths_seen: list[str] = []
            errors: list[str] = []
            for t in wave_tasks[:_MAX_ARTIFACT_PATHS_PER_WAVE]:
                paths_seen.append(str(t.relative_to(run_dir)))
                report = t / "report.md"
                if report.exists():
                    text = report.read_text(encoding="utf-8", errors="replace")
                    for line in text.splitlines():
                        low = line.lower()
                        if ("error" in low or "failed" in low or "exception" in low) and len(errors) < 5:
                            errors.append(line.strip()[:200])
            digest.waves.append(
                WaveSummary(
                    wave=wave_n,
                    tasks_completed=len(wave_tasks),
                    artifact_paths=paths_seen,
                    errors=errors,
                )
            )

    # ---- Hypothesis strategy distribution (Wave 2) ----
    wave2_json = run_dir / "wave2_hypotheses.json"
    if wave2_json.exists():
        try:
            payload = json.loads(wave2_json.read_text(encoding="utf-8"))
            hyps = payload.get("hypotheses") or payload.get("top_k_hypotheses") or []
            strat_counter: Counter[str] = Counter()
            spec_test_counter: Counter[str] = Counter()
            tier_counter: Counter[str] = Counter()
            for h in hyps:
                s = str(h.get("generation_strategy", "unknown"))
                strat_counter[s] += 1
                if h.get("claim_layer") == "speculative" and h.get("testability_path"):
                    spec_test_counter[s] += 1
                tier = str(h.get("claim_layer", "unknown"))
                tier_counter[tier] += 1
            digest.hypothesis_strategies = [
                HypothesisStrategyCount(
                    strategy=s,
                    count=c,
                    speculative_with_testability=spec_test_counter.get(s, 0),
                )
                for s, c in sorted(strat_counter.items())
            ]
            digest.evidence_tier_distribution = dict(tier_counter)
        except json.JSONDecodeError as exc:
            digest.notable_issues.append(f"wave2_hypotheses.json parse error: {exc}")

    # ---- Henry verdicts ----
    henry_dir = run_dir / "tasks" / "henry"
    if henry_dir.exists():
        verdict_counter: Counter[str] = Counter()
        for f in henry_dir.glob("**/verdict.json"):
            try:
                v = json.loads(f.read_text(encoding="utf-8"))
                verdict_counter[str(v.get("verdict", "unknown"))] += 1
            except json.JSONDecodeError:
                verdict_counter["parse_error"] += 1
        digest.henry_verdict_counts = dict(verdict_counter)

    # ---- Novelty gate stats (count of [S]-with-testability surfaced in brief) ----
    brief_html = run_dir / "delivery" / "patient_brief.html"
    if brief_html.exists():
        text = brief_html.read_text(encoding="utf-8", errors="replace")
        digest.novelty_gate_stats = {
            "world_unknown_section_present": int("World-Unknown" in text),
            "research_direction_framing_present": int("research direction" in text.lower()),
        }

    # ---- Notable issues — cap at 20 ----
    digest.notable_issues = digest.notable_issues[:_MAX_NOTABLE_ISSUES]

    # ---- Size estimate ----
    digest.digest_byte_size_estimate = len(digest.model_dump_json().encode("utf-8"))

    return digest
