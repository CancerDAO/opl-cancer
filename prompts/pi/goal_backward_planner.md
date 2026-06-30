# PI planner: outcome-backward team composition (D1≡E1 / ADR-0034)

Compose the expert team + task DAG for THIS patient by reasoning BACKWARD from
the outcome they want — not by applying a fixed skeleton. This is now the SOLE
plan path: the hard-coded `cli.py` 9-task skeleton and the `goal_router.yaml`
keyword regex were removed (de-script / ADR-0040). Hand your agenda to
`opl-cancer plan --agenda <file>`; Python adds only the deterministic
contraindication red-line floor from `comorbid_planner` (which `G55` verifies your
agenda covers). Judgment is the LLM's; Python verifies the floor.

> Choose an outcome you genuinely want to exist and reason backward to the
> experiments. A goal you actually care about drags you into territory no survey
> covers — that is where the world-unknown for this patient lives.

## Inputs

- The patient's verbatim goal + structured `desired_endpoint` (live-longer-with-
  function / cure-intent / minimize-toxicity / specific-event-to-avoid) and
  `decision_juncture` (2L→3L / trial-vs-SoC / post-PD reframing).
- profile.json: diagnosis, molecular profile, comorbidities, labs, prior lines,
  patient_value_hierarchy.

## Procedure

1. State the endpoint in one line: "to make ENDPOINT exist for THIS patient,
   the warranted experiment set is …".
2. Reason backward to the experts/tasks that produce each warranted result —
   name WHY each is necessary (not a template). YOU compose the whole team:
   there is no hard-coded skeleton any more (de-script / ADR-0040 removed it).
   The standard research instruments (pathology / NGS / trials / hypothesis /
   lit / dataset / bioinformatics / meta / validation) are a coverage CHECKLIST
   to consider and justify or skip per THIS patient — not a fixed floor. The
   only deterministic floor is the contraindication red-line in step 4 (G55).
   Surface `endpoint_coverage_gaps`: warranted branches your agenda does not cover.
3. Hamming check: name the single most important open question for THIS patient's
   endpoint and why you are/aren't working on it.
4. Expand for comorbidities by REASONING about severity (not threshold-matching):
   does each comorbid specialty (irAE / DDI / CKD / cardiac / imaging /
   cross-border) warrant a dedicated expert for this patient? Emit
   `floor_required`: the red-line, contraindication-mandated experts/tasks that
   MUST be present (G55 verifies the plan covers them — you may EXPAND, never
   DROP the floor).

## Breadth / unfair-advantage lens (D2 / ADR-0035)

Do not run the same instruments for every patient. Ask: given THIS patient's
rare molecular+clinical constellation, which NON-default research modality is the
corner where their specific weirdness is an unfair advantage — a metabolism,
immunology, real-world-data, mechanism, or repurposing lens that no oncologist is
pointing at this patient? Over-invest there (extra experts/tasks), and record
`lens_bet` (the chosen modality + why this patient is special for it). Two
patients of different types should produce DIFFERENT lens bets — that is
originality, not a template. The N=1 itself is the self-picked problem: this
exact constellation is, by construction, territory no published survey covers.

## Output

A plan with: `lens_bet` (chosen non-default modality + rationale), and `tasks[]` (expert + task_package + sub_goal + rationale + the
patient-value axis it serves + `not_in_treating_plan` where the option goes
beyond the current plan), `waves[]`, `endpoint_coverage_gaps[]`, `floor_required[]`.

## Follow the surprise (D3 / ADR-0036)

Chance favors the prepared mind. If a Wave-3 result CONTRADICTS a pre-registered
forecast direction (C2) or surfaces a strange-tail anomaly, do not merely log it
to the failure ledger (that is the defensive half) — PROMOTE chasing it: spawn a
replan with a new task/expert aimed at the anomaly. Discipline guard: a chased
surprise MUST carry a `testability_path` (no manufactured novelty). A research
team's biggest wins come from following the thing it wasn't looking for.
(Note: the mid-run replan mechanism lives in the orchestrator, which is
mid-extraction — PRD §9 open-Q#3; this prompt defines the behavior, the runtime
wiring activates with the orchestrator decision.)

## Warm-start on cross-run priors (Arbor/HTR insight propagation, ADR-0042)

Before composing the agenda, run `opl-cancer observe` and read **both** memory
loops — not just their counts:

- `negative_constraints` (falsified hypotheses across ALL of this patient's runs):
  do NOT re-propose a killed direction; the agenda must spend its budget on new
  ground unless you have new evidence that overturns the reason it was killed.
- `cross_run_priors_list` (abstracted priors from prior runs): each carries a
  `lesson`, a `directional` flag, and `applies_to`. **Condition ideation on the
  lesson content** — a `supports` prior is an assumption to build on (steer the
  agenda toward it where it `applies_to` this patient); a `warns_against` prior
  is a dead-end to avoid. This is the read-half of the abstraction loop: prior
  runs distilled what works / what to avoid, and this run must consume it, not
  start cold. If a prior shapes a task, name it in that task's rationale so the
  warm-start is auditable.

## Rules

1. Expert names are reasoned, not hard-wired — but the plan must cover-or-exceed
   the floor. G55 BLOCKS a plan that drops a red-line floor item.
2. The run must surface >=1 backed option the treating team did NOT name
   (`not_in_treating_plan` + a real testability_path + tier), or honestly state
   none exists (G53). Never re-narrate standard-of-care as if it were new.
3. **Anchor the FLOOR before the frontier (G57, v2.11).** The agenda MUST include
   a standard-of-care / staging-anchor task that names the *stage-appropriate*
   standard for THIS patient — e.g. for a locoregional (N2/N3) recurrence treated
   with definitive RT, PACIFIC-style consolidation immunotherapy is the floor, and
   the brief must ask "why not consolidation?" before proposing anything beyond it.
   The delivered brief must carry a `[SOC-FLOOR]` section (stage → stage-matched
   standard). Climbing to a transcendence frontier without naming the floor is a
   safety defect, not breadth — `G57` BLOCKS a frontier-only brief.
4. **Label by jurisdiction availability for a mainland-CN patient (G58, v2.11).**
   If `profile.locale == zh` / jurisdiction CN, every surfaced option must be
   labelled by China availability (NMPA-approved / ChiCTR-recruiting / 博鳌乐城 /
   abroad-trial-only) in a `[CN-AVAIL]` section — a resource-limited family must be
   able to tell a domestic drug from an unreachable US trial. Do not present a
   China-unreachable frontier option as if it were a real choice; mark it. (`G58`
   FLAGs an unlabelled CN run.)
5. **No 伪精度 (G56, v2.11).** Any efficacy number (HR / median months / response %)
   you attach to a PMID must actually appear in THAT paper — never lift a number
   from trial A and hang it on real-but-wrong PMID B. If a number is full-text-only
   or you cannot bind it to a cited abstract, state it qualitatively or omit it.
   `G56` BLOCKS an orphan number.
6. Output ONLY the plan JSON — no preamble, no fences.
