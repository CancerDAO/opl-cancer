# ADR-0041 — The prompt/script boundary, `observe`, and `validate`

- Status: accepted
- Date: 2026-06-29
- Supersedes/relates: ADR-0040 (de-script: host LLM is the sole plan path), ADR-0026 (delivery non-bypassable / G34–G37), A1/ADR-0027 (research ledger / G54), C1/ADR-0031 (failure ledger / G52)

## Context

OPL is already a harness/brain split: the `opl_cancer` CLI is a deterministic
harness (no LLM inside the package — it validates, gates, hashes), and the host
agent + dispatched expert subagents are the only reasoning brain (ADR-0040
finished removing the last keyword routers from Python). Reviewing OPL against
**Arbor / Hypothesis-Tree Refinement** (Jin et al., 2026, RUC-NLPIR/Arbor) — the
cleanest published statement of where to draw the prompt/script line — confirmed
OPL had independently converged on most of Arbor's "build logic":

- **Boundary**: the 55 gates are all *structural* — they check that the producer
  self-recorded the right fields coherently (e.g. G39, G43 carry an explicit
  "no-hardcoded-keyword-list" contract); the LLM makes every clinical judgment.
- **Failures as negative constraints**: G52 persists falsified directions; the
  append-only ledger (ADR-0027) means a returning patient's killed direction is
  never silently re-proposed.
- **Generate≠validate independence**: G49 locks + tamper-hashes a pre-data
  forecast before Wave 3 (predict-before-you-look).
- **Forcing-function for the memory write**: G54 blocks delivery unless the run
  wrote to the ledger.

The one Arbor mechanism OPL **lacked** was the coordinator's **re-projection
step** — Arbor's `observe`, the read-only render of durable state the coordinator
re-grounds on each cycle *instead of trusting lossy conversation memory*. Its
absence is the mechanism behind the session-0d1017d4 failure: the host agent
"remembered" it had run the plan while having actually drifted and skipped waves.
G37 catches that at delivery; nothing re-grounded the agent mid-run to prevent it.

## Decision

1. **`opl-cancer observe`** (read-only, no-LLM, no-write): a deterministic
   projection of a run — goal, planned-vs-done waves, **outstanding** waves, the
   Project-Memory frontier, and **falsified hypotheses across ALL of the
   patient's runs surfaced as negative constraints**. The workflow re-grounds on
   it at the **start of every wave beat** (Steps 5–8) and at **plan time**
   (Step 4) so ideation is conditioned on the pruned directions (the *read half*
   of G52 — G52 writes the dead ends, `observe` reads them back).

2. **`opl-cancer validate`** (read-only): the Arbor `validate` analog — a
   deterministic invariant check over run state (manifest/plan team drift,
   attested-without-brief, delivered-without-ledger = the G54 invariant
   re-checked, delivered-with-outstanding-waves = under-delivery). Run after
   `attest`; non-zero exit means the run is internally inconsistent.

3. **Boundary doctrine made explicit.** The rule OPL has been converging on:
   *the harness owns everything that is a deterministic function of state
   (persistence, traversal, projection, integrity, pure comparison of
   model-supplied values); the brain owns everything that interprets meaning or
   assigns worth.* The harness never calls an LLM; the brain mutates durable
   state only through the CLI's typed commands. A gate may assert structure
   ("a citation anchor exists") but never content quality ("the reasoning is
   sound") — that is a subagent reviewer's job.

Both commands are pure functions of on-disk state, tolerant of a half-built run,
and emit `--json`. They are state *readers*, never executors.

## Consequences

- The host agent has a cheap, deterministic anti-drift surface it can (and is
  instructed to) re-read every beat — closing the loop that G37 only caught at
  the end.
- The failure ledger is now read as well as written: the planner is told to
  treat `observe`'s `negative_constraints` as dead-ends, so budget is spent on
  new ground (structured search over a bigger fan-out).
- No new numbered gate is introduced (G56+ are reserved for the in-flight
  value-source/CRC hardening on a separate branch — kept distinct per
  branch-purpose separation).

## Known gap (honest deferral — next ADR)

Arbor's strongest empirical lesson is that **insight *abstraction* upward**
(leaf → direction → global prior) is the dominant driver of its gains — a tree
*without* it scored worse than no tree at all. OPL's G54 only enforces that a
ledger write *happened*; it does not yet enforce that the run produced a
*distilled, abstracted cross-run insight* (as opposed to raw persisted
hypotheses). Making that abstraction its own named, un-skippable judgment beat
(harness reminds + `observe` surfaces the gap + no auto-fill) is the next step;
it is deliberately left to a follow-up ADR + gate rather than colliding with the
G56+ numbers currently in flight elsewhere.
