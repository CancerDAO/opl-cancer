"""tools/run_quad_evaluation.py — Iter 11: Quad Independent Evaluator scaffold.

Generates 4 evaluator prompts and a JSON result schema for parallel
third-party subagent dispatch (memory:feedback_review_via_parallel_subagents).

The 4 dimensions (spec §17 — Validation Stack):
- architecture   : two-layer dispatch, 18-expert roster, no HITL, main-thread dispatch
- safety         : founder-mode discipline, no paternalism, no silent fallback, IRB substitute
- code_quality   : mypy --strict, ruff, coverage, file responsibility, SQL-injection sweep
- ux             : patient brief readability, three-tier discipline, PMID hyperlinks, command-form detector

CLI:
    python tools/run_quad_evaluation.py --out evaluator_workspace/
    python tools/run_quad_evaluation.py --dimension architecture --out evaluator_workspace/

The tool does NOT itself dispatch subagents (CI determinism); it writes
``prompts/<dim>.md`` + ``schema.json`` so the operator (or main-thread Claude)
hands each prompt to an independent third-party evaluator and collects JSON
verdicts. ``tools/aggregate_evaluator_verdicts.py`` then merges them.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

DIMENSIONS: tuple[str, ...] = ("architecture", "safety", "code_quality", "ux")

DIMENSION_PROMPTS: dict[str, str] = {
    "architecture": """# Independent Evaluator — Architecture (spec §2)

You are an independent third-party reviewer. You do NOT know the user's
preferences and you do NOT echo the user's framing. Evaluate the OPL-for-Cancer
repository against the **spec § 2 architectural contract**:

1. **Two-layer dispatch**: every expert runs Executor (Opus) + Reviewer (cheaper) — confirm by reading `src/opl_cancer/experts/*.py`.
2. **18-expert roster**: roster registry exposes exactly 18 experts (see `experts/roster.py`).
3. **Main-thread dispatch**: orchestrator runs in main thread; subagents are short-lived (see `glue/wave*_runner.py`).
4. **No HITL gate**: there must be NO `input()` / `prompt_user_y_n` in the runner hot path.
5. **Main-thread only writes** to canonical patient dir; subagents return JSON.

Return JSON conforming to the supplied schema. Cite file paths + line numbers
for every finding. Score 0-10 per criterion; verdict ∈ {pass, conditional, fail}.
""",
    "safety": """# Independent Evaluator — Safety (memory:feedback_no_offline_only / no_false_completion)

You are an independent third-party reviewer. Evaluate the safety posture:

1. **Founder-mode discipline**: no paternalistic copy in `delivery/patient_brief.html` templates. Patient is the decision-maker.
2. **No silent fallback**: when integrator/LLM unavailable, the system MUST raise — confirm in `integrators/*.py` and `llm/*.py`.
3. **No LLM-synthesised evidence**: every evidence claim must trace back to an integrator hit (PMID / trial ID / FDA label). Spot-check `experts/*.py` reviewer prompts.
4. **IRB substitute**: validation stack (Henry / risk-card / quad-evaluator) is the IRB substitute — confirm presence at `src/opl_cancer/validators/`.
5. **PHI hygiene**: synthetic patients prefixed `anon_` ; no real-name patterns leak into briefs.

Return JSON conforming to schema. Cite paths + line numbers. Score 0-10.
""",
    "code_quality": """# Independent Evaluator — Code Quality

You are an independent third-party reviewer. Evaluate:

1. **mypy --strict** must pass on `src/opl_cancer/`. Run it.
2. **ruff** must report zero violations on `src/`. Run it.
3. **Test coverage**: ≥ 70% line coverage on `src/opl_cancer/`. Run `pytest --cov`.
4. **File responsibility**: each module < 600 lines; god-files flagged.
5. **SQL injection / shell injection sweep**: grep for `subprocess.*shell=True`, raw string concat into SQL.

Return JSON conforming to schema. Include actual tool output excerpts.
""",
    "ux": """# Independent Evaluator — UX (patient-readability)

You are an independent third-party reviewer. Open the most recent
`patients/<code>/triggers/<run_id>/delivery/patient_brief.html` and evaluate:

1. **Patient-readable**: no expert jargon left undefined; technical depth matches `profile.preferences.depth`.
2. **Three-tier discipline**: every claim labelled `established` / `exploratory` / `speculative`.
3. **PMID linkage**: every PMID is a hyperlink to `pubmed.ncbi.nlm.nih.gov/<id>`.
4. **Command-form detector (G7)**: no imperative leakage ("You should immediately X"). Patient is informed, not commanded.
5. **Risk-card acknowledgement**: outstanding risk cards surfaced clearly.

Return JSON conforming to schema. Cite HTML excerpt lines.
""",
}

RESULT_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft-07/schema#",
    "title": "QuadEvaluatorVerdict",
    "type": "object",
    "required": ["dimension", "verdict", "score", "findings", "evaluator_id"],
    "properties": {
        "dimension": {"type": "string", "enum": list(DIMENSIONS)},
        "verdict": {"type": "string", "enum": ["pass", "conditional", "fail"]},
        "score": {"type": "number", "minimum": 0, "maximum": 10},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["severity", "message"],
                "properties": {
                    "severity": {"type": "string", "enum": ["info", "warn", "error"]},
                    "message": {"type": "string"},
                    "path": {"type": "string"},
                    "line": {"type": "integer"},
                },
            },
        },
        "evaluator_id": {"type": "string"},
        "notes": {"type": "string"},
    },
}


def build_prompt(dimension: str) -> str:
    if dimension not in DIMENSION_PROMPTS:
        raise ValueError(f"unknown dimension: {dimension}; expected one of {DIMENSIONS}")
    return DIMENSION_PROMPTS[dimension]


def generate_all(out_dir: Path) -> dict[str, Path]:
    """Write prompt + schema files; return mapping dim -> prompt_path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    prompts_dir = out_dir / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    paths: dict[str, Path] = {}
    for dim in DIMENSIONS:
        p = prompts_dir / f"{dim}.md"
        p.write_text(build_prompt(dim), encoding="utf-8")
        paths[dim] = p
    (out_dir / "schema.json").write_text(
        json.dumps(RESULT_SCHEMA, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "README.md").write_text(
        "# Quad Evaluator workspace\n\n"
        "Hand each `prompts/<dim>.md` to an independent third-party evaluator.\n"
        "Collect verdicts as `verdicts/<dim>.json` conforming to `schema.json`.\n"
        "Then run `python tools/aggregate_evaluator_verdicts.py --workspace .`\n",
        encoding="utf-8",
    )
    return paths


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate quad-evaluator prompts + schema.")
    p.add_argument("--out", type=Path, default=Path("evaluator_workspace"))
    p.add_argument("--dimension", choices=DIMENSIONS, default=None)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.dimension:
        prompt = build_prompt(args.dimension)
        args.out.mkdir(parents=True, exist_ok=True)
        target = args.out / "prompts" / f"{args.dimension}.md"
        target.parent.mkdir(exist_ok=True)
        target.write_text(prompt, encoding="utf-8")
        print(f"wrote {target}")
        return 0
    paths = generate_all(args.out)
    for dim, p in paths.items():
        print(f"{dim}: {p}")
    print(f"schema: {args.out / 'schema.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
