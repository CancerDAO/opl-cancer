# Research-Team Iteration — Implementation Status

Branch: `feat/research-team-p0` (isolated git worktree off `f6c702b`; the
in-flight `feat/deterministic-retrieval-standardization` WIP was never touched).
Each item is a self-contained commit; full suite green per commit.

Baseline at start: 1793 passing. Now: **1852 passing, 8 skipped** (only the
pre-existing WIP-broken `tests/test_glue/test_sniffer_halt.py` excluded — it
imports `SnifferHalt`, which does not exist at `f6c702b`). Gates **42 → 51**
(new G45/G46/G47/G48/G49/G50/G51/G52/G54; G44 reserved for the retrieval branch,
G38 reserved; G53/G55 pending D1).

## DONE (committed, TDD, green)

| Item | What shipped | Commit |
|---|---|---|
| A1 | research-ledger spine (one append-only typed-record store) + persist at deliver + warm-start planner + G54 + no-orphan CI guard | `1126895` |
| B1 | false-hope firewall: soc_baseline + world_known_comparator + G45/G46 + producers + render | `7434cc9` |
| A3 | G48 research_delta (FLAG a null-research run) | `c981838` |
| A2 | reality-outcome loop + `opl-cancer reconcile` + outcome_reconciliation.md | `0d69fe2` |
| C3 | run-level failure-ledger (error_analysis.md) + G52 + brief section | `6756adc` |
| B3 | attribution/ablation field + reviewer WARN | `8075f45` |
| B2 | read-deep: source_section enum + G47 + n1_applicability_audit.md | `efd398c` |
| E3 | LLM actionability-tier classifier — deleted `_TIER_KEYWORDS` | `28535d5` |
| — | integration: fire run-level + claim-level gates at attest (top-down trace) | `f1eb7be` |
| C2 | predict-before-you-look: forecast schema + G49 + forecast_registration.md | `67750cb` |
| C1 | honest-tournament gates G50/G51 + tests | `6e2009c` |

Fully wired + firing at attest: **A1, A2, A3, B1, B2, B3, C3** (+ their gates).

## PARTIAL — verifiable core done, activation pending the founder's
## orchestrator-extraction decision (PRD §9 open-Q#3)

- **C2 (G49)** — gate + Hypothesis forecast fields + prompt done & tested. The
  Wave-2 LOCK wiring (stamp forecast_locked_at/hash in `wave2_runner` before
  Wave 3) lives in the orchestrator that is mid-extraction (`conftest` parks its
  tests). G49 is registered + tested; not live-wired.
- **C1 (G50/G51)** — gates + tests done. Producers (tournament emitting
  `killed_candidates.jsonl` via `prune_below`; renderer flagging a rendered
  leaderboard) are orchestrator-zone. Gates registered + tested; not live-wired.

## NOT STARTED (next session)

- **D1≡E1** — LLM outcome-backward planner replacing the fixed `cli.py:335-345`
  skeleton + `goal_router.yaml` regex + `comorbid_planner` thresholds; +
  `desired_endpoint`/`decision_juncture` intake; + G53 novel_candidate_presence;
  + G55 plan_floor_coverage (deterministic red-line safety floor). Biggest item;
  not orchestrator-blocked — buildable next. (G53/G55 numbers reserved.)
- **D2** — breadth/unfair-advantage lens planner (depends on D1).
- **E2** — LLM intake/method router replacing `intake_router.py` keyword lists.
- **D3** — follow-the-surprise channel (orchestrator replan; partly founder-gated).
- **D4** — re-aim evolution into the patient path. **Directly conflicts**
  `docs/iteration/EVOLUTION_EXTRACTION_TODO.md` — needs the founder's call on
  PRD §9 open-Q#3 before implementation.

## Founder decisions still open (PRD §9)

1. G48 research_delta = FLAG (recommended) vs BLOCK.
2. Reality-loop trigger = auto on any `inbox/` clinical file (recommended) vs
   patient-confirmed.
3. **Orchestrator extraction direction** — keep evolution/tournament in the
   patient path (this iteration's position; unblocks C1/C2 wiring + D3/D4) vs
   continue the extraction. This gates the PARTIAL + two NOT-STARTED items.

To run the suite: `PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q --ignore=tests/test_glue/test_sniffer_halt.py`
