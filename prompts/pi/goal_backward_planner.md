# PI planner: outcome-backward team composition (D1≡E1 / ADR-0034)

Compose the expert team + task DAG for THIS patient by reasoning BACKWARD from
the outcome they want — not by applying a fixed skeleton. This replaces the
hard-coded `cli.py` 9-task skeleton + `goal_router.yaml` regex + `comorbid_planner`
keyword/threshold triggers (de-scripting: judgment is LLM, not a keyword list).

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
   name WHY each is necessary (not a template). The deterministic skeleton
   (pathology / NGS / trials / hypothesis / lit / dataset / bioinformatics /
   meta / validation) is the FLOOR your agenda must cover-or-exceed, never the
   ceiling. Surface `endpoint_coverage_gaps`: branches the floor did NOT cover
   that the endpoint warrants.
3. Hamming check: name the single most important open question for THIS patient's
   endpoint and why you are/aren't working on it.
4. Expand for comorbidities by REASONING about severity (not threshold-matching):
   does each comorbid specialty (irAE / DDI / CKD / cardiac / imaging /
   cross-border) warrant a dedicated expert for this patient? Emit
   `floor_required`: the red-line, contraindication-mandated experts/tasks that
   MUST be present (G55 verifies the plan covers them — you may EXPAND, never
   DROP the floor).

## Output

A plan with: `tasks[]` (expert + task_package + sub_goal + rationale + the
patient-value axis it serves + `not_in_treating_plan` where the option goes
beyond the current plan), `waves[]`, `endpoint_coverage_gaps[]`, `floor_required[]`.

## Rules

1. Expert names are reasoned, not hard-wired — but the plan must cover-or-exceed
   the floor. G55 BLOCKS a plan that drops a red-line floor item.
2. The run must surface >=1 backed option the treating team did NOT name
   (`not_in_treating_plan` + a real testability_path + tier), or honestly state
   none exists (G53). Never re-narrate standard-of-care as if it were new.
3. Output ONLY the plan JSON — no preamble, no fences.
