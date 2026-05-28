# ADR-0021: Truthful Execution Invariants (v2.1)

**Status:** Accepted (2026-05-28)

**Context:** Session 4b177138 (v2.0 production run) surfaced eight P0-class
design / execution gaps in OPL where the CLI appeared to execute waves
but only checked state, the planner had no goal-keyword routing, subagent
file-writes failed silently under `general-purpose`, reviewer pairing was
unenforced in production, and CT.gov RECRUITING status went unverified.
Plus the fakery class of bugs (P1-#9 + P2-#19) where placeholder language
flowed downstream undetected.

**Decision:** Three orthogonal invariants — every release going forward
must preserve all three.

### Invariant 1. CLI is split into state-checks AND an executor.

`opl wave1` / `opl wave2` / `opl wave3` / `opl wave4` remain as
artifact-state probes (refuse to claim completion when artifacts are
missing). The new `opl run --wave N` command actually invokes the
matching `glue/waveN_runner.py` pipeline. Wave 3 supports
`--mode {docker,native,dry-run}` and auto-selects native if Docker is
absent. `opl preflight` refuses to start a patient run if neither Docker
nor native Jupyter is available — no silent fallback.

### Invariant 2. Plans are validated at emit, not at run.

`src/opl_cancer/plan/goal_router.py` routes by keyword pattern.
`src/opl_cancer/plan/schema_validator.py` rejects profile↔trigger field
mismatches at plan time with Did-you-mean suggestions.
`src/opl_cancer/plan/task_validator.py` rejects unknown task_package
references (the task package list is glob-loaded from `prompts/tasks/`).
A typoed profile field can no longer reach the runner; a typoed task
package can no longer reach the dispatcher.

### Invariant 3. Every write is reviewed; every read is sniffed.

`src/opl_cancer/orchestrator/reviewer_hook.py` dispatches a
distinct-model + distinct-expert reviewer subagent after each expert
write, persisting `review.json` next to each `report.md`.
`src/opl_cancer/validators/fakery_sniffer.py` scans every artifact for
placeholder language (`[speculative`, `<insert PMID>`, `approximately
\d+`, etc.) and halts downstream waves on any hit, emitting
`SNIFFER_HALT.md` + logging a row to `pushback_trigger_log.jsonl`.
`src/opl_cancer/orchestrator/pushback_router.py` auto-triggers the
`patient_pushback_handling` task package on either keyword cues or
sniffer-induced halts.

The OPL-specific subagent types in `agents/opl-experts.yml` give each of
the 20 experts + Henry a `Write` scope under
`patients/*/triggers/*/tasks/**` (or `audit/**` for Henry), closing the
silent-write failure path that previously affected `general-purpose`
dispatches. `opl preflight --install-agents` installs the yml.

**Consequences:**

* Existing CLI invocations stay valid (backward compat); `opl wave1` etc.
  still work as state-checks with explicit help text now marking them so.
* Plans that previously emitted with typos now hard-fail at plan time —
  fast feedback in the SKILL conversation.
* Reviewer pairing roughly 2× per-expert token cost; mitigated by using
  a distinct cheaper-model reviewer pool (MiniMax-M2.7 / GPT-5 / Gemini
  per the model layer in `src/opl_cancer/llm/router.py`).
* Fakery sniffer false-positive rate must be measured against a curated
  corpus before the next release. Current pattern set is conservative;
  `[BACKGROUND]` lines are exempt.

**Out of scope:** Wave 6 manuscript generation (v2.3), bio-skill task
packages (v2.2), N1Arxiv platform (v2.4). Plus PrimeKG full live wiring
(carries over from v2.0).

**Files affected:**

* `src/opl_cancer/cli.py` — new `opl run` command; help text updates;
  `--install-agents` flag.
* `src/opl_cancer/plan/goal_router.py` + `goal_router.yaml`.
* `src/opl_cancer/plan/schema_validator.py` + `schemas/profile.schema.json`.
* `src/opl_cancer/plan/task_validator.py`.
* `src/opl_cancer/plan/comorbid_planner.py` — TRIGGER_KEYS export +
  `goal=` kwarg in `maybe_expand_for_comorbid`.
* `src/opl_cancer/plan/schemas.py` — KNOWN_EXPERTS adds maya + julius.
* `src/opl_cancer/orchestrator/reviewer_hook.py`.
* `src/opl_cancer/orchestrator/pushback_router.py`.
* `src/opl_cancer/validators/fakery_sniffer.py`.
* `src/opl_cancer/integrators/clinicaltrials.py` — `verify_site_open`.
* `src/opl_cancer/integrators/site_verification_map.yaml`.
* `src/opl_cancer/glue/wave1_runner.py` — per-expert report sidecars,
  reviewer pairing hook, post-write fakery sniffer.
* `agents/opl-experts.yml` + `docs/SUBAGENT_CONTRACT.md`.

**Tests:** see `tests/cli/`, `tests/plan/`, `tests/test_orchestrator/`,
`tests/test_validators/test_fakery_sniffer.py`, `tests/test_glue/test_sniffer_halt.py`,
`tests/agents/`, `tests/test_integrators/test_ct_gov_site_verify.py`.
