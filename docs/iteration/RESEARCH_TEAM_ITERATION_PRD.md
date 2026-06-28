# PRD — OPL as a Compounding Research Team (P0 + P1)

> **Status:** Draft for founder review · **Author:** OPL contributors · **Scope:** P0 + P1 (15 items)
> **Source:** maps Vivek's *"how to be good at research"* onto OPL via an 11-agent repo audit
> (workflow `opl-research-excellence-audit`, 8 principle-audits + adversarial + completeness critics).
> **Companion docs:** `references/v2-paradigm.md`, `references/v2-roadmap.md`, `docs/adr/0010-v2-paradigm-shift.md`,
> `docs/adr/0026-delivery-non-bypassable.md`, `references/founder-mode-philosophy.md`.

---

## 0. The thesis (why this iteration exists)

OPL today is **the most rigorous research-*report generator* on earth, named a research *team*.** All 44 mechanical
gates inspect the **report** (anchored, tiered, safe, complete, reproducible). **Not one checks that research
happened** — that the team learned something it didn't know, found out whether it was right, and got smarter for
*this* patient next month. The essay's whole test — *"research speed is the speed at which you discover you're
wrong"* — has no channel in OPL through which **reality** can tell it it was wrong.

This is the same blade you already trusted at v1→v2. The v2 forensic concluded *"a polished MTB, not an AI
scientist team"* and fixed *the report only contained the world-known*. The essay aims one level higher: **even the
world-unknown machinery produces an artifact, because the team does not compound and never closes the loop on
reality.**

### Final form (what OPL is after this iteration)

1. **It compounds.** One wired patient research ledger; run N+1 knows the patient better than run N, never
   re-proposes a direction it already falsified, and starts warm.
2. **It closes the loop on reality.** When a real scan/marker/response/toxicity arrives in `inbox/`, the team scores
   its prior predictions against *that* — not against more literature.
3. **It is gated on research-delta, not just report-quality.** A cold re-run that re-derives an identical beautiful
   brief is *flagged*, even when all safety gates pass.
4. **It separates true from false hope by construction.** Every speculative / world-unknown candidate carries a fair,
   quantified standard-of-care comparator rendered inline; no Elo number reads as absolute strength.
5. **It reads deep, not wide.** Full-text + appendix + the source paper's own limitations are in scope; an
   abstract-only "established" claim is mechanically illegal.
6. **It has calibrated taste.** Within a run it records a pre-data forecast, locks it before the data, and compares.
7. **It picks problems backward** from what the patient wants to exist, and can be surprised into a new direction.
8. **It generalizes.** Routing, planning, triage and classification are LLM-reasoned per patient — not keyword lists and fixed templates — so a new cancer type or comorbidity needs no code change. Python verifies; the LLM judges (§2B).

---

## 1. The dominant finding: built-but-disconnected (read before any task)

The audit's #1 result is **not** "missing scaffolding." It is **orphaned scaffolding** — each one a "looks-like vs
is-like" tell. Verified orphan cluster:

| Symbol | File | Status |
|---|---|---|
| `patient_value_hierarchy_weights()` | `plan/prior_run_ingestion.py:90-106` | docstring claims "Wave 2/3 ranking pre-pends these"; **0 callers** |
| `ProjectMemoryStore.save_insight()` | `memory/store.py:45` | only caller is the `withdraw` command (`cli.py:~1526`) |
| `ingest_prior_runs()` rich path | `plan/prior_run_ingestion.py` | only `latest_prior_run_id` wired (manuscript tag) |
| `prune_below` / `best_first_journal` | `orchestrator/best_first_journal.py:55-63` | never called in live tournament; nodes hardcoded `status='alive'` |
| `cost_tracker.record_subagent` | `memory/cost_tracker.py:120-177` | 0 callers; `wave1_runner.py:388` hardcodes `token_cost:0` |
| `feedback_log` | (advertised in SKILL.md memory layout) | no writer, no reader |
| `PaperQA2Integrator` | `integrators/paperqa.py` / `cli.py:~831` | built with **no `corpus_dir`** → silently `None` → full text never read |
| `evolution/` engine | `cli.py:1307-1318` | being **extracted out** of the patient install |

**Engineering posture for this iteration: wire these stubs and add a CI guard against orphans / live-docstrings-on-dead-code. Several items rated "L" by per-slice auditors are actually "M" because the schema already exists.** Do not design new subsystems where a stub exists — connect it.

### Three consolidations that collapse 12 proposals into 3 primitives

- **One memory-writer closes four principles.** Persisting InsightCards + falsified hypotheses + tournament rounds +
  forecasts + outcomes + provenance index at `deliver/attest` simultaneously satisfies write-everything-down,
  tighten-the-loop, find-your-people, *and* feeds taste/stare-at-outputs. Auditors proposed **five separate ledgers**
  (`memory/falsified/`, `graveyard`, `baseline_ledger`, prior-disconfirmers, `feedback_log`) for what is structurally
  **one append-only ledger with typed records**. → **Workstream A.**
- **One "best-real-option" object serves three principles.** `soc_baseline` (best SoC/trial/EAP option for the
  patient's exact setting + expected PFS/OS + HR/CI + PMID) is simultaneously the `world_known_comparator` in the
  world-unknown render, the seeded competitor in the Elo bracket, and the `delta_vs_baseline` anchor. Produce **once**
  in `treatment_line_recommendation`; three consumers read it. → **Workstream B.**
- **Gate inflation on unverifiable fields is a trap.** A gate that checks "the forecast field is non-empty" cannot
  tell an honest forecast from a fabricated one. **New gates only over machine-verifiable facts** (comparator-non-null,
  forecast-timestamp-precedes-data, provenance-hash-matches, abstract-only-source cap, artifact-exists). Everything
  self-asserted (attribution/primary_carrier, value-misalignment narrative, boundary_cases) goes to **reviewer/Henry
  reasoning**, not a new gate number.

---

## 2. Do-NOT-rebuild list (already is-like — credit and leave)

| Capability | Where | Verdict |
|---|---|---|
| Live primary retrieval over model memory | G1/G2/G36 + Evidence Contract | is-like — only **depth** of reading is missing |
| Within-run disagreement surfacing | G20 (`g20_pi_disagreement_surfacing.py`), G43 (`g43_epistemic_symmetry.py`) | is-like — only **cross-run** compounding is missing |
| Read the raw record before asserting | G35 (`g35_clinical_fact_provenance.py`), `staging_workup.md` | is-like — only **aggregate** failure-reading is missing |
| I²/random-effects/CI discipline | G17 (`g17_meta_i2_policy.py`), `n1_cohort_projection.md` | is-like — only the **tuned-baseline + ablation** half is missing |
| Within-run falsification | Wave-4 `hypothesis_validation.md` (supported/weakened/falsified, support_score) | is-like — only the **pre-data forecast** half is missing |
| Engineering=research (harness) | deterministic CLI + fail-closed gates | is-like — strongest embodiment in the skill |
| Reproducible recipe replay | `tools/reproduce.py` | is-like for recipe integrity |

**Out of scope this iteration (explicitly deferred):**

- ❌ Cross-run Brier / hit-rate / reliability-bin infrastructure — statistical noise at current run volume; a
  "validated 50% (N=2)" line reads as false confidence. Ship the **within-run** forecast lock only.
- ❌ Cross-patient federated prior pool / public insight publishing — large privacy/governance surface; a CancerDAO
  **product** decision, not an OPL engineering iteration (was roadmap ADR-0018).
- ❌ Re-running the tournament under a 2nd model for stability — doubles the most expensive wave; contradicts cheap-first.
- ❌ ~12 new blocking gates on self-asserted fields.

---

## 2B. Second dominant finding: judgment hard-coded as script (kills generalization)

The harness-split was done **half-way**. Python became the gate harness — but a large slice of *reasoning*
stayed hard-coded in Python/YAML as keyword lists, regex routers, fixed task skeletons, and threshold tables.
That is exactly why OPL "runs the same template for every patient": the agenda, the goal→expert routing, the
comorbidity triggers, the task routing, and the actionability tiering are all **medical judgment written as
`if keyword in text`**. A dedicated scan found **7 KILL surfaces, 10 KEEP, 1 borderline.**

**Governing rule — the harness-split, completed (add to `CONTRIBUTING.md`):**
> Python **may** normalize identifiers and verify contracts. Python **must never** judge patient phenotypes or
> compose task/expert routing. If a thing changes per-patient or per-cancer-type, it is judgment → an LLM
> prompt/subagent. If it is a fact or a contract, it is deterministic Python. *(Reasoning generalizes and belongs
> to the LLM; verification must be deterministic and belongs to Python — never mix them.)*

**KILL — judgment disguised as determinism (→ LLM prompt):**

| Surface | Hard-codes | → replace with |
|---|---|---|
| `cli.py:335-345` | fixed 9-task skeleton (Rosa→path, Bert→NGS, Rick→trials…) for **every** patient | LLM planner composes team + task DAG |
| `plan/goal_router.yaml:16-30` | goal-text→expert **regex** routing | LLM semantic goal→expert routing w/ rationale |
| `plan/comorbid_planner.py:63-213` | thresholds (prior_lines≥3, eGFR≤60, age≥70…) + keyword banks → specialist triggers | LLM reasons about severity; **red-line subset → deterministic floor gate** |
| `plan/intake_router.py:29-43` | `_KNOWN_TASK_KEYWORDS` substring→task package | LLM task-package router |
| `plan/intake_router.py:51-68` | `_UNKNOWN_DAG_STUBS` keyword→fixed method DAG | LLM method-DAG composer (the stubbed M5) |
| `glue/render_bridge.py:116-159` | `_TIER_KEYWORDS` substring→actionability tier | LLM actionability-tier classifier |

**KEEP — legitimate determinism (must stay Python, LLM-free):** all mechanical gates (fact verification);
ontology/identifier normalization (`canonicalize/` — drug→RxNorm, gene→HGNC, cancer→OncoTree,
`evidence_level._CROSSWALK`, genome-build); JSON-schema validation; provenance journaling; statistical method
math; the no-LLM safety gates (G24 crisis, privacy scrub) *designed* deterministic as a safety floor;
state-machine plumbing.

**BORDERLINE — `permission_levels.py:19-29`** (L0–L4 mapping): keep deterministic. A consent/transparency
contract must be **predictable**, not LLM-variable; only its *inputs* (is-off-label / is-serious-risk) may be
LLM-judged upstream.

**The conversion pattern (so we don't trade safety for generalization): LLM judges, a gate verifies the floor.**
When a killed script also encoded a *safety floor* (the red-line comorbidity thresholds), extract that floor into
a deterministic gate — the LLM may **expand** the team/agenda freely (generalization), but may **never drop** a
floor-mandated item (safety). Pure-routing keyword lists (goal_router, intake, tier) carry no floor and just
become prompts validated by their output schema.

---

## 3. The items (P0 + P1) organized into 5 workstreams

Legend: **★ net-new** · **○ on v2-roadmap, re-prioritized/re-aimed** · effort S/M/L · gate = new machine-verifiable gate.

### Workstream A — The Compounding Spine (keystone; blocks A2/A3, C2, C3, D4)

**A1 ○→P0 — Wire the ONE patient research ledger.** *(pulls roadmap ADR-0017 forward from P1; broadens it from
"Sid episodic log" to the whole spine)* · effort **M** · ADR-0027
- Extend `ProjectMemoryStore` (`memory/store.py`) with typed records: `hypotheses` (incl. `status='falsified'`),
  `tournament_rounds`, `forecasts`, `outcomes`, `failure_piles` — one append-only ledger, typed rows, **not** five stores.
- Add a deterministic post-delivery step (`glue/delivery_runner.py` + `cli.py` attest path) that persists every
  delivered claim/hypothesis/round the host already wrote to `triggers/<run_id>/`. Pure harness; no LLM added.
- Actually call `ingest_prior_runs()` in the planner (`cli.py` plan path) and **kill the `patient_value_hierarchy_weights` orphan** (wire it or delete the false docstring).
- Serialize `best_first_journal.to_jsonl()` (today built and dropped in `wave2_runner.py`).
- **gate G54 `memory_ledger_written` (BLOCK):** attest fails if the run produced claims/hypotheses but wrote zero rows.
- **CI guard:** new `tests/test_no_orphans.py` — fail if a public symbol with a "wired into X" docstring has no
  non-test caller (covers the orphan cluster permanently).

**A2 ★ P0 — Close the loop on REALITY.** *(the single missing primitive no auditor proposed)* · effort **L** · ADR-0028
- New `prompts/tasks/outcome_reconciliation.md`: when a new scan/marker/RECIST/toxicity arrives in `inbox/`, score
  the team's prior ranked hypotheses/options/forecasts against **that real datum** (not against more literature; not a
  fresh `recist_progression.md` analysis that ignores priors).
- Persist `{prediction, pre_registered_direction, real_world_verdict, team_was_right}` into the A1 ledger
  (`outcomes` records). This is the **only ground-truth error signal in the system.**
- Wire the Feedback agent (`inbox/` watcher) to trigger reconciliation on new clinical files.

**A3 ★ P0 — `research_delta` gate.** · effort **M** · (folds into ADR-0028)
- **gate G48 `research_delta` (FLAG, not hard-block):** compares this run to the prior run on the same patient via the
  A1 ledger; flags a run that produced **zero net-new knowledge** (no direction killed, no candidate the prior run
  lacked, no calibration update, no resolved outstanding question, no surprise chased). The mechanical embodiment of
  "team, not essayist." FLAG (surfaced to host + patient note), not BLOCK, to avoid punishing a legitimately stable
  follow-up — but the flag must appear in the delivery contract.

### Workstream B — The False-Hope Firewall (independent of A; can run in parallel)

**B1 ★ P0 — `soc_baseline` / `world_known_comparator` (ONE object, three consumers).** · effort **L** · ADR-0029
- Add required `soc_baseline{best_option, expected_pfs/os, HR, CI, PMID, patients_own_current_plan?}` to
  `treatment_line_recommendation.md` output + `schemas/claim.v2.schema.json`; every other option states `delta_vs_baseline`.
- Add required `world_known_comparator{}` to each world-unknown candidate (`hypothesis_generation.md`,
  `drug_repurposing.md`): the best real option for the same setting + its anchor + `human_efficacy_data_for_candidate:
  none|preclinical|case_report` + the honesty line.
- Render inline: in the options section (`delta_vs_baseline`) and **inside the orange box** of the world-unknown
  section (`patient_brief.html.j2:154-205`, `patient_brief.md.j2:68-90`, `render/brief_render.md:89-96`).
- **gate G45 `world_unknown_comparator` (BLOCK — safety, fail-closed):** block render of any `world_unknown_candidate`
  whose comparator/`best_world_known_option` is null.
- **gate G46 `soc_baseline_quantified` (BLOCK):** block a treatment-line claim that ranks options without a populated
  `soc_baseline`. Keep G41 (`soc_completeness`) as the separate WARN gate it already is.

**B2 ★ P0 — `n1_applicability_audit` + read deep + abstract-only cap.** · effort **L** · ADR-0030
- Fix the enabler: extend `integrators/paperqa_full_text.py` to fetch the PMC-OA **package** (full-text JATS XML +
  supplementary files) via `oa.fcgi`; add a Wave-1 prefetch that writes full text into a per-run corpus; **fix
  `cli.py:~831` to construct `PaperQA2Integrator(corpus_dir=...)`** (today it raises → silently `None`).
- New `prompts/tasks/n1_applicability_audit.md`: for every established/exploratory PMID driving a patient-facing
  option, extract from full text/supplement — (a) inclusion/exclusion criteria, (b) the subgroup/forest-plot effect
  matching the patient's axes (line, biomarker, ECOG, organ function), (c) the source paper's **own** limitations
  verbatim quote. Emit `applicability_to_n1{patient_in_subgroup, subgroup_effect, exclusion_hit, source_limitation_quote}`.
  Henry raises a risk-card when a pivotal trial excluded patients like this one or showed no benefit in their subgroup.
- Add `source_section` enum `{abstract, full_text, supplementary, subgroup_table, limitations}` to each PMID evidence
  entry (`schemas/claim.v2.schema.json`).
- **gate G47 `source_section_depth` (BLOCK):** any `established` claim driving a patient-facing option must have ≥1
  evidence entry with `source_section ∈ {full_text, supplementary, subgroup_table}`; else cap `claim_layer` at
  `exploratory` (or block if rendered as actionable). Closed-access PMIDs tagged `[ABSTRACT-ONLY]`, never fabricated.
- Add a "Source-study caveats" subsection to the brief, distinct from OPL's own N=1 limitations.

**B3 ★ P1 — attribution / ablation (reviewer-reasoning, NOT a hard gate).** · effort **M**
- Add `attribution{primary_carrier_expert, primary_carrier_evidence_ref, survives_without_primary: bool, rationale}`
  to L2/L3 recommendations + world-unknown candidates (`claim.v2.schema.json`).
- If `survives_without_primary == false`, floor the claim's tier to the carrier's tier. Render: "rests primarily on
  [single cohort PMID X]; remove it and this weakens to speculative."
- Enforce via **reviewer/Henry focus + WARN** (`claim_audit.md`), not a BLOCK gate (self-asserted field).

### Workstream C — The Honest Loop (kill + forecast + failures)

**C1 ★ P0 — Make the tournament kill + stop presenting unscored Elo as validated.** · effort **M** · ADR-0031
- Wire `best_first_journal.prune_below` into `orchestrator/tournament_loop.py`: after each round, mark candidates
  >threshold below top-1 as `status='pruned'`, stop judging them, write `killed_candidates.jsonl{hyp_id, round,
  final_elo, kill_reason}`.
- **gate G50 `tournament_kill_recorded` (BLOCK):** block when Wave 2 ran ≥4 hypotheses but `killed_candidates.jsonl`
  is empty and no explicit "all-survived" justification exists.
- **gate G51 `unfalsified_ranking` (BLOCK):** when the brief renders the hypothesis leaderboard, require either a
  Wave-4 scoring artifact per top hypothesis **or** a per-hypothesis badge "unfalsified ranking — not yet tested
  against data" under speculative framing. (Critical in the common non-Docker Wave-1/2/5 path where Wave 3/4 are skipped.)

**C2 ★ P1 — Predict-before-you-look (within-run forecast lock only).** *(depends on A1 for persistence)* · effort **M** · ADR-0032
- Add `prior_expectation{predicted_wave3_result, confidence_0_1}` to `Hypothesis` (`memory/schemas.py`), filled at
  generation time (`hypothesis_generation.md`) **before** any Wave-3 data; add `forecast_locked_at` + `forecast_hash`.
- Add `updated_belief{posterior_confidence, surprise: none|mild|strong, what_changed}` to the validation output
  (`hypothesis_validation.md`), computed by comparing the locked forecast to the Wave-3 evidence.
- **gate G49 `forecast_pre_registration` (BLOCK — verifiable fact):** for each top-k hypothesis, require
  `forecast_locked_at` whose timestamp **precedes** the earliest Wave-3 data artifact, and `forecast_hash` matches.
  This is the one machine-verifiable half; **no cross-run Brier** (deferred §2).

**C3 ★ P0 — Run-level failure-ledger (Ng's "read all failures, sort, attack biggest").** *(feeds A1)* · effort **M** · ADR-0033
- New `prompts/tasks/error_analysis.md` dispatched after Wave 4, before Henry: read **every** failure artifact in
  `triggers/<run_id>/` (reviewer fails, falsified/weakened hypotheses, G14 cohorts with subgroup match <0.5,
  single-source data points, integrator-empty raises, UNKNOWN-heavy fields) → write `failure_ledger.json`: failures
  sorted into piles by root cause, biggest pile named, each top-3 conclusion flagged if its evidence overlaps a pile.
- **gate G52 `failure_ledger_written` (BLOCK):** block if failure artifacts exist but no ledger was produced, **and**
  block if a top-3/headline conclusion cites evidence the ledger marks as the biggest pile with no caveat token.
- Surface the **content** (not just counts) of the ledger in `pi_delivery.md` + the patient brief — a mandatory "what
  the team could not confirm" section. Persist the biggest pile to the A1 ledger (`failure_piles`).
- Upgrade `tools/observe.py` from count-only to a per-run readable failure digest.

### Workstream D — Originality (outcome-backward + breadth + surprise)

**D1 ★ P0 — Outcome-backward planning + "candidate the oncologist didn't name" gate.** · effort **M** · ADR-0034
- Extend `prompts/pi/intent_parser.md` + `schemas/profile.schema.json` + `plan/schemas.py` with structured
  `desired_endpoint` (live-longer-with-function / cure-intent / minimize-toxicity / event-to-avoid) and
  `decision_juncture` (2L→3L / trial-vs-SoC / post-PD reframing).
- New `prompts/pi/goal_backward_planner.md`: host-reasoned planning that takes the verbatim goal + structured
  endpoint + value hierarchy + profile and emits a backward-chained agenda; the deterministic `cli.py:335-345`
  skeleton becomes the **floor** the agenda must cover-or-exceed (never the ceiling). Emit `endpoint_coverage_gaps`
  (branches the template missed) and surface them in the Step-4 echo.
- **gate G53 `novel_candidate_presence` (BLOCK, negative-guarded):** delivery must contain ≥1 option tagged
  `not_in_treating_plan: true` traceable to the patient's endpoint **with a real `testability_path` + tier**, OR an
  explicit honest "this run found no option beyond your current plan, here is why." (Negative guard prevents
  satisfying it with a novel-looking but unbacked option.)
- Repoint `hypothesis_generation.md` strategy 1 from `literature_gap` (mode-a, survey-of-gaps) to `endpoint_backward`
  (mode-b): "what experiment, if it succeeded, would most move E for THIS patient and is enumerable by no survey?"

**D2 ★ P1 — Breadth / unfair-advantage lens planner.** *(depends on D1; "wander on purpose", owned by no auditor)* · effort **M** · ADR-0035
- Replace "every patient gets the same t1–t9 instruments" with a planning step: "given THIS patient's rare
  constellation, which non-default modality (metabolism / immunology / real-world-data / mechanism / repurposing) is
  the unfair-advantage corner where no oncologist is looking?" — and over-invest there. Pay tuition in several lenses,
  then bet where the N=1 is special.

**D3 ★ P1 — Follow-the-surprise channel.** *(depends on C2: a surprise = a contradicted forecast)* · effort **M** · ADR-0036
- When a Wave-3 result contradicts the pre-registered forecast direction or surfaces a strange-tail anomaly, spawn a
  replan that **promotes chasing it** (new task, new expert) rather than only logging it to the failure ledger.
- Discipline guard: a chased "surprise" must carry a `testability_path` (no manufactured novelty).

**D4 ○→re-aim P1 — Keep the evolution loop in the patient path; re-aim it at the disease frontier.** *(was ADR-0020)* · effort **M** · ADR-0037
- Stop extracting `evolution/` out of the patient install (`cli.py:1307-1318`).
- Re-target the analyzer from "OPL-software self-improvement for the next *different* patient" to "**this patient /
  this disease's research frontier**," fed by the A2 reality ledger. Upgrade `collector.py` to capture the strange
  tail (reviewer-fail reasons, falsified-hypothesis rationale, G14 low-match cohorts) instead of 5 keyword-grepped
  lines. Keep the no-auto-apply / human double-signoff policy.

---

### Workstream E — De-script the judgment layer (LLM judges, Python verifies) *(completes the harness-split; E1 ≡ D1)*

**E1 ★ P0 — LLM-reasoned planner (merges with & upgrades D1).** · effort **L** · ADR-0034
- Replace the fixed skeleton (`cli.py:335-345`) + goal→expert regex (`plan/goal_router.yaml`) + threshold/keyword
  comorbidity triggers (`comorbid_planner.py:63-213`) with ONE host-reasoned planner — the same
  `prompts/pi/goal_backward_planner.md` artifact as D1 — that reads goal + structured endpoint + profile +
  comorbidities and composes the expert team + task DAG with per-task rationale. Expert names become soft
  suggestions, not hard wiring.
- **Preserve safety deterministically — gate G55 `plan_floor_coverage` (BLOCK):** extract the red-line subset of
  comorbid thresholds (those backed by `clinical_stop_rules.json` / `drug_comorbidity_contraindications.json` /
  G40) into a deterministic floor; the LLM plan may expand beyond it, but if a red-line is present the mandated
  expert/task must be in the plan.

**E2 ★ P1 — LLM task-package + method-DAG router.** · effort **M** · ADR-0038
- Replace `intake_router.py:29-43` `_KNOWN_TASK_KEYWORDS` and `:51-68` `_UNKNOWN_DAG_STUBS` with an LLM router that
  semantically matches the patient question to the task-package registry (`prompts/tasks/*.md`) and, for open-set
  questions, composes a method DAG from the MethodRegistry (finally implements the stubbed M5 composer). Python
  keeps registry enumeration + schema validation of the chosen package.

**E3 ★ P1 — LLM actionability-tier classifier.** · effort **M** · ADR-0039
- Replace `render_bridge.py:116-159` `_TIER_KEYWORDS` substring matching with a classifier prompt that reasons
  about assay turnaround + regulatory/data-access constraints → {actionable_this_week, weeks, months_or_more,
  research_only}. Python keeps the enum schema + that a tier was assigned.

**E4 ★ P0 — CI guard against new judgment-as-script.** *(folds into the A1 no-orphan CI)* · effort **S**
- Lint that flags NEW module-level keyword tuples / routing regex in `plan/`, `glue/render_bridge.py`, and intake
  routing. Keeps the dividing line from eroding back into Python.

---

## 4. Gate allocation (G45+ — all over machine-verifiable facts)

| Gate | Name | Type | Verifiable fact | Item |
|---|---|---|---|---|
| G45 | `world_unknown_comparator` | BLOCK | comparator object present + `best_world_known_option` non-null | B1 |
| G46 | `soc_baseline_quantified` | BLOCK | `soc_baseline` block populated (HR/CI/PMID) when options ranked | B1 |
| G47 | `source_section_depth` | BLOCK | established patient-facing claim has ≥1 full_text/supplement/subgroup source | B2 |
| G48 | `research_delta` | FLAG | run produced ≥1 net-new ledger delta vs prior run | A3 |
| G49 | `forecast_pre_registration` | BLOCK | `forecast_locked_at` precedes earliest Wave-3 artifact + hash matches | C2 |
| G50 | `tournament_kill_recorded` | BLOCK | `killed_candidates.jsonl` non-empty when N≥4 (or justified) | C1 |
| G51 | `unfalsified_ranking` | BLOCK | Wave-4 score artifact OR "unfalsified" badge per rendered top hyp | C1 |
| G52 | `failure_ledger_written` | BLOCK | `failure_ledger.json` exists when failures exist; headline not propped by biggest pile | C3 |
| G53 | `novel_candidate_presence` | BLOCK | ≥1 `not_in_treating_plan` candidate (w/ testability+tier) OR honest null | D1 |
| G54 | `memory_ledger_written` | BLOCK | ledger rows written at attest when claims/hyps produced | A1 |
| G55 | `plan_floor_coverage` | BLOCK | LLM-composed plan covers the deterministic red-line safety floor (contraindication-mandated expert/task present) | E1 |

**Not gates (reviewer/Henry reasoning):** attribution/`primary_carrier` (B3), value-misalignment narrative, `boundary_cases`.
Update `references/mechanical-gates.md` header (stale "G1–G43"; reality is G1–G44, G38 reserved → new G45–G54).

---

## 5. Dependency graph

```
A1 (ledger) ──┬─▶ A2 (reality loop) ──▶ A3/G48 (research_delta)
              ├─▶ C2 (forecast persistence) ──▶ D3 (surprise = contradicted forecast)
              ├─▶ C3 (failure persistence)
              └─▶ D4 (evolution re-aim, also needs A2)

B1 (soc_baseline object) ──┬─▶ B1-render (G45 comparator)
                           └─▶ C1-seed (SoC in Elo bracket, P1 stretch)

B2 (full-text enabler) ──▶ B2 (n1_applicability_audit, G47) ──▶ B3 (attribution)

D1 (endpoint + goal_backward) ≡ E1 (LLM planner, same artifact; G55 floor) ──▶ D2 (lens planner)
E2 (LLM intake router) · E3 (LLM tier classifier) — independent ; E4 (CI guard) folds into A1

C1 (kill + unfalsified guard) — independent of A (uses run-local artifacts)
```

**Keystone = A1.** **Parallelizable from day 1 = A1, B1, B2-enabler, C1, D1≡E1, E2, E3** (no cross-deps).
**Build order:** A1 → (A2, C2, C3) ; B1 → B-render ; B2-enabler → B2 → B3 ; D1≡E1 → D2 ; C2 → D3 ; A2 → D4 ; E2/E3 anytime ; E4 with A1.

---

## 6. Branch strategy (per `CONTRIBUTING.md` branch-purpose-separation + one-branch-one-deliverable)

Current branch `feat/deterministic-retrieval-standardization` has uncommitted work — **do not** build on it. Each
workstream ships as its own branch + ADR + E2E matrix; **product branches stay independent of any benchmark/adapter
branch** (no `bench-`/`feat-` mixing).

| Branch | Items | ADR | Deliverable |
|---|---|---|---|
| `feat/research-ledger-spine` | A1 + CI orphan guard | 0027 | wired ledger + G54 + no-orphan CI |
| `feat/reality-outcome-loop` | A2 + A3 | 0028 | outcome reconciliation + G48 |
| `feat/false-hope-baseline` | B1 | 0029 | `soc_baseline`/comparator object + G45/G46 |
| `feat/read-deep-n1-applicability` | B2 (+B3) | 0030 | PMC-OA package + applicability audit + G47 |
| `feat/honest-tournament` | C1 | 0031 | real kills + G50/G51 |
| `feat/predict-before-look` | C2 | 0032 | within-run forecast lock + G49 |
| `feat/run-failure-ledger` | C3 | 0033 | error-analysis + G52 |
| `feat/outcome-backward-planner` | D1 + E1 + E4 | 0034 | endpoint intake + **LLM planner replacing skeleton/goal_router/comorbid-thresholds** + floor gate G55 + no-script CI guard + G53 |
| `feat/breadth-lens-planner` | D2 | 0035 | unfair-advantage lens step |
| `feat/follow-the-surprise` | D3 | 0036 | anomaly → replan |
| `feat/evolution-disease-frontier` | D4 | 0037 | re-aimed evolution in patient path |
| `feat/llm-intake-router` | E2 | 0038 | LLM task/method router replacing intake keyword lists |
| `feat/llm-tier-classifier` | E3 | 0039 | LLM actionability-tier classifier replacing `_TIER_KEYWORDS` |

Each branch: own ADR, own E2E matrix (§7), updates `references/mechanical-gates.md` + `CHANGELOG.md` + relevant README
(per branch-readme-sync rule), version bump per semver. Merge order follows the dependency graph; A1 + B1 + B2 +
C1 + D1 are the P0 core that lands first.

---

## 7. E2E validation matrix (per multi-case-validation rule: ≥2 patients, ≥2 cancer types)

OPL E2E = patient records → full delivery (5-Wave / 20-expert / Henry / patient_brief / all gates) — **not** "ran to
chair." Reuse the `references/v2-e2e-validation-matrix.md` shape. Minimum cohort: the v2 forensic case **PT-EE62321353
(KRAS G12C MSS mCRC L4+)** + one **different cancer type** (e.g. a lung/EGFR or breast/HR+ case from `patients/` or
`opl_test_data/`).

| Item | Programmatic success criterion (both patients) |
|---|---|
| A1 | After 2 sequential runs, `memory/` ledger has ≥1 InsightCard + ≥1 falsified hypothesis from run 1 readable in run 2; CI orphan test passes; G54 blocks a stubbed empty-ledger run |
| A2 | Drop a synthetic follow-up scan into `inbox/` → an `outcomes` record scores ≥1 prior prediction as right/wrong against the scan (not against literature) |
| A3 | A deliberate cold re-run (identical inputs) trips G48 FLAG; a run with a killed direction does not |
| B1 | Every `world_unknown_candidate` in the brief renders a non-null comparator line; G45 blocks one with comparator removed; options show `delta_vs_baseline` |
| B2 | ≥1 `established` claim carries a `subgroup_table`/`supplementary` source; G47 caps a hand-crafted abstract-only "established" claim to exploratory; PaperQA2 corpus is non-None |
| C1 | Wave 2 with ≥4 hypotheses writes ≥1 killed candidate; non-Docker run shows the "unfalsified ranking" badge; G50/G51 block the inverse |
| C2 | Top-k hypotheses carry `forecast_locked_at` < earliest Wave-3 artifact; G49 blocks a forecast written after the data |
| C3 | `failure_ledger.json` produced with ≥1 named pile; a headline propped by the biggest pile is blocked by G52 unless caveated |
| D1 | Brief contains ≥1 `not_in_treating_plan` candidate w/ testability+tier OR explicit honest null; G53 blocks the inverse; `desired_endpoint` present in profile.json |
| D2 | Two patients of different types select **different** non-default lenses (proves it's patient-specific, not a fixed template) |
| D3 | A planted contradicting Wave-3 result spawns a replan task that chases it (with testability_path) |
| D4 | `evolve` runs inside the patient path; analyzer output references this disease/patient, not OPL-software design |
| E1 | Two **different** cancer types produce **different** expert teams (not the fixed t1–t9); G55 blocks a plan missing a contraindication-mandated expert; no keyword/threshold remains in the plan path |
| E2 | A patient question with **no keyword match** routes to the correct task package (semantic); an open-set question composes a method DAG |
| E3 | A testability path worded with **no tier keyword** is still classified into the correct actionability tier |
| E4 | CI flags a planted keyword→expert router added to `plan/` |

---

## 8. Success metrics (the reframe, measured)

1. **Compounding:** run N+1 starts warm — measurable ledger carryover; zero re-proposal of a prior-falsified
   direction without new evidence.
2. **Reality-closure:** ≥1 `outcomes` record per patient who has any follow-up datum; the team can state its own
   right/wrong record per patient (not a population Brier).
3. **False-hope separation:** 100% of world-unknown candidates carry a fair comparator; 0 abstract-only "established"
   patient-facing claims.
4. **Research-delta:** every run is either a net-new-knowledge run or explicitly FLAG'd as a stable follow-up.
5. **No new orphans:** CI orphan guard green; the 8-symbol orphan cluster reduced to 0.
6. **Generalization (de-scripting):** the 7 KILL surfaces converted to LLM prompts; `plan/` + intake + tier paths
   contain zero keyword/threshold routing; a brand-new cancer type or comorbidity needs no code change (no-script CI guard green).

---

## 9. Open questions for founder sign-off

- **G48 `research_delta` as FLAG vs BLOCK** — recommend FLAG (a stable, honest follow-up shouldn't exit non-zero).
  Confirm.
- **Reality-loop trigger** — auto-reconcile on any `inbox/` clinical file, or only on patient confirmation?
  (Founder-mode default = auto, surfaced.)
- **D4 evolution** — keep in patient install (this PRD's position) vs continue the extraction in
  `EVOLUTION_EXTRACTION_TODO.md`. These now conflict; this PRD argues to **reverse** the extraction and re-aim.
- **Sequencing** — land all five P0-core branches (A1/B1/B2/C1/D1≡E1) before any P1, or interleave C2/D-series earlier?
- **De-scripting aggressiveness** — convert all 7 KILL surfaces, or stage E1 (the planner — biggest leverage, P0) first
  and leave E2/E3 (intake + tier routing, P1) for a follow-up? `permission_levels.py` L0–L4 mapping stays deterministic
  regardless (consent contract). Recommend: E1 in the P0 wave, E2/E3 in the P1 wave.
