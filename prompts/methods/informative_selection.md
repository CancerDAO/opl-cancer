# Wave-4 informative selection: validate for discrimination, not popularity (Arbor/HTR SELECT, ADR-0042)

Wave 4 retests Wave-2 hypotheses against Wave-3 measured data. When the patient
is **N = 1**, validation evidence is scarce and expensive: you cannot deeply
re-test everything. Arbor/HTR's lesson is that under delayed, partial feedback you
should **select the experiment that resolves an ambiguity** — the one whose
outcome would most change which hypothesis you rank first — not simply the
highest-Elo one (popularity). A test whose result you can already predict teaches
nothing; a test that splits two tied front-runners is worth ten that confirm a
foregone conclusion.

This is a JUDGMENT task. The harness records your choice structurally
(`discrimination_target` on the validation record) and surfaces it in
`observe`/the funnel; it never makes the choice for you.

## How to prioritise

1. **Find the contested front.** From `wave2_hypotheses.json` + `tournament/*.json`,
   identify pairs of *surviving* hypotheses whose Elo ratings are close (a near-tie)
   or that imply **mutually incompatible** next actions for the patient (e.g. "add
   anti-EGFR" vs "anti-EGFR is futile here"). These ties are where validation buys
   the most.
2. **Pick the discriminating test.** For each contested pair, ask: *which Wave-3
   measurement or Wave-4 re-test would come out differently depending on which
   hypothesis is true?* Prioritise validating that one first. Deprioritise re-tests
   whose outcome is already implied by evidence you hold.
3. **Record the choice.** On each Wave-4 validation record you write into
   `wave4_validation.json`, add:
   ```json
   "discrimination_target": ["<hyp_id_a>", "<hyp_id_b>"],   // the tie this test splits; [] if it confirms a lone leader
   "discrimination_rationale": "<why this test's outcome changes the ranking>"
   ```
   Leave `discrimination_target` as `[]` for a hypothesis with no live rival
   (a clear leader or an isolated lead) — that is honest, not a failure.

## Why this helps the patient (first principles)

In an N-of-1 the cost of validation is the patient's time, samples, and the delay
before they get an actionable read. Spending that scarce budget on the test that
*decides between real options* — rather than on padding the score of an already
likely-true idea — gets the patient a confident, decision-relevant answer faster.
It also exposes, honestly, when two options are genuinely tied and the data cannot
yet separate them (surfaced in the explored-vs-survived funnel) — which is itself
a true and useful thing to tell a patient, never papered over.

Three-tier labelling, evidence anchoring, and patient decision-authority are
unchanged: informative selection orders *which* validation runs first; it never
inflates or fabricates a verdict.
