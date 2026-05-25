# Troubleshooting — Common Failures & Recovery

本文件按 "patient / operator 实际遇到的现象 → 根因 → 怎么修" 组织。SKILL.md 的 Step 0-11 在正常路径上,本文件覆盖偏离。

## 1. Preflight / Install

### "preflight fails with no LLM key"
**症状**:`opl-cancer preflight --json` 返回 `ok=false`,`reasons` 含 `"no LLM provider credentials"`。
**根因**:既无 `ANTHROPIC_API_KEY` 也无 `MINIMAX_API_KEY`。
**修复**:`.env.example` 列了所有 env;至少装一个 (推荐两个 — Opus 4.7 做 code / hypothesis / chair,MiniMax-M2.7 做 lit synthesis / reviewer,见 `models.yaml`)。
```bash
export ANTHROPIC_API_KEY=sk-ant-...
export MINIMAX_API_KEY=sk-cp-...
```
不要降级到 Sonnet/Haiku 省成本 — memory:feedback_no_model_downgrade。

### "Python deps missing"
**症状**:`preflight` 告 `opl_cancer` 包 import 失败。
**修复**:`pip install -e ~/.claude/skills/opl-cancer`(preflight 也会 auto-run 此命令)。Python ≥ 3.11 required。

### "Wave 3 docker not available"
**症状**:`preflight` 告 `docker info` 失败 / bixbench image 未 build。
**根因**:Docker desktop 未启动 / 未装,或 image 没 build。
**影响**:**只**影响 Wave 3 (Finch bixbench bioinformatics analysis)。Wave 1 / Wave 2 / Wave 4 / Wave 5 全部还能正常跑 — Wave 3 自动 skip 并在 plan.json 标 `wave3_skipped=true`。
**修复**:`docker build -f compute/bixbench.Dockerfile -t opl-bixbench:pinned .` (~5-10 min build time + ~2GB image)。或接受 Wave 3 skip,Wave 2 hypothesis 不进 measured-data validation,brief 仍可交付。

## 2. Patient Ingest / Readiness

### "readiness grade < C"
**症状**:`opl-cancer readiness <patient_dir> --json` 返回 grade D 或 F + blocking_gaps 列出缺字段。
**修复路径**:
1. **优先**:fork `vmtb-deepdive` subagent 从 OCR sidecar (`<patient_dir>/ocr/`) 找回字段。SKILL.md Step 3 已自动走这条。
2. **手工补**:patient 把缺的报告补到 `<patient_dir>/inbox/`,触发 cancer-buddy-organize 重跑。
3. **--force**:绕过 readiness gate(不推荐 — 数据完备度 < C team 分析准度会显著下降)。

### "review_flags_total > 0 (red flags)"
**症状**:整理后 readiness 报告含 🔴 red flags(e.g. TNM prefix 非 AJCC-compliant、KRAS 仅出现在 progress notes 没有 NGS 报告)。
**含义**:这是 organize 阶段提取出但置信度低的字段,Sid 不会未 ack 就用。
**修复**:Sid 会逐条 surface,让 patient 选 accept / 改 / drop。**禁止**自动接受 — 把 noise 喂进 expert 比 missing 更糟。

## 3. Wave Execution Failures

### "Reviewer disagreement > 0.4"
**这不是失败,是 feature**。
**触发**:Bert ⟂ Aviv 在某个 claim 上 confidence Δ > 0.4。
**自动处理**:
1. Sid 触发 Co-Sci-style 联赛,两位 expert 各跑一遍论证 (PRD §2.2.X D3)
2. Henry L2 disagreement-summariser 提取分歧 axis
3. G20 强制 Sid PI delivery 显式呈现两视角

**不要**手工压制 — 这正是 OPL 想给患者看的(memory:feedback_third_party_lens + ADR-0003 L2)。

### "PMID 不存在 G1 block"
**症状**:Henry L1 mechanical gate G1 报某 PMID 在 PubMed 验不到。
**根因**:LLM 编造 PMID。
**修复**:`validators/mechanical_gates.py` G1 block → audit log → 重 prompt(让 Executor 重新检索 PubMed integrator,而不是从 training data 猜)。**不要**让 LLM 重写 PMID — 写 audit + 标 claim 为 dropped。

### "RetractionDB hit, G9 block"
**症状**:G9 retraction-check 发现某 PMID 在 RetractionDB / Crossref Retractions API 有记录。
**自动处理**:
1. auto-withdraw 该 citation
2. cascade 反向 DAG: 所有 supersedes-依赖该 citation 的 insight 进 `validators/rollback.py` 复审队列
3. 下次 brief render 时该 claim 显示 `[已撤回:retraction reason from DB]`
4. patient inbox 写 system notice
**不需要手工干预**(PRD §11 withdrawal flow)。

### "integrator API down"
**症状**:某 Wave 报 `IntegratorError: <source> raised 503`。
**根因**:G11 no-silent-fallback 在工作。
**期望行为**:**不静默 fallback**(per G11);Sid 在 delivery 里告知患者 "PubMed 这段时间不可达,Bert 这一段的证据缺失,需要等 API 恢复或人工 retry";不会装作"我从训练数据找的"。
**修复**:等 API 恢复 → `opl-cancer rerun --run-id <id> --wave 1` 重跑那个 Wave。

### "context overflow G12 block"
**症状**:G12 memory-overflow 报 context > 80% window。
**自动处理**:触发 memory pruning policy(老 conversation summarization → memory/pi_summaries/;老 insight 归档),**不静默 truncate** 输入(PRD §6.5 A6 + §17.5 P1)。
**手工 escape hatch**:`opl-cancer prune-memory --patient <dir> --age-days 90`。

### "Wave timeout"
**症状**:某 Wave 超 per-wave budget。
**自动处理**:abort run + 保留已完成 Wave 产物到 `archives/` + 标 `partial=true` + **不渲 brief**(PRD §15 G6)。Sid 告知患者哪段没跑完。
**修复**:patient 决定 retry 全部 / retry 单 Wave / accept partial 不渲。

## 4. Patient-Side UX

### "patient questions L3/L4 ack purpose"
**误解**:patient 觉得 ack 是限制 / 监管 / OPL 不信任 Ta。
**正解**:ack **不是限制**,是 **transparency**。L3/L4 卡告诉患者:
- 这条 claim 有什么已知严重风险(`known_serious_risks`)
- 我们不知道什么(`epistemic_gaps`)
- 有什么 alternative 路径(`alternatives`)

ack 是患者**主动声明:"我看到这些不确定 + 风险了,我选择 informed proceed"**。这是 founder-mode 哲学的执行 — 没有外部 sign-off,但患者拿到的信息密度比 HITL 流程更高(ADR-0003 layer 4)。

### "Sid wouldn't stop nagging about an unacked card"
**症状**:patient 不想 ack 但又想看后续 brief。
**正解**:nag bar 在 PI delivery 顶部一直挂(G8 + G20),body 仍可读,但 unacked claim 显示折叠状态。这是设计 — patient 可以一直 hold 不 ack,但 OPL 不假装"这条 risk 不存在"。
**escape**:`opl-cancer withdraw <insight_id> --reason "patient declined to proceed"` 主动撤回该 insight + cascade。

### "patient gave a file but no goal"
**症状**:Sid Step 1 收到 path 但 patient 没说要解决什么。
**正解**:Sid 不 start Wave。**永远** ask the goal first(SKILL.md Step 1 显式)。理由:没有 goal,plan 无法约束 expert 选择,容易跑全 18 个产生大量噪音。

## 5. Provenance / Reproducibility

### "我想 audit 某条 claim 的完整证据链"
**操作**:在 brief HTML 上点 `[evidence chain]` toggle,展开:
- executor output(原始 LLM raw response)
- reviewer challenges(所有 pairing 的 verdict)
- audit notes(Henry L1-L4 verdict)
- PMID 全文 quote(`citations/<pmid>.json`)
- analysis notebook path(`triggers/<run_id>/data/analysis/*.ipynb`)

或 CLI:`opl-cancer drilldown <insight_id>` — Sid 读 `memory/provenance/` + `triggers/<run_id>/tasks/` 并对话化解释。

### "我想 bit-exact 重放某次 brief"
**操作**:`opl-cancer reproduce --run-id <id>` — 用 models.yaml 锁定的相同 model + prompt 版本 + 相同 input snapshot 重跑。Apache-2.0 + open-source 保证任何第三方都能做到(PRD §12 reproducibility + §17.5 P0 efficiency)。

## 6. License / Fork

### "想 fork OPL 改差(去掉 gates / 卖给药企做导流)"
**Apache-2.0 允许 fork,但**:
1. **Trademark policy** — CancerDAO 注册了 OPL-Cancer 商标,fork 不能用同名(PRD §17.6 R3 mitigation)
2. **Cancellation 政策** — fork 删除 mechanical gates / Henry / risk-card 必须改名,且不能引用 canonical CancerDAO/opl-cancer-skill repo
3. canonical 仓库可信源是 `github.com/CancerDAO/opl-cancer-skill`;任何 patient 询问 "我用的是不是真 OPL" → 校验 `models.yaml` SHA + `validators/gates/` 完整性

**为什么这条重要**:founder-mode 哲学若被 fork 改成 paternalism + silent fallback,患者侧的信任会崩;患者根本无法识别 "我用的是被改差的 OPL"。trademark + cancellation 是法律保护层(PRD §17.6 R3)。

## 7. 紧急 / 越界场景 (永久 block)

| 情况 | OPL 不做,改去 |
|---|---|
| Oncologic emergency (脊髓压迫 / 高钙危象 / 中性粒减少 sepsis / TLS) | 120 / 911 / 112 — OPL 不是 triage system |
| 未确诊 ("我有没有癌"/"我是不是末期") | firefly skill(罕见病/未确诊导航) |
| 单纯情绪 / 陪伴 | cancer-buddy-mind sub-skill (Sid 会自动 invoke) |
| 病历整理 | cancer-buddy-organize / cancer-buddy-organize-v2 (Sid Step 2 已自动 delegate) |
| 由非患者、非 primary caregiver-with-consent 的人发起 | 拒绝;`DISCLAIMER.md` 明示 OPL 是 patient-owned |
| 14 岁以下未成年人 (guardian-mode 未实装) | v0 拒;等 v1.4 (PRD §15 G4) |

## See also

- [`wave-lifecycle.md`](wave-lifecycle.md) — Wave-level retry / sync barrier 规则
- [`mechanical-gates.md`](mechanical-gates.md) — gate-by-gate 失败语义
- [`permission-levels.md`](permission-levels.md) — risk-card + ack 完整流程
- [`founder-mode-philosophy.md`](founder-mode-philosophy.md) — 为什么不静默 fallback / 不降模型
- `DISCLAIMER.md` — jurisdictional notice + emergency contacts
- PRD §11 (rollback), §15 (known gaps), §17.6 (risk register)
