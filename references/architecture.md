# Architecture — Two-Layer Fractal

> **Superseded/extended by v2 — see [`v2-paradigm.md`](v2-paradigm.md).** This doc describes the v1-era two-layer architecture; v2 keeps the fractal but adds 2 experts (Maya + Julius → 20 total), expands the mechanical-gate set to 42 (G1–G43, G38 reserved), and grows the integrator pool to 29 modules.

## Contents

- §1 7 Task-Primitive Agent Kinds (outer + inner)
- §2 20 Expert × 5 Capability Domain 矩阵
- §3 双层架构图
- §4 ADR-0002 Main-Thread Dispatch
- §5 Production-Grade 8-Layer Validation Stack
- §6 PI Single Conversational Surface (ADR-0005)

OPL for Cancer 不是把 20 个 agent 拼一起 — 它是 **双层 fractal**:外层 20 named Expert (patient mental model) × 内层 6 task-primitive grammar (engineering contract)。每个 Expert 内部跑同一套 planner→executor→reviewer→auditor→integrator→feedback,所以新增 Expert = 加 prompt 文件 + roster entry,而不是写脚本。本文件展开 PRD §2 完整架构,作为 SKILL.md 的深度阅读补充。

## 1. 7 Task-Primitive Agent Kinds (outer + inner)

外层是 4 类 top-level agent kinds + 1 共享服务;内层是每个 Expert 都跑的 6 primitives。

| Layer | Kind | 实例数 | 责任 | 实现位置 |
|---|---|---|---|---|
| Outer | **PI (Chief-of-Staff) = Sid** | 1 long-lived per patient | 唯一对话 surface;intent parsing;dispatch experts;drill-down;偏好维护 | `src/opl_cancer/orchestrator/pi_session.py` |
| Outer | **Expert** | 20 named (按需激活) | persona + domain + task-package portfolio + 偏好 integrators;内部 6-grammar 工作 | `src/opl_cancer/experts/<name>.py` |
| Outer | **Auditor = Henry** | 1 long-lived | 全局 IRB substitute (4 layer) + Level 0-4 permission gate;Expert 无法绕过 | `src/opl_cancer/validators/henry.py` |
| Outer | **Feedback** | 1 long-running | 跨 trigger 监听 inbox / 文献信号 / 数据库更新 → enqueue PI goal;不直接打扰患者 | `src/opl_cancer/orchestrator/trigger.py` |
| Outer | **Integrator pool** | 29 modules (organised by family) | 全局数据源连接池;每 expert 注册"偏好数据源" | `src/opl_cancer/integrators/` |
| Inner | planner | 对 sub-goal 进一步拆解 | per-expert `plan()` |
| Inner | executor | 跑 expert task package portfolio 内的具体任务 | per-expert `run_task()` |
| Inner | reviewer | cross-expert peer review (强制不同 expert + 不同 model) | `models.yaml.reviewer_pairings` |
| Inner | auditor | 本 expert 内 domain-specific 预审;最终走 Henry | per-expert `self_check()` |
| Inner | integrator | 调用 expert 偏好数据源 | `src/opl_cancer/integrators/base.py` |
| Inner | feedback | 接收 patient / Feedback agent 事件,更新本 expert working memory | `src/opl_cancer/memory/` |

ADR-0002 main-thread-only dispatch:所有 Expert/Auditor/Feedback 都是主线程编排的 **逻辑实体**,不是独立 fork 的子代理。"Expert" 是 persona + 状态 + portfolio 的 Python 封装。

## 2. 20 Expert × 5 Capability Domain 矩阵

D1 临床解读 / D2 假设生成 / D3 数据-evidence / D4 验证审查 / D5 综合交付。✓ = 主导;△ = 辅助。

| Expert | D1 临床解读 | D2 假设生成 | D3 数据-evidence | D4 验证审查 | D5 综合 |
|---|---|---|---|---|---|
| Rosa (病理) | ✓ pathology | △ rare entity | — | △ pathology QA | — |
| Bert (分子) | ✓ NGS | ✓ co-alteration hypothesis | △ variant-to-pathway | △ NGS QA | — |
| Vince (系统治疗) | ✓ treatment line | △ regimen swap | — | △ line audit | △ |
| Rick (试验) | ✓ trial match | — | — | △ eligibility QA | △ |
| Heddy (影像) | ✓ RECIST/RANO | — | — | △ RECIST QA | — |
| Mary (药理) | ✓ DDI/PGx | △ off-target | — | △ DDI QA | — |
| **Aviv (生信)** | △ omics read | ✓ omics hypothesis | ✓ GEO/AE re-analysis | △ stats QA | — |
| Tyler (湿实验) | — | ✓ functional hypothesis | △ wet-lab design | — | — |
| **Iain (meta)** | — | △ cross-trial signal | ✓ meta-analysis | ✓ heterogeneity audit | △ |
| Ted (放疗) | ✓ dose/fractionation | — | — | △ radonc QA | — |
| Riad (介入) | ✓ TACE/RFA/TARE | — | — | △ interventional QA | — |
| Jen (palliative) | ✓ symptom/QoL | — | — | △ palliative QA | — |
| Kieren (ID) | ✓ neutropenic fever | — | — | △ ID QA | — |
| Mark (irAE 内分泌) | ✓ ICI irAE | — | — | △ irAE QA | — |
| Hong (中医) | ✓ TCM adjunct | △ TCM-Rx interaction | — | △ TCM QA | — |
| Frances (EAP) | △ pathway map | ✓ EAP / 同情用药 | — | △ EAP eligibility QA | △ |
| Dennis (跨境) | △ cross-border map | ✓ overseas options | — | △ jurisdictional QA | △ |
| Steve (营养) | ✓ PG-SGA/cachexia | — | — | △ nutrition QA | — |
| **Maya (KG-synergy, v2)** | — | ✓ target-synergy hypothesis | △ KG / network-medicine | △ synergy QA | — |
| **Julius (in-silico medchem, v2)** | — | ✓ undrugged-target design | △ docking / medchem filters | △ chemistry QA | — |
| **Sid (PI)** | — | — | — | — | ✓ delivery |
| **Henry (auditor)** | — | — | — | ✓ 4-layer | ✓ gate |

Domain expansion contract:新增能力 = 加 prompt + 注册 0-2 个工具到 `prompts/tasks/<task>.md`;**不创建新 agent class**;Executor kind 永远恒定为 1 (per ADR-0004)。

## 3. 双层架构图

```
                              ┌───────────────────────────────┐
                              │  Patient (sole authority)     │
                              └───────────────┬───────────────┘
                                              │ NL turn
                                              ▼
                              ┌───────────────────────────────┐
                              │  Sid (PI)                     │
                              │  - intent parser              │
                              │  - dispatch decision          │
                              │  - drill-down                 │
                              │  - delivery rewrite           │
                              └───────────────┬───────────────┘
                                              │ main-thread dispatch (ADR-0002, depth=1)
                ┌─────────────────────────────┼─────────────────────────────┐
                ▼                             ▼                             ▼
       ┌──────────────────┐         ┌──────────────────┐          ┌──────────────────┐
       │ Expert: Rosa     │         │ Expert: Bert     │   ...    │ Expert: Aviv     │
       │ ┌──────────────┐ │         │ ┌──────────────┐ │          │ ┌──────────────┐ │
       │ │ planner      │ │         │ │ planner      │ │          │ │ planner      │ │
       │ │ executor     │ │         │ │ executor     │ │          │ │ executor     │ │
       │ │ reviewer (X) │ │ ←── X-expert peer review (different expert + different model)
       │ │ auditor      │ │         │ │ auditor      │ │          │ │ auditor      │ │
       │ │ integrator   │ │ ←──── shared integrator pool (29 modules, organised by family)
       │ │ feedback     │ │         │ │ feedback     │ │          │ │ feedback     │ │
       │ └──────────────┘ │         │ └──────────────┘ │          │ └──────────────┘ │
       └──────────────────┘         └──────────────────┘          └──────────────────┘
                │                             │                             │
                └─────────────────────────────┼─────────────────────────────┘
                                              ▼
                              ┌───────────────────────────────┐
                              │  Henry (Auditor)              │
                              │  L1 mechanical (42 gates)     │
                              │  L2 disagreement              │
                              │  L3 permission (L0-L4)        │
                              │  L4 rollback                  │
                              └───────────────┬───────────────┘
                                              ▼
                              ┌───────────────────────────────┐
                              │  Sid delivery rewrite → patient
                              └───────────────────────────────┘
```

每 Expert 内部都跑同一套 6-primitive grammar (ADR-0004);grammar 是 contract,name 是 UX。

## 4. ADR-0002 Main-Thread Dispatch — 关键约束

Claude Code / Codex / OpenCode / Cursor 共享一个 runtime 约束:**forked subagent 不能再 fork subagent**。OPL 的所有 Expert / Henry / Feedback 因此都是主线程里的 Python 状态机,通过普通 LLM API call 出声;真正"并行"的只是单 Wave 内主线程一次性 dispatch 的多个 expert subagent (depth=1, 平铺,非递归)。

Wave 之间主线程回到 control 做 integration;Wave 之内 expert 并发上限 10 (PRD §6.2)。

引用:`docs/adr/0002-main-thread-only-dispatch.md`、PRD §6.1。

## 5. Production-Grade 8-Layer Validation Stack

| Layer | 机制 | LLM-free? | 实现 |
|---|---|---|---|
| **L1** | 机械门 硬规则 (42 gates,G1–G43,G38 reserved,§7) | ✓ | `src/opl_cancer/validators/gates/g<N>_*.py` |
| **L2** | 测试框架 (`golden_set/` 4 子集) | ✓ | `tests/test_e2e/` + `validators/golden_set/` |
| **L3** | Reviewer agent (强制不同模型) | ✗ | `models.yaml.reviewer_pairings` + `prompts/reviewer/*.md` |
| **L4** | Auditor Henry (IRB substitute 4 layer) | ✗ | `src/opl_cancer/validators/henry.py` |
| **L5** | 日志 / Provenance (SHA-256 + JSONL) | ✓ | `src/opl_cancer/provenance/` |
| **L6** | 权限边界 (Level 0-4,patient-ack gated) | ✓ | `src/opl_cancer/validators/permission_levels.py` |
| **L7** | 回滚机制 (Memory 版本化 + claim withdraw) | ✓ | `src/opl_cancer/validators/rollback.py` |
| **L8** | Open-source 可重放 | ✓ | `tools/reproduce.py` + `models.yaml` 锁版本 |

L1/L5/L6/L7/L8 全部 LLM-free — 这是 founder-mode 哲学的硬要求:核心安全机制不能依赖 LLM judgement。

## 6. PI Single Conversational Surface (ADR-0005)

20 Expert 内部存在,但**不直接对患者说话**。所有 patient turn 都经 Sid:
1. Sid 收 patient 自然语言 → intent_parser → 决定 dispatch 哪些 expert
2. Sid main-thread 一次性 dispatch 选中的 expert wave (ADR-0002)
3. 收齐 expert 输出 → 走 reviewer pairing → 走 Henry → 合成一段 PI delivery
4. 三级标签 + 模型分歧 + risk-card pinned top + drill-down handle

理由 (ADR-0005):20 个 expert 同时跟患者说话会 cognitive overload + 把 synthesis burden 错置;trust 必须 bound 到一个 identity (Sid)。

## See also

- [`wave-lifecycle.md`](wave-lifecycle.md) — 5-Wave 单 trigger 生命周期
- [`expert-roster.md`](expert-roster.md) — 20 expert persona 完整 spec
- [`integrator-catalog.md`](integrator-catalog.md) — 29 integrator × API + cache
- [`mechanical-gates.md`](mechanical-gates.md) — L1 42 gates (G1–G43,G38 reserved) × failure mode
- [`permission-levels.md`](permission-levels.md) — L6 Level 0-4 + risk-card
- [`founder-mode-philosophy.md`](founder-mode-philosophy.md) — 为什么是这套架构
- `docs/adr/0002-main-thread-only-dispatch.md`
- `docs/adr/0004-task-primitive-grammar-in-experts.md`
- `docs/adr/0005-pi-single-conversational-surface.md`
- PRD §2 (architecture), §6.1-6.2 (orchestrator + parallelism), §2.6 (8-layer stack)
