# Task: unknown_task_intake (Sid-level)

> RFC 0001 §8 item 8 — the c3195b66 bug fix.
> Until v2.5, any patient question that didn't map to a hand-written task package was *refused*.  v2.5 routes through this Sid-level prompt: acknowledge → decline naive shortcuts → compose a method-primitive DAG → emit an L4 disclosure card.
>
> v2.5 ships the prompt + a keyword-matched DAG stub (`route_intake`). M5 swaps the keyword stub for a real LLM TaskComposer that produces a DAG over the full `MethodRegistry`.

## When to use

The patient (via Sid) asked a question that **does not match** any of the 63 existing task packages.  Examples:
- "Will you auto-download public databases, run AutoML, and predict my prognosis?"  ← canonical c3195b66
- "Cross-reference my MET-amp NSCLC with every TKI tested against my P53 mutation"
- "Run a population-pharmacokinetics fit on my drug levels"
- novel combinations no v2.4 task package anticipated

If the question maps to an existing `prompts/tasks/<x>.md`, **do NOT route here** — let `intake_router` send it to that package directly.

## What you must do (4 parts)

### 1. Acknowledge

Restate the patient's question in your own words, in their language (Chinese / English / Spanish), with no condescension.  Use Sid's voice (no "as the PI"; speak person-to-person).

### 2. Decline naive shortcuts (with reasons)

If the question implies a method that is **unsafe for an N=1 patient context**, decline that specific shortcut and explain **why**.  Cover at least:
- Why naive AutoML on N=1 overfits — sample-size, IID violation, no held-out validation
- Why "find the optimal model" is a category error in a context with one observed unit
- Why the safe alternative still produces decision-relevant information

Do **not** decline the patient's intent — decline only the naive method.

### 3. Compose a method DAG

Use `MethodRegistry` (`src/opl_cancer/methods/`) to pick the primitives that *can* answer the underlying intent.  Emit a DAG with:
- `nodes`: list of `{id: <method_id>, role: <intent_label>}` entries
- `edges`: directed dependencies (e.g. `kaplan_meier → conformal_prediction` for prognostic-curve uncertainty)
- `unresolved`: questions you can't compose around — surface them, don't hide

For the c3195b66 question the canonical DAG is:
```
kaplan_meier          (baseline prognostic curve from matched cohort)
  → conformal_prediction  (distribution-free uncertainty band on this patient)
  → cohort_projection     (project to patient-specific covariate stack)
  → sensitivity_analysis  (what-if drivers, exposure variation)
```

### 4. Emit an L4 disclosure card

Every output from this task is **Level-4 speculative** by definition (composed pipeline that hasn't been certified for routine use).  Emit the standard `l4_card.json` with:
- `risk_tier: L4`
- `composed: true`
- `methods_used: [<list of method IDs from §3>]`
- `validation_status: composed_not_certified`
- `safety_notes: [...]`
- Plain-language explanation per `prompts/safety/disclosure_card_template.md`

## Output schema

```json
{
  "matched_task_package": "unknown_task_intake",
  "acknowledgement": "...",
  "decline_reasons": ["...", "..."],
  "method_dag": {
    "nodes": [
      {"id": "kaplan_meier", "role": "baseline_prognosis"},
      {"id": "conformal_prediction", "role": "uncertainty_band"}
    ],
    "edges": [
      {"from": "kaplan_meier", "to": "conformal_prediction"}
    ]
  },
  "unresolved": [],
  "l4_disclosure_card": "string (rendered patient-readable disclosure)"
}
```

## Non-negotiables

- **Provenance**: every method ID in `method_dag` must be present in `MethodRegistry` (no fabricated IDs).
- **Three-tier label**: this output is always **speculative**.  Never re-label as established/exploratory.
- **No silent refusal**: if you cannot compose any DAG, return `unresolved: [...]` listing why, but still ack + L4-disclose.  The intake_router must never bounce back a flat "we can't help you".
- **Patient is sole decision authority**: surface this in the disclosure card.

## Reviewer / auditor expectations

- **Henry (auditor)**: confirms L4 card is rendered, methods exist in registry, decline_reasons reference at least one named risk (overfitting / N=1 / IID).
- **Sid**: receives this output and surfaces it to the patient in one turn — no human-in-the-loop external sign-off (founder mode).

— end of unknown_task_intake.md —
