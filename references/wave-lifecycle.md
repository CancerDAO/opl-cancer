# Wave Lifecycle — Single Trigger Run State Machine

## Contents

- §1 End-to-end flow (ASCII)
- §2 Per-Wave Task Packages
- §3 Sync Barrier Rules
- §4 Failure / Retry Strategy
- §5 Reviewer Pairing Constraint (G13)
- §6 Streaming PI Delivery (planned)

一个 trigger run = 一段 patient 提出的 goal + Sid 编排的 5 Wave。本文件展开 PRD §4 的完整状态机,补 SKILL.md Step 4-10 的工程细节(dependency、并发上限、retry、同步屏障)。

## 1. End-to-end flow (ASCII)

```
[ patient ] ─NL/file─▶ [ Sid (PI) ]
                            │ intent_parser → 分流:
                            │   ├ drill-down old claim → memory/provenance/ 直接答 (不走 Wave)
                            │   ├ 偏好更新           → pi_session/preferences.json
                            │   ├ 闲聊/情绪          → Sid 自答 (可选 invoke 陪伴/心理支持类工具)
                            │   └ 新 goal           → 进入 Wave pipeline ↓
                            ▼
                     [ planner ]                          (Sid top-level)
                            │ inputs: case_text.md + profile.json + goal + Memory
                            │ outputs: plan.json
                            │   - expert 集 (subset of 20)
                            │   - per-expert sub-goal
                            │   - Wave 选择 (1-5 subset)
                            │   - integrator family 集 (F1-F10 subset)
                            ▼
                     [ G5 + G6 mechanical gates ]
                            │ 违反 → abort + Sid 告知 patient
                            ▼
        ┌─── Wave 1 · world-known retrieval ──────────────────────────┐
        │  parallel experts (主线程 fan-out, depth=1):                │
        │    Rosa → pathology_interpretation                          │
        │    Bert → molecular_ngs_interpretation                      │
        │    Heddy → recist_progression                               │
        │    Rick → trial_matching (CT.gov + ChiCTR)                  │
        │    Vince → treatment_line_recommendation                    │
        │    ...                                                      │
        │  cross-expert reviewer pairings (models.yaml,              │
        │    不同 expert + 不同 model);prompts: pmid_quote_verify,    │
        │    retraction_check, self_contradiction, numerical_sanity,  │
        │    stats_correctness                                        │
        │  output: triggers/<run_id>/tasks/<task_id>/                 │
        │            executor_output.json + reviewer_verdict.json     │
        └────────────────────────────┬────────────────────────────────┘
                                     │ sync barrier
                                     ▼
        ┌─── Wave 2 · hypothesis tournament (Co-Sci + Robin) ────────┐
        │  T6 hypothesis_generation (4-strategy blind-spot)          │
        │  T7 drug_repurposing (Co-Sci Evolution 6-strategy)         │
        │  T8 literature_synthesis (PaperQA2 anti-halluc)            │
        │  T8b expanded_access_navigation + cross_border (parallel)  │
        │  Co-Sci Elo Tournament 3-5 rounds (early-stop on top-1 ×2) │
        │  Robin EXPERIMENTAL_INSIGHTS_APPENDAGE → next round prompt │
        │  Reflector 6-mode between rounds                           │
        └────────────────────────────┬────────────────────────────────┘
                                     │ sync barrier
                                     ▼
        ┌─── Wave 3 · data-evidence (Finch bixbench) ────────────────┐
        │  T9 dataset_acquisition (GEO/ArrayExpress/SRA              │
        │     + match_score G14)                                     │
        │  T10 bioinformatics_data_analysis (Finch ReAct +           │
        │      bixbench Docker — DESeq2/limma/scanpy/scvi)           │
        │  T11 meta_analysis (metafor/PythonMeta + PRISMA flow)      │
        │  T12 single_cell_reanalysis (if applicable)                │
        │  T13 pathway_enrichment (GSEA/ORA/Hallmark/KEGG/Reactome)  │
        │  gates: G14 dataset-match, G15 MT-correction,              │
        │         G16 batch-effect, G17 I²-policy, G18 PRISMA        │
        │  outputs: data/<accession>/ + meta_analysis/* + *.ipynb    │
        └────────────────────────────┬────────────────────────────────┘
                                     │ sync barrier
                                     ▼
        ┌─── Wave 4 · hypothesis validation against measured data ───┐
        │  T14 hypothesis_validation: re-test each Wave 2 hypothesis │
        │    against Wave 3 measured outputs.                        │
        │  per-hypothesis verdict: survives / weakened / falsified / │
        │    new (Wave 3 surfaced finding the pool missed)           │
        └────────────────────────────┬────────────────────────────────┘
                                     │ sync barrier
                                     ▼
        ┌─── Henry (auditor, IRB substitute 4-layer) ────────────────┐
        │  inputs: 所有 expert outputs + reviewer verdicts + plan +  │
        │           profile                                          │
        │  L1 mechanical (58 gates: 54 registry-swept G1–G37,        │
        │    G39–G43, G45–G55, G60 + 4 delivery-only G56–G58, G61;   │
        │    G38/G44/G59 reserved)                                   │
        │  L2 disagreement (reviewer Δ confidence > 0.4 → 两视角)    │
        │  L3 permission gate (Level 0-4 per claim)                  │
        │  L4 rollback registry                                      │
        │  Henry 不修改 claim,只决定 render/risk-card-required/block │
        └────────────────────────────┬────────────────────────────────┘
                                     ▼
        ┌─── Wave 5 · render patient brief + Sid delivery ───────────┐
        │  patient_brief.html + patient_brief.md (full report)       │
        │  pi_delivery.md (Sid conversational rewrite,not single-    │
        │    shot HTML push)                                         │
        │  L3/L4 unacked risk-card → 顶部 nag                        │
        └────────────────────────────┬────────────────────────────────┘
                                     ▼
                       provenance.jsonl + memory update
                                     ▼
                  [ patient ] ◀── drill-down / iterate / archive
```

## 2. Per-Wave Task Packages

| Wave | Task packages | 触发条件 | 依赖 |
|---|---|---|---|
| 1 | D1 临床解读族:`pathology_interpretation` · `molecular_ngs_interpretation` · `recist_progression` · `trial_matching` · `staging_workup` · `irae_management` · `ddi_screening` · `nutrition_assessment` · `palliative_planning` · `radonc_dosing` · `interventional_options` · `infection_control` · `tcm_oncology` · `china_rwe_adjustment` | 默认开 (任何 patient question 都需要 retrieval) | plan.json + G5/G6 |
| 2 | D2 假设生成族:`hypothesis_generation` · `drug_repurposing` · `literature_synthesis` · `expanded_access_navigation` · `cross_border_options` | 仅当 plan 包含 hypothesis / 重定位 / 跨境 / EAP intent | Wave 1 outputs |
| 3 | D3 数据-evidence:`dataset_acquisition` · `bioinformatics_data_analysis` · `meta_analysis` · `single_cell_reanalysis` · `pathway_enrichment` | 仅当 plan 包含 N=1 projection / GEO 重分析 / meta intent;**需要 Docker** | Wave 1 + Wave 2 |
| 4 | `hypothesis_validation` | 仅当 Wave 2 跑过 | Wave 2 + Wave 3 |
| 5 | `patient_brief_rendering` + `pi_delivery` rewrite | 永远跑 (final render) | Henry pass |

Wave 1 + Wave 5 是 minimum viable path (no docker / no hypothesis tournament);Wave 2-4 按 plan 选择性触发。

## 3. Sync Barrier Rules

- **Wave 内并行**:单 Wave 内 Executor 并发上限 **10** (PRD §6.2);超过分多 sub-wave。
- **Reviewer 1:1 跟 Executor**:reviewer model ≠ executor model (G13);配对表来自 `models.yaml.reviewer_pairings`。
- **Wave 间硬同步屏障**:全部 Executor + 对应 Reviewer 完成,主线程更新 memory,才进下一 Wave。无 streaming Wave (PRD §17.5 P0 efficiency optimization 提到改进项)。
- **Henry 永远 last**:全部 Wave 完成后才跑 Henry (顶层 auditor);Henry 不能与 Wave 并跑。

## 4. Failure / Retry Strategy

| Failure | Strategy | 实现 |
|---|---|---|
| Executor 单次失败 (LLM API err / timeout) | 1 次 retry;仍失败 → 弃 claim + 写 audit log | `orchestrator/dispatch.py` |
| Reviewer 失败 | 同上,但 reviewer-empty 不阻 Executor surface — Henry L2 标 "no reviewer" |
| Mechanical gate block (58 gates: G1–G37, G39–G43, G45–G55, G60 registry-swept + G56–G58, G61 delivery-only; G38/G44/G59 reserved) | 不静默 truncate;重 prompt + 重跑;仍 block → 弃 claim + audit log | `validators/mechanical_gates.py` |
| Integrator API down (G11) | **必 raise,不静默 fallback**;Sid 告知 patient 哪个 source 不可达 | `integrators/base.py` |
| Wave 超时 (per-wave budget) | abort run + 保留已完成 Wave 产物到 archives/ + 标 partial | `orchestrator/dispatch.py` wave timeout |
| Patient 主动 cancel | 主线程 checkpoint → 保留已完成 Wave + 标 partial + **不渲 brief** | PRD §15 G6 |

## 5. Reviewer Pairing Constraint (G13)

`models.yaml.reviewer_pairings` 强制:
- Reviewer expert ≠ Executor expert (cross-expert peer review)
- Reviewer model ≠ Executor model (cross-model audit) — 防 echo chamber (failure mode E6)
- 每对 pairing 走 5 个 reviewer prompts:`pmid_quote_verify` · `retraction_check` · `self_contradiction` · `numerical_sanity` · `stats_correctness`
- Reviewer confidence delta > 0.4 → trigger expert 联赛 (Co-Sci-style) → Henry 判 + Sid 显式两视角呈现 (G20)

## 6. Streaming PI Delivery (planned, PRD §17.5 P0)

v0:Sid 等全部 Wave 完成才说话 (single-shot delivery)。
v0.1:Sid 监听 wave 完成事件 → 增量告知患者进度 ("Wave 1 finished, 5 expert delivered, found 2 disagreements, continuing to Wave 2...") → 降低患者感知延迟 ~70%。

## See also

- [`architecture.md`](architecture.md) — 7-task-primitive + 8-layer validation
- [`mechanical-gates.md`](mechanical-gates.md) — 全规则 (58 mechanical gates — 54 registry-swept G1–G37, G39–G43, G45–G55, G60 + 4 delivery-only G56–G58, G61;G38/G44/G59 reserved)
- [`troubleshooting.md`](troubleshooting.md) — Wave-level failure 恢复
- PRD §4 (lifecycle), §6.2 (parallelism + retry), §17.5 (P0/P1/P2 optimization)
- `src/opl_cancer/orchestrator/dispatch.py`
