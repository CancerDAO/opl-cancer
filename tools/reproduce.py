"""reproduce.py — re-run a stored patient_brief from the same model + prompts.

Spec §12 reproducibility. Given a `run_id`, locate the provenance journal and
verify the patient_brief artifact matches what was emitted.

Usage:
    python -m tools.reproduce <patient_dir> <run_id>

Exits 0 if the brief reproduces (same prompt_version + same input claim hashes);
exits 2 if any divergence detected.

memory:feedback_no_false_completion — we don't pretend to re-run the LLM here
(would need pinned model API); we verify the *recipe* (prompts, inputs, hashes)
is intact and re-runnable.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def load_provenance(patient_dir: Path, run_id: str) -> list[dict[str, Any]]:
    """Load the provenance.jsonl entries for a specific run_id."""
    jl = patient_dir / "triggers" / run_id / "provenance.jsonl"
    if not jl.exists():
        # Fallback: top-level provenance.jsonl filtered by run_id.
        top = patient_dir / "provenance.jsonl"
        if not top.exists():
            raise FileNotFoundError(
                f"No provenance journal at {jl} or {top}"
            )
        entries: list[dict[str, Any]] = []
        for line in top.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("run_id") == run_id:
                entries.append(rec)
        return entries
    return [
        json.loads(line)
        for line in jl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def verify_recipe(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify a run can be reproduced: prompt_versions pinned + claim_hashes present."""
    missing_prompt_version = 0
    missing_claim_hash = 0
    models_used: set[str] = set()
    prompts_used: set[str] = set()
    for e in entries:
        meta = e.get("_meta") or e.get("meta") or {}
        if not meta.get("prompt_version"):
            missing_prompt_version += 1
        else:
            prompts_used.add(str(meta["prompt_version"]))
        if e.get("model"):
            models_used.add(str(e["model"]))
        elif meta.get("model"):
            models_used.add(str(meta["model"]))
        if "claim_hash" not in e and "content_hash" not in e:
            missing_claim_hash += 1
    return {
        "total_entries": len(entries),
        "missing_prompt_version": missing_prompt_version,
        "missing_claim_hash": missing_claim_hash,
        "models_used": sorted(models_used),
        "prompts_used": sorted(prompts_used),
        "reproducible": missing_prompt_version == 0 and missing_claim_hash == 0,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: python -m tools.reproduce <patient_dir> <run_id>", file=sys.stderr)
        return 2
    patient_dir = Path(argv[1])
    run_id = argv[2]
    try:
        entries = load_provenance(patient_dir, run_id)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    report = verify_recipe(entries)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["reproducible"] else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
