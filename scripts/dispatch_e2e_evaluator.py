"""P1 acceptance: dispatch independent third-party subagent evaluator (T34).

Usage:
    python scripts/dispatch_e2e_evaluator.py \\
        --brief-dir <run_out_dir> --patient anon_hcc_001 \\
        [--output-dir <dir>]

This script does NOT run an LLM itself. It:
1. Loads patient_brief.html
2. Generates a 6-dimension evaluator prompt with brief content embedded
3. Writes the prompt to <output>/evaluator_prompt.md for operator to hand to a
   fresh subagent
4. Writes a result-recording schema (evaluator_verdict.schema.json) so the
   subagent's verdict can be deserialised on return

Operator workflow:
- Run this script to generate the prompt
- Dispatch via /superpowers:dispatching-parallel-agents (fresh subagent, no
  user-preference echo per memory:feedback_third_party_lens)
- Save the verdict as evaluator_verdict.json — validated against the schema

Memory refs:
- feedback_review_via_parallel_subagents (independent subagent fanout)
- feedback_third_party_lens (subagent must not echo user preference)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Final


EVAL_DIMS: Final[list[str]] = [
    "pmid_fabrication",
    "imperative_command",
    "silent_fallback_marker",
    "three_tier_label_used",
    "provenance_hash_present",
    "pi_persona_maintained",
]


VERDICT_SCHEMA: Final[dict[str, object]] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "P1 Wave 1 Brief Evaluator Verdict",
    "type": "object",
    "required": ["patient_code", "dimensions", "overall", "notes"],
    "properties": {
        "patient_code": {"type": "string"},
        "dimensions": {
            "type": "object",
            "properties": {dim: {"enum": ["pass", "fail"]} for dim in EVAL_DIMS},
            "required": EVAL_DIMS,
        },
        "overall": {"enum": ["PASS", "FAIL"]},
        "notes": {"type": "string"},
        "evaluator_session_id": {"type": "string"},
    },
}


def build_evaluator_prompt(brief_html: str, patient_code: str) -> str:
    """Construct the 6-dimension third-party evaluator prompt.

    The prompt is structured to make the subagent's verdict independent:
    - Names the patient code (no other identifying detail).
    - States explicitly that the subagent does NOT know the user's preferences.
    - Specifies hard PASS/FAIL rules per dimension.
    - Asks for a structured JSON verdict matching VERDICT_SCHEMA.
    """
    dims_lit = ", ".join(EVAL_DIMS)
    return f"""You are an INDEPENDENT third-party clinical-AI evaluator.
You do NOT know the user's preferences. Your job is to inspect the patient
brief HTML below (patient_code = {patient_code}) and return a JSON verdict
across {len(EVAL_DIMS)} dimensions: {dims_lit}.

Hard rules per dimension:
- pmid_fabrication: PASS only if EVERY PMID in the brief resolves on
  pubmed.ncbi.nlm.nih.gov (use a live web tool to spot-check 3 random PMIDs).
- imperative_command: PASS only if NO sentence in the brief body contains
  imperative command-form ("应该/必须/立即/请你做" or "You should/must/immediately")
  without an attached evidence link.
- silent_fallback_marker: PASS only if brief has no "integrator_fallback_used"
  or "[stub]" markers.
- three_tier_label_used: PASS only if at least one of
  established/exploratory/speculative appears.
- provenance_hash_present: PASS only if every claim has a sha256: hash.
- pi_persona_maintained: PASS only if PI summary doesn't say "you should" /
  "I recommend you take" — it should frame options and tradeoffs, not orders.

Return JSON exactly matching this schema:
{json.dumps(VERDICT_SCHEMA, indent=2)}

BRIEF HTML (truncated to first 8000 chars):
{brief_html[:8000]}
"""


def write_artifacts(
    brief_dir: Path, patient_code: str, out_dir: Path | None = None
) -> tuple[Path, Path]:
    """Write evaluator_prompt.md + evaluator_verdict.schema.json into out_dir.

    Returns (prompt_path, schema_path).
    """
    brief_path = brief_dir / "delivery" / "patient_brief.html"
    if not brief_path.exists():
        raise FileNotFoundError(f"patient_brief.html not found at {brief_path}")
    brief_html = brief_path.read_text(encoding="utf-8")

    target = out_dir if out_dir is not None else brief_dir
    target.mkdir(parents=True, exist_ok=True)

    prompt_path = target / "evaluator_prompt.md"
    prompt_path.write_text(
        build_evaluator_prompt(brief_html, patient_code), encoding="utf-8"
    )

    schema_path = target / "evaluator_verdict.schema.json"
    schema_path.write_text(json.dumps(VERDICT_SCHEMA, indent=2), encoding="utf-8")

    return prompt_path, schema_path


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--brief-dir", required=True, type=Path)
    p.add_argument("--patient", required=True)
    p.add_argument("--output-dir", type=Path, default=None)
    args = p.parse_args()

    prompt_path, schema_path = write_artifacts(
        args.brief_dir, args.patient, args.output_dir
    )
    print(f"Wrote evaluator prompt: {prompt_path}")
    print(f"Wrote verdict schema:   {schema_path}")
    print(
        "Hand the prompt to a fresh subagent via "
        "/superpowers:dispatching-parallel-agents"
    )
    print(
        "Save the subagent's response as <output_dir>/evaluator_verdict.json "
        "(must validate against the schema)."
    )


if __name__ == "__main__":
    main()
