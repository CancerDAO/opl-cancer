<div align="center">

# OPL for Cancer.skill

> *"让每一个人都能拥有一个完整的 AI 科研团队，只为他/她一个人工作。"*

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-blueviolet)](https://claude.ai/code)
[![CancerDAO](https://img.shields.io/badge/CancerDAO-Open%20Source-orange)](https://github.com/CancerDAO)

<br>

标准治疗用尽了，医生说"再看看"，但您不想就这样等？<br>
基因报告做了一堆，看不懂哪条是真有用？<br>
听说国外有新药，但不知道怎么查、怎么对照自己的情况？<br>
想给医生准备一份扎实的会诊材料，又不知道从哪里下手？

这些事，过去要靠一支专科医生 + 病理 + 影像 + 试验匹配 + 药学 + 数据分析的团队。<br>
现在，您可以**拥有一个专为您一个人工作的 AI 科研团队**。

<br>

把您的病历、基因报告、治疗经过交给团队。它会分 **5 步**走完一轮研究：<br>
**准备 → 想办法 → 查数据 → 审核 → 写报告**。<br>
每一步都跟您报进度。结果一份给您看的简单版，一份给医生看的专业版。

[团队能做什么](#团队能做什么) · [安装](#安装) · [使用](#使用) · [运行示例](#运行示例) · [设计哲学](#设计哲学)

</div>

---

## 团队能做什么

| 您遇到的问题 | 团队怎么帮您 |
|-------------|-------------|
| 化疗 / 靶向 / 免疫都用过了，下一步呢？ | 18 位虚拟专家分头查 NCCN / CSCO / FDA / NMPA 指南 + 真实病例评估下一线方案 |
| 基因报告我看不懂哪条最关键 | 比对 OncoKB / CIViC / cBioPortal，标出可成药变异 + 抗药机制 + 临床证据等级 |
| 在招的试验有没有适合我的？ | 同时查 ClinicalTrials.gov + 中国 ChiCTR + 香港 HKCTR，按适配度排短名单 |
| 一种新药国外刚批，国内能用吗？ | 查 NMPA / 国家医保局 / 海南博鳌乐城 / 港澳药械通 的可得性和成本范围 |
| 我用过的某条线为什么没效？想看真实数据 | 在 TCGA / cBioPortal / GEPIA3 公开数据库对照您的肿瘤特征 + 跑 meta 分析 |
| 想给主诊医生准备一份扎实的二次意见材料 | 生成一份带 PMID 引用 + 风险卡 + 决策树的专业版会诊报告 |
| 副作用怕碰上，又怕没药用 | 副作用专家 (Mark) 单独评估 irAE / 心脏 / 肾 / 肝 / 骨髓多器官累积风险 |
| 想要一份能跟家人讲清楚的简单解释 | 生成 2 页的通俗版简报，专业术语翻译，5 个该问医生的关键问题 |

---

## 5 步流程

```
准备       18 位专家分头读病历 + 查指南 + 找试验           ~5-8  分钟
想办法     列出 10-20 种可能的方案，让它们互相比一比      ~8-15 分钟
查数据     拿前 3 名方案到公开肿瘤数据库做对照            ~5-12 分钟
审核       内部审查员一条条核对证据 + 标风险              ~3-6  分钟
写报告     一份给您 + 一份给医生，同时给出               ~2-4  分钟
```

每一步开始、中间 (>60 秒)、结束都自动给您报进度。结果总计 30-50 分钟。

---

## 安装

```bash
# 全局安装 (所有项目都能用，推荐)
npx skills add CancerDAO/opl-cancer-skill -g

# 或安装到当前项目
npx skills add CancerDAO/opl-cancer-skill
```

装完重启 Claude Code，对它说 `OPL` / `给我我的 AI 科研团队` / `帮我跑研究` 就能用。

### 出发前一次自检

```bash
opl-cancer preflight
```

这一步检查：Python 版本、AI 模型 key、29 个公开数据库接口、Wave 3 计算环境 (本地 Python 默认；Docker 可选)。任一项不通过会给您具体修复指令。

> **隐私优先：可替换的本地 OCR**。默认走云端 OCR；如果您希望病历完全不离本机，安装姊妹 skill [`cancer-buddy-organize-local-skill`](https://github.com/CancerDAO/cancer-buddy-organize-local-skill) (PaddleOCR + 本地 NER + 双层 PII 脱敏)，输出契约完全兼容，下游所有 OPL 模块无需改动。

---

## 使用

直接用大白话开始就行：

```
我有 NSCLC，二线进展了，想让团队帮我看下一步
肠癌 KRAS G12C 突变，国内有什么药我能用？
帮我跑一次 meta 分析，看看免疫治疗 + 抗血管对我这种情况有没有用
我有一堆基因报告 + CT，想让 AI 团队把它当一个 N=1 课题来跑
```

团队会先理解您的情况 (患者 / 家属 / 照护者)，再用 5 步流程给您一次完整的研究。

### 您可以给团队什么

| 输入 | 格式 |
|------|------|
| 病理 / 基因 / 影像 / 血检报告 | PDF / 图片 / 文字描述都行 |
| 治疗经过 | 哪种药、用了多久、副作用、停的原因，用大白话讲 |
| 想要的目标 | "看下一线方案" / "查临床试验" / "给医生写会诊材料" / "搞懂这个突变意味着什么" |
| 家庭和地点情况 | 在哪个城市，能不能跨境就医，预算大概多少 (影响推荐路径) |

---

## 运行示例

### 场景一：标准治疗用尽，问下一线

```
用户        ❯ 肠癌 IV 期，FOLFOX 化疗 + 西妥昔单抗，
              用了 8 个月进展了。现在医生说没什么好办法。
              基因报告有 KRAS G12C 突变。
              [拖入基因报告 + 影像 + 病理 3 个文件]

OPL 团队    ❯ 收到。我让团队跑一遍：18 位专家分头查 + 假设比对
              + 公开数据库对照，整个过程会分 5 步给您报进度。
              整体大概 30-50 分钟。费用大概 3-8 美元 (取决于
              方案复杂度)。要开始吗?

用户        ❯ 开始。

OPL 团队    ❯ [1/5 准备 / Getting ready] 团队正在读您的病历
              + 找匹配的指南 + 在公开试验库里搜适合您的研究。
              大概 5-8 分钟。

              [1/5 准备 / Getting ready] 已经把您的病历读完，
              正在判断这次的目标和会上场哪些专家...

              [1/5 准备 / Getting ready] ✓ 5 位专家的初步资料
              齐了，其中 2 处会附加风险说明。
              下一步: 想办法 — 团队会列 10-20 种可能的方案
              让它们互相比一比。

              [2/5 想办法 / Brainstorming] ...
              [3/5 查数据 / Cross-checking] ...
              [4/5 审核 / Double-checking] ...
              [5/5 写报告 / Writing up] ...

              ✓ 两份报告好了：

              • 简单版 (给您看的): delivery/patient_plain_brief.html
              • 专业版 (给医生看的): delivery/patient_brief.html

              简单版里有 5 个该问医生的问题，可以直接打印带去。
```

### 场景二：基因报告看不懂

```
用户        ❯ 这是我妈的二代测序报告，里面这一堆字母看不懂
              [拖入 NGS PDF]

OPL 团队    ❯ 我先帮您把基因报告读一遍。

              [1/5 准备 / Getting ready] 团队的基因专家
              (Bert) 在比对 OncoKB / CIViC / ClinVar 三个
              公开权威数据库，找出哪些变异是有药、哪些是
              抗药信号、哪些是背景噪声...

              [1/5 准备 / Getting ready] ✓ 关键发现 3 条：

              1. KRAS G12C — 一种基因变化，有专门的靶向药
                 (OncoKB 一级证据，FDA 已批准)
              2. RNF43 突变 — 与一类抗体药 (anti-EGFR) 的
                 效果差有关 (公开数据显示在结肠癌里特别明显)
              3. TP53 突变 — 这个比较常见，会让预后稍差，
                 但本身没有靶向药能直接对它做文章

              其他 12 处变异都是低级别或意义不明，可以先放下。
              要继续走完整流程看下一步方案吗？
```

### 场景三：跑到一半您想跳过

```
OPL 团队    ❯ [3/5 查数据 / Cross-checking] 在公开数据库里
              跑了 28/71 个查询，上游限速所以排队比较慢。
              预计还需要 8 分钟。

用户        ❯ 等不了那么久，跳过这一步直接出报告

OPL 团队    ❯ 收到。但是请注意：跳过查数据这步，团队的内部
              审查员 (Henry) 会按规则把"没有真实数据支撑"
              的结论标红 (因为关键证据缺位)。您有两个选择：

              (a) 同意以"数据层缺位"标记继续，最后报告头部
                  会清楚说明哪些结论是只有理论支撑、没有
                  真实数据验证的；
              (b) 不跳过，但我把查询限速调小到 4 秒一次
                  (有少量错误风险)，大概 3 分钟跑完。

              您选 a 还是 b？

用户        ❯ b

OPL 团队    ❯ 好，限速调到 4 秒。继续跑...
```

---

## 设计哲学

OPL for Cancer 是一个"科研协作 + 严肃证据"的系统，**不是**一个治疗决策替代者。

在癌症相关的关键决策里——治疗方案、换不换线、要不要再做一次活检——必须发生在您和主诊医生之间。团队的职责是**让您和您的医生都拿到更扎实的素材**。

团队会做的：

- **把世界已知的信息系统地调出来** (29 个公开数据库 + 国内外指南 + 在招试验)
- **主动产生世界未知的新信息** (在公开数据上跑 meta 分析、对照 TCGA、产出新假设)
- **每一条结论都标证据等级** (确证 / 探索 / 推测 三档，对应不同决策权重)
- **每一条结论都标来源** (PMID / 试验编号 / 指南章节 / 数据集) — 您和医生可以追溯
- **不同模型相互复核** (Henry 内部审查 + 不同 LLM 跨家族复核，避免单一模型偏差)
- **检测到危机信号会优先给您本地求助路径** (24 小时心理热线、急诊指引)

团队**不会**做的：

- **不会代替医生给您下治疗指令** — 它产出的是 "证据 + 选项 + 风险"，决策权 100% 在您
- **不会编造数据** — 找不到的就标"证据不足"，不会用 LLM 想象出 PMID
- **不会替您决定要不要告诉家人** — 这一类家庭沟通问题路由到 [cancer-buddy](https://github.com/CancerDAO/cancer-buddy-skill) (姊妹 skill)
- **不会处理急诊场景** — 任何危及生命的情况请立刻拨打 120 / 911 / 当地急救号

### 您是唯一的决策者 (founder mode against cancer)

OPL 的核心信念："患者本人是自己案例的唯一决策人。"

这意味着：

- 不需要 IRB 外部审批就能为您一个人启动一次研究
- 高风险结论会要求您 (而不是 IRB / 医生) 阅读并确认风险卡
- 您随时可以中途让团队跳过 / 简化 / 暂停 / 取消 (使用普通中文/英文就行)
- 已经做完的部分永远不会因为您中途取消而丢失

---

## 技术实现

如果您是开发者或研究者，下面是技术层的概览：

- **18 named experts** + PI (Sid) + 内部审查员 (Henry) — 完整的 6-primitive 任务调用语法
- **29 数据接口** — PubMed / NCCN / CT.gov / ChiCTR / HKCTR / OncoKB / CIViC / cBioPortal / GDC / ClinVar / gnomAD / GEO / TCGA (via GEPIA3) / ArrayExpress / SRA / DepMap / CCLE / Hartwig / BeatAML / ICGC / Open Targets / FDA-EAP / NMPA-EAP / EMA-EAP / RxNorm / RetractionDB / PaperQA2 / Unpaywall + Crossref
- **26 mechanical gates** — G1-G24 (基础合规 + 数据分析 + PI/Auditor) + G25-G27 (v1.5 新增：deferred-evidence-block / evidence-strength-ranking / privacy-scrub)
- **5-Wave 生命周期** — retrieval → hypothesis tournament (Co-Sci Elo) → data-evidence (cBioPortal + GEPIA3 + meta-analysis) → validation → delivery
- **Founder-mode 安全栈** — G24 危机检测 (中英文 SI / SH 词库 + 危机热线路由) · G7/G19 命令式语气检测 · `guardian_ack_protocol.md` 儿科情境 · `boundary_unregulated_channel_disclosure.md` 灰色市场前瞻 + 回溯模式
- **双 audience 交付** — `patient_plain_brief` (2 页通俗版) + `pi_delivery` (完整专业版，PMID-anchored)

详细架构、风险等级、机械门定义、可重现性脚本都在 [`references/`](references/) 和 [`docs/adr/`](docs/adr/)。

### 模型层

主 executor 跑在 Claude Code 主线程 (token 来自您订阅的 Claude Code，不需要单独 API key)。Reviewer pool 需要一个非 Anthropic 的外部 key (默认 MiniMax-M2.7，免费申请) — 这是 v1.5 强制的 G13 跨家族复核规则。

### 测试与可重现性

1126 单元/集成测试，本地用 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/` 跑全集 (排除真实 API 联调)。所有 mechanical gate 都有针对性测试。每次 patient run 会写一份 `triggers/<run_id>/provenance.jsonl` 记录所有 LLM 调用 + 数据库查询 + 哈希指纹。

---

## 贡献

我们欢迎以下方向的贡献：

- **新 task package** — 比如新癌种的诊疗指南专题、新副作用的多器官评估
- **新 integrator** — 接入新的公开数据库 (基因型 / 影像 / RWE 队列)
- **新 mechanical gate** — 您观察到一类不容易被现有 26 个门捕捉的失败模式
- **新 expert persona** — 当前 18 位还没覆盖到的领域 (比如核医学、儿肿、罕见癌)
- **多语言 delivery** — 当前主要是中英双语，欢迎日文 / 西班牙文 / 阿拉伯文 plain-brief 渲染

请先开 issue 描述您观察到的真实场景，然后 PR。Contribution guide 在 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

## 许可证

Apache-2.0。见 [LICENSE](LICENSE)。

## 免责声明

OPL for Cancer **不是**临床决策支持工具，**不是**诊断设备，**不替代**任何执业医生。它是一个开源的科研协作 skill，把患者本人放在决策中心。详细免责声明：[`DISCLAIMER.md`](DISCLAIMER.md)。

**任何危及生命的状况，请立刻拨打当地急救号码 (中国大陆 120、美国 911、欧洲 112、香港 999)。**

---

<div align="center">

由 [CancerDAO](https://github.com/CancerDAO) 开源维护 · [社区讨论](https://github.com/CancerDAO/opl-cancer-skill/discussions) · [报告问题](https://github.com/CancerDAO/opl-cancer-skill/issues)

</div>
