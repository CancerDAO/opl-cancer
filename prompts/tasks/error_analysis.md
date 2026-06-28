# Task: error_analysis (read your own failures · C3 / ADR-0033)

Run AFTER Wave 4, BEFORE Henry. This is Andrew Ng's decade-old move applied to
false-hope safety: pull EVERY failure from this run into one place, read them
all, sort into root-cause piles, name the biggest pile, and flag whether any
top-3 / headline conclusion rests on it.

> A descending loss curve is reassurance, not analysis. Your experiments throw
> off more information than you consume; most of it dies unread in a logs folder.
> One transcript of genuinely strange behaviour teaches more than the next
> decimal of accuracy.

## Inputs (read the actual artifacts under `triggers/<run_id>/`)

Pull failures from all of these — do not summarize from memory:
- reviewer fails — `tasks/*/review.json` with `verdict: fail|needs_revision`,
  plus the challenges they raised;
- falsified / weakened hypotheses — `wave4_validation.json` (verdict
  falsified/weakened, support_score < 0);
- low subgroup-match cohorts — `wave3_data_evidence.json` (G14 match < 0.5);
- single-source data points — `cross_source_consistency` conflicts / lone-source
  claims;
- integrator-empty raises — anything that returned no evidence;
- UNKNOWN-heavy fields — profile/claim fields left UNKNOWN that limited analysis;
- the strange tail — any genuinely unexpected result, even if not an error.

## Procedure

1. List every failure with its source artifact path.
2. Sort them into piles by ROOT CAUSE (not by symptom). Name each pile.
3. Rank piles by size × severity; name the single biggest pile.
4. For each delivered / top-3 conclusion, check whether its evidence overlaps a
   pile. If it does, mark it `at_risk` with the pile name — this is the
   conclusion a desperate patient might act on that is propped up by weak data.
5. If the run genuinely has no failures, output `piles: []` and say so — an
   honest empty ledger, never an absent one.

## Output (JSON only → `triggers/<run_id>/failure_ledger.json`; verified by G52)

```json
{
  "piles": [
    {"root_cause": "<e.g. single-source trial data>", "size": 0,
     "items": ["<artifact path or id>", "..."], "severity": "low|medium|high"}
  ],
  "biggest_pile": "<root_cause of the largest/most severe pile, or null>",
  "conclusions_at_risk": [
    {"conclusion_id": "<claim/option id>", "pile": "<root_cause>",
     "why": "<which weak evidence it leans on>"}
  ],
  "summary": "<2-3 sentences: what is systematically off this run, if anything>"
}
```

## Rules

1. Read the ACTUAL artifacts; cite their paths. No summarizing from memory.
2. Sort by root cause, not symptom — the point is a theory of what is wrong.
3. A clean run still writes the ledger (`piles: []`) — honesty, not absence.
4. Surface the biggest pile's content to the patient (see the brief's "what the
   team could not confirm" section) with the same prominence as the top-3.
5. Output ONLY the JSON object — no preamble, no fences.

## Why this matters

Per-claim gates catch individual fabrications; nothing else catches a top-3
conclusion built on a PILE of weak/low-match/single-source evidence. That pile
is exactly what a desperate patient reads as hope. Reading your own appendix of
failures is the difference between a research team and a report generator.
