# Task: progress_message_rendering (v1.5.1)

**Audience**: the patient + family member reading the chat in real time.
This is NOT the final delivery (see `patient_plain_brief_rendering.md`)
— this is the **status-update layer** that fires between every stage
boundary AND every ~60 seconds within a long stage.

**Why it exists.** v1.5 retro feedback: "opl-cancer 太久了, 用户一直在
等好几个小时, 普通人体验较差; 输出内容太专业 — 存档可以专业, 但
输出给用户要通俗。" A run can take 30–90 minutes; without periodic
plain-language status the patient + family stare at a frozen screen
and start to doubt whether anything is happening.

This task is **automatic**. The orchestrator (SKILL.md Steps 4–10)
MUST emit one of these messages at every numbered stage transition AND
whenever a single sub-step exceeds ~60 seconds. Patients should NEVER
wait more than ~60s without a visible update.

---

## The 5 stage labels (canonical, plain-language)

| Stage | Internal name | User-facing label (zh / en) |
|---|---|---|
| 1 | Wave 1 — retrieval | **准备 / Getting ready** (整理病历 + 查指南 + 找试验) |
| 2 | Wave 2 — hypothesis tournament | **想办法 / Brainstorming** (列出可能的方案, 互相 PK) |
| 3 | Wave 3 — data evidence | **查数据 / Cross-checking** (拿您的特征到公开数据库里对照) |
| 4 | Wave 4 + Henry — validation + audit | **审核 / Double-checking** (一条一条核对证据, 排雷) |
| 5 | Wave 5 — delivery | **写报告 / Writing up** (一份给您看的, 一份给医生看的) |

NEVER use the internal name in the user-facing chat. Always use the
zh + en label combo (skill defaults to zh for mainland CN patients;
en or bilingual per `profile.delivery_language`).

---

## Message templates

### A · Stage start (1-2 sentences max)

Pattern: `[当前阶段标签] 团队正在 <plain verb>, 大概要 <ETA range>。`

Examples:

- `[1/5 准备] 团队正在整理您的病历 + 查指南 + 找匹配的临床试验。预计 5-8 分钟,完成后会告诉您拿到了什么。`
- `[2/5 想办法] 团队在列出 10-20 种可能的方案,然后让它们互相 PK 找出最有把握的几个。大概 8-15 分钟。`
- `[3/5 查数据] 团队在公开数据库 (TCGA 这种)里对照您的肿瘤特征。大概 5-12 分钟,慢的地方是有些查询要排队等。`
- `[4/5 审核] 团队的内部审查员 (我们叫 Henry) 一条一条核对证据。大概 3-6 分钟。`
- `[5/5 写报告] 同时写两份: 一份给您看的简单版, 一份给医生看的专业版。大概 2-4 分钟。`

### B · Heartbeat during a stage (only if >60s since last message)

Pattern: `[当前阶段标签] 还在 <具体进行的动作>, 已经完成 <N/total>, 预计还需要 <N> 分钟。`

Examples:

- `[1/5 准备] Bert 在读您的基因报告, Rick 在查 ClinicalTrials.gov 上的试验 (CT.gov + 中国 ChiCTR)。 已经完成 3 个专家中的 1 个, 预计还需要 4 分钟。`
- `[2/5 想办法] 第 2 轮 PK 进行中, 17 个方案里有 8 个进入下一轮。预计还需要 6 分钟。`
- `[3/5 查数据] 在公开数据库里跑了 45/71 个查询, 上游限速所以每个之间要等 12 秒。预计还需要 5 分钟。`
- `[4/5 审核] Henry 在核对第 18 条结论, 一共 27 条。预计还需要 2 分钟。`

### C · Stage end (what was found, what's next)

Pattern: `[当前阶段标签 ✓] <一句话总结这一阶段拿到了什么>。<下一阶段会做什么>。`

Examples:

- `[1/5 准备 ✓] 您的病历整理好了, 找到 5 个潜在试验 (3 个在国内, 2 个香港)。下一步: 想办法 — 团队会列出 10-20 种可能的方案让它们互相 PK。`
- `[2/5 想办法 ✓] 17 个方案里挑出了前 3 名 (具体内容会在最后报告里给您看)。下一步: 查数据 — 拿这 3 个去对照公开数据库, 看证据强不强。`
- `[3/5 查数据 ✓] 70/71 个查询成功, 1 个失败 (上游服务器问题, 不影响整体结论)。下一步: 审核 — Henry 一条一条核对。`
- `[4/5 审核 ✓] 27 条结论里 24 条直接通过, 2 条需要附加风险说明, 1 条被退回重做。下一步: 写两份报告。`
- `[5/5 写报告 ✓] 简单版 + 专业版都好了。简单版给您和家人, 专业版可以给医生。`

### D · Unexpected delay (>2× ETA)

Pattern: `<这一阶段比预计慢, 原因是 X, 现在 Y, 还需要大约 Z 分钟。如果不想等可以告诉我跳过 / 简化。>`

Examples:

- `准备阶段比平时慢, 原因是 ClinicalTrials.gov 现在响应慢, 我们已经重试了 2 次。还需要大约 5 分钟。如果不想等可以告诉我先跳过试验匹配 (Wave 1 的其他部分照常)。`
- `查数据这一步公开数据库限速比平时严, 进度从快变慢。还需要大约 8 分钟。要不要先看前面已经拿到的结论?`

### E · Hard blocker (must stop)

Pattern: `<停了, 原因是 X, 影响 Y, 现在请您决定 Z。>`

Examples:

- `停在审核这步 — Henry 发现一条关键结论用的真实数据缺位 (内部代号 G25)。我们不能跳过, 不然会推荐没数据支撑的方案。可选: (a) 等我重新去拿数据 (10 分钟), (b) 把这一条退到附录、其他结论继续。您选哪个?`
- `检测到您的家属手机号被写进了一份内部草稿 (G27 隐私保护规则触发)。已经自动遮掉, 但会重写那段。要 1-2 分钟。`

---

## Hard rules

- **No internal jargon.** Words that MUST be translated on first
  use in the chat (use the lay synonym, then optionally parenthesize
  the original term for transparency):

  | jargon | 通俗 zh | plain en |
  |---|---|---|
  | Wave 1/2/3/4/5 | 准备 / 想办法 / 查数据 / 审核 / 写报告 | getting ready / brainstorming / cross-check / double-check / writing up |
  | hypothesis | 治疗方案 / 可能的路 | possible path |
  | tournament | PK / 互相比一比 | head-to-head comparison |
  | Elo | 排名分 (可省略) | ranking score |
  | meta-analysis | 几个研究的合并数据 | pooled study results |
  | I² heterogeneity | 这些研究之间差别有多大 | how different the studies are |
  | ctDNA | 血液里的肿瘤指标 | tumor signal in blood |
  | log2FC | 表达高 / 低多少 | how much higher / lower |
  | retrieval / fetch | 找资料 | look up |
  | integrator | 数据接口 | database connection |
  | gate | 内部检查规则 | internal check |
  | provenance | 来源凭证 | source trail |
  | irAE | 免疫治疗的副作用 | immunotherapy side effect |
  | mPFS / mOS / ORR | 中位无进展期 / 总生存期 / 客观缓解率 (each on first use needs lay translation per `references/patient_jargon_glossary.json`) | (see glossary) |

  The full mapping lives in `references/patient_jargon_glossary.json`
  (v1.5.1 expanded). When in doubt, check that file.

- **ETA must be a range, not a single number.** Patients quote single
  numbers back at you. Always say "5-8 分钟" not "7 分钟".

- **Never silent past 60s.** If a stage takes longer, emit a Pattern-B
  heartbeat. If the stage is approaching 2× its original ETA, switch
  to Pattern-D.

- **No outcome promises in progress messages.** "团队找到了一个一定有效
  的方案" = BLOCK. Even at stage-end, frame as "前 3 名" not
  "最有效的".

- **Always pair Chinese + English label.** Some patients prefer one
  language, but having both visible reduces the cost of mis-translation.

- **Never reveal internal codes (RC-001, RC-NEW-A, H02, t10, G7, G25,
  ...) in the chat surface.** The patient brief at the end may show
  them in an appendix; the live chat must not.

- **Never apologize for technology.** "Sorry the system is slow" = bad.
  "查数据这步比平时慢, 我们多等 5 分钟会拿到更稳的结论" = good.

---

## Where this contract is enforced

- **Skill prompt level** — SKILL.md Steps 4–10 each cite this contract
  and include a worked example of the stage-start + stage-end message.
- **Python helper** — `src/opl_cancer/glue/progress_reporter.py`
  provides a `ProgressReporter` class that runners call when emitting
  stage transitions and heartbeats. It computes ETA from historical
  wave timings (median of the last 5 runs of the same shape).
- **Mechanical check** — `tests/test_progress_reporter.py` asserts
  the label format, ETA range, no-jargon constraint via
  `validators/gates/g27_privacy_scrub.py`-style regex.

---

## Output JSON envelope

When the runner calls `ProgressReporter.emit()`, the helper also
appends to `triggers/<run_id>/progress.jsonl`. Each line:

```json
{
  "ts": "2026-05-25T10:34:12Z",
  "stage": 3,
  "stage_label_zh": "查数据",
  "stage_label_en": "Cross-checking",
  "phase": "heartbeat | start | end | delay | block",
  "user_message": "[3/5 查数据] 在公开数据库里跑了 45/71 个查询...",
  "internal_detail": "GEPIA3 batch 45/71, rate-limit 12s, ETA 5min",
  "eta_min": [4, 6],
  "elapsed_s": 312
}
```

Internal detail goes to the JSONL (audit trail). The user-facing
message is `user_message` only.

---

## Acceptance criteria (smoke test)

A run should produce:

1. ≥ 5 progress messages (one per stage minimum).
2. No two consecutive messages > 60 s apart during an active stage.
3. Zero internal-code leakage (`tests/test_progress_reporter.py`
   regex-scans the message stream).
4. ETA range present in every start / heartbeat / delay message.
5. Stage-end message names the next stage by lay label.
