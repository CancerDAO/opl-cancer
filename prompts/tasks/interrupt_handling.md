# Task: interrupt_handling (v1.5.2-3)

**Audience**: the main-thread assistant during Steps 4-10 of a patient run.

**Why**: a full opl-cancer run takes 30-90 minutes. The user must be able to
intervene — skip a stage, simplify scope, pause, ask for a partial preview,
swap experts, cancel — without losing work. This task is the canonical
intent-to-action mapping the assistant invokes the moment the user types
anything mid-run that is not a plain question.

The canonical translation table lives in `SKILL.md` §"Interrupt protocol".
This file documents the JSON envelope the assistant emits + the safety
checks each action must pass.

## Input

- `user_message`: the raw user input mid-run (verbatim).
- `current_stage`: integer 1-5 (matching the lay labels 准备 / 想办法 / 查数据 / 审核 / 写报告).
- `run_manifest`: `triggers/<run_id>/run_metadata.json` so the assistant
  knows what is complete vs in-flight.
- `henry_gates_armed`: list of mechanical-gate IDs that would fire if a
  stage gets skipped (e.g. `["G25"]` when Wave 3 is in progress).

## Output

```json
{
  "task": "interrupt_handling",
  "user_message_verbatim": "<verbatim string>",
  "parsed_intent": "SKIP_STAGE | SIMPLIFY_STAGE | PAUSE | PARTIAL_DELIVERY | CANCEL | REPLAN | STATUS_ETA | UNKNOWN",
  "stage_at_interrupt": <int 1-5>,
  "applies_to_stage": <int 1-5>,
  "ack_message_to_user": "<plain-language echo of what we understood>",
  "safety_warnings": [
    {
      "gate": "G25",
      "consequence": "Henry will BLOCK delivery if Wave 3 deferred",
      "options": ["a", "b"],
      "options_text": ["以 patient_optout 继续 (头部加标记)", "走 native Python 不跳过"]
    }
  ],
  "plan_modification": {
    "skip_stages": [],
    "simplify_directives": {
      "wave2_rounds_cap": null,
      "wave3_gepia3_query_cap": null,
      "wave3_skip_subtasks": []
    },
    "drop_experts": [],
    "add_experts": []
  },
  "needs_user_confirm": true,
  "next_assistant_action": "ask_confirm | apply_immediately | render_partial | terminate"
}
```

## Procedure

1. **Pattern-match** `user_message` against the SKILL.md interrupt
   protocol table. If no pattern matches confidently (regex confidence
   < 0.7), set `parsed_intent: "UNKNOWN"` and ask the user to clarify
   with the 7 canonical options inline.
2. **Acknowledge within 5 seconds.** Always emit the ack_message_to_user
   before any further work. The acknowledgement must restate the user's
   intent in plain language ("收到 — 您想..."). No silent application.
3. **Run safety checks.** For SKIP_STAGE and REPLAN, consult
   `henry_gates_armed`:
   - If `G25` armed AND user wants to skip Wave 3 → surface the
     2-option choice (patient_optout continuation OR native-Python
     path) per SKILL.md §"Hard rules" #3.
   - If REPLAN drops a comorbid-trigger expert (Mark with active
     irAE, Mary with CKD, etc.) → surface the per-expert safety
     concern, require explicit `confirm-override`.
4. **Echo modifications.** For SIMPLIFY_STAGE, echo the EXACT
   reduction in plain language ("4 轮 → 2 轮, 17 候选 → 10 候选") and
   wait for the user's `yes`. Do not silently apply.
5. **CANCEL preserves artifacts.** Write
   `triggers/<run_id>/canceled.json` with:
   ```json
   {
     "canceled_at": "<ISO8601>",
     "reason": "<user message or 'no_reason_given'>",
     "completed_stages": [<int>...],
     "in_flight_stage": <int>,
     "resumable_via": "opl-cancer resume --run-id <id>"
   }
   ```
   Offer PARTIAL_DELIVERY before terminating.
6. **PAUSE blocks the next stage.** Call
   `ProgressReporter.block(stage, reason_zh, options_zh)` (v1.5.1)
   so the chat surface visibly waits for input. The assistant does
   not start the next stage until the user replies.

## Hard rules (mirror SKILL.md §"Hard rules" — non-negotiable)

1. Acknowledge ≤ 5 s.
2. Never silently change scope.
3. Skip is gate-aware (Henry G25 enforcement).
4. Cancel always preserves artifacts (honest-failure policy).
5. Replan re-runs comorbid expansion (P0-6 `plan/comorbid_planner.py`).

## Failure modes

| Mode | Symptom | Action |
|---|---|---|
| Intent ambiguous | Multiple canonical actions match | Ask the user to pick from the 7 canonical options inline; do NOT guess |
| Safety override demanded | User says "I really don't want Mark even with active irAE" | Require explicit `confirm-override`; record into `triggers/<run_id>/safety_overrides.jsonl` |
| Cancel mid-write | User cancels while a Wave runner is mid-await | Let the current await finish (it is the only safe boundary), then write `canceled.json`. Do not kill the Python task abruptly |
| PARTIAL_DELIVERY with no claims yet | Stage 1 only barely started | Tell the user there is nothing to render yet; offer to wait 1-2 more minutes for Stage 1 to finish |

## Worked examples

See `SKILL.md` §"Interrupt protocol" §Examples — three concrete
exchanges (SKIP with safety surface, SIMPLIFY with echo, CANCEL with
partial-delivery offer).

## Acceptance criteria (smoke test)

A simulated mid-run input "跳过查数据" must:

1. Emit `parsed_intent: "SKIP_STAGE"` with `applies_to_stage: 3`.
2. Emit `ack_message_to_user` containing "收到" + "跳过" + "查数据".
3. Emit `safety_warnings` with `gate: "G25"`.
4. Set `needs_user_confirm: true`.
5. NOT modify the plan until the user replies `a` or `b`.

These cases are tested in `tests/test_interrupt_handling.py`.
