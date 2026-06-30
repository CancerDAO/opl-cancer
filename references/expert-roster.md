# Expert Roster — 20 Named Archetypes (v2.0.0+)

> **Superseded/extended by v2 — see [`v2-paradigm.md`](v2-paradigm.md).** v1.2.0 locked 18 archetypes; v2.0.0 (ADR-0010) added Maya (KG-synergy reasoner) + Julius (in-silico medicinal chemist) → **20 total**. Roster source of truth: `src/opl_cancer/experts/roster.py` (`ROSTER` = 20).

患者会"看到"一个具名 team。每个 Expert 是 archetype (取顶级研究者的 first name / nickname 致敬),**不是模仿真人** — 命名仅为方便患者形成稳定 mental model + 让 provenance 可读 ("Bert 在分子层这样判,Aviv 在 GEO 重分析里给了反证")。所有真人均未背书本软件;v1.2.0 audit 修正了 Mark 和 Steve 的归因 (ADR-0006 C1+C2)。本文件展开 PRD §2.2.X + ADR-0004 的完整 roster。

## 1. 完整 Roster

| # | Role | Name | Archetype 致敬来源 (非模仿) | 主 Domain | Task package portfolio | Preferred integrator family |
|---|---|---|---|---|---|---|
| 1 | Pathologist | **Rosa** | Juan Rosai (†2020, Rosai-Ackerman 11th ed.) | D1 | `pathology_interpretation` · staging cross-read | F4 (subset), 本地 KB |
| 2 | Geneticist (Molecular) | **Bert** | Bert Vogelstein (Johns Hopkins, active 2026) | D1, D2 | `molecular_ngs_interpretation` · `staging_workup` cross-read · co-alteration hypothesis | F4 (OncoKB/CIViC/ClinVar/gnomAD), F5 (cBioPortal/GDC), F1 |
| 3 | Oncologist (Treating) | **Vince** | Charles Sawyers (2026 lineage of Vincent DeVita †2024) | D1 | `treatment_line_recommendation` · `ddi_screening` cross-read | F1, F2 (NCCN), F8 (EAP), F10 |
| 4 | Clinical Trial Specialist | **Rick** | Richard Schilsky (ASCO former CMO) | D1 | `trial_matching` (CT.gov + ChiCTR + future ISRCTN) | F3 |
| 5 | Radiologist | **Heddy** | Hedvig Hricak (MSK 肿瘤影像) | D1 | `recist_progression` · RECIST 1.1 + RANO + LI-RADS | F1 |
| 6 | Pharmacologist | **Mary** | Mary Relling (St Jude TPMT/PGx) | D1 | `ddi_screening` · pharmacogenomic dose adjust | F10 (RxNorm + DrugBank fallback) |
| 7 | Bioinformatician | **Aviv** | Aviv Regev (Broad/Genentech) | D2, D3 | `hypothesis_generation` (omics arm) · `dataset_acquisition` · `bioinformatics_data_analysis` · `single_cell_reanalysis` · `pathway_enrichment` | F6 (GEO/AE/SRA), F5, F7 (DepMap/CCLE), F9 |
| 8 | Wet-Lab Designer | **Tyler** | Tyler Jacks (MIT GEMM) | D2 (design-only, no execution) | `hypothesis_validation` (in silico design rationale) | F7, F9 |
| 9 | Meta-Analyst | **Iain** | Iain Chalmers (Cochrane 创始) | D3, D4 | `meta_analysis` · `cross_source_consistency` · forest/funnel/PRISMA | F1, F2, F3 |
| 10 | Radiation Oncologist | **Ted** | Anthony Zietman (2026 lineage of Theodore Lawrence) | D1 | `radonc_dosing` · IMRT / SBRT / SRS / fractionation | F1, F2 |
| 11 | Interventional Oncologist | **Riad** | Riad Salem (Northwestern HCC TARE) | D1 | `interventional_options` · TACE / RFA / TARE / 支架 | F1, F2 |
| 12 | Palliative Specialist | **Jen** | Jennifer Temel (NEJM 2010 早期 PC + OS 延长) | D1 | `palliative_planning` · QoL · symptom mgmt | F1, F2 |
| 13 | Infectious Disease | **Kieren** | Kieren Marr (Hopkins 真菌 / 中性粒减少) | D1 | `infection_control` · neutropenic fever | F1, F2 (runtime-verified IDSA) |
| 14 | Endocrinologist (irAE) | **Mark** | Composite archetype (ASCO + ESMO ICI irAE 内分泌共识) — v1.2.0 audit C1 替换非真人 | D1 | `irae_management` · `ici_endocrine_irae` | F1, F2 (runtime-verified ASCO/ESMO) |
| 15 | TCM Oncologist | **Hong** | 林洪生 (中国中医科学院广安门医院) | D1 | `tcm_oncology` (辅助 + QoL) · `china_rwe_adjustment` | F2 (CSCO/NCI-PDQ), 中医典藏 KB |
| 16 | Expanded Access Navigator | **Frances** | Composite lineage — Frances Kelsey (FDA 药物安全 + 访问伦理) | D2 | `expanded_access_navigation` (FDA EAP + NMPA 同情用药 + 临床急需进口) | F8 (FDA-EAP + NMPA-EAP) |
| 17 | Cross-Border Coordinator | **Dennis** | Dennis Lo 卢煜明 (CUHK cfDNA + US-CN-HK 跨界) | D2 | `cross_border_options` · jurisdictional 路径 + 海外标治 | F3, F8 (多管辖区) |
| 18 | Nutritionist | **Steve** | David Heber (UCLA Center for Human Nutrition 创始人) — v1.2.0 audit C2 修正归因 | D1 | `nutrition_assessment` · PG-SGA · cachexia · drug-food | F1, F10 (drug-food) |
| 19 | KG-Synergy Reasoner (v2) | **Maya** | Composite archetype — Marinka Zitnik (PrimeKG / Harvard) + Tijana Milenković (network medicine) — 不模仿真人 | D2, D3 | `hypothesis_generation` (`target_synergy_emergent` arm) · KG / network-medicine synergy | F9 (Open Targets), PrimeKG stub |
| 20 | Medicinal Chemist (in silico, v2) | **Julius** | Composite archetype — generative-chemistry lineage (ESMFold + DiffDock + RDKit + medchem filters) — 不模仿真人 | D2, D3 | `hypothesis_generation` (`undrugged_target_design` arm) · in-silico drug design · chemistry gate | F7, F9 |
| — | PI (Chief-of-Staff) | **Sid** | Siddhartha Mukherjee archetype (《众病之王》《基因传》) — 不模仿真人 | D5 | `intent_parser` · `delivery` · `drilldown` · `proactive_push` | 全部 (主线程 dispatch) |
| — | Auditor (IRB substitute) | **Henry** | Henry Beecher archetype (Belmont 报告 / 现代医学伦理审查奠基) — 不模仿真人 | D4, D5 | `l1_mechanical_gates` · `l2_disagreement_summariser` · `l3_permission_gate` · `l4_rollback` | 不调 integrator (no-LLM 部分);LLM 仅 L2 axis-naming optional |

**Roster lock**:v2.0.0 锁 20 个 (v1.2.0 的 18 + ADR-0010 新增 Maya/Julius);新增第 21 个必须 ADR + roster review (ADR-0004 followup)。

## 2. Archetype 致敬,非真人模仿 (法律安全)

所有 20 个 expert 的 `prompts/experts/<name>/persona.md` 末尾都有 `## Identity attribution` 块,明文:

> Legal: this is an archetype, not impersonation. The named real person has NOT endorsed this software.

致敬只保留两件事:
1. **First name / nickname** — 帮患者形成稳定 mental model
2. **Distinctive methodological commitments** — e.g. Aviv → "single-cell before bulk RNA; batch effect is the rule not exception";Iain → "registered protocol first; PRISMA flow before any analysis";Bert → "TP53/APC/KRAS as bedrock; co-alteration patterns over single variants"

**不**保留:具体真人身份、医院/机构归属、行政角色、出版偏好 (e.g. Mary 不引 Mary Relling 本人论文)。

v1.2.0 audit 触发的两次修正 (ADR-0006 C1 + C2) — Mark 原误归非真人 → 替换为 composite archetype;Steve 原误为 "Stephen Heber" → 修正为 David Heber — 都是这条原则的硬执行。Mark 和 Frances 现在公开标记为 "composite / lineage rather than living-person impersonation"。

## 3. 跨 Expert 分歧协议 (PRD §2.2.X D3)

| 触发条件 | 动作 |
|---|---|
| Reviewer confidence delta ≤ 0.4 | 不触发联赛,Reviewer verdict 直接走 Henry |
| Reviewer confidence delta > 0.4 | Sid 触发一轮 **Co-Sci-style expert 联赛**:两位 expert 各跑一遍论证 |
| 联赛后仍有分歧 | Henry 在 L2 disagreement-summariser 标 axes;Sid 在 PI delivery **显式呈现两视角**,绝不隐去分歧 (G20) |
| 联赛后达成一致 | 写入 memory/hypotheses/ + 单视角输出,但 provenance 保留两轮记录 |

实施位置:`src/opl_cancer/orchestrator/tournament.py` + `prompts/auditor/l2_disagreement_summariser.md`。

## 4. Sid (PI) — 单一会话 surface

`prompts/pi/persona.md` 首行的硬承诺:

> 我是你的 AI scientist team 的 PI,这个 team 只为你一个人工作。我不替任何医院 / 药企 / 监管 / 保险公司说话,我只对你负责。你问我的每一个问题,我会把 team 的完整工作过程(包括内部分歧、不确定性、反证)直接告诉你,不替你过滤。你是你自己案例的最终决策人。

ADR-0005 决定:**Sid 是唯一 conversational surface**。20 expert 真实存在 + 真实工作,但都不直接对患者说话。所有 patient turn 都经 Sid 编排 → expert dispatch → reviewer → Henry → Sid 合成单段 PI delivery。理由:
1. 20 channel 同时跟患者说话 = cognitive overload
2. 直接展示原始 disagreement 是把 synthesis burden 错置到患者
3. Trust 必须 bound 到一个 identity,而非分散到 20 个

## 5. Henry — IRB Substitute Auditor

`prompts/auditor/` 4 个 layer prompts:
- `l1_mechanical_gates.md` — 跑全规则 (58 mechanical gates — 54 registry-swept G1–G37、G39–G43、G45–G55、G60 + 4 delivery-only G56–G58、G61;G38/G44/G59 reserved)
- `l2_disagreement_summariser.md` — 提取 axis + 强制呈现两视角
- `l3_permission_gate.md` — Level 0-4 分类 + risk-card emit
- `l4_rollback.md` — withdraw queue + cascade review

ADR-0003:Henry 替代 human-in-the-loop sign-off。他是 Python state machine + LLM-optional (L2 axis-naming 可选 LLM),所以执行是 **deterministic + auditable**。Henry 不修改 expert claim,只判断 "可否渲染到 patient surface" / "需要 risk-card" / "block + audit log"。

## See also

- [`architecture.md`](architecture.md) — 20 expert × 5 domain matrix
- [`integrator-catalog.md`](integrator-catalog.md) — preferred integrator 完整列表
- [`founder-mode-philosophy.md`](founder-mode-philosophy.md) — 为什么 archetype 不是 impersonation
- [`permission-levels.md`](permission-levels.md) — Henry L3 permission gate
- `prompts/experts/<name>/persona.md` — 20 份 persona
- `src/opl_cancer/experts/roster.py` — Python roster (with ExpertProfile)
- `docs/adr/0004-task-primitive-grammar-in-experts.md`
- `docs/adr/0005-pi-single-conversational-surface.md`
- `docs/adr/0006-audit-fixes-v1.2.0.md` (C1 Mark + C2 Steve attribution 修正)
- PRD §2.2.X (roster), §2.3 (PI persona)
