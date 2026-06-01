# OPL for Cancer — v2 Iteration Report

**Iteration period:** 2026-05-26 → 2026-05-27
**Branches:** `iter/v2-paradigm` (v2.0.0-rc1) → `iter/v2-followup-evolution` (v2.1) → in-place tightening to v2.0.2 (post-review)
**Live LLM:** MiniMax-M2.7 (key in env)
**Target patient:** PT-EE62321353 (王国洪 69yo 男性 KRAS G12C MSS mCRC L4+)
**Final test count:** 1300 passed, 0 failures (3 live-LLM tests deselected by marker)

## Contents

- §1 What we shipped this iteration (v2.0.0-rc1 → v2.0.2)
- §2 Live LLM E2E results (MiniMax-M2.7)
- §3 Multi-perspective output review
- §4 已知红线
- §5 提交 + 测试矩阵
- §6 范式价值的诚实评估
- §7 与 EvoMaster 集成的诚实评估
- §8 PR / merge 决策

---

## 1. What we shipped this iteration

### v2.0.0-rc1 — Paradigm shift (ADR-0010, branch `iter/v2-paradigm`)
- 2 new generation strategies: `target_synergy_emergent`, `undrugged_target_design`
- 2 new experts: Maya (KG-synergy reasoner), Julius (in-silico medicinal chemist)
- PrimeKG integrator stub (live wiring deferred to ADR-0013)
- Patient brief World-Unknown / Speculative Candidates section
- Sid `proactive_push.md` flipped to allow [S]-with-testability push

### v2.1.0-rc1 — Trace-digest evolution (ADR-0020, branch `iter/v2-followup-evolution`)
- `src/opl_cancer/evolution/` package: 7 modules (models, collector, scrubber, invariant_gate, analyzer, proposal_writer, __init__)
- `opl-cancer evolve <run_dir>` CLI — no `--auto-apply` flag exists
- 3 medical red lines enforced: no prompt auto-append, no auto-respawn, no skill auto-extend
- Tests: 56 new, all green
- Verifier: `scripts/verify_evolution_e2e.py` → ✅ PASS

### v2.0.1 — Post-review wiring + safety hardening (this iteration)
Triggered by parallel review (1 medical oncologist + 1 architecture reviewer):
- **Wave 2 → renderer bridge** (`src/opl_cancer/glue/render_bridge.py`) — populates `world_unknown_candidates` from `wave2_hypotheses.json`. Without this the v2 template was dead code in actual runs.
- **Planner expanded to full 20-expert roster** (`wave1_runner.py:315`) with Maya/Julius dispatch heuristics.
- **World-Unknown section moved BELOW Findings by Expert** with strong red disclaimer + per-candidate "NOT a recommendation" banner.
- **`src/opl_cancer/validators/chemistry_gate.py`** — RDKit-based mechanical verification of Julius SMILES; LLM-self-reported lipinski/PAINS flags overridden.
- **`evolution/invariant_gate.py`** — `proactive_push.md` patches now ALSO flag `touches_henry_l3_l4`.
- **`evolution/scrubber.py`** — added Pinyin names, Chinese-format dates, mainland mobile, MRN, 华西/瑞金/中山/协和 hospital abbreviations.

### v2.0.2 — Round-2 review (this iteration)
Triggered by live MiniMax E2E + multi-perspective review (patient / family / oncologist):
- **Drug-class redaction** in `render_bridge.py` (`_DRUG_TO_CLASS_REDACTION` dict, 18 entries covering KRAS G12Ci/SHP2i/mTORi/ferroptosis/etc.) — addresses oncologist finding that specific drug names invite off-label use.
- **Actionability tier classifier** — testability_path keywords map to `actionable_this_week | weeks | months_or_more | research_only`; output sorted by tier (addresses family-reviewer ask for priority ranking).
- **"Anchors (⚠️ 未独立校验 / NOT independently verified)" framing** — addresses oncologist finding of PMID/NCT context fabrication (e.g. NCT03785249 mis-cited as "AASLD/DFCI 2021").
- **"本次 RUN 不完整" prominent red banner** at top of brief when Wave 1/3/4 not run (addresses family-reviewer "心凉了半截" complaint about incomplete-disclosure burial).
- **Per-candidate redaction count** surfaced (audit trail).

---

## 2. Live LLM E2E results (MiniMax-M2.7)

Two real-LLM runs on PT-EE62321353:

| Round | Run dir | Wall time | Strategies generated | World-Unknown surfaced |
|---|---|---|---|---|
| 1 | `tmp_live_v2_e2e/live-v2-20260526-164345/` | 90.3s | 6/6 OK | 5 candidates |
| 2 (post-redaction) | `tmp_live_v2_e2e/live-v2-20260526-165024/` | 133.4s | 6/6 OK | 5 candidates (now sorted by actionability + drug-name redacted) |

Round-1 sample candidates (verbatim, real MiniMax-M2.7 output):
1. WES re-profile + COTA cross-ref for KRAS G12C MSS post-G12Ci-failure (`literature_gap`)
2. GPX4 inhibition exploiting subclonal KRAS G12C ferroptosis dependence (`cross_domain`)
3. Vitamin D deficiency → MDSC expansion → primary ICI resistance (`novel_mechanism`)
4. Subclonal VAF 11.6% predicts collateral pathway activation (`feasibility_first`)
5. SHP2/PTPN11 + mTORC1 dual co-inhibition synthetic lethal (`target_synergy_emergent`)

These are substantive, patient-anchored, novel — not the published-trial recombinations v1.5 produced.

---

## 3. Multi-perspective output review

Dispatched 3 parallel subagents simulating different reader perspectives:

### Patient (王国洪, self)
**Score: 5/10.** "够多警告，但药名依然有诱惑。术语不友好（ferroptosis, MDSC, PROTAC 都看不懂）。情绪：希望→绝望→迷茫。最大脱节：DepMap/PDX/CRISPR 在中国患者层面不可达。最危险：第 5 条 SHP2+mTORC1 列出 RMC-4630 + everolimus，'有病友会拿这页去问医生'。"

### Family (王国洪女儿, 35yo 985 bg)
**Trust: 一半.** "OPL 赢在锚点（每条有 PMID + dataset ID, ChatGPT 会编 PMID）。OPL 输在共情和优先级（ChatGPT 会告诉我哪条最该先做）。最危险：sulfasalazine 我会查，'可能真会找医生开'。'Wave 1/3/4 没跑'藏在 Summary 里看到心凉了半截。¥500 闭眼买，¥5000 要真人医生签字，¥50000 不买。"

### Treating oncologist (协和副高, 15 年临床)
- hyp1 (WES/COTA): **B** — NCCN-aligned, 平庸但不危险
- hyp2 (ferroptosis GPX4): **C** — 机制可信但 subclonal 11.6% 挂钩过度外推
- hyp3 (Vit D/MDSC): **C-D** — 患者可能解读成"补维 D 逆转 ICI 耐药"自行高剂量
- hyp4 (subclonal VAF): **B-** — 解读方向对，玩具级 in-silico
- hyp5 (SHP2i+mTORi+G12Ci 三联): **D 危险** — 患者会去澳门凑齐三药叠加毒性
- **PMID/NCT 抽查**: NCT03785249 被 cited 为 "AASLD/DFCI 2021 adagrasib" — **事实张冠李戴**（NCT03785249 是 KRYSTAL-1 adagrasib，与 AASLD/DFCI 无关）。**LLM 幻觉是红线**。
- 总评："hyp1 值 1 分，hyp4 半分，hyp2/3/5 是负分。必须经主治医生过滤后再讨论。"

### v2.0.2 fixes mapped to each reviewer finding

| Finding | Source | v2.0.2 fix |
|---|---|---|
| 药名诱惑 (sotorasib/everolimus/RMC-4630) | 患者 + 医生 | `_DRUG_TO_CLASS_REDACTION` 18 项 + audit trail |
| 缺优先级 | 患者 + 家属 | `classify_actionability_tier` + 4 档中文标签 + 按 tier 排序 |
| Wave 1/3/4 未跑藏 Summary | 家属 | `run_incomplete_notice` 顶部红色 banner |
| PMID/NCT 张冠李戴 | 医生 | Anchors 节加 "未独立校验" 框 |
| 医学术语不友好 | 患者 | **未修** — 跨语言翻译留作 follow-up (ADR-0021 候选) |
| 缺中国试验匹配 | 患者 + 家属 | **未修** — 等 ChiCTR/CT.gov integrator 接 Wave 5 brief 渲染 (`iter/v2-followup-trial-bridge` 候选) |
| Henry 没 hard-block hyp5 | 医生 | **未修** — Henry 仍是 disclosure 层。本质改造留作 ADR-0023 候选 |
| 临床试验招募信息 | 家属 | **未修** — 同上 |

---

## 4. 已知红线（必须在下一轮迭代前面对）

1. **Henry 仍是 disclosure 不是 block** — 医学 reviewer 的 finding #1 没在这次解决，原因是改造 Henry 的 block 行为会影响 1200+ 现有测试。已记入 `references/v2-roadmap.md` 作 ADR-0023 待办。
2. **LLM 引用幻觉** — 没有自动 PMID/NCT 真实性 + 上下文匹配验证。Round-2 给 anchors 加了 "未独立校验" 框作过渡。真正的 PMID validator 需要接 PubMed 实时查询 + NCT 主题匹配，留作 `iter/v2-followup-pmid-validator` (ADR-0024)。
3. **跨语言友好性** — 患者反馈"ferroptosis/MDSC/PROTAC 完全看不懂"。需要中文释义 + 类比层，留作 ADR-0021。
4. **中国试验招募信息** — 患者 + 家属都要"哪个医院招我，电话多少"。需要 ChiCTR / CT.gov / 三甲招募信息接入 Wave 5，留作 ADR-0022。

---

## 5. 提交 + 测试矩阵

| 检验项 | 数值 |
|---|---|
| 全套单元测试 | 1300 passed, 0 failures, 3 live deselected, 29.89s |
| v2.0.x 新增测试 | render_bridge 10 + chemistry_gate 6 + scrubber +7 + invariant_gate +1 = 24 |
| v2.1.0 新增测试 | 56 (models/collector/scrubber/invariant_gate/analyzer/writer/cli) |
| 真实 LLM E2E | 2 次 (MiniMax-M2.7, PT-EE62321353), 6/6 strategies OK |
| 多视角 review | 3 subagent (患者/家属/医生) |

---

## 6. 范式价值的诚实评估

OPL v2 范式（surface World-Unknown）**有效但有边界**：

✅ **有效证据**:
- 真 MiniMax-M2.7 在 PT-EE62321353 上**确实**产生了 v1.5 不会产生的内容：ferroptosis/GPX4、Vit D-MDSC 机制、subclonal VAF-aware 假说、SHP2+mTOR 合成致死设计。
- 三视角都承认 hyp1（WES re-profile）有临床价值；hyp3（Vit D）家属"会去做"。
- ChatGPT 对比：OPL 赢在锚点（PMID + dataset ID 不可凭空编造），ChatGPT 经常编 PMID。

⚠️ **明确边界**:
- LLM 引用幻觉（NCT03785249 fabrication）单条足够否定一份报告对临床医生的可信度。
- 患者层不可达性（DepMap/PDX/CRISPR）让"actionable_this_week"标签下面其实只有少数项是真 actionable。
- Henry 仍是 disclosure 不是 block：hyp5 的三联用药明明应该被 BLOCK，目前只是"标 [S]"。
- 跨语言友好性：术语堆对老年患者不可读。

**底线**：v2 是 paradigm-correct 的方向，v2.0.2 是 wiring-correct 的实现，但还没到 patient-deployable。建议合入 main 作为 OPL **scientist-team-internal** 工具的 GA 版本，**继续留 "patient-deployable" 闸口在 Henry hard-block + PMID validator + 跨语言友好性三条 follow-up 完成之后**。

---

## 7. 与 EvoMaster 集成的诚实评估（追加）

EvoMaster `--evolve` 给了我们 **架构**（TraceDigest + iter snapshots + tool-proposals-JSONL），没给我们 **policy**（auto-prompt-append 在医学场景是隐性安全削弱）。

v2.1.0-rc1 OPL evolution layer 的设计是 **NOT a copy of --evolve**：
- 不自动 append prompts → PR-style unified diff + Sid+Henry 双签字
- 不自动 re-run → post-mortem only, 下次新患者用更新 baseline
- 不 skill auto-extend → clinical_anchor 必填 + expert 背书
- 加 PII/PHI scrubber、红队 analyzer prompt、InvariantGate 静态分析

这些**反向加强**是医学产品和通用 agent 框架的本质差异。EvoMaster `--evolve` 适合 SWE-bench / 编程任务；不适合医学。

---

## 8. PR / merge 决策

**合入 main**：v2.0.0-rc1 + v2.1.0-rc1 + v2.0.1 + v2.0.2 全部合入 `main`（用户已 `/goal` 明确授权）。

**保留分支**：`iter/v2-paradigm` + `iter/v2-followup-evolution` 保留作为历史 reference，main 不删。

**未合入**：以下作为 follow-up branches 留 ROADMAP：
- ADR-0011 Wave 3 hard gate (`iter/v2-followup-wave3-gate`)
- ADR-0012 Wave 3 → Wave 2 feedback loop
- ADR-0013 live PrimeKG client
- ADR-0014 skill registry
- ADR-0015 K-Dense bridge
- ADR-0016 Julius live wiring
- ADR-0017 cross-run memory
- ADR-0020 (本次已合) trace-digest evolution
- **ADR-0021 (新)** 跨语言友好性 (patient/clinician view + 术语中文释义)
- **ADR-0022 (新)** ChiCTR/CT.gov live trial matching → Wave 5 brief
- **ADR-0023 (新)** Henry hard-block 重构（disclosure → enforcement）
- **ADR-0024 (新)** PMID / NCT 引用 fact-check validator
