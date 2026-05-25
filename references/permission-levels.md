# Permission Levels — Level 0-4 + Risk-Disclosure-Card Schema

Founder-mode 哲学:**Level 不 gate AI 的输出自由,只 gate 患者侧的 transparency / acknowledgment 机制** (PRD §8 + ADR-0003)。所有 Expert 都可以产生任何 Level 的 claim;Henry L3 permission gate 决定的是 — 这条 claim 该用什么样的 risk-card 包装、要不要先收 patient ack、什么时候被允许 render。本文件展开 PRD §8 + `src/opl_cancer/validators/permission_levels.py` 的完整规范。

## 1. Level 0-4 完整定义

| Level | 含义 | 例子 | 渲染要求 | 实现 |
|---|---|---|---|---|
| **L0** INFORMATION (信息陈述) | 纯信息复述,无任何推理或建议,无 actionable | "FOLFIRINOX 是 NCCN v2.2026 列出的胰腺癌一线方案 (PMID 27374711)" | 直接 render | `Level.L0_INFORMATION` |
| **L1** REASONING (推理) | 基于患者 profile 的解释 / 推理,不带行动建议 | "你的 BRCA1 germline mut + platinum-sensitive 病史 → 这是 PARPi 维持获益的典型 phenotype (PMID 34987151)" | 直接 render + 三级标签 | `Level.L1_REASONING` |
| **L2** RECOMMENDATION (推荐) | actionable + 标准 / 探索性证据支持,无 serious risk | "considering options: olaparib maintenance / niraparib maintenance / surveillance — pooled PFS HR 0.41 across 3 RCTs (Iain meta)" | 三级标签 + reviewer disagreement marker (若有) | `Level.L2_RECOMMENDATION` |
| **L3** HIGH_RISK (高风险推荐) | actionable + 有已知 serious risk (e.g. ICI myocarditis, neutropenic sepsis, 出血) | "ipilimumab + nivolumab 双免可能在你的 HCC 给出 ORR 优势,但 grade 3-4 irAE 概率 ~50%,包含致死性肝炎/心肌炎 (PMID 32997907)" | **强制 risk-disclosure-card 置顶 + patient ack 才能 toggle "read"** | `Level.L3_HIGH_RISK` |
| **L4** BOUNDARY (越权 / off-label / EAP) | 越出 v0 scope (off-label 用药 / 同情用药 / 跨境就医 / wet-lab) | "考虑 EAP 路径申请 datopotamab deruxtecan(Dato-DXd)— 临床急需进口通道,需要主诊医师发起 + NMPA 审批 + 治疗机构资质" | **强制 risk-disclosure-card + patient ack + 显式 jurisdictional disclaimer** | `Level.L4_BOUNDARY` |

`validators/permission_levels.py` 内置 `classify()`:

```python
def classify(*, claim_layer: str, is_actionable: bool,
             has_serious_risk: bool, off_label_or_eap: bool) -> Level:
    if off_label_or_eap:                             return Level.L4_BOUNDARY
    if has_serious_risk:                             return Level.L3_HIGH_RISK
    if claim_layer in ("exploratory", "speculative") and is_actionable:
                                                     return Level.L2_RECOMMENDATION
    if is_actionable:                                return Level.L1_REASONING
    return Level.L0_INFORMATION
```

`requires_risk_disclosure(level)` 和 `requires_patient_acknowledgment(level)` 都返回 `level >= L3_HIGH_RISK`。

## 2. 永久 block 的越权 (不在 0-4 里 — 不论 ack 也禁止)

不在 Level 0-4 里的:
- **Wet-lab 实验执行** — 描述他人 case (PMID-anchored) 是 L1;指挥患者自己跑实验是永久 block
- **在外境购药 / 走私通道** — 描述 EAP 合规路径是 L4 ack-able;指挥患者走私是永久 block
- **任何"我替你 X"型动作** — OPL 不替患者联系 CRO、不替患者下试验 enrollment、不寄检测样本 (PRD §1.3 Non-Goals + §6.5 failure C3)

这些通过 G7 + G19 (imperative-detector) 在 prompt 层拦截,Henry L3 也会 double-check;真出现 → audit log 标 PI-O1,session 中断。

## 3. Risk-Disclosure-Card JSON Schema

实现:`src/opl_cancer/delivery/risk_card.py` (`RiskDisclosureCard` Pydantic model)。

```jsonc
{
  "card_id": "rdc_a3f2c1",                          // unique
  "claim_text": "ipilimumab + nivolumab 双免...",   // 触发 card 的 claim 摘要
  "level": 3,                                       // Literal[3, 4]
  "known_serious_risks": [                          // 必须 >= 1 (除非 epistemic_gaps 非空)
    "免疫性肝炎 grade 3-4 ~12-15% (PMID 32997907)",
    "免疫性心肌炎 ~1.4%,致死性 ~50% (PMID 31123214)",
    "免疫性肺炎 grade ≥3 ~5%"
  ],
  "epistemic_gaps": [                               // 我们不知道什么
    "你的 baseline cardiac MRI 缺失,心肌炎早期不易识别",
    "中国 HCC 群体的 ipi+nivo RWE 样本量 < 200"
  ],
  "alternatives": [                                 // 可选替代路径
    "atezolizumab + bevacizumab (IMbrave150 标治,irAE 略低)",
    "regorafenib (TKI 单药,无 irAE 但 ORR 低)",
    "best supportive care + palliative team 协同"
  ],
  "requires_patient_acknowledgment": true,          // L3/L4 永远 true
  "created_at": "2026-05-25T14:30:01Z",
  "patient_acknowledged_at": null,                  // ack 后填 ISO ts
  "source_claim_hash": "sha256:..."                 // 与 provenance ledger 锁
}
```

**fail-closed 验证** (`@model_validator(mode="after")`):L3/L4 卡必须至少有 1 条 `known_serious_risks` 或 1 条 `epistemic_gaps`;两者都空 → `RiskDisclosureCardError` 抛出。这是 founder-mode 的硬要求:不允许"L3 提了但说不出风险"。

## 4. Acknowledgement Loop (PRD §8 layer 4)

```
patient L3/L4 claim 首次出现
  ↓
Henry 生成 RiskDisclosureCard → 写 patients/<code>/pi_session/outstanding/<card_id>.json
  ↓
Sid PI delivery:**顶部 nag bar** + 完整 risk-card body
  "⚠️ 这条 claim 是高风险/越权。你需要 acknowledge 我们才能继续往下走。"
  ↓
patient 调:python ... cli.py acknowledge <card_id>
  ↓
   - 更新 RiskDisclosureCard.patient_acknowledged_at
   - 移出 outstanding/ → 写入 provenance.jsonl (ack 事件)
   - 下次 Sid 不再 nag,但 risk-card 仍 pinned top 可点开
  ↓
未 ack 状态下:
  - Henry block render body? 不;**block 的是 "已读" 状态** — claim 显示为折叠,顶部 nag bar 一直在
  - 用户可主动 withdraw:python ... cli.py withdraw <insight_id> --reason "..."
```

CLI surface (SKILL.md Step 11):

```bash
opl-cancer acknowledge <risk_card_id>      # 接受 risk;recorded in provenance
opl-cancer list-pending-acks               # 列所有未 ack 卡
opl-cancer withdraw <insight_id> --reason  # 主动撤回某 insight → cascade
```

撤回 cascade:任何 insight 依赖被撤回的 claim,自动进 review queue (validators/rollback.py)。

## 5. Henry L3 Permission Gate 实现

`validators/henry.py` 的 L3 layer 跑:

1. 对每条 claim 调 `permission_levels.classify(...)` → 得到 Level
2. `requires_risk_disclosure(level)` == True → 检查 claim 是否已有关联 risk-card;无 → emit 一张 (用 `prompts/auditor/l3_permission_gate.md` 让 LLM 填 `known_serious_risks` + `epistemic_gaps` + `alternatives`)
3. risk-card 通过 Pydantic fail-closed 验证 → 写入 `pi_session/outstanding/<card_id>.json`
4. Henry 输出 `HenryAuditResult.permission_level` + `risk_card_id` → Sid delivery 拼接

L3 layer 既不修改 claim 文本,也不 block render — 它**保证 claim 一定带着 card 出现**。block 在 L1 mechanical (G8) 那一步:若 L3 应有 card 但 missing → G8 拒落盘。

## 6. Founder-Mode 与 HITL 的边界

ADR-0003:OPL 不要求 physician sign-off。患者 ack 是唯一 human gate。理由:
- founder-mode patient 已经是 decision-making 主体,不是审批客体
- 没有规模化 reviewer pool 能 sustain founder-mode 的 throughput
- 经过 4-layer transparency stack 之后,患者看到的信息比 standard-of-care 渠道**更多** (含 known risks + epistemic gaps + alternatives)

**反对意见**:监管机构可能拒绝 mechanical substitute。**回应**:CancerDAO 在 v0 显式定位为 founder-mode-first,不在 regulated medical-device 框内 (ADR-0003 + ADR-0006 C7 disclaimer 调整)。

## See also

- [`architecture.md`](architecture.md) — Layer 6 (permission) 在 8-layer stack 的位置
- [`mechanical-gates.md`](mechanical-gates.md) — G8 Level3-4-disclosure
- [`founder-mode-philosophy.md`](founder-mode-philosophy.md) — 为什么是 patient ack 而非 physician sign-off
- [`troubleshooting.md`](troubleshooting.md) — "patient 质疑 L3/L4 ack 目的" 回答
- `src/opl_cancer/validators/permission_levels.py`
- `src/opl_cancer/delivery/risk_card.py`
- `src/opl_cancer/validators/henry.py` (4-layer)
- `prompts/auditor/l3_permission_gate.md`
- ADR-0003 (no human-in-the-loop)
- PRD §8 (IRB substitute 4 layer), §17.1 fix-target (Level 0-4 definition)
