# OPL run — interrupt protocol

> Loaded by `SKILL.md` when the patient interrupts a run (skip / simplify / pause / cancel / replan / status). The five Operating-contract rules + the Evidence Contract in `SKILL.md` still bind.

## Contents

Trigger detection table · Hard rules · Wiring · Examples · Implementation footprint

## Guardrails

- Acknowledge the parsed intent within 5 seconds; never silently change scope (echo the exact reduction and wait for `yes`).
- Skips are gate-aware — surface the gate that will BLOCK (e.g. skipping Wave 3 trips `G25`) before honouring the skip.
- Cancel always preserves completed artifacts (no rollback); the patient can resume by `run_id`.
- Replan re-runs comorbid expansion; manual expert drops that hit a safety trigger require explicit override confirmation.

## Use When

The patient sends a mid-run control message (skip / simplify / pause / cancel / replan / status) between any two lifecycle steps.

## Output Format

A ≤5-second acknowledgement of the parsed intent, then the canonical action applied — one of SKIP-STAGE / SIMPLIFY-STAGE / PAUSE-AND-SHOW-PARTIAL / PARTIAL-DELIVERY / CANCEL / REPLAN / STATUS+ETA — with any scope change echoed back and confirmed (`yes`) before it is applied.

## Interrupt protocol (v1.5.2-3) — when the user wants to skip / simplify / pause / cancel

A full run takes 30-90 minutes. During that time the user may type a mid-run command. This section is the canonical translation table from natural-language input to a deterministic plan modification. Apply at any point between Steps 4 and 10.

### Trigger detection (regex + intent)

| Pattern (zh / en) | Canonical action |
|---|---|
| `跳过` / `不要这一步` / `这步可以省` / `skip` / `skip this stage` / `skip [stage name]` | **SKIP-STAGE** — drop the current stage, jump to the next. Requires user re-confirmation of consequences (e.g. "跳过 Wave 3 = 没有真数据支撑, Henry G25 会 BLOCK 最终交付,要换 patient_optout 标记吗?"). |
| `简化` / `做简单点` / `不要那么细` / `simplify` / `lighter version` / `quick version` | **SIMPLIFY-STAGE** — reduce scope within the current stage (e.g. Wave 2 from 4 rounds → 2 rounds; Wave 3 fewer GEPIA3 queries; Wave 1 only the top-3 highest-priority experts). Always echo back the new shape: "好的, 想办法这一步从 4 轮 PK 改成 2 轮, 前 3 名出来就停。" |
| `停一下` / `暂停` / `先停` / `等一下` / `pause` / `hold on` / `wait` | **PAUSE-AND-SHOW-PARTIAL** — finish the current heartbeat unit but do NOT start the next sub-step. Show everything completed so far + ask "您看完想继续 / 修改 / 取消?" |
| `先看到目前为止的` / `现在能看到什么` / `show me what you have so far` / `partial` / `preview` | **PARTIAL-DELIVERY** — same as pause but additionally render a draft `patient_brief.html` from claims gathered so far, marked `[DRAFT — incomplete]` in the header. Resume on confirmation. |
| `算了` / `取消` / `不要了` / `cancel` / `stop` / `abort` | **CANCEL** — write `triggers/<run_id>/canceled.json` with timestamp + reason. Persist all completed artifacts (no rollback). Do NOT delete the run dir. Ask "要不要把已经做完的部分用简单版报告先给您看?" If yes → PARTIAL-DELIVERY. |
| `换一下专家` / `去掉 X` / `加上 Y` / `swap experts` / `drop X` / `add Y` | **REPLAN** — pause; show the current plan; ask for explicit add/drop list; rebuild plan via `cli.py plan` with the modified expert set; re-emit `comorbid_expansion_triggers_fired` so the user can see the delta; confirm; resume. |
| `怎么这么慢` / `还要多久` / `快点` / `why so slow` / `how much longer` / `hurry up` | **STATUS+ETA** — emit an immediate stage heartbeat (force=True), include current elapsed wall-time + projected total. Do NOT try to literally speed up unless paired with SIMPLIFY. |

### Hard rules

1. **Acknowledge within 5 seconds.** Even before the interrupt action lands, the assistant must echo the parsed intent in plain language. Example: *"收到 — 您想 [简化 / 跳过 想办法 / 现在停下]。让我把当前正在跑的 [...] 收尾,然后给您看到目前为止的结果。"*
2. **Never silently change scope.** If the user says "简化", echo the exact reduction back ("4 轮 → 2 轮, 17 个方案候选 → 10 个候选") and wait for `yes` before applying.
3. **Skip is gate-aware.** Some skips trip Henry G25 (deferred-evidence-block). If the user wants to skip Wave 3, the assistant MUST surface "跳过 Wave 3 会让 Henry G25 BLOCK 最终交付。可选: (a) 同意跳过, 我会在报告头部加'数据层缺位'提醒并把 patient_optout 标记打上; (b) 不跳过, 我们换 native Python 路径 (不需要 Docker) 继续跑。您选哪个?"
4. **Cancel always preserves artifacts.** No rollback. The user can resume next time by pointing at the same `run_id`. This is non-negotiable: lost work is never the right answer (no-false-completion rule).
5. **Replan re-runs comorbid expansion.** When the user adds / drops experts manually, the comorbid trigger heuristic (P0-6 `plan/comorbid_planner.py`) STILL runs over the modified plan — its triggers are safety nets that should fire even on a hand-edited plan. If the user explicitly says "I really don't want Mark even though I have an active irAE," echo back the safety risk and require explicit `confirm-override` confirmation.

### Wiring

- The skill's main thread (the assistant) is the interrupt handler **and the executor**. The Wave runners (`wave1_runner.py` / `wave3_runner.py`) are pure scaffold/validate — they call no LLM; the reasoning is your subagent dispatch between CLI beats. The interrupt protocol works between stages (between dispatch beats), not mid-subagent.
- Mid-stage SIMPLIFY for Wave 3 (the longest stage) is supported via `OPL_NATIVE_LIVE` env or `GEPIA3Integrator(min_request_interval_s=...)` knobs. The assistant translates "查数据快一点" → "把 GEPIA3 限速调小 / 跳过单细胞重分析" + confirms.
- For PAUSE / PARTIAL-DELIVERY, the assistant calls `ProgressReporter.block(...)` (v1.5.1) with explicit options so the chat surface visibly waits for user input.

### Examples

**Skip with safety surface:**

> *User:* 跳过查数据这步, 直接到审核.
> *Assistant:* 收到。但是请注意: 想办法 (Wave 2) 出来的方案如果没有公开数据库的对照, 我们的内部审查员 (Henry) 会按规则 BLOCK 最终报告 (因为关键证据缺位)。可选: (a) 您同意以 "数据层缺位" 标记继续, 我会在报告头部说清楚; (b) 换 native Python 路径 (不需要 Docker, 大约 5-12 分钟) 继续跑数据。您选 a 还是 b?

**Simplify with echo:**

> *User:* 想办法那步做简单点.
> *Assistant:* 好的。原来是 4 轮 PK 出前 5 名, 改成 2 轮 PK 出前 3 名, 大概 4-6 分钟 (原来 8-15 分钟)。这样可以吗? (回 yes 我就改。)

**Cancel with partial delivery offer:**

> *User:* 算了, 太久了, 不做了.
> *Assistant:* 收到, 已经取消。已经做完的部分都保留着, 您下次想继续可以告诉我 run-id `<id>`。要不要我现在给您看一份简单版的部分报告? 大概 30 秒就能渲染出来。

### Implementation footprint

- This section is the contract (read by both the assistant and the patient).
- No new Python entry point needed — the Wave runners already accept `reporter` (v1.5.2-1); the assistant calls `reporter.block(...)` / `reporter.delay(...)` per the patterns above when user interrupts arrive.
- A new task package `prompts/tasks/interrupt_handling.md` codifies the LLM-side logic (lives in v1.5.2-3 alongside this SKILL.md section).

---

