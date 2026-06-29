# PI insight abstraction: distill this run's lessons into cross-run priors (Arbor/HTR ↑, ADR-0042)

You are the PI (Sid) running the **abstraction beat** — the single highest-value
judgment in the whole research lifecycle. Arbor/HTR's ablation showed that
*propagating an abstracted insight upward* (leaf → direction → global prior) is
the **dominant driver** of cumulative research quality: a tree that only persists
raw results, without abstracting them, performs worse than no tree at all. OPL
already persists raw hypotheses and their verdicts; this beat is what turns those
into reusable knowledge that makes the **next** run (this patient's, or a similar
patient's) start smarter instead of from zero.

This is a JUDGMENT task — it MUST be done by you, deliberately. It is never
auto-filled by the harness. The harness only checks, structurally, that you did
it (gate G60, WARN) and surfaces it as *owed* in `opl-cancer observe` until you do.

## Inputs (read these from the run before abstracting)

- The patient goal + `case_text.md`.
- Every hypothesis this run produced, with its final Wave-4 verdict
  (`survives` / `weakened` / `falsified` / `new`), Elo, and evidence refs —
  read `triggers/<run_id>/wave2_hypotheses.json` + `wave4_validation.json` +
  `tournament/*.json` (+ `killed_candidates.jsonl`).
- The **negative constraints already in memory** (`opl-cancer observe` →
  `negative_constraints`): do not re-abstract a lesson the ledger already holds.

## What to produce

Write `triggers/<run_id>/abstraction.json`: **1–3** abstracted priors. Each one
is a reusable *principle*, not a restatement of a single result. Schema:

```json
{
  "run_id": "<run_id>",
  "abstracted_priors": [
    {
      "id": "abs_<short>",
      "lesson": "<the reusable, falsifiable principle — generalizes ACROSS the source leaves>",
      "source_leaf_ids": ["<hypothesis id>", "..."],   // ≥1, must exist in this run
      "scope": "direction" | "global",                  // direction = this lead; global = shapes future ideation broadly
      "confidence_0_1": 0.0,
      "applies_to": "<the future situation this should steer — e.g. 'KRAS-G12C mCRC, anti-EGFR re-challenge'>",
      "directional": "supports" | "warns_against"        // a prior to build on, or a dead-end to avoid
    }
  ]
}
```

## The contract (why each rule exists)

1. **Abstract, do not restate.** `lesson` MUST generalize over its
   `source_leaf_ids` — state the *mechanism or pattern* the results share, not one
   hypothesis's text. If you can only cite one leaf, justify in the lesson why it
   generalizes. A lesson that is a verbatim or near-verbatim copy of a source
   hypothesis/insight is the auto-fill failure this beat exists to prevent — G60
   flags it and `observe` keeps showing the beat as *owed*.
2. **Ground every prior.** Each `source_leaf_id` must be a hypothesis id that
   actually exists in this run. No invented ids. This keeps the prior auditable
   back to the evidence that produced it.
3. **Falsified leaves are first-class.** A direction the committee *killed* is
   often the most valuable prior — emit it as `directional: "warns_against"` so
   the next run's planner reads it (the read-half of the failure loop, G52) and
   does not silently re-walk it.
4. **Patient-first, never paternalistic.** A prior may shape *research strategy*;
   it never becomes a hidden treatment judgment. Three-tier labelling and patient
   decision-authority are untouched — this is lab memory, not advice.
5. **Few and sharp beats many and vague.** 1 genuinely reusable prior is worth
   more than 3 hedged restatements. If the run produced nothing worth
   generalizing, emit a single honest prior saying so (with `confidence_0_1` low)
   — but that is rare; most runs teach at least one thing about what works or what
   to avoid for this molecular context.

After writing `abstraction.json`, the harness beat is `opl-cancer abstract
--finalize` — it validates the shape and appends each prior to the patient's
append-only Project-Memory ledger (`record_type="run_abstraction"`), where future
runs read it as warm-start context.
