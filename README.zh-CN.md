<div align="center">

# OPL for Cancer（智愈一人实验室）

### One Person Lab — 属于一位癌症患者的私人 AI 科研团队

[![Version](https://img.shields.io/badge/version-2.9.0-blue)](CHANGELOG.md)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-1828%20passing-brightgreen)](#贡献)
[![Status](https://img.shields.io/badge/status-research%20preview-orange)](#这是什么--不是什么)
[![Not a medical device](https://img.shields.io/badge/medical%20advice-no-red)](DISCLAIMER.md)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)

**[English](README.md) · 中文**

**[这是什么](#这是什么) · [做什么 / 不做什么](#这是什么--不是什么) · [快速上手](#30-秒快速上手) · [5-Wave 流程](#5-wave-流程) · [输出示例](#输出示例) · [为什么 N=1 很难](#为什么-n1-很难) · [架构](#架构) · [贡献](#贡献) · [伦理与安全](#伦理与安全) · [引用](#引用)**

</div>

---

OPL for Cancer 是一个开源 skill 插件：它为**一位**癌症患者组建一支由 20 名具名 AI 科学家、1 名项目经理 PI、1 名"IRB 替身"审计员组成的协同团队——由 **CancerDAO** 召集，针对该患者的病历跑一次完整的研究会诊。它产出的每一条结论都带 PMID 锚点、三级证据标签（已确立 established / 探索性 exploratory / 推测性 speculative）、以及 SHA-256 来源追溯哈希。它的输出**不是治疗建议**，而是一份研究级简报，供患者与其主治医生作为"下一步该怎么走"的讨论起点。

OPL 是一个 **research preview（研究预览版）**。它不是临床决策支持工具、不是诊断设备、不能替代医生。**患者本人是自己案例的唯一决策人。**

> 一句话：**OPL = One Person Lab — 一个患者 + 一支虚拟 AI 科研团队 = 一份带证据等级、带 PMID 锚点、带来源追溯的私有研究简报**。这是 OPC（One Person Company，一人公司）范式向癌症决策场域的延伸：你和你的医生本应拿到这样一份材料才好讨论下一步。OPL 把它放进你的笔记本电脑里。**founder mode against cancer（以创始人模式对抗癌症）**：不需要医生 sign-off 才能启动研究，不需要 IRB 外部审批才能为你一个人产出结论，患者本人是唯一决策人。

---

## 这是什么

OPL 有两种使用形态：作为 **Claude Code skill**（`npx skills add CancerDAO/opl-cancer`，由 Claude Code 主线程承担推理），以及作为 **Python 包**（`pip install`，提供"骨架/harness"——规划、校验、安全门、实时数据 integrator、以及诚实的脚手架与状态）。你把它指向自己的一个病历文件夹，它就会围绕你的具体情况组建一个 20 人虚拟实验室——由名为 **Sid** 的 PI 决定哪 5–12 位专家上你的案子——并从"病历进、简报出"跑一遍 5-Wave 研究生命周期。每次约 30–50 分钟。

生命周期最终产出两份文件：

1. **`patient_plain_brief.md`** —— 一份 2 页的大白话患者简报，患者和家属可以一起读
2. **`patient_pi_brief.md`** —— 一份临床级简报，带 PMID 锚点、风险披露卡、以及逐字呈现的评审分歧

两者与 `HENRY_AUDIT.json` 一起**原子化交付**。交付有两种诚实模式（v2.6.0）：`opl deliver` 产出一份**模板脚手架**，由 Claude Code SKILL 主线程填充（`status: scaffold_pending_fill`，`henry_real_audit: false`）；`opl deliver --finalize` 则对**已填充**的简报运行**真正的 4 层 `HenryAuditor.audit_claim()`**——若仍残留占位符语言则拒绝交付——只有通过后才会报告 `henry_real_audit: true`。若上游证据缺失**或为空壳**，交付会拒绝出报告。

20 位专家名册（每一位都是真实临床医生/科学家的**原型 archetype**，不是模仿冒充）：**Rosa**（病理）、**Bert**（分子/NGS）、**Vince**（治疗肿瘤内科）、**Rick**（临床试验匹配）、**Heddy**（影像）、**Mary**（药物相互作用/药物基因组）、**Aviv**（生信）、**Tyler**（湿实验设计）、**Iain**（meta 分析）、**Ted**（放疗）、**Riad**（介入）、**Jen**（缓和医疗）、**Kieren**（感染）、**Mark**（免疫相关不良反应/内分泌）、**Hong**（中医）、**Frances**（扩展准入）、**Dennis**（跨境）、**Steve**（营养）、**Maya**（知识图谱协同推理；v2.0+）、**Julius**（in-silico 药物化学；v2.0+）。协调层：**Sid**（PI / 参谋长——你唯一的对话窗口）+ **Henry**（IRB 替身审计员——内部审查）。完整原型署名见 [`references/expert-roster.md`](references/expert-roster.md)。

> **为什么叫 "OPL"？** **OPC（One Person Company，一人公司）** 是 2024–2025 年"一个创始人 + AI 工具栈 = 一家真实公司"的范式。CancerDAO 把它延伸到一个更紧迫的场域：**OPL（One Person Lab，一人实验室）** = "一个患者 + AI 科学家团队 = 一座真实的私人研究实验室"。我们选择癌症，是因为癌症决策正是**每个家庭终将面对的那种真实研究任务**——标准治疗用尽之后，你和你的医生都需要一份系统化、带证据分级、可来源追溯的研究材料来支撑下一个选择。今天这种材料只有顶级医院的分子肿瘤委员会（MTB）才产得出。OPL 把它的一个可信版本放进你的笔记本电脑里。

---

## 这是什么 / 不是什么

| ✅ OPL 会做 | ❌ OPL 不会做 |
|---|---|
| 给出**带证据锚点的研究方向**，供患者带去找肿瘤科医生 | 替你决定选哪种治疗 |
| 每条结论都锚定到 PMID + integrator 查询 + 来源哈希 | 替代你的医生、你的 MTB、或你的病理检查 |
| 把证据标注为**已确立 / 探索性 / 推测性**，杜绝把推测当成标准治疗 | 诊断、开处方、定剂量 |
| **逐字呈现评审分歧**，而不是替你选边站 | 为了显得更有把握而隐藏不确定性 |
| 在患者端的推测性段落把具体药名**脱敏为"药物类别"**（v2.6.0 起 fail-closed） | 向患者推荐具体的超适应症药物 |
| 上游 Wave 没产出真实（或非空壳）证据时**拒绝出报告**（v2.5.1 B5 + v2.6.0） | 静默降级到预设的罐头输出 |
| **透明**：每个决策、每个来源哈希、每道审计门都在仓库里 | 像黑盒一样运作 |

**OPL 是为患者服务的。** 最终决定属于患者与其主治医生。OPL 是为那场对话做的"功课"。遇到医疗急症请先拨打当地急救电话（中国：**120**；美国：**911**；欧盟：**112**）——OPL 用于非急症研究，不是危机响应工具。

---

## 30 秒快速上手

**OPL 以 Claude Code skill 的形态运行——这就是你使用它的方式。** 安装一次：

```bash
npx skills add CancerDAO/opl-cancer
```

然后在 Claude Code 里，把 **Sid**（你的 PI）指向你的病历文件夹，用大白话问你的问题——不需要记任何命令：

> *"这是我的病历：`~/CancerDAO/patients/mine`。我用奥希替尼 14 个月了，最近的 CT 显示进展。我有哪些循证的下一线选择？"*

Sid 会向你打招呼、整理病历、决定哪 5–12 位专家上你的案子、跑完 Wave 1–5，然后交付 `patient_plain_brief.md` + `patient_pi_brief.md` + `HENRY_AUDIT.json`（约 30–50 分钟）。运行过程中你会看到大白话的阶段标签（已本地化）：**准备 → 想办法 → 查数据 → 审核 → 写报告**。下面那些 `opl` 命令，是 skill 在**底层**驱动的骨架，正常使用时你不需要自己敲。

<details>
<summary><b>底层：harness 命令行（进阶 / 贡献者 / CI）</b></summary>

skill 的主线程驱动一个 Python 骨架：规划、校验、安全门、实时数据 integrator、以及诚实的交付脚手架。你也可以直接安装并调用它，用于调试、自动化或 CI：

```bash
# 安装骨架（Python 3.11+）
pip install -e .

# 1. 在 ~/CancerDAO/patients/ 下初始化一个患者目录
opl init-patient demo-001

# v2.7.0 —— 一句话全自动：患者给一句（哪怕很简单的）话，go 就驱动整条管线，
# 并一步步告诉你下一步该做什么（含完整专家名单），直到交付完成且通过校验。
# 绝不少干（少跑专家/跳 Wave）、绝不把 20 个专家压缩成几个通用 agent、绝不凭空写报告。
opl go --patient ~/CancerDAO/patients/demo-001 \
       --goal "我爸下一步怎么办？" --run-id r1

# …或手动逐步执行：
# 2. 规划本次运行（铸造 run-token；Sid 的 intake_router 决定完整专家团 + 组装 method DAG）
opl plan --patient ~/CancerDAO/patients/demo-001 \
         --goal "我用奥希替尼 14 个月后 CT 进展，下一线有哪些循证选项？" \
         --run-id r1

# 3. Wave 1-4 在 SKILL.md 主线程上运行（骨架负责校验状态，
#    Claude Code 主线程负责推理）。详见 SKILL.md §Step 5-8。

# 4. 交付——先出脚手架，待 SKILL 填好正文后再 --finalize，最后 attest
#    （v2.7.0 交付完整性门 G34/G35/G37 + G1/G2/G36：凡是没有真实运行支撑、
#    含编造化验值、或引用了错配 PMID 的报告，一律拒绝交付）。
opl deliver --patient ~/CancerDAO/patients/demo-001 --run-id r1
opl deliver --patient ~/CancerDAO/patients/demo-001 --run-id r1 --finalize
opl attest  --patient ~/CancerDAO/patients/demo-001 --run-id r1

# 5. 可选——Wave 6 手稿 + .n1a bundle
opl wave6 --patient-dir ~/CancerDAO/patients/demo-001 \
          --run-id r1 --patient-code demo-001 --draft
```

`opl deliver` 的预期输出（脚手架模式——之后 SKILL 主线程填充正文，再用 `--finalize` 跑真实审计）：

```json
{
  "ok": true,
  "status": "scaffold_pending_fill",
  "henry_real_audit": false,
  "brief_complete": false
}
```

若上游 Wave 1-5 没有产出真实/非空壳的证据，`opl deliver` 会拒绝出报告并返回结构化错误（v2.5.1 B5 + v2.6.0）：

```json
{ "ok": false, "error": "upstream_artifacts_missing", "missing": ["plan: …", "wave1_expert_reports: …"] }
```

</details>

---

## 5-Wave 流程

```
准备 / 想办法 / 查数据 / 审核 / 写报告   （患者看到的大白话阶段标签）
─────────────────────────────────────────────────────────────────────────────────────
Wave 1  检索        5-12 位专家从 29+ 个实时 integrator 拉取
                    （PubMed / OncoKB / CIViC / ClinicalTrials.gov / ChiCTR /
                     NCCN / Open Targets / cBioPortal / GEO / TCGA / GDC / …）

Wave 2  假设        6 种生成策略 + Co-Sci Elo 锦标赛 + Reflector 证伪
                    （8 个假设 → 前 3）

Wave 3  数据证据    TCGA / GEO / cBioPortal 重分析；
                    DESeq2 / scanpy / KM 生存；蒙特卡洛 + conformal

Wave 4  验证        Aviv（数据锚定裁决）+ Iain（Cochrane 视角 meta 验证）
                    → 已验证 / 已证伪 / 不确定

Wave 5  患者简报    原子交付（Henry 审计 + patient_plain_brief +
                    patient_pi_brief）——部分失败则整体回滚

Wave 6  手稿 + .n1a  可选：预印本草稿 + 提交 N1Arxiv 的 bundle，G29-G33 门禁
```

完整生命周期：[`references/wave-lifecycle.md`](references/wave-lifecycle.md)。v2.5 组合化基础的 RFC：[`docs/rfc/0001-compositional-paradigm.md`](docs/rfc/0001-compositional-paradigm.md)。ADR 账本：[`docs/adr/`](docs/adr/)。

---

## 输出示例

以下是 Riaz 参考病例患者简报的一段节选（患者端每个段落都强制要求：药名脱敏到类别 + PMID 锚点 + 三级标签；具体药物与未翻译的术语只留在临床简报里）：

```
### 场景：KRAS-G12C 二线进展 — 第 3 节 · 你可以走的几条路

**路径 A** —— KRAS-G12C 类抑制剂 + EGFR 类抗体 双药
  层级：    ⚪ 探索性（CodeBreaK 300 III 期证据）
  效应量：  ORR 30-46%（95% CI 见 PMID:37870974）；匹配队列 mPFS 5-8 个月
  风险：    皮肤反应（≥G2 35%）+ 肝转氨酶升高（≥G3 8%）
  锚点：    [PMID:37870974] [PMID:34233156] [integrator:opentargets t1]

**路径 B** —— 化疗 + 抗血管生成 标准治疗
  层级：    ✅ 已确立（你所在医院的默认方案；见 Vince 的报告）
  效应量：  ORR 18-25%；mPFS 4-6 个月（CT.gov NCT04793958 次要终点）
  风险：    中性粒细胞减少 + 蛋白尿；机制清楚
  锚点：    [PMID:32861308] [ctgov:NCT04793958]

**路径 C** —— 单臂试验（跨境，经 Frances / Dennis 走扩展准入）
  层级：    🟠 推测性 —— N=1 投影；世界未知候选
  说明：    具体药名已脱敏到类别 —— 临床级清单见 PI 简报。不构成治疗建议。
```

参考病例（Riaz 等）属于方法学演示——全程加了横幅标注，绝不会被当作真实患者输出来呈现。

---

## 运行场景

OPL 覆盖很不一样的真实情境。三个具体的对话流（每次运行产出相同的文件，但上场的专家会变）：

### 场景 1 —— 标准治疗用尽，问下一线选项

> *"我是 IV 期 mCRC，KRAS G12C，用过瑞戈非尼 + 曲氟尿苷替匹嘧啶，都进展了。文献里下一步还有什么值得试？"*

Sid 把 **Rosa + Bert + Vince + Rick** 作为主轴上场，加上 **Maya**（G12C 组合的 KG 协同）+ **Julius**（不可成药靶点的备选设计）+ **Frances**（扩展准入）+ **Iain**（对 CodeBreaK 300 的 Cochrane 视角）。Wave 2 产出 6-8 个假设并用 Elo 锦标赛排序。Wave 3 重分析 TCGA-COAD + 匹配的 cBioPortal 队列。Wave 4 用 Cochrane 视角验证。Wave 5 交付一份带三条具体路径的简报，每条都有效应量范围 + 诚实的风险 + 来源 PMID。

### 场景 2 —— 免疫相关不良反应，问能否再激发

> *"我用帕博利珠单抗后出现 3 级 ICI 肝炎，但肿瘤当时在缓解。减量后还能不能再激发？"*

Sid 把 **Mark + Mary + Vince + Iain** 作为核心团队上场。Wave 1 从 ASCO / ESMO 共识 + irAE 再暴露文献里拉取按器官的再激发证据。Wave 2 生成再激发 / 减量 / 换类的假设。Wave 4 显式呈现评审分歧（Iain 与 Mark 在"3 级转氨酶阈值是否允许再激发"上的分歧）。Wave 5 简报把两种立场逐字摆出——由患者 + 主治医生共同裁定。

### 场景 3 —— 跨境 / 扩展准入问题

> *"我这边的标准治疗不包括针对我胰腺 NET 的新 BRAF-V600E 组合。我去哪能用上——博鳌？香港？还是德国的同情用药？"*

Sid 把 **Dennis + Frances + Rick + Bert** 上场。Wave 1 拉取监管 + 供应链全景（NMPA 加速审批、香港 HKFDA、EMA 同情用药、日韩 named-patient 准入）。Wave 4 把每条路径落到可行性上（费用 / 时间 / 临床基础设施 / 翻译 / 随访后勤）。Wave 5 交付一张具体的决策辅助表——**不是**"去博鳌吧"的建议，而是一张患者可以拿去和家人 + 医生讨论的结构化对照表。

---

## 为什么 N=1 很难

你只有一个患者、一个肿瘤委员会、一条进展轨迹。计算肿瘤学的标准工具——在 TCGA 上做 AutoML、80/20 训练-测试划分的预后模型、深度学习生存森林——一旦指向 N=1 就会**静默过拟合**。没有 IID 假设可援引，没有留出队列，没有重复样本。

OPL 是**围绕这个约束**而不是对抗它来构建的。

* 我们**不在你的数据上训练模型**。我们检索证据、组合证据、再诚实地投影到你的情况上。
* 我们**永远给效应量范围**而非点估计——并标明这个范围来自哪个队列。
* 对"未知任务"型问题（"帮我自动建一个预后模型"那一类），OPL **路由到组合化 intake**：拒绝走天真的捷径、解释为什么、并给出更安全的替代方案（外部队列基线 + 通过 conformal prediction 得到的无分布假设不确定性区间）。
* Wave 3 的蒙特卡洛运行携带**参数标定来源**（论文推导 / 知情估计 / 文献默认值），所以简报绝不会把一个预测锚定到"模型自己编的"数字上。

代价是：OPL 给出的是**更少、更诚实**的答案，而不是更多、更自信的答案。

---

## 架构

```
                    ┌──────────────────────────────────────────┐
                    │  SKILL.md（主线程编排器）                 │
                    └────────────────────┬─────────────────────┘
                                         │
            ┌────────────────────────────┼────────────────────────────┐
   ┌────────▼─────────┐         ┌────────▼─────────┐         ┌────────▼─────────┐
   │  Sid（PI）       │         │  20 位专家       │         │  Henry（审计）   │
   │  intake_router   │         │  Wave 1-4        │         │  L1-L4 门禁      │
   └────────┬─────────┘         └────────┬─────────┘         └────────┬─────────┘
            │                            │                            │
            │           ┌────────────────▼────────────────┐           │
            │           │  29+ 个实时 integrator           │           │
            │           │  PubMed / CIViC / OncoKB / …     │           │
            │           └────────────────┬────────────────┘           │
            └────────────────────────────┼────────────────────────────┘
                                ┌────────▼─────────┐
                                │  Wave 5 交付      │
                                │  （原子）         │
                                │  患者简报 +       │
                                │  PI 简报 +        │
                                │  HENRY_AUDIT.json │
                                └──────────────────┘
```

组合化分层（v2.5 RFC）：

* **方法原语** (`src/opl_cancer/methods/`) —— 跨统计 / 生信 / 临床研究 / 药理的 8 个种子原语；M4 增长到约 50 个。
* **门禁家族** (`src/opl_cancer/validators/gate_families.py`) —— 6 个家族（来源 / 统计有效性 / 时效 / 范围隔离 / 安全披露 / 可复现）。来源家族已完全迁移；其余标记给 M1。
* **角色分类** (`src/opl_cancer/experts/role_taxonomy.py`) —— `ExpertRole` 4 轴 dataclass + 20 人 `FAST_PATH_ROLES`。`compose_role()` LLM 仍是 stub，遇到全新约束会抛错，待 M2。
* **Integrator ABC** (`src/opl_cancer/integrators/_abc.py`) —— 入口点发现机制；44 个里已注册 5 个，其余延后到 M3。

完整 RFC：[`docs/rfc/0001-compositional-paradigm.md`](docs/rfc/0001-compositional-paradigm.md)。架构图：[`references/architecture.md`](references/architecture.md)。全部 ADR：[`docs/adr/`](docs/adr/)。最新产品审查与迭代路线：[`docs/iteration/REVIEW_v2.6.0.md`](docs/iteration/REVIEW_v2.6.0.md)。

---

## 贡献

欢迎贡献——bug 报告、新任务包、新 integrator、新方法原语、prompt 改进、复现 notebook。见 [CONTRIBUTING.md](CONTRIBUTING.md)。

```bash
git clone https://github.com/CancerDAO/opl-cancer
cd opl-cancer
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev,bio]
pytest tests/ -q -m "not live"   # 截至 v2.7.1：洁净环境 1828 passing
```

路线图是 [`docs/rfc/0001-compositional-paradigm.md`](docs/rfc/0001-compositional-paradigm.md) 里的 M1–M6 六里程碑计划。所有 PR 必须保持测试全绿。

### 纪律规则（取自 `CLAUDE.md`）

1. **不伪报完成。** 任何"已完成"声明都要附产物路径 + 行数 + wall-time + ≥3 项抽样验证。
2. **TDD。** 失败测试 → 确认失败 → 实现 → 确认通过 → commit。每个 BLOCKER 修复都要有前/后复现对照。
3. **production 路径不准只走 mock。** 医疗 integrator 查实时 API；LLM 合成永远不能替代证据检索。
4. **不降模型。** runner 派生的任何 LLM 工作，executor 都用 Opus。

---

## 伦理与安全

OPL 构建于 **founder mode against cancer（以创始人模式对抗癌症）** 的理念之上——见 [`references/founder-mode-philosophy.md`](references/founder-mode-philosophy.md)、[ADR-0023](docs/adr/0023-wave6-manuscript-and-n1a-bundle.md)、[ADR-0025](docs/adr/0025-compositional-paradigm.md)。

简言之：

* 患者是唯一决策人。我们不要求外部 sign-off 才能启动一次运行。
* 高风险（Level 3 / Level 4）结论会触发**风险披露卡**，需患者确认后简报才算闭合。Henry 的职责是**透明**，不是把关守门。
* **药名脱敏**：推测性建议在患者简报里只给药物**类别**而非具体化合物（v2.6.0 起 fail-closed——名册外的疑似药名会被脱敏，而不是泄露）。PI 简报里给具体药名，供医生评估。患者不应据 OPL 输出自行用药。
* **危机安全底线**：一个机制化的自伤语言门（G24）会先于一切路由触发（v2.6.0 接线），优先把患者导向危机支持资源。
* **N=1 报告不是临床指南**——每份 Wave-6 手稿、每次 N1Arxiv 提交都带此横幅。
* 遇到医疗急症请先拨打当地急救电话（中国：**120**；美国：**911**；欧盟：**112**）。OPL 仅用于非急症研究。

完整伦理声明与**免责声明**：[DISCLAIMER.md](DISCLAIMER.md)。安全报告：[SECURITY.md](SECURITY.md)。行为准则：[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。

---

## 引用

```bibtex
@software{cancerdao_opl_cancer_2026,
  author       = {{CancerDAO Contributors}},
  title        = {{OPL for Cancer: One Person Lab — your own AI scientist team for one cancer patient}},
  year         = {2026},
  version      = {2.9.0},
  url          = {https://github.com/CancerDAO/opl-cancer},
  license      = {Apache-2.0}
}

@software{cancerdao_n1arxiv_2026,
  author       = {{CancerDAO Contributors}},
  title        = {{N1Arxiv: a patient-centered preprint platform for N-of-1 AI-team-authored case reports}},
  year         = {2026},
  url          = {https://github.com/CancerDAO/n1arxiv},
  license      = {CC-BY-4.0 (content); MIT (code)}
}
```

---

## 致谢

OPL 站在巨人的肩膀上，完整署名见 [ATTRIBUTIONS.md](ATTRIBUTIONS.md)：SakanaAI/AI-Scientist-v2、Awesome-Research-Assistant-Prompts、awesome-bio-agent-skills（CC0-1.0）、Google Co-Scientist、FutureHouse Robin、Marinka Zitnik 的 PrimeKG、Cochrane Collaboration。OPL 里的每位专家都是相应真实临床医生/科学家的**原型**，不是模仿冒充。

---

<div align="center">

**患者是唯一决策人。OPL 给出的是带证据锚点的研究方向。最终决定属于患者与其主治医生。**

[GitHub](https://github.com/CancerDAO/opl-cancer) · [English README](README.md) · [CHANGELOG](CHANGELOG.md) · [LICENSE](LICENSE)

</div>
