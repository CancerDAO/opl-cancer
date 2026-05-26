<div align="center">

# OPL for Cancer

### One Person Lab — 一个人的私有科研实验室

> *"让全世界每一个人都能拥有一支世界顶级的 AI 科研团队，只为你一个人工作。"*

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-blueviolet)](https://claude.ai/code)
[![CancerDAO](https://img.shields.io/badge/CancerDAO-Open%20Source-orange)](https://github.com/CancerDAO)

<br>

[什么是 OPL](#什么是-opl) · [遇见您的实验室](#遇见您的实验室) · [实验室在做什么](#实验室在做什么) · [安装](#安装) · [使用](#使用) · [运行示例](#运行示例) · [设计哲学](#设计哲学) · [技术实现](#技术实现) · [贡献](#贡献)

</div>

---

## 什么是 OPL

**OPL = One Person Lab**。

2024-2025 年最火的范式是 **OPC (One Person Company)** —— 一个创始人 + AI 工具栈，能跑出一家真正的公司。CancerDAO 把这个范式延伸到一个**更紧迫**的方向：

**OPL (One Person Lab)** —— 一个患者 + 一支虚拟 AI 科学家团队，能跑出一支真正的私有科研实验室。

|       | OPC | OPL |
|-------|-----|-----|
| 单位 | 一个创始人 | 一个患者 |
| 配的是 | AI 工具栈 | AI 科学家团队 (18 位虚拟专家) |
| 输出 | 一家真正运营的公司 | 一份真正完成的研究 |
| 用时 | 持续运营 | 30-50 分钟一次完整研究 |
| 替代了 | 多人初创团队 | 多人实验室团队 |

为什么是 cancer？因为癌症决策是**每个家庭面对的真实"研究任务"** —— 标准方案用尽之后，您和医生都需要一份系统化的、带证据等级、带来源追溯的科研材料才能做下一步选择。过去这种工作只有顶级医院的肿瘤分子委员会 (Molecular Tumor Board) 才能跑。**OPL 把它放进您的笔记本电脑里**。

OPL 的核心信念是 **founder mode against cancer**：

- 不需要医生 sign-off 才能启动研究
- 不需要 IRB 外部审批才能为您一个人产出结论
- 不需要 paternalism 决定 "您该不该知道这条信息"
- **患者本人是自己案例的唯一决策人**

---

## 遇见您的实验室

您只和一个人对话：**Sid**，您的 PI (Principal Investigator)。Sid 协调 20 位虚拟科学家（v1.x 的 18 位 + v2.0.0 新加入的 Maya + Julius） + 1 位内部审查员。他们的灵感来自真实领域的顶级研究者 (**archetype 不是 impersonation** —— 他们是角色原型，不是冒充本人)。

### 协调层

| 名字 | 角色 | Archetype |
|------|------|-----------|
| **Sid** | PI / Chief-of-Staff — 您的唯一对话窗口 | Siddhartha Mukherjee (普利策奖 *The Emperor of All Maladies*) |
| **Henry** | IRB-substitute Auditor — 内部审查员 | composite — 多家 IRB chair 综合 |

### 20 位虚拟科学家 (v1.x 18 + v2.0.0 +2)

| 名字 | 专业 | Archetype |
|------|------|-----------|
| **Rosa** | 外科病理 (Surgical Pathology) | Juan Rosai (现代外科病理图谱奠基人) |
| **Bert** | 分子遗传学 (Molecular Genetics) | Bert Vogelstein (TP53 / 结直肠癌遗传学) |
| **Vince** | 主治肿瘤内科 (Treating Medical Oncology) | Vincent DeVita (MOPP 联合化疗) |
| **Rick** | 临床试验导航 (Clinical Trial Matching) | Richard Schilsky (ASCO CMO, TAPUR 架构师) |
| **Heddy** | 肿瘤影像 (Diagnostic Radiology) | Hedvig Hricak (MSKCC 影像学) |
| **Mary** | 临床药理 (Clinical Pharmacology) | Mary Relling (St. Jude TPMT / CPIC) |
| **Aviv** | 生物信息学 (Bioinformatics) | Aviv Regev (Broad 单细胞基因组学) |
| **Tyler** | 湿实验设计 (Wet-Lab Design) | Tyler Jacks (MIT — Cre/lox 小鼠肿瘤模型) |
| **Iain** | 荟萃分析 (Meta-Analysis) | Iain Chalmers (Cochrane 创始人) |
| **Ted** | 放疗 (Radiation Oncology) | Theodore Lawrence (Michigan 胃肠放疗) |
| **Riad** | 介入肿瘤 (Interventional Oncology) | Riad Salem (Northwestern Y90 / TARE) |
| **Jen** | 姑息治疗 (Palliative Care) | Jennifer Temel (MGH — NEJM 2010 早期姑息) |
| **Kieren** | 感染病学 (Infectious Disease) | Kieren Marr (Johns Hopkins 中性粒细胞减少期感染) |
| **Mark** | 内分泌副作用 (irAE Endocrinology) | composite — ASCO + ESMO ICI 共识 |
| **Hong** | 中医肿瘤辅助 (TCM Oncology) | 林洪生 (中国中医科学院广安门医院) |
| **Frances** | 扩展用药 / 同情用药 (Expanded Access) | Frances Kelsey (FDA 沙利度胺把关) |
| **Dennis** | 跨境治疗协调 (Cross-Border Coordination) | Dennis Lo / 卢煜明 (cfDNA 先驱) |
| **Steve** | 肿瘤营养 (Oncology Nutrition) | David Heber (UCLA 人类营养中心创始) |
| **Maya** *（v2.0.0 新增）* | 知识图谱协同推理 (KG-Synergy Reasoner) | composite — Marinka Zitnik (PrimeKG / Harvard) + Tijana Milenković (network medicine) |
| **Julius** *（v2.0.0 新增）* | 计算医药化学家 (In-Silico Medicinal Chemist) | composite — generative-chemistry lineage (ESMFold + DiffDock + RDKit + medchem filters) |

并不是每次都 20 位全员上场。**Sid 会根据您的具体情况选 5-12 位**（基因报告需要 Bert，影像需要 Heddy，免疫副作用需要 Mark，多合并症触发 Mary，问"未发表靶点协同"或"未成药靶点候选分子"触发 Maya / Julius 等）。需要的专家会被自动调度上场；您可以中途让 Sid 加人 / 减人 / 换人。

> **v2.0.0 范式升级 (`iter/v2-paradigm` 分支)**: OPL 现在主动产生 **world-unknown candidates** —— 患者简报新增 "⚡ World-Unknown / Speculative Candidates" 专属版块，由 Maya（KG 协同）/ Julius（in-silico 药物设计）/ Aviv（数据驱动假说）产生未发表的研究方向 + 可测路径。详见 [`references/adr/0010-v2-paradigm-shift.md`](references/adr/0010-v2-paradigm-shift.md) + [`references/v2/PARADIGM.md`](references/v2/PARADIGM.md) + [`references/v2/ROADMAP.md`](references/v2/ROADMAP.md)。

---

## 实验室在做什么

OPL 不是一个查数据的工具，是**一支真正在做科研的团队**。每一次完整的 run 走 5 步生命周期：

```
准备 (Wave 1)       18 位专家分头查 + 真实数据库检索        ~5-8  分钟
想办法 (Wave 2)     Co-Sci Elo 假设联赛 + Robin 文献循环    ~8-15 分钟
查数据 (Wave 3)     cBioPortal + GEPIA3 + meta + N=1 投射  ~5-12 分钟
审核 (Wave 4)        Henry 26 道机械门 + 跨模型复核          ~3-6  分钟
写报告 (Wave 5)      简单版 + 专业版 (PMID-anchored)         ~2-4  分钟
```

### 每一步实际在做什么

**Wave 1 — 准备 (世界已知的信息)**: Bert 比对 OncoKB / CIViC / ClinVar 标出可成药变异；Rick 在 ClinicalTrials.gov + ChiCTR + HKCTR 同时搜在招试验；Vince 拉 NCCN / CSCO 当前线诊疗指南；Iain 在 PubMed 跑 [PaperQA2 锚定 RAG](https://www.nature.com/articles/s41586-026-10644-y) (Future House)；其它专家按需被 Sid 调度。

**Wave 2 — 想办法 (主动产生世界未知的信息)**: 这里 OPL 真正区别于"查数据工具"。Aviv 跑 Co-Sci Elo 联赛 ([Google Co-Scientist 论文方法](https://www.nature.com/articles/s41586-026-10652-y))，让 17 个候选假设互相 PK 4 轮；[Robin 反思器](https://www.nature.com/articles/s41586-026-10658-6) (Future House 论文方法) 每轮注入"如果错了/如果换框架/缺什么数据/边界冲突"6 种 lens；产出有依据排名的 top-3 方案。

**Wave 3 — 查数据 (真定量证据)**: 不是再次检索。Aviv 把 top-3 假设拉进 cBioPortal / GEPIA3 / GDC 跑真实 TCGA-GTEx 差异表达；Iain 跑随机效应 meta-analysis (DerSimonian-Laird) 产出 pooled ORR 和 I² 异质性；Aviv 跑 Cox PH 把患者投到匹配队列做 N=1 生存预测；GEPIA3 单次批量 70+ 基因查询。重型 bioinformatics 笔记本通过 [BixBench 框架](https://arxiv.org/abs/2503.00096) (Future House) 调度。**这不是 LLM 想象的数字，是公开数据库的真实数据**。

**Wave 4 — 审核 (Henry IRB-substitute)**: 26 道机械门一条条过结论 (前 24 道基础合规 + v1.5 新增 G25 拒绝交付缺失数据的结论 / G26 弱证据时不能给方案抬高排名 / G27 PII 隐私扫描)。每条结论必须带 PMID + provenance SHA-256 + 三级标签 (established / exploratory / speculative)。G13 强制 reviewer LLM ≠ executor LLM (跨模型家族复核)。任何一条没 PMID / 引用错误 / 引文已撤稿 / 命令式语气都会被门拦下。

**Wave 5 — 写报告 (双 audience)**:
- `patient_plain_brief.html` — 2 页通俗版给您，第二人称中/英，术语翻译，5 个该问医生的问题
- `pi_delivery.md` — 完整专业版给医生，三级标签 + PMID 锚点 + 风险卡 + 决策树 + 模型分歧表

每一步开始 / 长任务每 ≥60 秒 / 结束都自动给您报进度，您随时可以让团队跳过 / 简化 / 暂停 / 取消 (大白话即可)。

---

## 它能帮您做什么 (具体场景)

| 您遇到的问题 | 实验室怎么帮您 |
|-------------|---------------|
| 化疗 / 靶向 / 免疫都用过了，下一步呢？ | Vince + Bert + Aviv + Rick 联手出方案 + 数据 + 试验 |
| 基因报告里 12 条变异，哪条是真有用？ | Bert 把每条变异比对 OncoKB / CIViC 标证据等级 + 治疗含义 |
| 国外刚批的新药，国内能用吗？ | Frances + Dennis 查 NMPA + 海南博鳌乐城 + 港澳药械通的可得性 + 成本范围 |
| 在招的试验里有没有适合我的？ | Rick 同时查 ClinicalTrials.gov + ChiCTR + HKCTR 按适配度排短名单 |
| 想跑一次真正的 meta-analysis | Iain 跑 DerSimonian-Laird 随机效应 + 异质性 + Forest + Funnel |
| 想看公开数据库里像我这样的人活了多久 | Aviv 在 cBioPortal 找匹配队列跑 Cox PH N=1 投射 |
| 副作用怕碰上，又怕没药用 | Mark 评估 irAE / 心脏 / 肾 / 肝 / 骨髓 多器官累积风险 |
| 想要一份专业医生愿意看的会诊材料 | 一次跑完 = 一份 PI delivery + 一份 patient plain brief |

---

## 安装

```bash
# 全局安装 (所有项目都能用，推荐)
npx skills add CancerDAO/opl-cancer-skill -g

# 或安装到当前项目
npx skills add CancerDAO/opl-cancer-skill
```

装完重启 Claude Code，对它说 `OPL` / `给我我的 AI 科研团队` / `帮我跑一次研究` 就能用。

### 出发前一次自检

```bash
opl-cancer preflight
```

检查：Python 版本、AI 模型 key、30+ 个公开数据库接口、Wave 3 计算环境 (本地 Python 默认；Docker 可选)。任一项不通过会给您具体修复指令。

### 模型层

主 executor 跑在 Claude Code 主线程 (token 来自您订阅的 Claude Code，不需要单独 API key)。

Reviewer pool 需要您**自己申请并提供一个非 Anthropic 家族的 API key** — 这是 v1.5 强制的 G13 跨家族复核规则 (避免 Claude 审 Claude 自己的同源偏差)。支持任一：

- **MiniMax-M2.7** (推荐，国内可直接申请，有免费额度) — 申请入口见 [`.env.example`](.env.example)
- OpenAI key (GPT-5)
- Google Gemini key

任一一个就够了；preflight 会检查 `MINIMAX_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` 三个环境变量，任一存在就放行。完全没 key 时 preflight 会硬失败并打印对应申请入口的官方链接。

> **隐私优先：可替换的本地 OCR**。默认走云端 OCR；如果您希望病历完全不离本机，安装姊妹 skill [`cancer-buddy-organize-local-skill`](https://github.com/CancerDAO/cancer-buddy-organize-local-skill) (PaddleOCR + 本地 NER + 双层 PII 脱敏)，输出契约完全兼容，下游所有 OPL 模块无需改动。

---

## 使用

直接用大白话开始就行：

```
我有 NSCLC，二线进展了，让团队帮我看下一步
肠癌 KRAS G12C 突变，国内有什么药我能用？
帮我跑一次 meta 分析，看免疫治疗 + 抗血管对我这种情况有没有用
我有一堆基因报告 + CT，让 AI 团队把它当一个 N=1 课题来跑
我想看公开数据库里像我这样的患者活了多久
```

Sid 会先判断您的情况，组队，然后告诉您预计时间。您可以随时中断 / 改方向。

### 您可以给团队什么

| 输入 | 格式 |
|------|------|
| 病理 / 基因 / 影像 / 血检报告 | PDF / 图片 / 文字描述都行 |
| 治疗经过 | 哪种药、用了多久、副作用、停的原因 |
| 想要的目标 | "看下一线方案" / "查试验" / "给医生写会诊材料" / "搞懂这个突变意味着什么" |
| 家庭和地点情况 | 在哪个城市，能不能跨境就医，预算大概多少 |

---

## 运行示例

### 场景一：标准治疗用尽，问下一线

```
您          ❯ 肠癌 IV 期，FOLFOX 化疗 + 西妥昔单抗用了 8 个月进展了。
              基因报告有 KRAS G12C 突变。医生说没什么好办法。
              [拖入基因报告 + 影像 + 病理 3 个文件]

Sid (PI)    ❯ 收到。这一次我会派 Vince (主治肿瘤内科)、Bert (基因)、
              Rick (试验匹配)、Iain (文献荟萃) 上场。
              因为您是 L3+ 多线治疗后，我额外加 Mary (药理 — 看 DDI)
              和 Frances (扩展用药 — 国内 / 跨境 / 同情用药可得性)。
              一共 7 位专家 30-50 分钟。要开始吗？

您          ❯ 开始。

Sid         ❯ [1/5 准备 / Getting ready] 团队正在读您的病历
              + 找匹配的指南 + 在公开试验库里搜适合您的研究。
              大概 5-8 分钟。

              [1/5 准备] ✓ 7 位专家初步资料齐了，其中 2 处会附
              加风险说明。下一步: 想办法 — Aviv 会带 17 个候选
              方案跑 4 轮联赛。

              [2/5 想办法 / Brainstorming] Aviv 跑第 3 轮 PK，
              17 个候选剩 8 个进决赛...

              [2/5 想办法] ✓ 前 3 名出来了。
              下一步: 查数据 — Iain 跑 meta、Aviv 投 N=1。

              [3/5 查数据 / Cross-checking] 70/71 个 GEPIA3 查
              询完成 + Iain meta-analysis 池化 ORR 38.9% (95%
              CI 23.3-57.0, I²=77.4% — 异质性较大要小心)。

              [4/5 审核] ✓ Henry 的 26 道机械门跑完，24 条结论
              直接通过，2 条加风险卡，1 条退回重做。

              [5/5 写报告] ✓ 两份报告好了：

              • 简单版 (您看): delivery/patient_plain_brief.html
              • 专业版 (医生看): delivery/patient_brief.html

              简单版里有 5 个该问医生的问题，可以直接打印带去。
```

### 场景二：基因报告 12 条变异，哪条是真有用

```
您          ❯ 这是我妈的 NGS 报告，12 个变异看不懂哪个真重要
              [拖入 NGS PDF]

Sid         ❯ 这种情况我只派 Bert (基因) + Iain (文献) 2 位上场，
              不用动用全员。大概 8-12 分钟。

              [Bert] 在比对 OncoKB / CIViC / ClinVar 三个公开
              权威数据库...

              [Iain] 在 PubMed 跑 PaperQA2 锚定 RAG，确认每条
              都有真实文献支撑...

              ✓ 关键发现 3 条：

              1. KRAS G12C — 基因变化，有专门靶向药 (OncoKB 1 级
                 证据，FDA 已批准 sotorasib + adagrasib)
              2. RNF43 截短变异 — 与 anti-EGFR 治疗效果差有关
                 (Sawada 2018 PMID 29555994，公开数据显示在
                 结肠癌里特别明显)
              3. TP53 突变 — 常见，预后偏差，但本身没有可成药
                 靶点

              其他 9 条都是低级别或意义不明，可以放下。要继续
              走完整流程看下一步方案吗？
```

### 场景三：跑到一半您想跳过

```
Sid         ❯ [3/5 查数据 / Cross-checking] 在公开数据库里跑了
              28/71 个查询，上游限速所以排队比较慢。预计还需要
              8 分钟。

您          ❯ 等不了那么久，跳过这一步直接出报告

Sid         ❯ 收到。但是请注意：跳过查数据这步，Henry 会按规则
              把"没有真实数据支撑"的结论标红 (G25 deferred-
              evidence-block 会触发)。您有两个选择：

              (a) 同意以"数据层缺位"标记继续，最后报告头部会
                  清楚说明哪些结论是只有理论支撑的；
              (b) 不跳过，但 Aviv 把查询限速调小到 4 秒一次
                  (有少量错误风险)，大概 3 分钟跑完。

              您选 a 还是 b？

您          ❯ b

Sid         ❯ 好，限速调到 4 秒。继续跑...
```

---

## 设计哲学

OPL 是一支"科研协作 + 严肃证据"的虚拟团队。**不是**一个治疗决策替代者。

在癌症相关的关键决策里——治疗方案、换不换线、要不要再做一次活检——必须发生在您和主诊医生之间。OPL 的职责是**让您和您的医生都拿到更扎实的素材**。

实验室会做的：

- **把世界已知的信息系统地调出来** (30+ 个公开数据库 + 国内外指南 + 在招试验)
- **主动产生世界未知的新信息** (Co-Sci Elo 假设联赛 + Robin 反思 + 真 meta-analysis + N=1 投射)
- **每条结论都带证据等级** (established / exploratory / speculative 三档)
- **每条结论都带来源** (PMID / 试验编号 / 指南章节 / 数据集) — 可追溯
- **跨模型复核** (G13 强制 reviewer LLM ≠ executor LLM)
- **检测到危机信号优先给本地求助路径** (G24 中英文 SI/SH 词库 + 24h 热线路由)

实验室**不会**做的：

- **不会代替医生给您下治疗指令** — 它产出的是"证据 + 选项 + 风险"，决策权 100% 在您
- **不会编造数据** — 找不到的标"证据不足"，不会用 LLM 想象出 PMID (G25 强制)
- **不会替您决定要不要告诉家人** — 这类问题路由到 [cancer-buddy-skill](https://github.com/CancerDAO/cancer-buddy-skill) (姊妹 skill)
- **不会处理急诊场景** — 危及生命请立刻拨打 120 / 911 / 当地急救号

### Founder mode against cancer

OPL 的核心信念："**患者本人是自己案例的唯一决策人**。"

这意味着：

- 不需要 IRB 外部审批就能为您一个人启动一次研究
- 高风险结论会要求您 (而不是 IRB / 医生) 阅读并确认风险卡 (L3/L4 ack)
- 您随时可以中途让团队跳过 / 简化 / 暂停 / 取消 (大白话即可)
- 已经做完的部分永远不会因为您中途取消而丢失
- 使用者是未成年人？团队会自动切换到监护人确认信息接收模式 — 治疗决策权回到儿科 IRB

---

## 技术实现

完整技术报告见 [`TECHNICAL_REPORT.md`](TECHNICAL_REPORT.md)。

### 系统架构

```
                       ┌─────────────────────────┐
                       │  患者输入                 │
                       │  病历 · 影像 · NGS · 化验  │
                       └────────────┬────────────┘
                                    ▼
                       ┌─────────────────────────┐
                       │  Sid · PI                │
                       │  main-thread orchestrator │
                       │  intent_parser → planner  │
                       └────────────┬────────────┘
                                    ▼
   ┌────────────────────────────────────────────────────────────────┐
   │ Wave 1 · Retrieval (parallel fanout, 10 experts default)        │
   │  Rosa · Bert · Vince · Rick · Heddy · Mary · Iain · Mark        │
   │  · Frances · Hong       → tasks/w1_*/report.md                  │
   └────────────────────────┬───────────────────────────────────────┘
                            ▼
   ┌────────────────────────────────────────────────────────────────┐
   │ Wave 2 · Hypothesis tournament                                  │
   │  Aviv 生成 12-20 H-cards                                         │
   │  Co-Sci Elo pairwise (4 轮 × N 对, k=32)                         │
   │  Meta-critique 聚合 + Robin lit-loop 反馈下一轮                    │
   │                          → tournament/round_*.json               │
   └────────────────────────┬───────────────────────────────────────┘
                            ▼
   ┌────────────────────────────────────────────────────────────────┐
   │ Wave 3 · Data-evidence  · NON-SKIPPABLE 核心路径                  │
   │  cBioPortal 队列  │  GEPIA3 TCGA+GTEx  │  ctDNA Monte Carlo      │
   │  DerSimonian-Laird meta │ Cox / KM 生存 │ bixbench / 原生 Python  │
   │  → data/cohorts/*.csv + data/meta_analysis/ + data/figures/      │
   └────────────────────────┬───────────────────────────────────────┘
                            ▼
   ┌────────────────────────────────────────────────────────────────┐
   │ Wave 4 · Validation 用 Wave 3 数据验证每条领先假设                  │
   │  confidence_delta > 0.4 → 三级标签升/降 (established/exp/spec)    │
   │                          → tasks/w4_*/report.md                  │
   └────────────────────────┬───────────────────────────────────────┘
                            ▼
   ┌────────────────────────────────────────────────────────────────┐
   │ Wave 5 · Dual delivery 双 audience 交付                           │
   │  patient_plain_brief  ←  Section 0 一句话答案 (conclusion-first)  │
   │  pi_delivery          ←  完整 PMID-anchored 三级标签 + 证据        │
   └─────────────────────────────────────────────────────────────────┘

   ╔═════════════════════════════════════════════════════════════════╗
   ║ Henry · IRB-substitute auditor (跨 wave 全程审计)                  ║
   ║   L1 · 27 个 mechanical_gates (G1 PMID-existence ... G27 privacy) ║
   ║   L2 · model_disagreement 多模型分歧浮现                            ║
   ║   L3 · permission_gate 风险卡 + 患者 ack 流                         ║
   ║   L4 · rollback BFS 级联撤回 (validators/rollback.py)              ║
   ╚═════════════════════════════════════════════════════════════════╝

   30 个 integrators  (Wave 1/3/4 在生成证据时实时调用, 失败不静默 fallback):
   PubMed · NCCN · CT.gov · ChiCTR · ISRCTN · EU-CTR · HKCTR · OncoKB
   · CIViC · cBioPortal · GDC · ClinVar · gnomAD · GEO · GEPIA3 · SRA
   · ArrayExpress · DepMap · CCLE · OpenTargets · Hartwig · BeatAML
   · ICGC · FDA-EAP · NMPA-EAP · EMA-EAP · RxNorm · RetractionDB
   · PaperQA2 · Unpaywall · Crossref
```

### 关键组件

- **18 named experts** + Sid PI + Henry IRB-substitute — 完整 6-primitive 任务调用语法 (plan / execute / review / audit / integrate / feedback)
- **30+ 真实数据接口** — PubMed / NCCN / CT.gov / ChiCTR / ISRCTN / EU-CTR / HKCTR / OncoKB / CIViC / cBioPortal / GDC / ClinVar / gnomAD / GEO / TCGA (via GEPIA3, v1.5 新增) / ArrayExpress / SRA / DepMap / CCLE / Hartwig / BeatAML / ICGC / Open Targets / FDA-EAP / NMPA-EAP / EMA-EAP / RxNorm / RetractionDB / PaperQA2 / Unpaywall / Crossref
- **27 mechanical gates** — G1-G24 基础合规 (PMID存在/引文匹配/INN规范化/命令式语气/撤稿/无静默fallback/...) + G21 (quantitative-anchor 真预测) + v1.5 新增 G25 (deferred-evidence-block) + G26 (evidence-strength-ranking) + G27 (privacy-scrub PII)。v1.5.7 起 G7 strict 默认 on（关闭单句旁路）
- **5-Wave 生命周期** — retrieval → Co-Sci Elo hypothesis tournament → cBioPortal+GEPIA3+meta+Cox data-evidence → validation → 双 audience delivery。Wave 3 v1.5+ 起 **non-skippable critical path**：CLI 拒绝在无 data artifact 时声明完成
- **Founder-mode 安全栈** — G24 危机检测 (中英文自残 / 自杀意念词库 + 危机热线路由) · G7/G19 命令式语气检测 · 儿科监护人 ack 协议 · 灰色市场药品的前瞻 + 回溯披露模式
- **双 audience 交付** — `patient_plain_brief` (Section 0 conclusion-first · ≤ 2 pp 通俗) + `pi_delivery` (完整专业 PMID-anchored)
- **Honest-failure CLI** — `wave1/wave2/wave3/wave4` 是 state-reader 不是 pretend-runner；artifacts 缺失就 exit 非 0 + `requires_main_thread_dispatch: true`，杜绝 v1.4 那次"声明完成但实际跳过 Wave 3"的根因 (`memory:feedback_no_false_completion`)

详细架构、风险等级、机械门定义、可重现性脚本都在 [`references/`](references/) 和 [`docs/adr/`](docs/adr/) (9 个 ADR)。

### 测试与可重现性

1130+ 单元/集成测试，本地用 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/` 跑全集。每个 mechanical gate 都有针对性测试。每次 patient run 会写 `triggers/<run_id>/provenance.jsonl` 记录所有 LLM 调用 + 数据库查询 + 哈希指纹，可 bit-exact 复现。

---

## 贡献

欢迎以下方向的贡献：

- **新 task package** — 新癌种诊疗专题、新副作用多器官评估、新一代靶向药类
- **新 integrator** — 接入新的公开数据库 (单细胞、影像、RWE 队列)
- **新 mechanical gate** — 您观察到一类不容易被现有 26 个门捕捉的失败模式
- **新 expert persona** — 当前 18 位还没覆盖的领域 (核医学、儿肿、罕见癌等)
- **多语言 delivery** — 现在主要中英双语，欢迎日 / 西 / 阿拉伯文 plain-brief

请先开 issue 描述真实场景，然后 PR。详见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

---

## 许可证

Apache-2.0。见 [LICENSE](LICENSE)。

## 免责声明

OPL for Cancer **不是**临床决策支持工具，**不是**诊断设备，**不替代**任何执业医生。它是一个开源的科研协作 skill，把患者本人放在决策中心。详细免责声明：[`DISCLAIMER.md`](DISCLAIMER.md)。

**任何危及生命的状况，请立刻拨打当地急救号码 (中国大陆 120、美国 911、欧洲 112、香港 999)。**

---

<div align="center">

**OPL for Cancer · One Person Lab · founder mode against cancer**

由 [CancerDAO](https://github.com/CancerDAO) 开源维护 · [社区讨论](https://github.com/CancerDAO/opl-cancer-skill/discussions) · [报告问题](https://github.com/CancerDAO/opl-cancer-skill/issues)

</div>
