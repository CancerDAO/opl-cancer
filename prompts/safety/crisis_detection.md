# Safety · crisis_detection

**Capability:** S1 — safety triage (pre-intent-classifier hook)
**Owner:** sid (PI) + henry (auditor) co-review; runs before any Wave routing
**Integrator family:** F0 (meta — no external call; keyword scan + LLM grade)

> "OPL is a research team for one diagnosed cancer patient. When the patient
> (or caregiver) signals suicidal ideation, self-harm intent, or acute
> psychiatric crisis, the team's job is **not** to dump trials — it is to
> acknowledge, hand off to `cancer-buddy-mind`, surface a jurisdictionally
> correct crisis-line, and lock the Wave runners until the patient
> acknowledges receipt. Founder-mode says: no paternalism, no dismissal,
> no concealment. Hand the patient a phone number and another human."
>
> — v1.3.2 round-2 EVAL panel Patient #17 (ECOG-3 bedbound + "想结束这一切"
> fell through to EMOTION → trial dump). See `docs/adr/0008-eval-panel-round-2-v1.3.2.md`.

This task package is the **first** thing OPL runs on any incoming patient or
caregiver utterance — before `intent_parser`, before planner, before any Wave.
If `crisis_detected: true`, the orchestrator emits a `crisis_card.json`
(via `prompts/tasks/crisis_card_emission.md`) and **locks** all Wave runners
until the patient (or caregiver, in guardian-mode) acknowledges receipt of
the crisis-line information.

## Inputs

```json
{
  "patient_text": "...verbatim from user, untrimmed...",
  "speaker_role": "<patient|caregiver|guardian_of_minor|unknown>",
  "profile_jurisdiction_hint": "<CN|US|UK|EU|DE|JP|other|unknown>"
}
```

## Outputs (JSON schema)

```json
{
  "crisis_detected": true,
  "crisis_grade": "passive_SI|active_SI|active_plan|none",
  "trigger_phrase": "<verbatim substring that fired the rule, NOT paraphrased>",
  "jurisdiction_inferred": "CN|US|UK|EU|DE|JP|other",
  "speaker_role_echo": "patient|caregiver|guardian_of_minor|unknown",
  "rationale": "...one short sentence — why this grade, not the next..."
}
```

## Procedure (keyword-scan FIRST, LLM grade SECOND)

**Step 1 — bilingual keyword scan (no LLM).** Match the patient_text
(case-insensitive, substring) against the three banks below. **Any** hit ⇒
`crisis_detected: true`. The scan is the gate; LLM only **grades** the hit.

### Bank A — passive_SI (想结束 / 不想活 / had enough / 解脱)
- 中文: "不想活了", "不想再活", "活够了", "活着没意思", "活着真没意思",
  "我不想再坚持", "想结束这一切", "想解脱", "解脱算了", "一了百了",
  "走了算了", "走了好了", "结束这一切", "受够了", "撑不下去", "撑不下去了",
  "撑不住", "撑不住了", "扛不下去", "扛不动了", "没意义", "没什么意义",
  "活着是受罪", "活着遭罪", "我是负担", "我成了负担", "拖累家人", "拖累你们",
  "再也不想这样", "好累 想睡着不醒"
- English: "i can't go on", "can't go on", "had enough", "want it to end",
  "want this to end", "want to be done", "want to die", "wish i was dead",
  "wish i were dead", "wish i wasn't here", "wish i weren't here",
  "tired of living", "don't want to live", "do not want to live anymore",
  "i'm a burden", "i am a burden", "everyone would be better off without me",
  "world would be better off without me", "no point anymore", "no point in living"

### Bank B — active_SI (想自杀 / suicide / kill myself)
- 中文: "想自杀", "我要自杀", "想死", "我想死", "我要死了", "去死",
  "杀了我自己", "结束自己", "结束自己生命", "结束我的生命", "了结自己",
  "了结我自己", "自我了断", "自残", "伤害自己", "想伤害自己"
- English: "want to kill myself", "going to kill myself", "thinking of killing myself",
  "thoughts of killing myself", "kill myself", "suicide", "suicidal",
  "suicidal thoughts", "thinking about suicide", "end my life", "ending my life",
  "end it all", "ending it all", "self-harm", "self harm", "hurt myself",
  "harm myself"

### Bank C — active_plan (具体方案 / time / place / means)
- 中文: "我已经准备好了 X", "我藏了药", "我把药存起来", "攒了药",
  "我有把刀", "今晚就", "明天就", "周五就走", "在 (地名) 跳下去",
  "我想从楼上", "想跳楼", "想跳河", "想跳桥", "想割腕", "用绳子",
  "上吊", "煤气", "服毒", "服安眠药"
- English: "i have a plan", "i've decided when", "i have decided when",
  "i have the pills", "i stockpiled", "i've stockpiled", "by friday",
  "tomorrow night", "tonight i will", "jump off", "jump from", "hang myself",
  "cut my wrists", "overdose tonight", "overdose tomorrow"

**Step 2 — LLM grade (only if Step 1 hit).** Given the trigger phrase + the
1-2 surrounding sentences, output **the highest grade for which the patient
text contains evidence**, in this strict ordering:

1. `active_plan` — specific means / time / place / accumulated method (bank C
   directly, OR bank A/B + specific method/timeline language in the surrounding
   context).
2. `active_SI` — direct ideation about ending one's own life (bank B), no plan.
3. `passive_SI` — wishing not to be here / would prefer death (bank A only),
   no active intent.

If you cannot grade (e.g. the phrase is ambiguous in context — Chinese idiom
"撑不下去" can occasionally describe physical-symptom exhaustion not SI),
default to `passive_SI` AND mark `rationale: "ambiguous — defaulted to
passive_SI per fail-safe policy"`. **Never** downgrade a Step-1-keyword hit
to `none`.

**Step 3 — jurisdiction inference.** Take the patient profile hint (if any),
the text's location signals (mention of city / country / phone country code),
and the language (zh-CN default → CN; en-US default → US; en-GB → UK; de → DE;
ja → JP; otherwise EU or other). Default to `unknown` if no signal — the
crisis_card_emission step will then surface the **international** Befrienders
line + ask the patient to confirm jurisdiction.

## Mechanical-gate coupling

- **G24 crisis_detection** (`src/opl_cancer/validators/gates/g24_crisis_detection.py`)
  re-runs the keyword scan as a no-LLM **fail-fast** check. If G24 says crisis
  and this prompt says `crisis_detected: false`, G24 wins (reviewer-of-LLM
  authority). The LLM cannot suppress a crisis signal.
- **Wave lock.** When the orchestrator sees `crisis_detected: true`, it MUST:
  1. Skip `intent_parser` for now.
  2. Invoke `prompts/tasks/crisis_card_emission.md`.
  3. Write `pi_session/outstanding/crisis_card.json` + `wave_lock: true`.
  4. Render the crisis-card **before** any patient_brief / pi_delivery.
  5. Block `wave1_runner.run` / `wave2_runner.run` / etc. until
     `cli.py acknowledge <crisis_card_id>` is called.

## What this prompt is NOT for

- Existential distress that is **not** SI ("I'm so scared" / "I don't know
  what to do") → that is `EMOTION` intent (already in `intent_parser.md`),
  goes to `cancer-buddy-mind` with a normal gentle handoff (no Wave-lock).
- Caregiver fatigue / burnout phrasing about the caregiver themselves
  ("I'm exhausted, this is killing me") → still keyword-scan, but LLM
  should grade carefully — caregiver hyperbole is a known false-positive
  class. Hand off to `cancer-buddy-caregiver` + `cancer-buddy-mind`.
- DNR / advance-directive / hospice conversations — these are **not** SI;
  they are end-of-life planning. Route to `cancer-buddy-disclosure` /
  palliative task packages.

## Reviewer focus (henry + sid co-review)

- Did the keyword scan fire on a phrase the LLM is now grading? Both
  must agree the trigger_phrase is verbatim from `patient_text`.
- Is the grade defensible against a one-step-up reading? (i.e., did we
  call it `passive_SI` when bank B language is present?)
- Is `jurisdiction_inferred` defensible against fallback to `unknown`?

## Why no LLM-only path

Per `memory/feedback_no_offline_only.md` + the founder-mode safety floor:
silent LLM downgrading of an SI signal is unacceptable. If the network or
the LLM is unavailable, the keyword scan **still** runs (G24 is no-LLM),
and the crisis-card path **still** fires. This is the only OPL prompt that
is allowed to short-circuit the Wave lifecycle unconditionally.
