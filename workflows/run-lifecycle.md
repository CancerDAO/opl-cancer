# OPL run lifecycle (Steps 0–11)

> Loaded by `SKILL.md` after the skill triggers. Follow this dialog exactly — each step has a safety reason; do not collapse / re-order. The five Operating-contract rules + the Evidence Contract in `SKILL.md` bind every step. Prefer the one-command path `opl-cancer go`.

## Contents

Step 0 Install/preflight · Step 1 Greet · Step 2 Organize · Step 3 Readiness · Step 4 Plan · Step 5-8 Wave 1-4 · Step 9 Henry audit · Step 10/10b Deliver · Step 11 Iterate · Acknowledge/withdraw · Observability

> **Interrupt handling** (skip / simplify / pause / cancel / replan / status) applies between any two steps below — see [`interrupt-protocol.md`](interrupt-protocol.md).

## Guardrails

- Never under-deliver, never collapse the planned team to generic agents, never free-hand a brief, never fabricate a clinical fact or citation (the 5 Operating-contract rules in `SKILL.md` — `G34`/`G37`/`G35`/`G1`/`G2`/`G36` enforce them, `exit≠0` on violation).
- You are the reasoning brain; the `opl-cancer` CLI is a deterministic harness that validates + gates what you wrote. Dispatch experts as subagents (`prompts/experts/expert_task_package.md`); do not expect the CLI to reason.
- Every clinical value carries a `[[src:...]]` anchor or is `UNKNOWN`; every PMID is from a live search this session and on-topic. No silent offline fallback.
- Deliver inline in chat (Step 10b) — a file pointer is not delivery.

## Use When

A cancer patient or caregiver presents records + a goal and wants the full research-team run — the default OPL path (`opl-cancer go`).

## Output Format

A completed run delivers, per Step 10/10b: an inline chat reply in 8 fixed parts (L3/L4 risk cards → goal+value echo → what-team-did → top-3 conclusions with tier labels + provenance → reviewer disagreements → trade-offs → optionful next steps → file pointers LAST), backed by `delivery/patient_brief.html` + `delivery/patient_plain_brief.html` + `delivery/pi_delivery.md`, all attested via `opl-cancer attest`.

When triggered, follow this dialog **exactly**. Each step has a safety reason — do not collapse / re-order.

---

**Step 0 — Install self-check + one-time bootstrap (per agent session — any agent).**

OPL installs via `npx skills add CancerDAO/opl-cancer-skill` into **whatever agent
you are running** (Claude Code, Codex, Cursor, OpenCode, …) — the skill dir is NOT
necessarily `~/.claude`. So the **one-time bootstrap** resolves the skill dir
portably (it is the directory containing this `SKILL.md`) and installs the harness:

```bash
# One-time, agent-agnostic — installs the `opl-cancer` console command onto PATH.
# <skill_dir> = the directory that contains this SKILL.md (resolve it from your
# agent's skill path; do NOT assume ~/.claude).
pip install -e "<skill_dir>"

# Then every command below is a bare, path-free, portable entry point:
opl-cancer preflight --json
```

If `opl-cancer` is not yet on PATH, `python "<skill_dir>/scripts/cli.py" preflight`
self-bootstraps on first run (or prints the exact `pip install -e` command — never a
raw traceback). See `references/agent-portability.md` for per-agent install dirs and
the executor-LLM contract below.

The preflight reports:
- Python ≥ 3.11 + `opl_cancer` package importable (the `scripts/cli.py` shim auto-runs `pip install -e <skill_dir>` on first use, or prints the one command to run).
- **Reasoning layer (no Python LLM, no provider key for the patient path — v2.8 harness-split):**
  - **Executor = you, the host agent.** Experts run as your dispatched subagents (`prompts/experts/expert_task_package.md`). On Claude Code that is your main-thread Opus; on Codex / Cursor / OpenCode it is that host's model. The Python package calls no LLM, so **no `ANTHROPIC_API_KEY` is needed for a patient run**. (`OPL_EXECUTOR_PROVIDER` still tags which host model you are, so G13 knows the executor identity.)
  - **Reviewer = a SECOND subagent you dispatch**, with a distinct persona and a distinct **declared** model identity. G13 deterministically checks that the executor and reviewer report artifacts declare *different* models (the old same-model echo chamber). This is a subagent dispatch, **not** a Python provider call — `MINIMAX_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` are **not** required for the patient path; they only feed the optional, being-extracted self-improvement engine.
- Integrator readiness — PubMed, NCCN PageIndex, CT.gov, ChiCTR, OncoKB, CIViC, RxNorm, GEO, ArrayExpress, SRA, DepMap, CCLE, ClinVar, gnomAD, Open Targets, RetractionDB, Unpaywall, PaperQA2 index, NMPA-EAP, FDA-EAP, cBioPortal, GDC.
- Optional compute runtime: `docker info` + `compute/bixbench.Dockerfile` build (Wave 3 only; skip-able).

If `preflight.ok == false`, surface the missing items and the exact install command. **Do not proceed to Step 1 until preflight passes for the providers actually needed by this run.** For pure Wave-1/Wave-2/Wave-5 the bixbench Docker is not required.

---

**Step 1 — Greet + ask for input.**

```
🧬 OPL for Cancer · 你的私人 AI 科研团队已上线

我是 Sid,你的 PI。我和我的 20 位团队成员(Rosa 病理、Bert 分子、Vince 治疗、Rick 试验、
Heddy 影像、Aviv 生信、Iain meta、Mary 药理、Ted 放疗、Riad 介入、Hong 中医、Mark irAE、
Kieren ID、Frances 同情用药、Dennis 跨境、Jen 缓和、Tyler 实验、Steve 营养、
Maya KG 协同推理、Julius in-silico 分子设计)只为你一个人工作。Henry 在后台做独立审查;
每条结论都有 PMID + provenance hash + 三级标签(established / exploratory / speculative);
你是这个案子唯一的决策人。v2 范式: 我会主动给你"世界未知候选" — 标 [S] speculative
+ 可测路径 + 不构成治疗建议 framing;具体药名隐去到 target class。

请给我:
  1. 你的病历入口(文件夹 / zip / PDF / 图片 / Word 都行,不用预先整理)
  2. 你这次想让 team 帮你解决什么 — 比如:
        · "我的二线进展了,三线有什么 evidence-based 选项?"
        · "帮我重读这份 NGS,把我没注意到的 actionable target 全列出来"
        · "帮我跑一次 hypothesis tournament — 我想看 team 能产生哪些非显然的方向"
        · "找全球可及的 trials,按地理/资格匹配排"
        · "帮我把 GEO 上同癌种 cohort 投射到我的 case,做 N=1 prediction"
        · "我用了 X 药,team 评一下 efficacy + risk + 同 class 替代"
        · "second-look — 我的医生方案是 X,team 看有没有遗漏"
```

Accept path + goal. If patient supplies only a path, ask the goal; if only a goal, ask for the path. Never start a Wave without both.

---

---

**Step 2 — Organize records → canonical patient directory.**

If the input is not already organized into the canonical layout (`~/CancerDAO/patients/<patient_code>/` with 11-bucket dirs + `profile.json` + `readiness.json` + `case_text.md` + OCR sidecars + optional `review_flags.md`), instruct the patient to organize their records into this layout first. OPL is downstream of records organization — it does not OCR / triage raw uploads itself. See `references/patient-data-layout.md` for the canonical schema.

If the input is already an organized patient directory (`profile.json` present), skip ingest and reuse.

Report to user: `patient_code` + `readiness_grade` (A/B/C/D/F) + `blocking_gaps[]` + `review_flags_total` (red/yellow/green).

If `review_flags_total > 0` (especially 🔴 red), surface them and require user confirmation before proceeding — these are extracted-but-suspicious fields (e.g. TNM prefix not AJCC-compliant, KRAS mention only in progress notes without an NGS report).

---

**Step 3 — Readiness gate + deepdive recovery.**

```bash
opl-cancer readiness <patient_dir> --json
```

If grade ≥ C → proceed to Step 4.

If grade < C AND `<patient_dir>/ocr/` exists, fork `vmtb-deepdive` subagent (cross-skill reuse — same contract) to mine sidecars for missing fields. Show recovered table; let user accept all / review one-by-one / skip. Then re-score.

If grade still < C and deepdive exhausted: surface blocking gaps and ask:
> "数据完备度 {grade}({score}/100)。缺失:{blocking}。继续生成需 --force。先补这些再跑,team 的分析会准很多。"

Wait for user decision.

---

**Step 4 — PI plans the run (Sid).**

> **Read the failure ledger before ideating (Arbor/HTR negative constraints — read half of `G52`).** First run `opl-cancer observe --patient <patient_dir> --run-id <run_id>` and pass its `negative_constraints` (hypotheses falsified in **any** prior run for this patient) into the planner. The agenda MUST NOT silently re-propose a killed direction; falsified ≠ forbidden forever, but re-opening one is a deliberate, evidence-backed choice that overturns the reason it was killed — never an accident. `G52` writes the dead ends; this is where the planner reads them back, so the run spends its budget on *new* ground (structured search, not a bigger fan-out).

> **Grant a depth budget for hot leads (Arbor/HTR re-entry, ADR-0042).** By default a plan is flat (`max_depth: 1`). If the goal is the kind where one promising direction may need a *focused deeper split* to be decision-relevant for the patient (e.g. a synergy lead whose mechanism forks), the planner MAY set `max_depth: 2-4` and list the directions worth deepening in `deepen_candidates`. This is ADDITIVE — it can only exceed the floor on a warranted lead, never shrink the planned team (`G55` still binds). Most runs stay flat; grant depth only when a deeper pass genuinely helps the patient, not by default.

> **Outcome-backward planning (D1/E1 · ADR-0034).** Dispatch the LLM planner
> `prompts/pi/goal_backward_planner.md` FIRST — it reads the patient's verbatim
> goal + structured `desired_endpoint`/`decision_juncture` (from
> `prompts/pi/intent_parser.md`) and reasons BACKWARD to the team/agenda, instead
> of applying a fixed template. The deterministic `opl-cancer plan` skeleton +
> `comorbid_planner` expansion is the FLOOR the agenda must cover-or-exceed (it
> emits `planned_experts` + `floor_required`; `G55` BLOCKS a plan that drops a
> red-line floor item). The planner also picks the patient's unfair-advantage
> `lens_bet` (D2) and must surface ≥1 backed `not_in_treating_plan` candidate or
> honestly state none (`G53`). Route the patient's question through the LLM
> intake router `prompts/pi/intake_router_llm.md` (semantic match to a task
> package / method DAG) rather than the legacy `intake_router.py` keyword tables
> (vestigial — pending removal). Judgment is the LLM's; the gates verify it.

Dispatch the planner: read `case_text.md` + `profile.json` + patient goal + Project Memory (if returning patient), decide:
- Which experts to activate (subset of 20 — incl. Maya when patient has ≥2 actionable molecular alterations or asks about target-target synergy; Julius when patient has an undrugged actionable target)
- Per-expert sub-goal
- Which Waves to run (often all 5; sometimes only 1 or 2)
- Which integrator families to call (subset of F1–F10)

**Cancer-type-aware planner hints** (planner must consider, not hardcode):
- **HCC / 肝细胞癌 / TACE-refractory**: Bert + Vince + Heddy + Aviv + Iain + Rick + **Riad (interventional — re-TACE / Y90 / RFA must be considered for BCLC C+ with hepatic-confined disease)** + **Hong (CN herbs × TKI interactions are real DDI)** + Mary (Child-Pugh dosing) + Frances (EAP) + Dennis (cross-border).
- **NSCLC EGFR-mut + brain/LM**: Bert + Vince + Heddy + Rick + Aviv + Iain + **Ted (LM SRS / HA-WBRT dosing)** + **Jen (LM palliative if confirmed)** + Frances (amivantamab EAP) + Dennis (US/EU trials).
- **TNBC / BRCA reversion / TROP2**: Bert + Vince + Aviv + Iain + Rick + Frances (sacituzumab EAP) + Tyler (any wet-lab biomarker).
- **TNBC + LM (leptomeningeal mets)**: Bert + Vince + Heddy + Aviv + Iain + Rick + **Ted (HA-WBRT — NRG-CC003 backbone for TNBC LM)** + **Jen (LM palliative — TNBC LM median survival 2-4 months, honest prognosis band mandatory)** + **Frances (sacituzumab + IT-nivolumab compassionate — IT-trastuzumab N/A for TNBC, IT-MTX is the established route, IT-pembrolizumab emerging)** + Tyler (any wet-lab biomarker). LM-route chemistry differs from breast-HER2 LM: IT-trastuzumab is not applicable; IT-MTX is the canonical IT route; IT-pembrolizumab is exploratory; HA-WBRT is the radiation backbone.
- **ICI irAE rechallenge**: Mark **(must lead)** + Vince + Bert + Iain + Rick + Mary (steroid taper × DDI).
- **AML R/R multi-driver / triplet**: Bert + Vince + Aviv + Iain + Rick + Mary (triplet DDI lead) + Kieren (neutropenic fever protocol if planned induction).
- **HRD+ ovarian post-PARPi**: Bert + Vince + Aviv + Iain + Rick + Mary (DDR-i DDI) + Frances (DDR-i EAP). For at-risk family members, Bert interprets proband germline variant + drafts cascade-testing handoff card pointing to a board-certified genetic counselor at the patient's institution (OPL does not perform cascade counselling itself — `prompts/tasks/family_cascade_routing.md`).
- **mCRPC + Lu-177 / AR-V7**: Bert + Vince + Aviv + Iain + Rick + Mary + **Riad (PSMA-targeted radioligand)** + Frances (Lu-177 NMPA EAP) + Dennis (Genesis / India generic Lu-177 — surface existence + safety, do not endorse).
- **Melanoma BRAF post-MAPKi + CNS**: Bert + Vince + Heddy + Aviv + Iain + Rick + Ted (CNS SRS/WBRT) + Mark (IO + irAE if rechallenge) + Jen (LM palliative) + Dennis (US trials).
- **Pancreatic KRAS G12C**: Bert + Vince + Aviv + Iain + Rick + Frances (adagrasib + cetuximab EAP) + Dennis (EU trials — KRYSTAL series).
- **mCRC KRAS G12C MSS, line 4+ (v1.5.7 — fills v1.4 retrospective gap)**: Bert + Vince + Aviv + Iain + Rick + **Frances (sotorasib + panitumumab / adagrasib + cetuximab / divarasib + cetuximab EAP — the G12Ci + anti-EGFR backbone is the SoC reference arm; CodeBreaK 300 and KRYSTAL-10 are anchor PMIDs)** + **Tyler (TROP2 expression read from GEPIA3 + cBioPortal — Dato-DXd / sacituzumab govitecan repurpose into mCRC if TROP2 high; ADC pull is exploratory in CRC)** + **Mark (MSS = immune-cold; ICI is OFF the table by NCCN; if anti-EGFR rash escalates, dose-modify NOT discontinue)** + **Mary (line 4+ patients typically carry CKD / CAD / prior ICI-thyroiditis — sotorasib hepatotoxicity × prior chemo cumulative load is a real DDI)** + **Heddy (RECIST 1.1 + serial CEA + ctDNA Monte Carlo — line 4+ benefit windows are short, imaging cadence Q6-8wk not Q12wk)** + **Hong (CN herbs × EGFR-ab skin reactions are a real DDI — turmeric, astragalus, ginseng documented)** + Frances (cross-border — sotorasib + panitumumab is FDA-approved post-CodeBreaK 300; adagrasib + cetuximab is EU EMA-recommended; divarasib is EAP-only) + Dennis (KRYSTAL series, CodeBreaK series, ACROBAT registry trials). **Wave 3 MUST include**: cBioPortal KRAS G12C + MSS CRC cohort extraction, TCGA + MSK-IMPACT survival projection, DerSimonian-Laird meta-analysis across CodeBreaK 300 / KRYSTAL-10 / divarasib arms, ctDNA Monte Carlo from baseline VAF. GEPIA3 default for TROP2 / WNT / MAPK / FRS2 transcriptomic axes.
- **Late-line (≥ 4 prior lines) resistance — generic disease-agnostic row**: when the patient has exhausted ≥3 SoC lines, planner MUST add: **Frances (EAP / compassionate-use lead — late-line patients live on EAP)** + **Heddy (short benefit-window imaging cadence — Q6-8wk for L4+)** + **Mary (cumulative organ toxicity from prior lines — hepatic / cardiac / renal reserve)** + **Tyler (any wet-lab biomarker repurpose — ADCs / radioligands / N=1 cohort projection)** + **Mark (irAE-rechallenge if prior ICI)** + **Riad (intra-arterial / interventional radioligand if hepatic-confined / bone-dominant)** beyond the disease-specific base set. Founder-mode: line 4+ patients have weeks-to-months not months-to-years; the team configuration must match the time horizon.
- **HER2+ gastric / CLDN18.2**: Bert + Vince + Aviv + Iain + Rick + Steve (peritoneal carcinomatosis nutrition) + Mary (T-DXd ILD risk).
- **MSI-H CRC / Lynch**: Bert + Vince + Mark + Iain + Rick. For Lynch family screening, Bert drafts cascade-testing handoff card → board-certified genetic counselor (`prompts/tasks/family_cascade_routing.md`).
- **Pediatric ALL R/R (KMT2A-r / Ph+ / B-ALL / T-ALL)**: Bert + Vince + Aviv + Iain + Rick + Frances **(revumenib / menin-i EAP for KMT2A-r pediatric)** + Mary **(pediatric weight-based DDI — vincristine / daunorubicin / blinatumomab / inotuzumab dosing)** + Mark **(pediatric CRS / ICANS — Lee criteria, NOT adult CTCAE)** + **trigger guardian_ack_protocol**. Bert drafts germline cancer-predisposition panel handoff card → board-certified pediatric genetic counselor (`prompts/tasks/family_cascade_routing.md`).
- **Pediatric AML R/R**: Bert + Vince + Aviv + Iain + Rick + Frances (revumenib EAP if KMT2A-r / NPM1-mut) + Mary (pediatric DDI) + Mark (pediatric CRS/ICANS if BiTE/CAR-T) + **trigger guardian_ack_protocol**.
- **Pediatric DIPG / brain tumor**: Bert + Vince + Heddy **(pediatric MR imaging — DIPG / HGG diffuse / midline H3K27M)** + Ted **(pediatric proton — craniospinal / focal)** + Rick + Frances (ONC201 / dordaviprone EAP for H3K27M) + Jen (pediatric palliative — caregiver-anchored) + **trigger guardian_ack_protocol**.
- **Pediatric solid (Ewing / RMS / neuroblastoma)**: Bert + Vince + Rick + Tyler (pediatric wet-lab biomarker / minimal residual disease) + Aviv + Iain + Frances (naxitamab / dinutuximab / chimeric mAb EAP) + Mary (pediatric DDI) + **trigger guardian_ack_protocol**.

These are starting brackets — the planner narrows by readiness signals + patient preference. Planner has discretion to add or drop experts based on the actual `profile.json`. **Pediatric rows additionally route through `prompts/tasks/guardian_ack_protocol.md` — the guardian acks information receipt only, not treatment-decision authority (which routes to pediatric IRB-supervised slot).**

```bash
opl-cancer plan \
  --patient <patient_dir> \
  --goal "<verbatim patient goal>" \
  --run-id <run_id> \
  --out <patient_dir>/triggers/<run_id>/plan.json
```

The plan goes through `validators/mechanical_gates.py` (G5 patient-context-isolation, G6 injection-scan over raw patient input) before any expert spins up. On violation: abort + tell user what was rejected and why.

Echo the plan to user in **plain language** (v1.5.1): NEVER say "Wave 1+2+3 / hypothesis tournament / wall-time / token cost / Reviewer pairing / Elo". Translate to lay terms.

Example: *"团队这次会上场: 病理 Rosa, 基因 Bert, 想方案 Aviv, 试验匹配 Rick, 查文献 Iain (共 5 位专家)。整个过程会分 5 步走 — 准备 / 想办法 / 查数据 / 审核 / 写报告, 一步一步给您报进度。整体大概 30-50 分钟, 费用大约 3-8 美元 (跑得多寡看您病情复杂度)。要开始吗?"*

If `comorbid_expansion_triggers_fired` is non-empty (v1.5 P0-6 surface), name the additional experts and what each one's lens covers: *"另外因为您有 [活动期免疫副作用 / 多种合并用药 / 慢性肾病 / ... 等], 团队还会加上 [副作用专家 Mark, 用药专家 Mary, ...] 来照顾这些方面。"*

> v1.5 — `cli.py plan` reads `profile.json` and **deterministically expands** the baseline t1-t9 skeleton when the patient phenotype hits multi-comorbid triggers (active irAE → Mark; ≥3 prior lines → Frances; ≥3 co-meds → Mary; CAD/PCI/LVEF≤50 → Mary cardiac; CKD or eGFR≤60 → Mary renal; mainland-CN patient → Riad + Dennis; imaging gap or age≥70 → Heddy). The CLI JSON output exposes `comorbid_expansion_triggers_fired` with per-trigger rationale. **You MUST surface the fired triggers** to the user in this Step 4 echo — silent override is forbidden (`docs/ANTI_PATTERNS.md` AP-9, AP-11).

Wait for user `yes` / adjust.

> v1.5 — every subagent dispatched in Steps 5..8 follows `prompts/safety/subagent_file_write_contract.md`: primary Write tool, fallback Bash heredoc with `OPL_REPORT_EOF` sentinel, JSON envelope confirmation with `report_path` + `report_bytes` + `report_sha256_short`. Orchestrator validates filesystem state matches the envelope; 1 retry on mismatch (`docs/ANTI_PATTERNS.md` AP-12 / F12).

> **Re-ground before every wave beat (Arbor/HTR `observe`).** A multi-wave run is long; your conversation memory of "what's already done" goes lossy after context compression and is the documented root cause of under-delivery (session 0d1017d4: skipped waves while *believing* the plan had run). So at the **start of each of Steps 5–8**, re-ground on the durable state, not your recollection:
> ```bash
> opl-cancer observe --patient <patient_dir> --run-id <run_id>   # read-only; never executes a wave
> ```
> It re-projects: planned-vs-done waves, **outstanding** waves, the memory frontier, and **falsified hypotheses across ALL of this patient's runs as negative constraints** (do not re-propose them). Dispatch the next *outstanding* wave from this projection; if `observe` shows a planned wave already done, do not silently re-run it. This is the prompt/script boundary in practice — the harness hands you a faithful projection; you do the judgment.

---

**Step 5 — Wave 1 · world-known retrieval (experts in parallel).**

Each selected expert runs its **task package portfolio** (e.g. Bert → `molecular_ngs_interpretation`, `pathology_interpretation` cross-read; Rick → `trial_matching` over CT.gov + ChiCTR; Heddy → `recist_progression`). **You dispatch them as subagents** per `prompts/experts/expert_task_package.md`; each writes its report into `triggers/<run_id>/tasks/w1_*/` (per ADR-0002 subagents do not fork subagents — you, the main thread, dispatch them). Then validate + gate with the harness:

```bash
# state-check: confirms your dispatched reports exist + runs the mechanical gates.
# This does NOT execute the experts — you already did, as subagents, above.
opl-cancer wave1 \
  --patient <patient_dir> --run-id <run_id> --plan <plan.json>
```

Cross-expert peer review is a **second subagent you dispatch** (distinct expert + distinct *declared* model; G13 checks the two report artifacts declare different models — `models.yaml.reviewer_pairings` is the expected-distinctness reference, no longer a Python model router). Reviewer prompts: `pmid_quote_verify` · `retraction_check` · `self_contradiction` · `numerical_sanity` · `stats_correctness`.

**Mandatory user-facing progress messages (v1.5.1).** Throughout this Step and Steps 6–10, you MUST emit plain-language progress updates per `prompts/tasks/progress_message_rendering.md`. Use the 5 canonical stage labels (准备 / 想办法 / 查数据 / 审核 / 写报告), NEVER "Wave 1 / hypothesis tournament / Elo / Henry / G25" in the chat surface. ETA is a range, never a single number. Heartbeat at least once every 60 seconds during long sub-steps. The Python helper `src/opl_cancer/glue/progress_reporter.py` (`ProgressReporter`) provides the format if you want to drive it from code; otherwise emit the strings directly.

Stage-start example: *"[1/5 准备 / Getting ready] 团队正在整理您的病历 + 查指南 + 找匹配的临床试验。大概 5-8 分钟。"*

Stage-end example: *"[1/5 准备 / Getting ready] ✓ 病历整理好了, 一共找到 5 个有可能合适的临床试验 (3 个在国内、2 个香港),还有 1 处医生之间看法不一样,我会在最后给您两个视角看看。下一步: 想办法 — 团队会列 10-20 种可能的方案让它们互相比一比。"*

The internal Wave 1 artifacts (per-expert reports, reviewer pairings, mechanical-gate verdicts) remain stored at `triggers/<run_id>/tasks/w1_*/` and are surfaced to the user only in the final clinician brief — not in the live chat.

---

**Step 6 — Wave 2 · hypothesis tournament (Co-Sci + Robin).**

Only if plan calls for it (always true for "research-grade analysis" / "hypothesis" intents). Tasks: `hypothesis_generation` (4-strategy blind-spot scanner) → `drug_repurposing` (Co-Sci Evolution 6 strategies) → `literature_synthesis` (PaperQA2 anti-hallucination RAG) → `expanded_access_navigation` + `cross_border_navigation` (parallel).

Then run Co-Sci Elo Tournament (3–5 rounds, early-stop on stable top-1 across 2 rounds):

```bash
opl-cancer wave2 \
  --patient <patient_dir> --run-id <run_id>
```

Robin EXPERIMENTAL_INSIGHTS_APPENDAGE feedback string flows back into each new round's Generation prompt. Reflector runs 6 modes between rounds.

Surface the top-3 paths to the user in plain language (v1.5.1):

Stage-start example: *"[2/5 想办法 / Brainstorming] 团队在列 10-20 种可能的方案, 然后让它们互相比一比, 找出最有把握的几个。大概 8-15 分钟。"*

Stage-end example: *"[2/5 想办法 / Brainstorming] ✓ 17 种可能的方案里挑出了前 3 名 (分别是 ...简述...)。下一步: 查数据 — 拿这 3 个方案去对照公开的肿瘤数据库, 看看现有研究里证据有多强。"*

Top-3 path summaries MUST be in lay terms — translate every medical term on first use per `references/patient_jargon_glossary.json`. The detailed hypothesis cards (HR / ORR / mPFS / Elo / parent-chain) stay in the clinician brief, NOT the live chat.

> v1.5: Wave 3 is **non-skippable critical path** (`docs/ANTI_PATTERNS.md` AP-1). The preflight check (`opl-cancer preflight`) refuses to start a patient run when neither jupyter (native) nor docker (bixbench) is available — no silent skip, no "Wave 3 will skip bixbench analysis" message. To bypass for dev/test only, use the assistant override `--allow-single-model` in preflight (NOT for patient runs).

---

**Step 7 — Wave 3 · data-evidence generation (native Python + GEPIA3, Docker opt-in).**

Tasks: `dataset_acquisition` (cBioPortal / GEO / ArrayExpress / SRA) → `gepia3_query` (TCGA + GTEx differential expression — v1.5 first-class, default for any TCGA-mappable cancer type) → `bioinformatics_data_analysis` (native scipy / PythonMeta / scanpy / lifelines via `NativeAnalysisRunner` — Docker fallback to `BixbenchRunner` for heavy R) → `meta_analysis` (metafor / PythonMeta + PRISMA flow) → `single_cell_reanalysis` (if applicable) → `pathway_enrichment` (GSEA / ORA / Hallmark / KEGG / Reactome / GO).

```bash
# v1.5+: default path uses NativeAnalysisRunner. --enable-docker is opt-in.
opl-cancer wave3 \
  --patient <patient_dir> --run-id <run_id>
```

Mechanical gates auto-enforce: G14 dataset-patient-match-score, G15 multiple-testing-correction, G16 batch-effect-declared, G17 meta-I²-policy + Henry self-verify-render mandate, G18 PRISMA-search-strategy, **G25 deferred-evidence-block** (v1.5 — refuses delivery if Wave-3 critical claim was skipped), **G26 evidence-strength-ranking** (v1.5 — caps Elo boost when subgroup match < 50% or I² > 60%, requires demotion-disclosed marker). Any gate block → re-run with corrections, surface to user as data-quality finding.

Outputs land in `triggers/<run_id>/data/` (per dataset, including `gepia3/aggregated_summary.csv`) + `meta_analysis/` (effect_sizes.csv + forest.png + funnel.png + pooled_estimates.json) + `analysis/*.ipynb` (reproducible notebooks).

User-facing surface (v1.5.1):

Stage-start example: *"[3/5 查数据 / Cross-checking] 团队在公开数据库 (TCGA 这种)里对照您的肿瘤特征。大概 5-12 分钟,慢的地方是查询要排队 (上游限速 12 秒一次,这是为了对方服务器稳定)。"*

Heartbeat example: *"[3/5 查数据 / Cross-checking] 还在跑公开数据库的查询, 已经完成 45/71 个。预计还需要 5 分钟。"*

Stage-end example: *"[3/5 查数据 / Cross-checking] ✓ 70 个查询里 70 个成功 (1 个失败是对方服务器问题, 不影响整体结论)。发现 2 个新方向值得记下来 (在报告里会标出来)。下一步: 审核 — 一条一条核对证据。"*

---

**Step 8 — Wave 4 · hypothesis validation against measured data.**

Each Wave 2 hypothesis is retested against Wave 3 measured outputs. Verdict per hypothesis: `survives` / `weakened` / `falsified` / `new` (Wave 3 surfaced new finding the hypothesis pool missed).

> **Informative selection (Arbor/HTR SELECT, N=1; `prompts/methods/informative_selection.md`).** Validation evidence is scarce for one patient — don't validate by popularity. When ≥2 surviving hypotheses are near-tied on Elo or imply mutually incompatible patient actions, prioritise the re-test whose outcome would **split the tie** (change the ranking), and record `discrimination_target: [hyp_a, hyp_b]` + `discrimination_rationale` on that Wave-4 record. The funnel surfaces how many ties the run actually resolved.

```bash
opl-cancer wave4 \
  --patient <patient_dir> --run-id <run_id>
```

---

**Step 8.5 — Deepen hot leads · re-entry (Arbor/HTR tree, ADR-0042; only if the plan granted depth).**

If `plan.json` set `max_depth > 1` and marked `deepen_candidates`, run `opl-cancer observe` and look at the hypothesis TREE + funnel: a `deepen_candidate` that is **near-tied with a rival** (its split is decision-relevant) and still has **depth budget** warrants a focused re-entry rather than stopping at the single pass.

```bash
opl-cancer deepen --patient <patient_dir> --run-id <run_id> --target <hyp_id>   # scaffolder: checks budget, never executes
```

Then **dispatch a focused mini Wave-2..4 scoped to that lead** — generate child hypotheses with `parent_chain=[<hyp_id>]` (refinements/alternatives that split it from its tie-rivals), run them through tournament + validation, then re-`observe` to see the deepened subtree.

**Loop-until-dry (the convergence rule, ADR-0042 ✗②).** Re-entry is a *bounded loop*, not a single shot. After each deepening round, re-`observe` and read the per-candidate state under "marked for DEEPEN":

- `deepenable …` → the lead still has budget + surviving children worth splitting further → may `deepen` again.
- `dry (converged)` → the last round produced child hypotheses but **none survived** → `deepen` refuses (`reason: direction_dry`); STOP deepening this lead, the direction is exhausted.
- `dead (Wave-4 falsified — do NOT deepen)` → the lead itself was disproven by Wave 4 → `deepen` refuses (`reason: target_dead`); STOP, never deepen a disproven direction (false-hope guard).
- `awaiting judgement (N children pending)` → the lead has children still PENDING Wave-4 judgement → `deepen` refuses (`reason: awaiting_judgement`); STOP this round, finish validating the existing children first; if Wave 4 already returned `inconclusive`, treat the lead as converged and proceed (do not re-spawn).
- `budget-spent` → the live frontier hit `max_depth` → STOP (raise `max_depth` only if a deeper split genuinely helps the patient).

So the loop terminates on **whichever comes first: the direction goes dry, or the depth budget is spent** — never an unbounded dig. This is **ADDITIVE**: it can only exceed the floor on a warranted lead, never shrink the planned team (`G55` still binds); `deepen` refuses past `max_depth` (`validate` flags `DEPTH_BUDGET_EXCEEDED`) and refuses a dry direction. The actual mini-wave *execution* is your dispatch (the CLI never executes any wave — same contract as Steps 5–8); the harness owns the budget, the convergence detection, and the tree projection. Skip this step entirely for a flat (`max_depth: 1`) run.

---

**Step 8.7 — Abstraction beat · distil cross-run priors (Arbor/HTR ↑, the dominant gain driver, ADR-0042).**

Before delivery, turn this run's results into reusable knowledge — the single highest-value judgment in the lifecycle. `observe` shows this as **OWED** until done.

```bash
opl-cancer abstract --patient <patient_dir> --run-id <run_id>            # scaffold: tells you to dispatch the beat
# dispatch prompts/pi/insight_abstraction.md → writes triggers/<run_id>/abstraction.json
opl-cancer abstract --patient <patient_dir> --run-id <run_id> --finalize # validate shape + persist to ledger
```

Dispatch `prompts/pi/insight_abstraction.md` as a subagent: it reads this run's hypotheses + Wave-4 verdicts and writes **1–3 grounded cross-run priors** (each generalises across ≥1 real leaf; a verbatim restatement of one hypothesis is rejected as auto-fill). `--finalize` persists them to the append-only ledger as `run_abstraction` rows, where the next run reads them as warm-start context (and the next planner reads the `warns_against` ones as dead-ends, completing the G52 read-loop). `G60` (WARN) records the skip in attestation if you omit this — it never withholds the patient's brief, but a run that doesn't abstract did not compound.

---

**Step 9 — Henry audit (IRB substitute, 4 layers).**

After all Waves finish, Henry runs **last** — the top layer — over the full claim set:

```bash
opl-cancer audit \
  --patient <patient_dir> --run-id <run_id>
```

Henry checks:
- **L1 mechanical** — all 58 gates (54 registry-swept + 4 delivery-only G56–G58/G61; G38/G44/G59 reserved) (G1 PMID-existence, G2 quote-match, G3 drug-normalization, G4 dose-unit-declared, G5 patient-context-isolation, G6 injection-scan, G7 imperative-detector, G8 Level-3-4 disclosure, G9 retraction-check, G10 guideline-version, G11 no-silent-fallback, G12 memory-overflow, G13 reviewer-model-distinct **[preflight hard-fail v1.5]**, G14–G18 data-analysis gates, G19 PI-imperative-detector, G20 PI-disagreement-surfacing, G22 DDR-zygosity, G23 recency-band, G24 crisis-detection, **G25 deferred-evidence-block [v1.5]**, **G26 evidence-strength-ranking [v1.5]**, **G27 privacy-scrub [v1.5]**, G28–G33 Wave-6 manuscript gates, **G34 delivery-attestation / G35 clinical-fact-provenance / G36 PMID-topic-relevance / G37 service-completeness [v2.7.0, ADR-0026]**, **G39 biomarker-contingency / G40 drug-comorbidity-safety / G41 SoC-completeness / G42 tier-discipline / G43 epistemic-symmetry [v2.7.1, ADR-0026 P1; G38 reserved]**, **G45–G55 research-team gates [v2.8, ADR-0027+: world-unknown comparator / SoC-baseline / source-depth / research-delta / forecast-preregistration / tournament-kill / unfalsified-ranking / failure-ledger / novel-candidate / memory-ledger / plan-floor]**, **G60 insight-abstraction-written [v2.13, ADR-0042]**, and the 4 delivery-only gates **G56 value-source-binding / G57 SoC-floor-present / G58 jurisdiction-availability [v2.11] / G61 wave3-substance-executed**) over every claim before rendering. Henry **self-verifies** that any G17 / G26 rendering mandate it issued is satisfied in the actual rendered artifact (closes v1.4 F10).
- **L2 disagreement-summariser** — Reviewer disagreement > 0.4 confidence delta → forced two-view delivery.
- **L3 permission gate** — every claim tagged Level 0 (info) / 1 (reasoning) / 2 (recommendation) / 3 (high-risk recommendation) / 4 (boundary). L3/L4 require a `risk_disclosure_card` written and patient-ack-gated.
- **L4 rollback registry** — retraction / new-evidence / patient-feedback / auditor-recheck withdraw queue.

Henry does **not** modify expert claims — only decides what may render.

User-facing surface (v1.5.1) — translate Henry verdicts to plain language. The internal name "Henry" can be mentioned by name once for warmth ("我们的内部审查员 Henry"), but the verdict words MUST be plain:

Stage-start example: *"[4/5 审核 / Double-checking] 我们的内部审查员 (Henry) 在一条一条核对证据, 把不稳的标出来。大概 3-6 分钟。"*

Stage-end example: *"[4/5 审核 / Double-checking] ✓ 27 条结论里 24 条直接通过, 2 条需要附加一段风险说明 (在报告里会标出来), 1 条被退回重做。下一步: 写两份报告 — 简单版给您, 专业版给医生。"*

Internal gate IDs (G1-G43), claim-level Level-3/Level-4 codes, RC-xxx risk-card IDs all stay in the archive (`triggers/<run_id>/tasks/henry/`) and the clinician brief — NEVER in the live user chat. See `prompts/tasks/progress_message_rendering.md` §"Hard rules".

---

**Step 10 — Wave 5 · render patient brief + Sid delivery rewrite.**

```bash
# v2.7.0: produce the honest scaffold, fill the briefs from the wave claims,
# then FINALIZE (real Henry audit + delivery-integrity gates G34/G35/G37 + G1/G2/G36).
opl-cancer funnel --patient <patient_dir> --run-id <run_id> --emit       # deterministic explored→survived counts → funnel.json
opl-cancer deliver --patient <patient_dir> --run-id <run_id>            # scaffold
#   ↳ fill patient_plain_brief.md + patient_pi_brief.md from real wave claims (incl. the funnel section, per brief_render.md §8)
opl-cancer deliver --patient <patient_dir> --run-id <run_id> --finalize # real audit + gates
opl-cancer attest --patient <patient_dir> --run-id <run_id>             # final integrity proof
opl-cancer validate --patient <patient_dir> --run-id <run_id>           # invariant check (exit≠0 = inconsistent state)
```

> **`validate` (Arbor/HTR invariant check).** After attest, `opl-cancer validate` re-checks run-state consistency deterministically — manifest/plan team drift, attested-without-brief, delivered-without-ledger (the `G54` learning-compounded invariant), and under-delivery (a planned wave with no artifacts). It is read-only and never executes a wave; a non-zero exit means the run is internally inconsistent and must not be presented as complete.

> `opl-cancer render` is **deprecated** (it was the `{"ok":true}` no-op stub that let session 0d1017d4 ship a free-handed brief). It now just runs the integrity gates and refuses. Use `deliver --finalize`. `deliver --finalize` and `attest` REFUSE (exit ≠ 0) unless the brief is backed by a real run: `run_token` manifest + recomputable provenance journal + real Henry audit + full planned team (`G37`) + on-topic, existing PMIDs (`G1`/`G2`/`G36`).

**v1.5 split**: every patient run produces TWO audience targets — pick by `profile.delivery_audience` (`clinical` = default, full medical content; `lay` = plain-language). When in doubt or when fatigue_flag / explicit user request fires, the planner emits both.

Three artefacts:
- `delivery/patient_brief.html` — full clinician-grade report with three-tier labels, PMID links, risk-disclosure-cards pinned top, model disagreement table, drill-down handles for every claim.
- **`delivery/patient_plain_brief.html` (v1.5)** — plain-language 2nd-person Chinese / English brief ≤ 2 pages. 4 sections: 你的病情一页纸 / 下一步要做什么 / 不同的选择 / 问医生 5 个问题. Jargon glossary at `references/patient_jargon_glossary.json`. No PMIDs in body, no risk-card tables, no Elo / I² stats — those stay in the clinician brief. See `prompts/tasks/patient_plain_brief_rendering.md`.
- `delivery/pi_delivery.md` — Sid's conversational rewrite (NOT single-shot HTML push):

  > "我让 team 跑了 4 个 GEO HCC TACE-refractory cohort + 一轮 hypothesis 联赛 + WNT pathway 重分析。**有 3 件事我想让你看看**:
  >   1. [established] 你的 RB1 mut + WNT pathway 高表达 → meta-pooled ICI ORR 0.31 [0.18-0.54](Iain 跑的 meta);
  >   2. [exploratory] 基于 GSE12345 + DepMap 投射,top-3 candidate drugs 是 X / Y / Z(Aviv 跑的 N=1 projection);
  >   3. **Reviewer 在这一点上分歧了**:Bert 认为这条 path 优先级高,Aviv 认为 sample size 不够强 — 我把两个视角都给你。
  > Risk-card 在顶部:Frances 的 EAP 路径有 L3 风险卡,需要你 ack 才能往下走。"

If any L3/L4 risk-card is unacked, Sid leads with it.

---

**Step 10b — Inline delivery to the chat (MANDATORY).** After `deliver --finalize` writes the files, the assistant (Sid) MUST speak the conclusions **inline in the chat reply** — the `pi_delivery.md` file is the *saved record* of the conversation, NOT a substitute for it. Files are persistence + drill-down evidence; the chat surface is the primary delivery medium.

Concrete contract — every patient run ends with a chat reply that contains, **in this order**:

1. **L3/L4 unacked risk-card** verbatim at top (if any), with `opl-cancer acknowledge <card_id>` hint — same content as the head of `pi_delivery.md`.
2. **Goal echo + value echo** (1-2 sentences) — "你这次的问题是 X, 你说过你的 value 排序是 Y, team 是按这个顺序跑的。"
3. **What team did this run** (1 short paragraph) — experts engaged, wave count, integrators called, wall-time. Run-metadata transparency.
4. **Top-3 conclusions with full content** — each with `[established]`/`[exploratory]`/`[speculative]` label + 1-2 sentences of substantive finding + provenance anchor (`[PMID: ...]`/`[NCT: ...]`/`[notebook: ...]`). **Not just titles** — the patient must read the conclusion in the chat, not in the file.
5. **Reviewer disagreement / cross-source conflict** (if any) — both positions named, no collapsing.
6. **Trade-off framed against `patient_value`** — option A vs B vs C, with axis-of-difference.
7. **Optionful next steps** — 2+ options + "ask team to do X" path. Never a single imperative.
8. **Drill-down + file pointers (LAST, not first)** — only AFTER the substantive content, list:
   - `delivery/patient_brief.html` — full clinician-grade report (PMID links + drill-down handles)
   - `delivery/patient_plain_brief.html` — plain-language 2-page brief
   - `delivery/pi_delivery.md` — this conversation, saved
   - `opl-cancer drilldown --run-id <id> --claim <id>` for evidence-chain
   - `opl-cancer reproduce --run-id <id>` for bit-exact rerun

**FORBIDDEN delivery patterns** (these are AP-13 anti-patterns, gate-blockable):

- ❌ "报告已生成,请查看 `delivery/patient_brief.html`。" (file-handoff without conclusions — this is the bug the patient reported)
- ❌ "Top-3 conclusions: (1) RB1 mut, (2) WNT pathway, (3) ICI candidate. 详见报告。" (titles without substance — patient must read content in chat)
- ❌ "完整结论在 pi_delivery.md 里。" (pointing to file as substitute for chat reply — the .md IS the chat content, not a replacement for it)
- ❌ Empty stage-end + file list — every run must end with the 8-step inline reply above, even for empty-evidence runs (in which case substitute the empty-integrator surface from `pi_delivery.md`'s "Empty-integrator handling" block).

**Implementation note**: after `deliver --finalize` succeeds, the assistant reads `delivery/pi_delivery.md` and pastes its full content (or a faithful rewrite respecting the 8-step shape above) into the chat. This is non-negotiable per `feedback_no_false_completion` — generating a file and then telling the user to read it is "delivery theater," not delivery.

---

**Step 11 — Drill-down + iterate.**

User can:
- Ask drill-down on any claim → Sid reads `memory/provenance/` + `triggers/<run_id>/tasks/` and explains the chain.
- Update preferences (depth, focus, language) → written to `pi_session/preferences.json`.
- File feedback / correction → `memory/feedback_log/` + cascade rollback if it invalidates downstream insights.
- Drop a new file → `inbox/` watcher triggers a new Wave run.
- Schedule monthly auto-run / opt into lit-signal alerts (PubMed/CIViC delta against profile keywords) — each goes through PI push-budget gating, never raw alert spam.

Archive trigger run when patient `/done`: `triggers/<run_id>/` → `archives/`.

---

## Patient-acknowledge & withdraw

```bash
opl-cancer acknowledge <risk_card_id>
opl-cancer withdraw <insight_id> --reason "<why>"
opl-cancer list-pending-acks
```

Withdraw cascades through the supersedes-DAG: any insight depending on a withdrawn claim is auto-reviewed.

## Patient observability

Every render contains an inline `[evidence chain]` toggle per claim showing: executor output → reviewer challenges → audit notes → PMID full quote → analysis notebook path. Patient can `python … cli.py reproduce --run-id <id>` to bit-exact re-run with the same models + prompt versions.
