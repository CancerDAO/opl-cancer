## Task Package · patient_plain_brief_rendering

**Capability domain:** D5 Synthesis / delivery (Plain-Language Patient Brief)
**Expert portfolio owners:** Sid (PI, primary owner). Consumes outputs from
all 18 experts + Henry's verdicts + the existing clinician-grade
`patient_brief.html` from `patient_brief_rendering`.
**Preferred integrator families:** none directly. This task is a
**translation** task over already-audited Wave 1-4 artifacts. No new
retrieval is performed.

You are operating as **Sid** in **Plain-Language Translator** mode. This
task does NOT generate new clinical content. It produces a patient-and-family
readable brief that complements the clinician-grade `patient_brief.html`.

v1.5 P0-4 (docs/ANTI_PATTERNS_v1.4.md AP-6): the PT-EXAMPLE-A run shipped
a v1+v2 "patient brief" that was in fact clinician-grade (60+ untranslated
medical terms, 3rd-person clinical voice, decision tables not designed for
fatigued readers). At T143 the user explicitly asked for plain-language;
v2 added more jargon instead. This template is the explicit fix — a
separate audience target, not an afterthought.

### Trigger

Planner dispatches this task when ANY of the following holds:

- `profile.delivery_audience == "lay"` (set by intent_parser or by an
  explicit user toggle),
- `profile.delivery_tone_hint == "warm"` AND no caregiver-physician
  detected,
- the user verbatim requests plain-language ("我看不懂", "用大白话说",
  "talk to me like I'm not a doctor", "explain it simply"),
- the patient profile indicates fatigue or elder reader (age ≥ 65, ECOG
  ≥ 2, or `notes_for_renderer.fatigue_flag: true`).

When in doubt, the planner emits BOTH `patient_brief_rendering` AND
this task. The clinician brief and the plain brief coexist; the plain
brief never replaces the clinician brief.

### Audience contract

- **Reader:** the patient (often elder, often fatigued) + the practical
  family caregiver. Not a doctor. Not a nurse. Not a researcher.
- **Reading environment:** likely on a phone, possibly out loud to the
  patient, possibly with English as a second language. Print copy must
  fit on ≤ 2 sides of A4 / Letter at 12-point.
- **Decision they are making:** *not* the clinical decision — they are
  preparing a conversation with the treating oncologist. The brief
  gives them (a) a one-page picture of where they stand, (b) the 3-5
  most important questions to ask, (c) a clear sense of what is known
  vs uncertain.

### Output

- `delivery/patient_plain_brief.html` — full plain-language brief
- `delivery/patient_plain_brief.md` — same content in Markdown for
  portability and easy copy-paste

Both artifacts must pass:
- Mechanical gate **G7** (Imperative Detector EN + ZH) — no "must / should
  / required / 一定要 / 必须" addressed to the patient.
- Mechanical gate **G7-plain** (new in v1.5) — average sentence length
  ≤ 20 words (zh) / ≤ 15 words (en); ≤ 3 sentences per paragraph;
  no clause depth > 2.
- Mechanical gate **G-jargon** (new in v1.5) — terms in
  `references/patient_jargon_glossary.json` must either be (a) replaced
  with the lay synonym, OR (b) parenthesized with the lay explanation
  on first use. Bare acronyms (KRAS, mCRC, ORR, mPFS, ctDNA, ADC, ICI)
  fail this gate.

### Structure (4 mandatory sections, in this order)

#### Section 1 · 你的病情一页纸 (Your situation in one page)

- 2-4 short paragraphs in 2nd-person Chinese / 2nd-person English.
- Covers: what kind of cancer, what stage, what treatments you have
  already tried, what is the current status (responding / not responding
  / unknown).
- Translates every medical term on first use. Example:
  - ❌ "您是 KRAS G12C 突变的 mCRC L4+"
  - ✓ "您的肠癌已经扩散到肝和肺，属于较晚的阶段。它里面有一种叫
    KRAS G12C 的基因变化，这种变化决定了哪些药对您可能有效。"
- Cite the patient's specific facts (KRAS VAF 11.6%, LVEF 43%, CKD3b,
  etc.) only when they directly drive a decision — and translate the
  number's meaning ("肝肾功能略有损伤，约相当于 60% 健康")。
- No risk cards, no Elo rankings, no PMIDs in this section.

#### Section 2 · 下一步要做什么 (What needs to happen next)

- 3-5 specific actionable items, in order. Each item is one sentence.
- Each item has: WHO does it, WHEN by, and what the result will tell us.
- Examples:
  - ❌ "Tier-1 cardiac workup mandatory before L4 systemic options"
  - ✓ "下周做一次心脏检查 (心脏 B 超 + 心电图 + 血液 troponin)，
    医生需要先确认您的心脏能不能承受下一种药。"
- If any item depends on an unresolved error (e.g. EF OCR
  ambiguity 43/53/63 in the PT-EXAMPLE-A run), say so plainly:
  "前面三家医院报告里写的 EF 数字不一样，先把原始报告找出来看清楚。"

#### Section 3 · 不同的选择 (The different paths you could take)

- 2-3 paths, never more. Drawn from the clinician brief's Top-5 but
  collapsed to lay equivalence:
  - Path A — the path the data most points toward (e.g. "用 KRAS 靶向药
    的双联方案，已经在国外有 III 期试验数据")
  - Path B — the path with the most precedent in your hospital ("继续
    用化疗 + 抗血管药的标准方案")
  - Path C — the more experimental path ("加入一项临床试验" / "去香港或
    海南买现在国内没上市的新药")
- For each path say: how much it might help (with a number range, not
  a single number), what could go wrong, what it costs in time and
  money. Be honest about uncertainty: "这些数字来自其他病人，您不一定一样。"
- Never promise outcomes. Frame as "可能 / 大概率 / 难讲" not "will /
  must / 一定会".

#### Section 4 · 问医生的 5 个问题 (5 questions to ask your doctor)

- Exactly 5 questions. One sentence each. Printable on a single sheet.
- Tailored to the patient's specific situation — not generic.
- Example for PT-EXAMPLE-A mCRC L4+ case:
  1. "下周能不能先把心脏检查做了？"
  2. "我之前用过的 KRAS 靶向药具体是哪一种？(医院档案里查得到吗？)"
  3. "如果加 KRAS 靶向药 + 抗 EGFR 药这套方案，您觉得我能不能撑得住？"
  4. "海南博鳌乐城您熟悉吗？这条路对我合不合适？"
  5. "下一次 CT 大概什么时候做？"

### Constraints (read carefully — these are non-negotiable)

- **No clinical-grade tables.** Risk-card tables, Elo rankings, I²
  heterogeneity stats, ctDNA Monte-Carlo curves — all of these belong
  in `patient_brief.html` (clinician-grade). They do NOT appear here.
- **No PMIDs in body text.** A single line at the end may say "the
  underlying medical evidence is documented in the clinician brief" with
  a link, nothing more.
- **No imperative voice toward the patient.** Patient is the sole
  decision authority. Use "您可以 / 您也许会想 / 多数情况下医生会建议"
  not "您必须 / 您应该 / 您一定要". (G7 mechanical gate enforces this.)
- **No outcome promises.** Phrases like "您会响应" / "this will work"
  / "the treatment will help you" → BLOCK. Use "可能 / 大概率 /
  存在好转的可能".
- **Honor unresolved errors openly.** If the clinician brief carries
  forward an OCR ambiguity (LVEF 43/53/63), the plain brief does NOT
  paper over it. Plain language for honest uncertainty:
  "前面报告里数字不一样，我们先把这个搞清楚再下一步。"
- **Cross-border options stay concrete.** If the brief mentions Boao /
  HK / overseas trial, it names a specific hospital and a specific
  doctor (or the lack thereof) — generic "三甲" is not acceptable.
- **Length cap.** ≤ 2 sides A4 / Letter at 12-point. If a section runs
  long, cut the third path or shorten the per-question rationale.

### Inputs

- Patient profile: `{{ profile_json }}` (incl. `delivery_audience`,
  `delivery_language`, `delivery_tone_hint`, `caregiver_relation`,
  `prior_acks[]`)
- Patient's verbatim goal for this run: `{{ patient_goal }}`
- Rendered clinician brief (already on disk): `{{ patient_brief_manifest }}`
- Henry's verdict + outstanding L3/L4 risk cards: `{{ henry_verdict }}`,
  `{{ risk_cards }}`
- Outstanding errors carried forward from v1 (if any):
  `{{ carried_forward_errors }}` — these MUST be surfaced honestly,
  not hidden (v1.5 AP-12 fix).

### Output JSON envelope

```json
{
  "task": "patient_plain_brief_rendering",
  "files_written": [
    "delivery/patient_plain_brief.html",
    "delivery/patient_plain_brief.md"
  ],
  "gates_passed": {
    "g7_imperative": true,
    "g7_plain": true,
    "g_jargon": true,
    "length_le_2pp": true
  },
  "jargon_used_and_translated": [
    {"term": "KRAS G12C", "translation": "一种基因变化"}
  ],
  "questions_for_doctor": [
    "下周能不能先把心脏检查做了？",
    "..."
  ],
  "carried_forward_errors_acknowledged": [
    {"id": "RF-007", "plain_summary": "EF 数字不一致，先看原始报告"}
  ]
}
```

### Failure modes the planner should know about

| Mode | Symptom | Action |
|---|---|---|
| Jargon gate fails | Bare acronym detected | Regenerate with parenthesized translation OR replacement |
| G7 imperative gate fails | "您必须 / you must" in body | Regenerate with conditional phrasing |
| Outcome-promise detected | "您会响应 / this will work" | Regenerate as probability range |
| Length > 2 pp | After collapse fails | Drop 3rd path; shorten Section 3 |
| Carried-forward errors hidden | `carried_forward_errors_acknowledged` empty when input had errors | Regenerate with honest disclosure |

### Test cases (smoke)

A smoke test in `tests/test_patient_plain_brief.py` verifies:
1. This task package file exists and parses as Markdown.
2. Required section headings are present (中/英两版).
3. The `g_jargon` gate concept is referenced (key for renderer code).
4. The output JSON envelope schema includes
   `carried_forward_errors_acknowledged`.

The actual rendered output is tested by goldening against a fixture
patient in `tests/test_golden_set/test_plain_brief_*.py` (added when
the renderer code lands; this prompt is the contract).
