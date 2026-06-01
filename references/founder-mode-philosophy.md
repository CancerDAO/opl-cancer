# Founder-Mode Philosophy

## Contents

- §1 五条核心原则 (硬约束)
- §2 为什么没有医生 sign-off (ADR-0003)
- §3 为什么是 archetype 不是 impersonation
- §4 OPL 的能力边界 (做什么 / 不做什么)
- §5 PRD §17 Self-Evaluation 引用

OPL for Cancer 的设计取舍**不**是"和现有医疗 AI 一样,只是更好"。它有一组 OPL-独有的硬哲学,决定了它做什么、不做什么、为什么会与其他癌症 agent 看起来不像。本文件展开 PRD §0 (Telos)、§1.3 (Non-Goals)、§17.3-17.7 (self-eval),以及 ADR-0003 的核心立场。

## 1. 五条核心原则 (硬约束,不可妥协)

### 1.1 Patient is sole decision authority

患者本人是自己案例的唯一决策人。Sid 不下达命令 (G7/G19 imperative-detector 在 prompt 层拦),Henry 不替患者签字,physician 可以 drill-down 但不 gate delivery。患者 ack 于 L3/L4 才是唯一 human gate。

ADR-0003 引用:**"founder-mode patients are themselves the decision-making party. They have explicitly chosen to take responsibility for their own care … inserting an external reviewer in front of their own data flow is paternalistic and inverts the consent model."**

### 1.2 No paternalism, no hidden disagreements

Reviewer 分歧永远 surface,三级标签 (established/exploratory/speculative) 永不被剥离;uncertainty 显式陈述,不"为了让患者好理解而抹掉"。

具体执行:G20 (PI-disagreement-surfacing) 强制 Sid delivery 含分歧 marker;Henry L2 disagreement-summariser 提取 axis;跨 expert confidence Δ > 0.4 → 触发 Co-Sci-style 联赛 + 显式两视角 (PRD §2.2.X D3 + ADR-0005 mitigation)。

### 1.3 Provenance-strict

每条 numeric / factual claim 必须挂 `[PMID]` / `[NCT]` / `[NCCN-section]` / `[notebook]` anchor + SHA-256 provenance hash。G2 (PMID-quote-match) 在 write-time block 未挂 anchor 的 claim。**LLM 永远不能直接合成证据** — 这是 `CONTRIBUTING.md` no-offline-only 规则的硬执行。

任何渲染过的 brief 都可以被第三方用 `tools/reproduce.py` 重放 (相同 model + prompt 版本)。

### 1.4 No silent fallback

Integrator API 失败必 raise (G11);LLM 不能替补查表。Sid 把这种"某 source 不可达"事件如实告知患者,而不是装作"刚才那段是从 PubMed 找的"。

PRD §6.5 D3 + `CONTRIBUTING.md` no-offline-only 规则:**医疗 agent 不允许把"我从训练数据猜的"包装成"查到的"**。这条比任何其他原则都硬。

### 1.5 No model downgrade for cost

`models.yaml` 锁定:Opus 4.7 跑 code / hypothesis reasoning / chair;MiniMax-M2.7 跑 lit synthesis / reviewer。深度调研 / PDF 抽取 / 医学综合 / hypothesis 联赛 一律不降级。

`CONTRIBUTING.md` no-model-downgrade 规则:**不为省钱降 Sonnet/Haiku**。subagent fanout 用并行 (Wave 内 10 并发) 而不是降模型节省 token。这是患者侧的承诺,不是工程便利。

### 1.6 Real prediction, not just labelling (附加)

Wave 3 输出必须是**量化预测** — pooled HR / OR / RR + 95% CI、N=1 projection score、Cox/KM survival、drug ranking with quantified score。三级标签标注的是**证据强度**,不是"我们到底敢不敢预测"。"speculative" 标签 ≠ "不预测",而是"预测了,但证据弱,你要知道"。

### 1.7 Apache-2.0 + open-source reproducible (附加)

整套架构、prompt、validator、gate、test set 全部 Apache-2.0 开源。任何第三方可以 audit / fork / 重放历史 brief。`tools/reproduce.py` + `models.yaml` 锁版本保证 bit-exact 重放。

## 2. 为什么没有医生 sign-off (ADR-0003)

主流医疗 AI 是 HITL (human-in-the-loop) 范式:临床医师在前置审,AI 只是 decision support,医师是 acting party。OPL 拒绝这套,理由两条:

1. **Founder-mode patient 不是审批客体**。他们已经走到 standard-of-care 用尽 / 试验无 slot / 跨境无路径的位置,主动选择自己负责。把外部 reviewer 插到他们和自己数据之间是 paternalism,是把 consent model 倒过来。
2. **没有规模化 reviewer pool**。一个 founder-mode patient 一周能产生几十次 agent run。volunteer clinician network 撑不住这个吞吐;付费 reviewer 又把 standard-of-care 的经济现实带回来。

替代方案 — **mechanical 4-layer transparency stack** (Henry):
- L1 forced risk-disclosure card (无法 suppress)
- L2 forced disagreement surfacing (不被 majority-vote 掩盖)
- L3 forced known-serious-risk checklist (per-drug catalogue)
- L4 forced patient-acknowledgment loop (L3/L4 必须 ack 才推进)

这不是"放弃 HITL,赌患者运气好";是**用机械 + 完全透明** 替代**人工 + 可能不透明**。患者看到的不确定性、分歧、已知风险,**比 HITL 工作流里医师过滤后给患者的更多**。这是 ADR-0003 的核心立场。

## 3. 为什么是 archetype 不是 impersonation (法律 + 哲学双重)

20 个 expert 都以顶级研究者的 first name 命名 (Rosa / Bert / Aviv / Iain / ...),但 `prompts/experts/<name>/persona.md` 末尾都明文 disclaimer:

> Legal: this is an archetype, not impersonation. The named real person has NOT endorsed this software.

只保留两件事:
1. **First name** — 让患者形成稳定 mental model (而不是"agent_07 说...")
2. **Distinctive methodological commitments** — Aviv → "single-cell before bulk RNA;batch effect is the rule";Iain → "PRISMA flow before any analysis";Bert → "TP53/APC/KRAS bedrock; co-alteration over single variant"

**不**保留:具体真人身份、机构归属、行政角色、出版偏好。

v1.2.0 audit (ADR-0006) 触发两次硬修正:Mark 原误归一个不存在的人 → 替换为 composite archetype (ASCO + ESMO irAE 共识);Steve 原误为 "Stephen Heber" → 修正为 "David Heber"。这两条都标进 CHANGELOG 是因为:一旦真人不存在或张冠李戴,法律 + 哲学双线崩 — 法律线是 attribution 错误,哲学线是 "我们假装在引述真人"。两者都不可接受。

## 4. OPL 与相邻工具类别的边界

OPL 不替代相邻的工具类别,而是与它们互补。按形态划分:

| 相邻工具类别 | 形态 | 阶段 | OPL 边界 |
|---|---|---|---|
| **一次性分子肿瘤会诊 (MTB)** | retrieval-only,一次性 board 报告 | 已确诊 + 已有 NGS | OPL = retrieval + generation + validation + memory(持续在线 PI session)。一次性会诊是单次产物;OPL 是 ongoing research team |
| **陪伴 / 病历整理类** | 陪伴 / 心理 / 病历整理 / 营养 / 教育 (不做临床决策) | 任何阶段 | 这类工具可被 Sid invoke (情绪 / 整理)。OPL 是 research-grade analysis — 每条 claim 有 PMID + provenance + 三级标签 |
| **罕见病 / 未确诊诊断导航** | 罕见病诊断导航 (HPO pipeline) | **未**确诊 / 诊断奥德赛 | 诊断导航解决 *toward* 诊断;OPL 解决 *from* 诊断 (已确诊后的研究 team)。诊断不明的 cancer case 走诊断导航;已确诊走 OPL |

**OPL 不做**:
- 给未确诊患者做诊断 (属于诊断导航类工具)
- 替患者做情绪 / 陪伴 / 自我管理日记 (属于陪伴 / 整理类工具)
- 单次 retrieval-only 会诊 (属于一次性 MTB 会诊)
- 急诊 triage / 寻 ICU (OPL 不是 triage system,见 SKILL.md "When NOT to invoke")

**OPL 专做**:已确诊后的 N=1 research-grade analysis — 治疗线决策、NGS 重读、trial matching、EAP 路径、跨境路径、hypothesis tournament、drug repurposing、GEO N=1 projection、meta-analysis 同癌种 cohort、second-look on physician's plan。

## 5. PRD §17 Self-Evaluation 引用

**§17.3 哪些目的已实现**:
- ✅ 完整 AI scientist team (7 task-primitive + 5 domain + 29 integrator modules)
- ✅ 为一个人服务 (per-patient Memory + PI long-lived + 严格 context isolation)
- ✅ 世界已知 retrieval (D1 + F1-F5/F8)
- ✅ 世界未知 generation (D2 + D3 + Co-Sci + Robin + Finch bixbench + meta)
- ✅ 患者是唯一决策人 (无 HITL + 4-layer IRB substitute + L3/L4 ack + 模型分歧强制透明)

**§17.4 核心 gap (诚实承认)**:
- ⚠️ **"全世界每个人"**:v0 实际只服务 founder-mode 子集(~< 0.1% 全球癌症患者) — 需要 Docker、有英文文献阅读基础、能自带 LLM key、信息素养高
- 走向"每个人"的路径:v0.1 cloud Jupyter (降技术门槛) → v0.2 claude.ai web wrapper (降工具门槛) → v0.3 多语言 (扩文化门槛) → v0.4 代理人模式 (扩生理 / 精神门槛) → v1.0+ patient-friendly 渐进信息呈现 (扩信息素养门槛 — 最难,且最不能违反 founder-mode 哲学)

**§17.6 风险登记 (与本哲学相关)**:
- PI 演化成"温和 paternalism" → persona.md + PI Reviewer 独立模型 + 命令式 mechanical gate + golden_set 加 "温和 paternalism 检测"
- Open-source 后被恶意 fork 改差 (去掉 mechanical gates / 卖给 vendor 替药企导流) → Apache-2.0 + Trademark policy (CancerDAO 注册 OPL-Cancer 商标,fork 不能用同名)+ canonical 仓库可信源
- 法律灰色 (患者真用 OPL 输出做了治疗决策出问题) → 发布前法务流程 (PRD §15 G8 标 open);明确 jurisdictional disclaimer per country (见 `DISCLAIMER.md`)

## See also

- [`architecture.md`](architecture.md) — 7-task-primitive 是哲学的工程化
- [`expert-roster.md`](expert-roster.md) — archetype 不模仿真人的执行
- [`permission-levels.md`](permission-levels.md) — patient ack 取代 physician sign-off
- [`mechanical-gates.md`](mechanical-gates.md) — gate 必须 LLM-free 的哲学根源
- `docs/adr/0003-no-human-in-the-loop.md` (本哲学的 ADR-canonical 表述)
- `docs/adr/0006-audit-fixes-v1.2.0.md` (Mark/Steve 归因修正 — archetype 原则的硬执行)
- `DISCLAIMER.md`
- PRD §0 (Telos), §1.3 (Non-Goals), §17.3-17.7 (self-evaluation)
