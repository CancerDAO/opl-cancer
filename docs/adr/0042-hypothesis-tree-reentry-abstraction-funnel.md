# ADR-0042 — Hypothesis tree, re-entry/depth, insight abstraction, informative selection, explored-vs-survived funnel

- Status: accepted
- Date: 2026-06-29
- Relates: ADR-0041 (prompt/script boundary, `observe`/`validate`), A1/ADR-0027 (research ledger, G54), C1/ADR-0031 (tournament kill record), C3/ADR-0033 (failure ledger, G52), D1/ADR-0034 (plan floor, G55)

## Context

Comparing OPL's architecture against **Arbor / Hypothesis-Tree Refinement**
(RUC-NLPIR/Arbor) surfaced four dynamics Arbor's *tree* has that OPL's fixed
linear waves did not. ADR-0041 had already adopted Arbor's re-projection
(`observe`) and invariant check (`validate`) and the failure read-half. The four
remaining gaps — all judged worth closing on first principles because each helps
the patient — are closed here. The unifying move: OPL's `Hypothesis.parent_chain`
field already encodes a tree; nothing read it. We now read it, and add the loops
that operate over it.

## Decisions

**① Insight abstraction upward (the dominant gain driver).** Arbor's ablation
showed abstracting results into reusable priors (leaf → direction → global) drives
most of its cumulative gains; G54 only checked that *a* ledger write happened, not
that the run *abstracted*. New: a PI **abstraction beat** (`prompts/pi/insight_abstraction.md`)
authors 1–3 grounded cross-run priors into `abstraction.json`; `opl-cancer abstract
--finalize` validates the shape (grounded in real leaves, no verbatim auto-fill)
and persists them to the ledger as `run_abstraction` rows. Gate **G60** (WARN,
block=False) records the skip in attestation and `observe` shows it as *owed* —
never withholding the patient's brief (a quality gate, not a safety gate). The
abstraction itself is JUDGMENT (a subagent); the harness only checks structure
and forces the beat to be visible — the prompt/script boundary applied to the
highest-value judgment.

**② Hypothesis tree + re-entry / adaptive depth (architectural).** The planner
may grant a depth budget (`Plan.max_depth`, `deepen_candidates`). `observe` now
renders the hypothesis **tree** (from `parent_chain`) Elo-ranked with depth.
`opl-cancer deepen --target <hyp_id>` is a read-only scaffolder: it checks the
depth budget and, when a lead is near-tied with a rival (a decision-relevant
split) and budget remains, tells the host to dispatch a **focused mini Wave-2..4**
producing child hypotheses (`parent_chain=[target]`). It refuses past `max_depth`;
`validate` flags `DEPTH_BUDGET_EXCEEDED`. Re-entry is strictly **additive** — it
can only exceed the floor on a warranted lead, never shrink the planned team
(G55 still binds), so "never under-deliver" is preserved.

**③ Informative selection under scarce N=1 validation.** `prompts/methods/informative_selection.md`:
in Wave 4, prioritise the re-test that **splits a near-tie** (changes the ranking)
over re-confirming a lone leader, and record `discrimination_target` /
`discrimination_rationale`. The funnel counts ties actually resolved. Judgment in
the prompt; the structural field is recorded and surfaced.

**④ Explored → survived funnel (honest transparency).** `_compute_funnel` is a
deterministic count over the wave artifacts (explored / killed-in-tournament /
validated / falsified / inconclusive / ties-resolved / tree-depth). `opl-cancer
funnel --emit` writes `funnel.json`; the patient brief renders a bilingual
"what we explored vs what survived" section (`patient_brief.md.j2` + render
contract `brief_render.md §8`). Counts = script; the prose = the brief. Surfacing
"inconclusive" honestly is itself useful to the patient and guards against a
false-confidence read.

## Boundary discipline

Every judgment piece lives in a prompt (abstraction lesson, which lead to deepen,
which tie to split); every deterministic piece lives in the harness (tree build,
depth-budget counter, funnel counts, gate G60's structural shape check). No LLM
was added to the Python package; the new commands are state readers/scaffolders
(`abstract` persists an LLM-authored artifact; `deepen`/`funnel`/`observe` never
write run reasoning). This is ADR-0041's boundary carried through.

## Consequences

- OPL is no longer a strictly-flat pipeline: a warranted lead can be deepened
  within a run, bounded by a deterministic budget — without ever under-delivering.
- Learning compounds *upward* (abstracted priors), not just *across* (raw ledger).
- The patient sees the full explored-vs-survived picture, not only the survivors.
- Gate numbering: **G60** used; **G56–G59 are reserved** for the in-flight
  value-source / CRC hardening on the parallel branch (branch-purpose separation).

## Known follow-ups

- `deepen` scaffolds the re-entry; the focused mini-wave execution is the host's
  dispatch (as with every wave — the CLI never executes). A future ADR may add a
  convergence gate (loop-until-dry) bounding deepening rounds.
- Cross-run priors are persisted + surfaced; a future step could weight the
  next run's ideation by prior confidence.
