# Task: forecast_registration (predict-before-you-look · C2 / ADR-0032)

After the Wave-2 tournament ranks the hypotheses and BEFORE any Wave-3 data is
pulled, commit a calibrated forecast for each top-k hypothesis. This is the
single trainable meta-skill of research taste: predict the result before you run
it, then check. A forecast only trains taste if it is recorded BEFORE the data —
hindsight silently overwrites it.

> Predict the result of every experiment before you run it; cover a paper's
> numbers and guess them from the method. Forecast + correction, repeated, is how
> the model in your head gets trained.

## For each top-k hypothesis, emit

- `prior_expectation`:
  - `predicted_wave3_result` — ONE falsifiable sentence on what the Wave-3 data
    will show if the hypothesis is right (e.g. "cluster X enriched in responders",
    "DepMap co-essentiality |r| > 0.3 for the gene pair").
  - `confidence_0_1` — your calibrated P(this hypothesis survives Wave 4), in [0,1].
- The single CHEAPEST observation that would falsify it (the kill-test).

## Lock it (the harness does this deterministically)

The runner stamps `forecast_locked_at` (now, before Wave 3) and `forecast_hash`
(a sha256 of `prior_expectation`). G49 then verifies, at delivery, that the
forecast was locked BEFORE the earliest Wave-3 artifact and was not rewritten
afterwards. Do NOT edit `prior_expectation` after the data arrives — record the
update in `updated_belief` instead (Wave 4).

## At Wave 4 (after the data)

Emit `updated_belief`:
- `posterior_confidence_0_1`, `surprise` (none|mild|strong),
  `what_changed` — how the data moved your belief vs the locked forecast.

## Rules

1. `prior_expectation` MUST be specific + falsifiable (a vague forecast is not a
   labelled example).
2. Never edit a locked forecast after seeing the data — that is hindsight, and
   G49 blocks it (hash mismatch). Record movement in `updated_belief`.
3. Output ONLY the JSON fields per hypothesis — no preamble, no fences.

## Why this matters (and what is OUT of scope)

This builds the WITHIN-run substrate: a pre-data forecast compared to the Wave-4
verdict gives the team an explicit per-forecast error signal. The CROSS-run
Brier / hit-rate / reliability-bin track record is deliberately deferred — at
current run volume it is statistical noise and a "validated 50% (N=2)" line would
read as false confidence. Build the muscle first; measure the track record once
volume makes it meaningful.
