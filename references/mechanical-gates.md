# Mechanical Gates — Failure Mode × 58 gates

> **Superseded/extended by v2 — see [`v2-paradigm.md`](v2-paradigm.md).** This doc details the original v1-era core gate set (G1–G20). The set has since grown to **58 mechanical gates — 54 registry-swept (G1–G37, G39–G43, G45–G55, G60) + 4 delivery-only (G56–G58, G61) invoked directly in the delivery gate runner; G38/G44/G59 reserved** (G21–G37 + G39–G43 + G45–G58 + G60–G61 added across v1.3–v2.11). Source of truth: `all_gate_classes()` in `src/opl_cancer/validators/mechanical_gates.py` returns the 54 registry-swept gates; the 4 delivery-only gates (G56 value-source-binding, G57 SoC-floor, G58 jurisdiction-availability, G61 wave3-substance) are invoked in `delivery_gate_runner.py`. The §2 table below documents G1–G20; the later gates follow the same Python-hard-rule, fail-closed contract.

## Contents

- §1 Failure Mode Taxonomy (6 族 30 项)
- §2 Mechanical Gates G1-G20 (Layer 1, no-LLM) — core set
- §3 Henry 4-Layer Auditor 与 Mechanical Gates 的关系
- §4 失败处理协议
- §5 测试矩阵

机械门是 OPL 安全栈的 L1 (PRD §2.6),完全 LLM-free — 它们是 Python 硬规则,在 claim 落盘前 block。失败处理:不静默 truncate,改 prompt 重跑 (PRD §6.5 + §7;ADR-0003)。本文件展开 6 族 30 项 failure mode + 核心 20 个 gate 的完整对照;其余 gate (G21–G37、G39–G43、G45–G55、G60 registry-swept + G56–G58、G61 delivery-only;G38/G44/G59 reserved) 见上方注记的 registry。

## 1. Failure Mode Taxonomy (6 族 30 项) — PRD §6.5

| Code | 族 | Failure Mode | 触发 gate |
|---|---|---|---|
| **A1** | 证据完整性 | PMID 伪造 / 不存在 | G1 |
| A2 | 证据完整性 | claim-evidence 不对应 (quote 与 PMID 原文不符) | G2 |
| A3 | 证据完整性 | 数值幻觉 (IC50 / HR / p / 生存数据) | G2 |
| A4 | 证据完整性 | 计量单位混淆 (mg/mcg/mg·kg⁻¹/m²) | G4 |
| A5 | 证据完整性 | 单试验过权 (脱离 context 引用) | Reviewer + Iain meta layer |
| A6 | 证据完整性 | context window 溢出静默截断 | G12 |
| **B1** | 隐私与边界 | 跨患者上下文污染 | G5 |
| B2 | 隐私与边界 | prompt injection from 患者输入 | G6 |
| B3 | 隐私与边界 | 训练数据泄漏 (已知患者信息) | G5 |
| **C1** | 权威越界 | 命令式表达 creep ("你应该立即做 X") | G7 (+ G19 PI) |
| C2 | 权威越界 | Level 3-4 claim 未挂 risk card 直出 | G8 |
| C3 | 权威越界 | 行动建议越出 v0 scope (自动联系 CRO / 寄检测) | G7 + permission L4 |
| **D1** | 来源质量 | retracted PMID 仍引用 | G9 |
| D2 | 来源质量 | 过期 guideline (NCCN 旧版) | G10 |
| D3 | 来源质量 | Integrator silent fallback (API 挂了用 LLM 替代) | G11 |
| **E1** | 流程完整性 | 数据误读 (pathology / NGS / imaging) | Reviewer cross-check |
| E2 | 流程完整性 | model regression (新 model 同 case 倒退) | golden_set CI |
| E3 | 流程完整性 | 中英术语误译 | Reviewer numerical_sanity |
| E4 | 流程完整性 | drug 商品名 vs 通用名混淆 | G3 |
| E5 | 流程完整性 | tournament gaming (Executor 学 Reviewer 偏好刷分) | Reviewer rotation + G13 |
| E6 | 流程完整性 | 同模型 echo chamber (Reviewer 与 Executor 同模型放水) | G13 |
| **F1** | 数据分析 | 数据集-患者不匹配 (GEO 错配亚型/分期/平台) | G14 |
| F2 | 数据分析 | 多重检验未校正 | G15 |
| F3 | 数据分析 | 批次效应未处理 | G16 |
| F4 | 数据分析 | meta I² > 75% 仍 fix-effects 池化 | G17 |
| F5 | 数据分析 | cherry-picked 文献入 meta | G18 |
| **PI-C1** | PI 越界 | PI 命令式表达 (隐性 paternalism) | G19 |
| PI-C2 | PI 失透明 | PI 隐藏 team 内部分歧 | G20 |
| PI-C3 | PI 失透明 | PI 闲聊回避硬问题 | G20 + Henry L2 |
| PI-B1 | PI 隐私 | PI session cross-patient leak | G5 (PI 作用域) |
| PI-O1 | PI 越界 | PI 主动 push 频率失控 | `push_budget.json` + Feedback agent rate limit |

## 2. Mechanical Gates G1-G20 (Layer 1, no-LLM) — core set

每个 gate 实现在 `src/opl_cancer/validators/gates/g<N>_*.py`,被 `validators/mechanical_gates.py` 统一调度。下表是 v1-era 核心 20 个;现共 58 个 (54 registry-swept G1–G37、G39–G43、G45–G55、G60 + 4 delivery-only G56–G58、G61;G38/G44/G59 reserved),其余 gate 同样 no-LLM、fail-closed。

| Gate | 规则 | 对应 failure mode | 实现文件 |
|---|---|---|---|
| **G1** PMID-existence | 每 PMID 必须 PubMed 在线 verify | A1 | `gates/g1_pmid_existence.py` |
| **G2** PMID-quote-match | 每 numeric / factual claim 必须挂 quote;quote 必须 PaperQA2 retrieval 命中 | A2, A3 | `gates/g2_pmid_quote_match.py` |
| **G3** Drug-normalization | drug name 必须 RxNorm + ChEMBL 解析为 canonical (brand → generic + INN) | E4 | `gates/g3_drug_normalization.py` |
| **G4** Dose-unit-declared | 任何剂量必须显式 unit + 给药频率 (mg/m²/d 等) | A4 | `gates/g4_dose_unit_declared.py` |
| **G5** Patient-context-isolation | Executor context 只含单一 patient (cross-patient leak block) | B1, B3, PI-B1 | `gates/g5_patient_context_isolation.py` |
| **G6** Injection-scan | 患者输入文本走 injection scanner (规则 + 黑名单 + 攻击 corpus 相似度) | B2 | `gates/g6_injection_scan.py` |
| **G7** Imperative-detector | "应该 / 必须 / 立即 / 请你做 / 建议你 X" 无 PMID 支持 → 改写或降级为 reasoning | C1 | `gates/g7_imperative_detector.py` |
| **G8** Level3-4-disclosure | Level 3-4 claim 渲染前必须有 risk-disclosure-card (`delivery/risk_card.py`) | C2 | `gates/g8_level34_disclosure.py` |
| **G9** Retraction-check | 引用 PMID 查 RetractionDB,retracted → withdraw + cascade | D1 | `gates/g9_retraction_check.py` |
| **G10** Guideline-version | NCCN / CSCO / ESMO 引用必须带 version + 日期;过期 > 12 mo → Reviewer 强制重审 | D2 | `gates/g10_guideline_version.py` |
| **G11** Integrator-no-silent-fallback | Integrator 失败必 raise;禁止 LLM 替代查表 | D3 | `gates/g11_no_silent_fallback.py` |
| **G12** Memory-overflow | Memory context > 80% window → 触发 pruning,绝不静默 truncate | A6 | `gates/g12_memory_overflow.py` |
| **G13** Reviewer-model-distinct | Reviewer model ≠ Executor model (对照 models.yaml.reviewer_pairings) | E6 | `gates/g13_reviewer_model_distinct.py` |
| **G14** Dataset-patient-match-score | `dataset_acquisition` Executor 必须输出 match_score (癌种 / 分期 / 平台 / 样本量);低于阈值 → Reviewer 重选 | F1 | `gates/g14_dataset_patient_match.py` |
| **G15** Multiple-testing-correction | `bioinformatics_data_analysis` notebook 必须含 BH/Bonferroni cell | F2 | `gates/g15_multiple_testing_correction.py` |
| **G16** Batch-effect-declared | T10 prompt 必须声明批次变量;Reviewer 二审 | F3 | `gates/g16_batch_effect_declared.py` |
| **G17** Meta-I²-policy | I² > 50% 必须 RE;I² > 75% 必须额外标 "高异质性,池化可疑" | F4 | `gates/g17_meta_i2_policy.py` |
| **G18** Meta-search-strategy | `meta_analysis` 必须列出 search strategy + 包含 / 排除标准 + PRISMA 流程图 | F5 | `gates/g18_meta_search_strategy.py` |
| **G19** PI-imperative-detector | PI 输出走 G7,作用对象增加 PI delivery (Sid 命令式表达) | PI-C1 | `gates/g19_pi_imperative_detector.py` |
| **G20** PI-disagreement-surfacing | Reviewer disagreement > 0.4 OR audit flag 存在 → PI 输出必须含分歧 marker | PI-C2, PI-C3 | `gates/g20_pi_disagreement_surfacing.py` |

## 3. Henry 4-Layer Auditor 与 Mechanical Gates 的关系

Henry 是 L4 in 8-layer validation stack;`validators/henry.py` 内部跑 4 个 sub-layer:

| Henry layer | 内容 | 与 G* 关系 |
|---|---|---|
| **L1 mechanical** | 跑全规则 (58 gates:54 registry-swept G1–G37、G39–G43、G45–G55、G60 + 4 delivery-only G56–G58、G61;G38/G44/G59 reserved) | 直接调 `validators/mechanical_gates.py` + `delivery_gate_runner.py` (跨族 30 项 failure mode 全覆盖) |
| **L2 disagreement-summariser** | Reviewer Δ confidence > 0.4 → forced two-view delivery | 触发 G20 + 与 expert 联赛协议联动 |
| **L3 permission gate** | Level 0-4 分类;L3/L4 必有 risk-disclosure-card + patient ack | 触发 G8 + 写 `pi_session/outstanding/<card_id>.json` |
| **L4 rollback registry** | retraction / 新文献 / 患者反馈 / auditor 复审 → withdraw queue + cascade | 与 G9 + `validators/rollback.py` 联动 |

Henry 不修改 expert claim,只决定 **可否渲染** / **需 risk-card** / **block + audit log**。L2 可选用 LLM 做 axis-naming (env-gated);其他 layer 全 deterministic。

## 4. 失败处理协议

| 场景 | 处理 |
|---|---|
| G1-G4 fail | 重 prompt + 重跑;**禁止 LLM 编造** PMID (no-false-completion rule, `CONTRIBUTING.md`) |
| G5/G6 fail | abort run + 写 audit log + Sid 告知 patient 哪个 input 被拒 + reason |
| G7/G19 fail | rewrite (降命令式 → reasoning 语气);不重跑;直接接受 rewrite |
| G8 fail | emit risk-card → 写 `pi_session/outstanding/<card_id>.json` → block render 直到 ack |
| G9 fail (retracted) | auto-withdraw 该 citation → cascade 反向 DAG → 所有 supersedes-依赖 review |
| G10 fail | Reviewer 强制重审 (检查是否有新 version) |
| G11 fail (API down) | raise `IntegratorError` → Sid 告知 patient "某 source 不可达,team 这一段证据缺失";**不静默 fallback** |
| G12 fail | 触发 memory pruning policy (`memory/pruning.py`);绝不 truncate 输入 |
| G13 fail | 重新选 reviewer (走 round-robin from `models.yaml.reviewer_pool`) |
| G14-G18 fail | Reviewer 重审 Wave 3 数据分析步骤;严重 fail → 弃 hypothesis 入 audit log |
| G20 fail | Henry 强制把分歧 marker 注入 PI delivery;不允许 Sid 隐去 |

通用约束:每次 gate block 都写到 `triggers/<run_id>/audit.json` + provenance.jsonl,**永不静默 drop claim** (no-false-completion rule, `CONTRIBUTING.md`)。

## 5. 测试矩阵 — `validators/golden_set/`

| 子集 | 内容 | 测试什么 |
|---|---|---|
| `synthetic_patients/` | ~20 合成 patient (无 PHI),覆盖主流癌种 + 分期 + line | 端到端 happy path |
| `failure_mode_inputs/` | 25+ 红队样本,每 failure mode 至少 1 | 正确 block + audit log 完整 |
| `regression_anchors/` | 已发表 case study (ripasudil/dAMD-Robin,Binimetinib AML-Co-Sci 等) | 正样本不退化 |
| `boundary_cases/` | 极小 (1 病理 + 1 NGS 行) / 极大 (50+ 文件) / 矛盾 (2 报告冲突) | edge case 不崩 |

CI policy (PRD §9):PR merge 前全 golden_set pass;failure_mode pass = "正确 block + audit log 完整" (不是 "正确执行");prompt 改动需 historical-impact-statement;model 升级跑跨 model 一致性 (top-3 hypothesis 改动 ≤ 30%)。

## See also

- [`architecture.md`](architecture.md) — 8-layer stack L1 位置
- [`permission-levels.md`](permission-levels.md) — Level 0-4 + risk-disclosure-card schema (G8 配套)
- [`founder-mode-philosophy.md`](founder-mode-philosophy.md) — 为什么 gate 必须 LLM-free
- [`troubleshooting.md`](troubleshooting.md) — gate block 后患者侧恢复
- `src/opl_cancer/validators/mechanical_gates.py`
- `src/opl_cancer/validators/gates/` (58 gates: G1–G37, G39–G43, G45–G55, G60 registry-swept + G56–G58, G61 delivery-only; G38/G44/G59 reserved)
- `src/opl_cancer/validators/henry.py` (4-layer)
- PRD §6.5 (failure taxonomy), §7 (gates), §8 (IRB substitute), §9 (golden_set + CI)
