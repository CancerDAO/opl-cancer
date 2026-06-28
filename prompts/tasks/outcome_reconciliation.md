# Task: outcome_reconciliation (reality-outcome loop · A2 / ADR-0028)

You are scoring the team's PRIOR predictions against the patient's ACTUAL
clinical course — the only ground-truth error signal OPL has. This is NOT a
fresh clinical analysis (that would ignore what the team already said). It is a
verdict on what the team already predicted, against what really happened.

> Research speed is the speed at which you discover you're wrong. This task is
> the channel through which reality tells OPL it was wrong (or right).

## Inputs

- `prior_predictions` — from `opl-cancer reconcile --patient … --run-id …`
  (the team's prior hypotheses + any pre-registered forecasts, pulled from the
  research ledger).
- The NEW clinical datum the patient dropped into `inbox/` — a scan / RECIST
  read, a tumour-marker trend, a pathology update, a response, a toxicity event.
  Read it from the actual file; never assume it.

## Procedure

1. Read the new clinical datum from `inbox/` by hand. Quote the specific value
   (e.g. "CT 2026-06-18: target lesions −34% vs baseline → PR by RECIST 1.1";
   "CEA 210→44 ng/mL over 8 wks"; "grade-3 colitis, drug held").
2. For each prior prediction that the new datum can speak to, write ONE outcome
   record (below). For predictions the datum cannot yet judge, record
   `real_world_verdict: "not_yet_observable"` and `team_was_right: null` — do
   NOT force a verdict.
3. Be symmetric (Darwin / Feynman): log the predictions the team got WRONG with
   the same prominence as the ones it got right. A team that only records its
   hits is fooling itself.
4. Never invent the datum or the verdict. If `inbox/` has no new clinical datum,
   output `outcomes: []` and say so.

## Output (JSON only — persisted via `opl-cancer reconcile --outcomes`)

```json
{
  "outcomes": [
    {
      "id": "O-<hyp_or_pred_id>",
      "hypothesis_id": "<the prior prediction's id, if it scores one>",
      "pre_registered_direction": "<what the team predicted would happen>",
      "real_world_datum": "<verbatim quote of the actual clinical datum + source/date>",
      "real_world_verdict": "confirmed|partly_confirmed|refuted|not_yet_observable",
      "team_was_right": true,
      "what_we_learned": "<1 sentence: how this updates the team's belief>"
    }
  ]
}
```

## Rules

1. `real_world_datum` MUST be a verbatim quote with a date/source from `inbox/`
   (or the organized record), never paraphrased from memory.
2. `team_was_right` is `true` / `false` / `null` (null = not yet observable).
3. Scored against the patient's reality — NOT against more literature (that is
   Wave 4's job and it is circular for this purpose).
4. Output ONLY the JSON object — no preamble, no fences.

## Why this matters

Without this loop, every "calibration" and "compounding" feature grades the
team against its own opinions. The reality outcome is what makes the research
ledger a record of KNOWLEDGE rather than a record of confidence. It also feeds
G48 (research_delta): a run that reconciles against reality has, by definition,
learned something this run.
