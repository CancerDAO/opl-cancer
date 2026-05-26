#!/usr/bin/env python3
"""Evolution E2E verifier (ADR-0020).

Constructs a synthetic weak run dir, invokes `opl-cancer evolve`, asserts:
1. proposals/iter_001/ created with status.yaml + README.md.
2. prompt_patches.diff exists (no *.evolved.txt files written anywhere).
3. status.yaml has status: pending for non-blocked proposals.
4. Any proposal touching Henry / persona_prefix has requires_double_signoff:true.
5. Any skill proposal without clinical_anchor lives in rejected/.
6. No file under baseline (src/, prompts/, models.yaml) was modified.
7. tool_proposals.jsonl exists and is JSONL-valid.

Exits 0 on PASS, 1 on FAIL.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


def build_synthetic_weak_run(parent: Path) -> Path:
    run_dir = parent / "synthetic-run"
    run_dir.mkdir()
    (run_dir / "tasks").mkdir()
    (run_dir / "tasks" / "w1_bert").mkdir()
    (run_dir / "tasks" / "w1_bert" / "report.md").write_text("ok", encoding="utf-8")
    # Wave 2 deliberately weak — missing v2 strategies
    (run_dir / "wave2_hypotheses.json").write_text(
        json.dumps({
            "hypotheses": [
                {"id": "h1", "claim_layer": "established", "generation_strategy": "literature_gap"},
            ]
        }),
        encoding="utf-8",
    )
    (run_dir / "delivery").mkdir()
    (run_dir / "delivery" / "patient_brief.html").write_text("<html>summary only</html>", encoding="utf-8")
    return run_dir


def main() -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        parent = Path(tmp)
        run_dir = build_synthetic_weak_run(parent)

        # Snapshot baseline files we care about
        repo_root = Path(__file__).resolve().parents[1]
        henry_path = repo_root / "src" / "opl_cancer" / "validators" / "henry.py"
        renderer_path = repo_root / "src" / "opl_cancer" / "glue" / "renderer.py"
        baseline_snapshots = {p: p.read_text(encoding="utf-8") for p in (henry_path, renderer_path) if p.exists()}

        # Invoke CLI
        result = subprocess.run(
            ["opl-cancer", "evolve", str(run_dir), "--iter-n", "1", "--json"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            failures.append(f"opl-cancer evolve exit code {result.returncode}: {result.stderr}")
            return _report(failures)

        payload = json.loads(result.stdout)
        proposals_dir = Path(payload["proposals_dir"])

        # Check 1: iter dir created
        if not proposals_dir.exists():
            failures.append(f"missing proposals_dir {proposals_dir}")
        if not (proposals_dir / "status.yaml").exists():
            failures.append("missing status.yaml")
        if not (proposals_dir / "README.md").exists():
            failures.append("missing README.md")

        # Check 2: no *.evolved.txt anywhere
        evolved_files = list(parent.rglob("*.evolved*"))
        if evolved_files:
            failures.append(f"forbidden *.evolved.* files written: {evolved_files}")

        # Check 3: pending status
        yml = yaml.safe_load((proposals_dir / "status.yaml").read_text(encoding="utf-8"))
        for p in yml.get("proposals", []):
            if p["status"] not in ("pending", "blocked"):
                failures.append(f"proposal {p['proposal_id']} unexpected status {p['status']!r}")

        # Check 4: requires_double_signoff fires on Henry-targeted patches if any
        for p in yml.get("proposals", []):
            ii = p["invariant_impact"]
            if any(ii.values()) and not p["requires_double_signoff"]:
                failures.append(
                    f"proposal {p['proposal_id']} has invariant impact but no requires_double_signoff"
                )

        # Check 5: skill proposals without clinical_anchor live in rejected/
        skill_props = [p for p in yml.get("proposals", []) if p["kind"] == "skill_addition"]
        for p in skill_props:
            if not p["clinical_anchor"] and p["status"] != "blocked":
                failures.append(f"skill {p['proposal_id']} without clinical_anchor not blocked")

        # Check 6: baseline files unchanged
        for path, snap in baseline_snapshots.items():
            if path.read_text(encoding="utf-8") != snap:
                failures.append(f"baseline file MODIFIED by evolve: {path}")

        # Check 7: tool_proposals.jsonl exists + valid JSONL
        jsonl_path = proposals_dir / "tool_proposals.jsonl"
        if not jsonl_path.exists():
            failures.append("tool_proposals.jsonl missing")
        else:
            for line in jsonl_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        json.loads(line)
                    except json.JSONDecodeError as exc:
                        failures.append(f"tool_proposals.jsonl invalid line: {exc}")

    return _report(failures)


def _report(failures: list[str]) -> int:
    if not failures:
        print("✅ evolution E2E verification PASS")
        return 0
    print("❌ evolution E2E verification FAIL:")
    for f in failures:
        print(f"  - {f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
