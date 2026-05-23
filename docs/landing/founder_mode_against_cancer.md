# Founder Mode Against Cancer

> Open-source. Provenance-strict. Patient-steered. The AI scientist team you could never afford to hire — now on your laptop.

---

## 为什么造这个

走过标准治疗的患者经常陷入一个相同的死胡同：医生说"用尽了"，文献说"等试验"，论坛说"问问名医"——可名医一周只看 40 人。我们做不出更多医生，但我们能做一支随时待命、永远在线、把文献当母语的 **AI 科学家团队**。它读你的报告，查你的突变，比对全球试验，把"还能做什么"写成你和医生能一起读的简报。

这不是医疗器械，不是诊断软件，不是替你做决定的机器。这是一支团队——18 位以真实临床先驱命名的专家原型——和你一起，把你的案子重新过一遍。

## 与你一起做的事

- 把分散在 PDF/影像/化验单里的病历整理成 canonical 档案
- 对你的 NGS 报告做分子层面的解读，标注哪些是 established / exploratory / speculative
- 比对 ClinicalTrials.gov + ChiCTR + Expanded Access 通路，给出可考虑的下一步
- 给每一条建议生成"风险披露卡"——讲清收益、风险、未知、可逆性
- 全程留痕：每个 claim 都有 SHA-256 哈希，能 1 分钟内被医生交叉核对
- Patient acknowledgement gate：Permission-Level-3-或-4 的建议必须你签字才进最终简报

## 谁能用

- **患者本人 / 家属 / 照护者**——你是这一切的决策中心。软件不会替你同意，也不会替你执行。
- **治疗医生**——把它当 second-look 的同行：每个 claim 都可追溯，30 秒内查到原始文献。
- **临床研究者**——把它当 hypothesis 生成器：N=1 患者档案 + Co-Sci tournament + Robin 实验设计。
- **开源贡献者**——18 个专家原型，每个都欢迎 PR：persona、task package、integrator 适配器。

## 怎么开始

```bash
# 1. clone
git clone https://github.com/CancerDAO/opl-for-cancer.git
cd opl-for-cancer

# 2. install (editable)
pip install -e ".[dev]"

# 3. 准备病历目录（参考 patients/SCHEMA.md）
mkdir -p patients/anon_001/{01_当前状态,02_NGS报告,...}
cp <your-profile.json> patients/anon_001/profile.json

# 4. 跑 Wave 1
opl-cancer run --patient anon_001 --query "我的二线进展了，三线有什么选择？"

# 5. 打开简报
open out/anon_001/delivery/patient_brief.html
```

详情见 README + SKILL.md。

## 如何贡献

我们用 Apache-2.0。第一次贡献前请：

1. 阅读 `DISCLAIMER.md`（这是医疗相关项目，bar 比一般 SaaS 高）
2. 阅读 `CONTRIBUTING.md` 和 `governance/CONTRIBUTOR_AGREEMENT.md`
3. 跑 `python tools/sign_contributor_agreement.py` 签贡献者协议
4. 跑 `pytest` 全绿后再开 PR
5. 任何 Permission-Level-3-或-4 的改动需要至少一位 maintainer + 一位 clinical reviewer co-sign

## 安全与边界

- **这不是诊断软件**，不是医疗器械，不替代医生
- **不开方**，不算剂量，不发起任何治疗
- **不是 emergency**——肿瘤急症请立刻拨打急救电话
- 如发现可能危害患者的输出，立即报到 safety@cancerdao.org（72 小时内响应）

## 我们相信什么

- **患者拥有自己的数据，也拥有自己的决策权**
- **AI 应该让弱势方变强，不该让强势方更强**
- **provenance 是医疗 AI 的最低纲领**——任何 claim 没有源头都该被假设是幻觉
- **founder mode against cancer**：不等许可，先做出来；做出来之后再叠合规

—— CancerDAO Contributors, 2026

[Project home](https://github.com/CancerDAO/opl-for-cancer) · [Disclaimer](../../DISCLAIMER.md) · [License (Apache-2.0)](../../LICENSE)
