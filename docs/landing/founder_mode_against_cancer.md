# Founder Mode Against Cancer

> 让全世界的每一个人都能拥有一个完整的 AI scientist team，只为他/她一个人工作 ——
> 调取世界已知的信息，**并主动产生世界未知的新信息**，
> 患者本人是自己案例的唯一决策人。
>
> —— PRD §0 Telos

Open-source · provenance-strict · patient-steered · founder-mode-against-cancer.
你买不起的私人科研团队，现在可以装在你的笔记本里。

---

## 为什么造这个

走过标准治疗的患者经常落在同一个死胡同：医生说"用尽了"，文献说"等试验"，论坛说"问问名医"——可名医一周只看 40 人。我们做不出更多医生，但我们能做一支随时待命、永远在线、把文献当母语、并且**会自己跑实验数据**的 AI 科学家团队。

这支团队同时跑三件事 —— 它们不是 1+2，是**三件套并列**：

- **D1 · 调取世界已知** —— 读你的病历、解读你的 NGS、复核分期、按 NCCN/CSCO/RECIST 给出当前 SOC 选项、扫 ClinicalTrials.gov + ChiCTR + FDA/NMPA 同情用药通路。
- **D2 · 产生世界未知（假设）** —— 跑 `hypothesis_generation` 4-strategy blind-spot scanner + `drug_repurposing` Co-Sci Evolution 6 策略 + Co-Sci Elo 联赛（3-5 轮，含 Reflector 6 模式 + Robin EXPERIMENTAL_INSIGHTS 回流），把"还没人写在论文里、但你的 case 配得上"的方向挖出来。
- **D3 · 产生世界未知（数据）** —— `dataset_acquisition` 从 GEO / ArrayExpress / SRA / DepMap / CCLE / cBioPortal / GDC 拉同癌种公开 cohort，跑 `bioinformatics_data_analysis`（Finch ReAct + bixbench Docker：DESeq2 / limma / scanpy / scvi）+ `meta_analysis`（metafor / PythonMeta + PRISMA 流程图），输出**真实统计量**：pooled HR/OR/RR + 95% CI + p-value + 患者投射 score + KM/Cox 预测 + drug ranking with quantified efficacy。然后 Wave 4 `hypothesis_validation` 把 D2 的假设拉回来用 D3 的真实数据回测，每一条得到 `survives / weakened / falsified / new` 的判决。

三级标签（established / exploratory / speculative）标的是**证据强度**，不是"把 prediction 降级成 hypothesis"。OPL 给你的是定量预测，不是 LLM 随手打个标签就交差。

这不是医疗器械，不是诊断软件，不是替你做决定的机器。这是一支**只对你一个人负责**的科学团队。

---

## OPL 团队做什么

你只和一个人对话：**Sid（PI / Chief-of-Staff）**。他是患者的唯一会话 surface —— 内部 18 位专家 + Henry + Feedback + ~22 integrators 你不需要看见，除非你想 drill-down。

```
你 ⇄ Sid（PI，长期记得你的 case 和偏好）
         │
         ├── 18 位 Expert（按需激活，每位有 task package portfolio）
         │     Rosa 病理 · Bert 分子 · Vince 治疗 · Rick 试验 · Heddy 影像
         │     Aviv 生信 · Iain meta · Mary 药理 · Ted 放疗 · Riad 介入
         │     Hong 中医 · Mark irAE · Kieren ID · Frances 同情用药
         │     Dennis 跨境 · Jen 缓和 · Tyler 实验设计 · Steve 营养
         │
         ├── Henry（IRB-substitute Auditor，全局 4 层审查 + Level 0-4 permission gate）
         ├── Feedback（跨 trigger 监听 inbox / 文献信号 / 数据库更新）
         └── ~22 Integrators（PubMed / NCCN / CT.gov / ChiCTR / OncoKB / CIViC / GEO / DepMap / ...）
```

**18 位 Expert 以真实临床先驱为 archetype 致敬命名（非真人模仿，法律安全）** —— persona 借鉴他们的方法论偏好和盲点关注，不绑定任何在世/已故个人。

**Hybrid lifecycle**：
- **Per-patient 持久 Project Memory**：你的 insight card / hypothesis / citation / evidence graph / tournament 历史 / feedback log 全部 append-only 版本化，团队跨 trigger 复用上次的工作。
- **Per-trigger ephemeral team runs**：每一次跑 = 一个 run_id，5 个 Wave 顺序展开：
  - Wave 1 retrieval（D1 expert 并行）
  - Wave 2 hypothesis tournament（Co-Sci Elo + Robin 文献回路）
  - Wave 3 data-evidence（Finch bixbench Docker 真实跑分析）
  - Wave 4 hypothesis validation（D2 假设 vs D3 真实数据回测）
  - Wave 5 Henry 审查 + Sid 对话式 delivery rewrite

**5 类 Trigger**：(1) 患者主动提问、(2) 新文件 drop 进 `inbox/`、(3) scheduled 月度 auto-run、(4) PubMed/CIViC lit-signal delta against 你的 profile、(5) integrator alert（NCCN 改版 / 关键 PMID retracted）。Feedback 不直接打扰你，所有 push 都经 Sid 的 push-budget 过滤。

---

## OPL 与 vMTB 的差异

很多人会问："这不就是 vMTB 升级版吗？" —— **不是**。

| 维度 | vMTB | OPL for Cancer |
|---|---|---|
| Telos | 检索 + 临床解读 | 检索 + 临床解读 **+ 主动产生世界未知信息** |
| 用户入口 | CLI 一次性调用，跑完即结束 | Sid 单一对话入口，per-patient 长记忆 |
| Lifecycle | Ephemeral（一次跑一次） | Hybrid：Project Memory + 多 trigger run |
| Hypothesis generation | 4-strategy（已有） | 4-strategy + Co-Sci Evolution 6 策略 + Co-Sci Elo 联赛 + Reflector + Robin 实验洞察回流 |
| 真实数据分析 | ✗（仅 retrieval） | ✓ Finch ReAct + bixbench Docker（DESeq2 / scanpy / scvi）|
| Meta-analysis | ✗ | ✓ metafor / PythonMeta + PRISMA flow + forest/funnel + I² 池化 |
| Hypothesis validation | ✗ | ✓ D2 假设 vs D3 真实数据回测，逐条 survives/weakened/falsified |
| 输出形态 | 一份 brief，结束 | append-only Project Memory + 持续 alert + 跨 trigger 复用 insight |
| 量化预测 | 三级标签 | 三级标签 + pooled HR/OR/RR + 95% CI + p-value + 患者投射 score + 药物 ranking |

**vMTB 是 retrieval-only**；OPL 是 **retrieval + generation + validation + memory**。

---

## 谁能用 · 谁不能用

**能用：**
- **患者本人 / 家属 / 主要照护者** —— 你是 OPL 唯一的服务对象，也是唯一的决策人。
- **临床研究者** —— 把它当 N=1 hypothesis 引擎 + 公开数据 re-analysis 工具。
- **开源贡献者** —— 18 个 expert persona、~34 个任务包、~22 个 integrator、20 个 mechanical gate 都欢迎 PR。
- **治疗医生** —— 不是 OPL 的服务对象，但**可以 drill-down 任何 claim 验证**：每条结论 30 秒内追到 PMID + 原文 quote + provenance hash + 可重放 notebook。医生**不签字、不决定患者读什么**。

**不能用：**
- **肿瘤急症**（脊髓压迫 / 高钙危象 / 中性粒减少性败血症 / TLS）→ 直接拨打 120 / 911 / 112，OPL 不是 triage。
- **任何非患者本人或患者授权照护者** —— OPL 是 patient-owned，不是医院/药企/监管/保险公司的工具。
- **诊断阶段**（"我是不是癌？"）—— OPL 工作 **from** 一个已确诊的 case，不 **toward** 诊断。未确诊请用 `firefly` 罕见病导航。
- **未成年人由监护人代操作** —— v1.3 还没实现 guardian-mode permission model，等 v1.4。

---

## 怎么开始（对话式，不是 CLI）

OPL 是一个 Claude Code skill plugin。一次安装，反复对话。

**安装（一次性）：**
```bash
npx skills add CancerDAO/opl-cancer-skill
# 克隆到 ~/.claude/skills/opl-cancer/
pip install -e ~/.claude/skills/opl-cancer
# 安装 Python deps（pyproject.toml）
```

可选：装 Docker 给 Wave 3 真实生信分析用（不装也能跑 Wave 1/2/5）。

**触发（自然语言，在 Claude Code / Codex / OpenCode / Cursor 任意一个 agent shell 里）：**

> "我有 NSCLC，三线进展了，想要 AI team 帮我分析下一步选项 —— 我的病历都在 `~/Downloads/我的病历`。"

skill 自检通过后，Sid 上线：

> 🧬 OPL for Cancer · 你的私人 AI 科研团队已上线
>
> 我是 Sid，你的 PI。我和我的 18 位团队成员只为你一个人工作。Henry 在后台做独立审查；每条结论都有 PMID + provenance hash + 三级标签；你是这个案子唯一的决策人。
>
> 请给我：(1) 病历入口 (2) 你想让 team 解决的问题。

之后 Sid 会：(1) 委派 `cancer-buddy-organize` 整理你的病历到 11-bucket canonical 目录（`01_当前状态 / 02_NGS报告 / 03_病理 / 04_影像 / 05_实验室 / 06_治疗历史 / 07_用药 / 08_症状 / 09_家族史 / 10_知情同意 / 11_诊断证明`），(2) 计算 readiness grade，(3) 给你计划，(4) 跑 5 个 Wave，(5) 用对话式 delivery 把团队工作过程（包括内部分歧）告诉你。

患者数据存在 `~/CancerDAO/patients/<patient_code>/`（**skill 仓库之外**——这样 skill 可以随时更新而不动你的数据）。

---

## founder-mode 哲学

1. **患者是唯一决策人。** Sid 不替你决定。没有外部医生 sign-off。L3/L4 高风险 claim 只需患者本人 acknowledgement，**不需要医生签字**。
2. **无 paternalism、无隐藏分歧。** Reviewer 之间的 disagreement 永远摆到台面，三级标签永远不被剥离，不确定性如实说，不和稀泥。
3. **Provenance 是医疗 AI 的最低纲领。** 每条数值/事实 claim 都有 `[PMID]` / `[NCT]` / `[NCCN-section]` / `[notebook]` 锚点 + SHA-256 hash。G2 mechanical gate 在写入时就拦截无锚点的 claim。
4. **No silent fallback。** Integrator API 失败必 raise，LLM 永远不替代查表，永远不静默降级到 snapshot。
5. **No model downgrade for cost。** Opus 4.7 跑 code / hypothesis reasoning / chair；MiniMax-M2.7 跑 lit synthesis / reviewer。不为省 token 牺牲深度。
6. **Real prediction，不只是打标签。** Wave 3 输出真实定量结果，不是 LLM 标个 exploratory 就交差。
7. **Open-source-reproducible。** Apache-2.0。任何 brief 第三方都能 `python tools/reproduce.py` 用同样的 model + prompt 版本 bit-exact 重跑。

---

## 安全与边界

- **不是诊断软件**，不是医疗器械，不替代医生。
- **不开方**，不算剂量，不发起任何治疗。
- **不是 emergency** —— 肿瘤急症请立刻拨打急救电话。
- **L3/L4 风险卡** 必须由患者本人 acknowledge 才进最终交付（`opl-cancer acknowledge <risk_card_id>`），可以随时 withdraw（级联回滚下游 insight）。
- 发现可能危害患者的输出 → 在 https://github.com/CancerDAO/opl-cancer/issues 提交 issue，72 小时内响应。
- 完整免责声明见 `/DISCLAIMER.md`。

---

## 如何贡献

Apache-2.0。三类贡献都欢迎：新增 expert persona / 新增 task package / 新增 integrator / 新增 mechanical gate / 新增 reviewer prompt / golden_set 反例。

1. 阅读 `/DISCLAIMER.md`（医疗 bar 比普通 SaaS 高）。
2. 阅读 `/CONTRIBUTING.md` 和 `/docs/governance/contributor_agreement.md`。
3. `python tools/sign_contributor_agreement.py` 签贡献者协议。
4. `pytest` 全绿、`golden_set` 不退步后开 PR。
5. **PR 治理 vs 患者侧 ack —— 两件不同的事**：
   - **PR 治理（开发者侧）**：改动 prompts / mechanical gates / permission policy 这类影响所有患者的代码，需要至少 1 位 maintainer + 1 位 clinical reviewer co-sign 才能合入主干。
   - **患者侧 L3/L4 claim 渲染（运行时）**：只需患者本人 acknowledgement，**不需要任何 maintainer/clinician/physician 签字**。Sid 不会因为某条 claim "没有医生背书" 而拦着你看见。

---

## 我们相信什么

- **患者拥有自己的数据，也拥有自己的决策权。** 团队只对你一个人负责。
- **AI 应该让弱势方变强，不该让强势方更强。** 你能调动的科研火力，从今天起，和顶级 lab 没有差。
- **provenance 是医疗 AI 的最低纲领。** 任何 claim 没有源头都该被假设是幻觉，G2 就是这条信念的 enforcement。
- **founder mode against cancer：** 不等许可，先把团队 ship 出来；ship 出来之后再叠合规、叠多语言、叠 guardian-mode。

—— CancerDAO Contributors, 2026

[Project home](https://github.com/CancerDAO/opl-for-cancer-skill) · [Disclaimer](../../DISCLAIMER.md) · [License (Apache-2.0)](../../LICENSE) · [PRD](../../docs/superpowers/specs/2026-05-23-opl-cancer-design.md)
