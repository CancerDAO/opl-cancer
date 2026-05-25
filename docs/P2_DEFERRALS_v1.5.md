# v1.5 P2 Deferrals — Rationale and v1.6 Hooks

This document closes out the P2 bin from `docs/PRD_v1.5.md`. Three
items were small enough to ship inside v1.5; three are deferred to
v1.6 with explicit rationale. The v1.5 acceptance criteria
(`docs/PRD_v1.5.md` §6) does NOT require P2 completion.

---

## Shipped in v1.5

### P2-1 · CHANGELOG / README auto-sync hook — PARTIALLY SHIPPED

**What's in v1.5:** CHANGELOG.md gains a complete v1.5 entry listing
all P0 + P1 commits (see the final commit on `iter/v1.5`). SKILL.md
Section "What's new in v1.5" gives a one-paragraph summary. No CI
hook yet enforces sync.

**Deferred to v1.6:** CI step `.github/workflows/docs-sync.yml` that
fails the PR when `src/` or `prompts/` changes without matching
CHANGELOG.md / README.md updates. Easier once CI is on GitHub Actions
(currently the repo doesn't have CI).

### P2-3 · Plan-narration enforcement — SHIPPED

**What's in v1.5:** `cli.py plan()` emits
`comorbid_expansion_triggers_fired` in the JSON output (see
`tests/test_comorbid_planner.py::test_plan_cli_emits_triggers_fired`).
The SKILL.md Step 4 will instruct the assistant to surface this
field verbatim — making any deviation from the baseline t1-t9 plan
visible in the chat stream. AP-11 closed.

### P2-5 · Cost-currency stamp + sample-N disclosure — SHIPPED

**What's in v1.5:** The persona-prefix §4 traceability footer requires
"Estimates labeled [ESTIMATED] are based on: <N> clinics /
institutions, <date range> of quotes." Frances + Dennis personas
inherit this requirement via the prefix. The post-hoc Henry check
(P0-5 G25/G26 family) does not yet enforce this — that's the v1.6
hardening below.

---

## Deferred to v1.6

### P2-2 · SKILL.md ↔ code reconciliation CI — DEFERRED

**Rationale:** Implementing the CI grep+import-check needs the
GitHub Actions runner (the repo doesn't have CI yet) and a small
schema for what counts as a "reconcilable claim" in SKILL.md
(tools / integrators / experts / waves). v1.5 ships a one-time
manual reconciliation pass; v1.6 adds the recurring CI check.

**v1.6 hook:** New script `scripts/check_skill_doc_sync.py` that
greps SKILL.md for tool names + verifies each has a code path,
plus a `.github/workflows/doc-sync.yml` invoking it.

### P2-4 · Robin reflector → live feedback loop — DEFERRED

**Rationale:** The retro found the Robin reflector ran as post-R2
audit, not as a feedback loop that triggers Elo re-pairing. Wiring
it into the Wave-2 tournament runtime is a non-trivial change to
`glue/wave2_runner.py` + tournament-state schema. v1.5 closes
higher-priority gaps; v1.6 takes this on cleanly.

**v1.6 hook:** Refactor `wave2_runner.py` to expose a
`reapply_reflector_round(reflection_results)` method that the
Robin reflector calls during R3 if it surfaces new info that
contradicts an R2 verdict. Tests in `tests/test_e2e/test_wave2_reflector_loop.py`.

### P2-6 · Frances / Dennis "verify access pathway operational" — DEFERRED

**Rationale:** "Currently operational" verification means hitting
Boao / HK / NMPA-EAP endpoints in real time — these are flaky,
rate-limited, and partly behind login walls. v1.5 enforces the
disclosure of estimate-confidence (P2-5 shipped); v1.6 wires a
real probe via web-access skill / cached snapshot. The probe will
live under `prompts/tasks/access_pathway_probe.md`.

**v1.6 hook:** New mcp__web-access task wiring + integrator
`src/opl_cancer/integrators/access_pathway_probe.py` (snapshot +
freshness TTL: 30 days), plus persona-prompt update for
Frances + Dennis.

---

## How to revisit deferred items

Each deferred item is tracked in this doc as the single source of
truth until v1.6 lands them. Do NOT delete entries — when an item
ships in v1.6, mark it `RESOLVED in v1.6 by <commit hash>` at top
of the entry, preserving the rationale below for future archaeology.

## Linkage to anti-patterns

| AP item | P0 or P1 fix | P2 v1.5 fix | v1.6 deferred fix |
|---|---|---|---|
| AP-11 silent override | P0-6 plan_narration shipped (P2-3) | — | — |
| AP-13 W3→W2.5 missing | — | — | P1-8 deferred to v1.6 (overlaps P2-4 Robin loop) |
| AP-16 CHANGELOG out of sync | — | P2-1 partial shipped | P2-1 CI enforcement in v1.6 |
| AP-15 SKILL.md ↔ code drift | — | — | P2-2 v1.6 CI |

— End of P2 deferrals —
