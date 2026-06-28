# EVOLUTION EXTRACTION TODO — `opl-cancer-evolution` standalone repo

> ⛔ **SUPERSEDED (research-team iteration, founder decision A — 搬回病人路径).**
> The founder chose to KEEP the tournament + evolution engine IN the patient
> product and reverse this extraction. Do NOT continue extracting `evolution/`
> /`orchestrator/`; instead re-aim the evolution loop at the disease frontier
> (D4, `memory/disease_frontier.py`) and wire the C1/C2/D3 runtime producers.
> See `docs/iteration/IMPLEMENTATION_STATUS.md` → "FOUNDER DECISION: A". This
> file is retained for history only.

Status: **decoupling DONE in `feat/harness-split`** (this branch). The patient
CLI now imports and runs with **zero** module-load dependency on
`src/opl_cancer/orchestrator/*` or `src/opl_cancer/evolution/*`. This file is the
manual follow-up checklist for the actual *extraction* to a separate repo
(`opl-cancer-evolution`). **Do NOT create the repo as part of the harness-split
branch** — this is a manual follow-up (PRD §3 / §9.1).

Proof the decouple already holds (run from repo root, working tree on this
branch — note the package is editable-installed from a *different* checkout, so
point PYTHONPATH at this tree):

```
PYTHONPATH=$PWD/src python -c "from opl_cancer import cli; print('patient cli imports clean')"
# With orchestrator/ + evolution/ physically removed, cli still imports and
# exposes 22 patient commands; `evolve` cleanly disappears (find_spec guard).
```

---

## 1. Files that MUST move to `opl-cancer-evolution`

### `src/opl_cancer/orchestrator/` (15 modules — the self-improvement engine)
- `__init__.py`
- `best_first_journal.py`
- `debate.py`            ← imports `_llm_contract`
- `dispatch.py`          (`ExpertHandler`, `dispatch_wave` — used by wave1 execution)
- `evolution.py`         ← imports `_llm_contract`
- `experimental_insights.py`
- `generation.py`        ← imports `_llm_contract` (`STRATEGIES`, `HypothesisGenerator`)
- `meta_critique.py`     ← imports `_llm_contract`
- `pi_session.py`        ← imports `_llm_contract`
- `pushback_router.py`   (`log_trigger` — best-effort, used by `glue/_post_write.py`)
- `reflection.py`        ← imports `_llm_contract`
- `reviewer_hook.py`     (G13 reviewer pairing hub — see §3; stdlib-only)
- `tournament_loop.py`   (`run_tournament`)
- `tournament.py`
- `trigger.py`

### `src/opl_cancer/evolution/` (7 modules — ADR-0020 post-mortem proposal generator)
- `__init__.py`
- `analyzer.py`          ← imports `_llm_contract`
- `collector.py`
- `invariant_gate.py`
- `models.py`
- `proposal_writer.py`
- `scrubber.py`

### The LLM contract + provider clients (the `llm/` dependency that must travel)
- `src/opl_cancer/_llm_contract.py` — **transitional shim** currently kept in
  the patient package ONLY to keep orchestrator/evolution importable after
  `opl_cancer.llm` was deleted. It exposes `LLMClient`, `LLMRequest`,
  `LLMResponse`, `LLMResponseParseError` (Pydantic schemas + abstract client,
  **no network code**). Imported by: `evolution/analyzer.py`,
  `orchestrator/{debate,evolution,generation,meta_critique,pi_session,reflection}.py`.
  → On extraction, **move this file into the evolution repo** and delete it from
  the patient package. The patient path never references it.
- The real provider clients were already deleted from the patient package
  (`opl_cancer.llm`: `__init__.py`, `base.py`, `errors.py`, `router.py`,
  `minimax_client.py`, `anthropic_client.py`, `prompts.py`). They live in git
  history at `HEAD:src/opl_cancer/llm` (last touched commit `dece615`,
  "feat(Iter13): v1.0.5 — per-task model routing"). The evolution repo will need
  a real LLM client (MiniMax-M2.7 per house default,
  `memory:reference_minimax_llm.md`) to replace the shim — recover these from git
  history or reimplement. **The patient package must NEVER regain a provider
  client** (HARNESS_SPLIT_PRD red line; `memory:feedback_no_offline_only`).

---

## 2. Dependencies that travel WITH the engine (back-references into patient pkg)

`orchestrator/*` + `evolution/*` import these patient-package modules. The
extracted repo must either depend on the patient package as a library, or these
shared primitives must be promoted to a common package:

- `from opl_cancer.memory ...`  (e.g. `memory.schemas.Hypothesis`, `memory.cost_tracker`)
- `from opl_cancer.plan ...`    (e.g. `plan.schemas` — `Plan`, `Task`, `WaveAssignment`)
- `from opl_cancer.prompts_loader ...`

Decision for extraction (manual): keep `opl-cancer` (patient) as a published
dependency of `opl-cancer-evolution`, importing `memory` / `plan` /
`prompts_loader` from it. These three are patient-safe primitives (no LLM, no
orchestrator) and are the only inward edges.

---

## 3. `reviewer_hook.py` — the 5-importer coupling hub (decision needed)

`orchestrator/reviewer_hook.py` (`run_reviewer_pairing`) is imported by 5 of 6
wave runners (`wave1/2/3/4/6_runner.py`). It depends ONLY on `json` + `pathlib`
(no `_llm_contract`, no other orchestrator module) and hardcodes its own
`_EXPERT_PAIRING` dict + `_MODEL_POOL` list in Python.

In `feat/harness-split` these 5 import edges were made **lazy** (in-function +
PEP 562 module `__getattr__` re-export so the B3 `test_sniffer_halt_wave*`
wiring contract still holds). So wave execution still needs the hook present, but
the wave runners *import* fine without it.

**Open decision for the extraction phase** (NOT done here, leave as choice):
- **Option A (recommended):** relocate `reviewer_hook.py` OUT of `orchestrator/`
  into a shared `opl_cancer/review/` (patient-side) package. It is stdlib-only
  and the patient wave runners legitimately call it during a live wave. This
  kills the single biggest decouple edge and lets a future patient-only wave run
  do reviewer pairing without the evolution engine.
- **Option B:** keep it in the evolution repo; wave execution then requires the
  engine installed (status quo, just relocated).

---

## 4. `models.yaml reviewer_pairings` — dead config to reconcile (flag, not block)

`models.yaml` has a `reviewer_pairings:` block (expert cross-domain map). It is
read by **no Python module** (`grep reviewer_pairings src/` matches only the G13
docstring). The live expert-pairing matrix is the hardcoded `_EXPERT_PAIRING` in
`orchestrator/reviewer_hook.py`, and the two even disagree (e.g. models.yaml
`rosa: rick` vs reviewer_hook `rosa: (heddy, vince)`). G13
(`validators/gates/g13_reviewer_model_distinct.py`) reads only
`executor_model.id` + `reviewer_pool[].id`, NOT `reviewer_pairings`.
→ During extraction, decide whether `reviewer_pairings` becomes the single source
of truth (and `reviewer_hook` reads it) or is deleted. Not a decouple blocker.
G13 itself is stdlib+yaml only and stays fully on the patient side.

---

## 5. CLI surface after extraction

- `opl evolve` (ADR-0020) is the only patient-CLI command that touches
  `evolution/*`. In `feat/harness-split` it is **conditionally registered** via
  `importlib.util.find_spec("opl_cancer.evolution")` in `cli.py` — present when
  the engine is installed, silently absent (clean `--help`) otherwise. When the
  engine moves to its own repo+CLI, drop the `evolve` command from the patient
  CLI entirely (or keep the find_spec guard so it lights up when the engine
  package is co-installed).
- No top-level `tournament` command exists; tournament is internal to
  `wave2_runner` execution only.

---

## 6. Tests that move / need fixing in the engine repo

Currently failing to COLLECT in the patient tree because they import the deleted
`opl_cancer.llm` (pre-existing harness-split state, NOT introduced by the
decouple work) — these belong with the engine + its restored LLM client:
- `tests/test_llm/*` (all)
- `tests/test_orchestrator/{test_debate_judge,test_evolution,test_generation,test_meta_critique,test_pi_session_llm,test_reflection,test_tournament_loop}.py`
- `tests/test_glue/test_wave2_runner.py`
- `tests/test_e2e/test_p2_hypothesis_e2e.py`, `tests/test_p2_acceptance.py`
- `tests/test_integration/test_minimax_live.py`
- `tests/test_evolution/test_cli_evolve.py` (keep a thin "evolve is gated"
  variant on the patient side)

Stays on the patient side and PASSES today:
`tests/test_e2e/test_pipeline_non_bypassable.py` (delivery guarantee),
`tests/test_glue/test_sniffer_halt_wave{2,3,4,6}.py` (B3 wiring via lazy
re-export), `tests/test_validators/test_g13_reviewer_model_distinct.py`,
`tests/test_orchestrator/test_reviewer_hook.py`, `tests/test_cli.py`.
