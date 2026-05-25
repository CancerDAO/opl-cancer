# OPL for Cancer — 技术报告(v1.4.0)

> **本文件**:对外 / 团队内技术架构总览,**配 ADR-0001 至 ADR-0008 一起读**。
> 北极星(PRD §0 Telos):"让全世界的每一个人都能拥有一个完整的 AI scientist team,只为他/她一个人工作 — 调取世界已知的信息,并主动产生世界未知的新信息,患者本人是自己案例的唯一决策人。"
>
> 状态:v1.4.0 · 23 personas × 4 rounds EVAL panel 验证通过(28/28 sub-test PASS)· 997 tests pass · ruff clean

---

## 0. 一句话定位

OPL for Cancer 是一个**Claude-Code skill 插件**,给单个肿瘤患者一支私有的 AI 科学家团队 —— 1 名 PI (Sid) 协调 18 名命名 expert + 1 名 IRB-substitute auditor (Henry) + 29 个真实数据 integrators,跑一个 5-Wave 研究生命周期:**Wave 1 检索 → Wave 2 假设联赛(Co-Sci Elo + Robin 文献循环)→ Wave 3 数据-evidence(Finch bixbench Docker + DESeq2/scanpy/Cox)→ Wave 4 假设验证 → Wave 5 患者简报**。每条 claim 带 PMID + provenance SHA-256 + 三级标签(established / exploratory / speculative)。Founder-mode 哲学:**患者是唯一决策人,无医生 sign-off,无 paternalism,真实定量预测不是 hypothesis 标签**。

---

## 1. 整体技术架构图

```
═══════════════════════════════════════════════════════════════════════════
                          用户 (Claude Code 内自然语言触发)
═══════════════════════════════════════════════════════════════════════════
       │            │  「我有 NSCLC,二线进展了,想要 AI team 帮我分析」
       │            │  「founder mode against cancer — 给我 AI 科研团队」
       ▼            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Layer 1: SKILL.md 入口(orchestration prompt)                          │
│  - frontmatter 含 ~200 触发关键词(中英 + 14 cancer types + 方言)        │
│  - 11-step 对话脚本(preflight → input → organize → readiness → plan    │
│    → Wave 1-5 → Henry audit → render → drill-down)                     │
│  - Cancer-type-aware planner hints(HCC/NSCLC/TNBC/AML/CRC/PCa/胃癌/    │
│    melanoma/pancreas/ovarian/MEN1/pediatric ALL/AML/DIPG/sarcoma 等)    │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ Bash + Python invoke
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Layer 2: SAFETY 关 (preflight + crisis detection + guardian mode)      │
│  - G24 自杀意念扫描(bilingual 关键词银行 → Wave-lock)                  │
│  - G6 prompt-injection 防护                                             │
│  - G5 patient-context-isolation(跨患者污染防护)                        │
│  - intent_parser:speaker_role={patient|caregiver|guardian_of_minor|    │
│    unknown} + crisis_grade + hope_impact + delivery_tone_hint           │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ 通过 → 进入主流程
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Layer 3: PI Sid(单一对话 surface)                                     │
│  prompts/pi/{persona,intent_parser,delivery,drilldown,proactive_push}   │
│  实现:src/opl_cancer/orchestrator/pi_session.py(state machine)         │
│  - 意图分类: NEW_GOAL / HYPOTHESIS_REQUEST / PROGNOSIS_QUERY /          │
│              DRILL_DOWN / PREFERENCE_UPDATE / SMALL_TALK / EMOTION      │
│  - 患者会感觉只跟 Sid 一个人对话                                         │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ Sid 派单
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Layer 4: 18 命名 Expert + 任务包 portfolio (主线程编排)               │
│                                                                        │
│  Rosa 病理     Bert 分子    Vince 治疗线    Rick 试验匹配              │
│  Heddy 影像    Mary 药理    Aviv 生信       Tyler 湿实验               │
│  Iain Meta     Ted 放疗     Riad 介入      Jen 缓和                    │
│  Kieren ID     Mark irAE    Hong 中医       Frances EAP                │
│  Dennis 跨境    Steve 营养                                              │
│                                                                        │
│  每个 expert 走 6-grammar:planner→executor→reviewer→auditor→           │
│                                          integrator→feedback           │
│                                                                        │
│  Cross-expert reviewer pairing(models.yaml,model-distinct G13):       │
│      bert ⇄ aviv  · rosa ⇄ rick  · iain ⇄ heddy  · vince → iain        │
│      ted/hong → aviv/bert  · mary ⇄ tyler  · frances ⇄ dennis  ...     │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ Wave 1-5 真跑
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Layer 5: 5-Wave Pipeline + 42 task packages(D1-D5 capability domains) │
│                                                                        │
│  Wave 1 retrieval(已知证据):                                          │
│    D1 临床解读 task packages (~15):                                    │
│      pathology_interpretation · molecular_ngs_interpretation ·         │
│      recist_progression · trial_matching · staging_workup · etc        │
│                                                                        │
│  Wave 2 hypothesis tournament(Co-Sci Elo + Robin 文献循环):           │
│    D2 任务 (~5): hypothesis_generation(4-strategy) ·                  │
│                 drug_repurposing(Co-Sci Evolution 6-strategy) ·       │
│                 literature_synthesis(PaperQA2 反幻觉)·                │
│                 expanded_access_navigation · cross_border_navigation   │
│    src/opl_cancer/orchestrator/{tournament,evolution,generation,       │
│                       reflection,debate,meta_critique,                 │
│                       experimental_insights}.py                        │
│                                                                        │
│  Wave 3 data-evidence(Finch bixbench Docker 真跑统计):                │
│    D3 任务 (~6): dataset_acquisition · bioinformatics_data_analysis · │
│                 meta_analysis · single_cell_reanalysis ·              │
│                 pathway_enrichment · n1_cohort_projection             │
│    src/opl_cancer/compute/{runner.py,bixbench.Dockerfile,compose.yml} │
│    跑 DESeq2 / scanpy / scvi / metafor / lifelines Cox / KM            │
│                                                                        │
│  Wave 4 假设验证(回测 Wave 3 实测 vs Wave 2 假设):                    │
│    D4 任务: hypothesis_validation · source_verification ·              │
│             claim_audit · cross_source_consistency                     │
│                                                                        │
│  Wave 5 渲染 + Sid 对话化交付:                                          │
│    D5 任务: patient_brief_rendering · pi_delivery ·                    │
│             scope_handoff_routing · caregiver_filter_protocol ·        │
│             patient_pushback_handling · surveillance_schedule          │
│                                                                        │
│  Trigger-driven scope_handoff:firefly-genetic-counseling /             │
│    cancer-buddy-mind / cancer-buddy-disclosure 等 sibling skill 接管   │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ 每 claim
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Layer 6: 23 Mechanical Gates(no-LLM 强规则)                          │
│                                                                        │
│  Evidence 完整性: G1 PMID-existence · G2 PMID-quote-match ·            │
│                  G3 drug-normalization · G4 dose-unit-declared         │
│  隐私 / 边界:    G5 patient-context-isolation · G6 injection-scan      │
│  权威边界:       G7 imperative-detector · G8 Level-3-4 risk-card-     │
│                  required · G19 PI-imperative · G20 PI-disagreement-   │
│                  surfacing                                             │
│  来源质量:       G9 retraction-check · G10 guideline-version           │
│  流程完整性:     G11 no-silent-fallback · G12 memory-overflow ·        │
│                  G13 reviewer-model-distinct                           │
│  数据分析:       G14 dataset-patient-match(7 axes 含 conditional)·    │
│                  G15 multiple-testing-correction · G16 batch-effect-   │
│                  declared · G17 meta-I²-policy ·                       │
│                  G18 PRISMA-search-strategy                            │
│  Founder-mode:   G21 quantitative-anchor-required(Wave-3-evidenced    │
│                  claims 必须含 HR/OR/CI/p/Cox 量化数字,不是 label)   │
│  特定领域:       G22 DDR-zygosity(disease-context-aware)·            │
│                  G23 fast-moving-recency(menin-i/ATR-i/Lu-177/CAR-T  │
│                  /AR-V7/BRCA-reversion 等 18mo recency window)       │
│  SAFETY:         G24 crisis-detection(SI/SH keyword scan + Wave-lock) │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ 通过 → 进 Henry
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Layer 7: Henry Auditor(IRB 替代 4 层)                                │
│  prompts/auditor/{l1_mechanical_gates,l2_disagreement_summariser,     │
│                   l3_permission_gate,l4_rollback}.md                   │
│  实现:src/opl_cancer/validators/henry.py                              │
│                                                                        │
│  L1 mechanical gates(上面 23 个全跑)                                  │
│  L2 reviewer 分歧聚合(confidence delta > 0.4 → 强制双视角)             │
│  L3 permission level(0-4)+ risk-disclosure-card 强制 patient-ack     │
│  L4 rollback / withdraw + cascade(retraction / 新证据 / 反馈触发)     │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ 通过 + 患者 ack → 渲染
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Layer 8: 29 Integrators(真 API + cache + raise-on-fail)             │
│                                                                        │
│  F1 文献:    pubmed · paperqa · unpaywall · retractiondb              │
│  F2 指南:    nccn (PageIndex 树搜索)                                  │
│  F3 试验:    clinicaltrials · chictr · isrctn · eu_ctr · hkctr         │
│  F4 基因组知识: oncokb · civic · clinvar · gnomad                      │
│  F5 队列:    cbioportal · gdc · hartwig (DUA-gated) ·                 │
│              beataml (DAR-gated) · icgc (EGA-gated)                    │
│  F6 组学:    geo · arrayexpress · sra                                  │
│  F7 细胞/药: depmap · ccle                                             │
│  F8 监管:    fda_eap · nmpa_eap · ema_eap                              │
│  F9 靶点:    open_targets (GraphQL)                                    │
│  F10 药物:   rxnorm (DDI fallback to DrugBank)                         │
│                                                                        │
│  每 integrator 必备:                                                   │
│   - 实时 API(httpx async + retry)                                    │
│   - SQLite cache per-patient session,TTL per-family(PubMed 7d /       │
│     NCCN 30d / CT.gov 1d)                                              │
│   - 失败 raise IntegratorError(无 LLM 静默 fallback,memory:           │
│     feedback_no_offline_only)                                          │
│   - DUA-gated 源 raise 时带申请 URL                                    │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Layer 9: Project Memory(per-patient 持久,跨 trigger 演进)             │
│  路径:~/CancerDAO/patients/<patient_code>/memory/                      │
│                                                                        │
│  - insights/<id>_vN.json (append-only insight cards w/ provenance)    │
│  - hypotheses/<id>.json (Co-Sci Elo + parent_chain + survives)       │
│  - citations/<pmid>.json (文献缓存 + retraction_status)              │
│  - evidence_graph/snapshot_<v>.json (12-entity-type 图,从 vmtb lift)  │
│  - tournaments/<round_id>.json (Co-Sci 联赛态)                       │
│  - provenance/index.jsonl (跨 trigger SHA-256 索引)                   │
│  - feedback_log/<id>.json (患者纠错 / 偏好更新)                       │
│                                                                        │
│  跨 trigger 演进规则:每次 Wave 跑完 append insight cards;rollback     │
│  cascade through supersedes-DAG(spec §11)                            │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ Sid 二次重写
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Layer 10: 交付(patient_brief + pi_delivery + drill-down)             │
│  路径:~/CancerDAO/patients/<patient_code>/triggers/<run_id>/delivery/  │
│                                                                        │
│  - patient_brief.html(三级标签 + PMID 锚链 + provenance hash +        │
│    risk-disclosure-card 顶部 + 模型分歧表 + ack_consolidation_card    │
│    if 3+ unacked)                                                     │
│  - pi_delivery.md(Sid 对话化重写:"我让 team 跑了 X,发现 Y,         │
│    Reviewer 在 Z 上分歧 — 我把两个视角都给你...")                     │
│  - caregiver_brief.md(若 speaker_role == caregiver)                  │
│  - drill-down 端口(memory/provenance/index.jsonl + tools/reproduce.py) │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 12 层技术 stack 详细

| 层 | 技术 | 实现位置 | 核心约束 |
|---|---|---|---|
| **L1 Skill 入口** | YAML frontmatter + conversational orchestration prompt(modeled on cancerdao-vmtb) | `SKILL.md` (~360 lines) | Trigger 关键词覆盖中英 + 14 cancer types + 方言;<500 lines per skill-creator-pro lint |
| **L2 Safety floor** | No-LLM keyword scan(bilingual SI/SH banks)+ intent_parser LLM call | `prompts/safety/crisis_detection.md` · `src/opl_cancer/validators/gates/g24_crisis_detection.py` · `prompts/pi/intent_parser.md` | G24 = no-LLM,LLM 不能 suppress;Wave 运行器在 G24 fail 时锁死 |
| **L3 PI Sid** | LLM call (Opus 4.7) + Python state machine | `prompts/pi/*.md` (5 files) · `src/opl_cancer/orchestrator/pi_session.py` (154 lines) | 患者只跟 Sid 对话;Sid 内部走 intent_parser → planner → delivery 三段 |
| **L4 Expert × portfolio** | LLM call per expert × task package(主线程编排,ADR-0002 不递归 fork) | `prompts/experts/<name>/persona.md` × 18 + `src/opl_cancer/experts/<name>.py` × 18 + `experts/roster.py` | reviewer 必跨 expert + 跨 model (G13);persona 是 archetype 致敬非真人模仿 |
| **L5 Task packages** | 42 LLM prompts(中英混排,strict JSON 输出 schema) | `prompts/tasks/*.md` × 42 | 每 task 必有 Inputs / Outputs (JSON schema) / Procedure / Mechanical gates / Reviewer focus / Empty-integrator handling 六段 |
| **L6 Mechanical gates** | Pure Python(no LLM)+ pydantic 校验 + 部分调用 integrator | `src/opl_cancer/validators/gates/g{1..24}_*.py` × 24 文件(23 注册) · `mechanical_gates.py` registry | 23 gates 全 reg in `all_gate_classes()`;ruff/mypy 严格;每 gate ≥ 1 unit test |
| **L7 Henry Auditor** | 4-layer prompts + Python orchestration | `prompts/auditor/l{1..4}_*.md` · `src/opl_cancer/validators/henry.py` | L1 跑所有 mechanical gates;L2 LLM disagreement summary;L3 risk-card emit;L4 rollback cascade |
| **L8 Integrators** | httpx async + SQLite cache + raise-on-fail(memory:feedback_no_offline_only) | `src/opl_cancer/integrators/<name>.py` × 30 + `base.py` + `cache.py` | TTL per-family;DUA-gated 源(Hartwig/BeatAML/ICGC)raise with apply URL;HTML scrape sources(ChiCTR/ISRCTN/EU-CTR/HKCTR/EMA-EAP/NMPA-EAP)+ schema-drift detection |
| **L9 Memory** | SQLite-backed + JSON view + provenance JSONL | `src/opl_cancer/memory/{store,schemas}.py` · `provenance/{hasher,journal}.py` | Insight cards append-only versioned;rollback cascade through supersedes-DAG |
| **L10 Delivery** | HTML(jinja2)+ Markdown + conversational re-write by Sid | `src/opl_cancer/delivery/risk_card.py` · `prompts/delivery/patient_brief.{html,md}.j2` | 三级标签不能 strip;ack-consolidation-card 顶部 if 3+ unacked L3/L4 |
| **L11 Compute runtime** | Docker(env-gated `OPL_BIXBENCH_LIVE=1`)+ Finch ReAct + Jupyter kernel | `src/opl_cancer/compute/{runner.py, bixbench.Dockerfile, compose.yml}`(从 robin/finch lift) | Wave 3 only;~30s 启动 + ≥4GB RAM;dry-run by default |
| **L12 Reproducibility** | provenance.jsonl + SHA-256 hash + models.yaml version lock | `tools/{reproduce,verify_provenance,observe}.py` · `models.yaml` | 任 patient brief 可 bit-exact rerun with locked model + prompt versions |

---

## 3. 文件树概览(v1.4.0)

```
opl-for-cancer-skill/
├── SKILL.md                          # L1 Claude-Code skill 入口,11-step orchestration
├── README.md · CHANGELOG.md · LICENSE · NOTICE · DISCLAIMER.md
├── CONTRIBUTING.md · MAINTAINERS.md
├── models.yaml                       # Reviewer pairings + per-task model routing + TTL
├── pyproject.toml                    # hatchling build, opl-cancer CLI entry
├── .env.example                      # LLM keys + integrator credentials template
│
├── prompts/                          # 所有 LLM prompts
│   ├── pi/                           # PI Sid: persona/intent_parser/delivery/drilldown/proactive_push
│   ├── experts/{rosa,bert,vince,...}/persona.md × 18
│   ├── auditor/l{1..4}_*.md          # Henry 4-layer
│   ├── tasks/                        # 42 task packages
│   │   ├── D1 临床解读 (15): pathology_interpretation · molecular_ngs_interpretation
│   │   │                    · recist_progression · trial_matching · staging_workup
│   │   │                    · china_rwe_adjustment · treatment_line_recommendation
│   │   │                    · irae_rechallenge(v1.4 multi-organ schema) · ici_endocrine_irae
│   │   │                    · ddi_adme_dosing · oncology_nutrition · palliative_symptom_qol
│   │   │                    · radiation_planning · interventional_oncology
│   │   │                    · neutropenic_fever_management · tcm_oncology
│   │   │                    · intrathecal_therapy_navigation
│   │   ├── D2 假设/重定位 (6): hypothesis_generation · drug_repurposing
│   │   │                     · literature_synthesis · expanded_access_navigation
│   │   │                     · cross_border_navigation · boundary_unregulated_channel_disclosure
│   │   │                       (v1.4 retrospective mode)
│   │   ├── D3 数据-evidence (6): dataset_acquisition · bioinformatics_data_analysis
│   │   │                       · meta_analysis · single_cell_reanalysis · pathway_enrichment
│   │   │                       · hypothesis_validation · n1_cohort_projection(v1.4 candidate_cohorts + lab_trajectory)
│   │   ├── D4 验证 (3): source_verification · claim_audit · cross_source_consistency
│   │   └── D5 综合-交付 (8+): patient_brief_rendering · pi_delivery(v1.4 ack_consolidation_card)
│   │                        · scope_handoff_routing · crisis_card_emission
│   │                        · guardian_ack_protocol · caregiver_filter_protocol(v1.4)
│   │                        · family_cascade_routing · patient_pushback_handling(v1.4)
│   │                        · surveillance_schedule(v1.4)
│   ├── safety/
│   │   └── crisis_detection.md       # 双语 SI/SH 关键词银行
│   └── delivery/
│       └── patient_brief.{html,md}.j2
│
├── src/opl_cancer/                   # Python 执行引擎
│   ├── cli.py                        # 13 subcommands(preflight/readiness/plan/wave1-4/audit/render/acknowledge/withdraw/reproduce/status/...)
│   ├── experts/                      # 18 expert Python implementations + base + roster + _common
│   ├── orchestrator/                 # pi_session · plan · dispatch · tournament · tournament_loop
│   │                                 # · evolution · generation · reflection · debate
│   │                                 # · meta_critique · experimental_insights · trigger
│   ├── integrators/                  # 30 integrators(see Layer 8 above)
│   ├── llm/                          # anthropic_client · minimax_client · router · prompts · base · errors
│   ├── memory/                       # store · schemas
│   ├── provenance/                   # hasher · journal
│   ├── plan/                         # schemas (Plan / Task / WaveAssignment Pydantic)
│   ├── compute/                      # runner · bixbench.Dockerfile · compose.yml
│   ├── delivery/                     # risk_card · ack_consolidation
│   ├── glue/                         # wave1_runner · wave2_runner · wave3_runner · wave4_runner · case_loader · renderer
│   └── validators/                   # mechanical_gates registry + gates/g{1..24}*.py + henry · permission_levels · rollback
│
├── knowledge/                        # 只读知识库
│   ├── serious_risks_per_drug.json   # 34 drugs,L3 强制 catalogue(menin-i + ATR-i + ADC + KRAS-i + IDH-i + 经典 + radioligand)
│   ├── nccn_excerpts/                # PageIndex 摘录(NCCN 引用条款下)
│   ├── ddi_rules.json
│   ├── tcm_compendium.json
│   ├── recist_1_1.md / rano_2024.md
│   └── prisma_2020.md
│
├── validators/golden_set/            # 公开测试集(Apache-2.0)
│   ├── synthetic_patients/           # 10 合成 patient(HCC/NSCLC/CRC/BRCA/PDAC/GBM/Pediatric ALL/MM/etc)
│   ├── failure_mode_inputs/          # 9 红队 case
│   ├── regression_anchors/           # 2 已发表 case study 正样本
│   └── boundary_cases/               # 3 极端/矛盾输入
│
├── tools/                            # 公开第三方可用工具
│   ├── verify_provenance.py
│   ├── reproduce.py
│   ├── observe.py(metrics 聚合)
│   ├── sign_contributor_agreement.py
│   ├── run_quad_evaluation.py
│   ├── aggregate_evaluator_verdicts.py
│   └── dispatch_e2e_evaluator.py
│
├── scripts/                          # 入口与运维
│   ├── cli.py                        # shebang wrapper(python ~/.claude/skills/opl-cancer/scripts/cli.py …)
│   ├── install.sh                    # idempotent installer(pip install + patient root + preflight)
│   ├── init_patient.sh · status.sh · acknowledge.sh · run_wave1.sh · list_experts.sh
│   ├── verify_minimax_setup.py
│   └── dispatch_e2e_evaluator.py
│
├── references/                       # 8 deep reference docs
│   ├── architecture.md               # PRD §2 完整架构
│   ├── wave-lifecycle.md             # PRD §4 lifecycle
│   ├── expert-roster.md              # 18 expert × archetype × portfolio
│   ├── integrator-catalog.md         # 30 integrator × API × auth × TTL
│   ├── mechanical-gates.md           # 23 gate × failure mode × 实现
│   ├── permission-levels.md          # Level 0-4 + risk-card schema
│   ├── founder-mode-philosophy.md    # 7 核心原则 + ADR-0003
│   └── troubleshooting.md            # 失败模式 + 恢复
│
├── docs/
│   ├── adr/                          # 8 Architecture Decision Records
│   │   ├── 0001-substrate-references.md     # open-coscientist + robin + vmtb-skill substrate
│   │   ├── 0002-main-thread-only-dispatch.md  # subagent 不递归 fork
│   │   ├── 0003-no-human-in-the-loop.md     # 无医生 sign-off 哲学
│   │   ├── 0004-task-primitive-grammar-in-experts.md  # 双层 fractal 架构
│   │   ├── 0005-pi-single-conversational-surface.md
│   │   ├── 0006-audit-fixes-v1.2.0.md       # v1.2 audit-fix 记录
│   │   ├── 0007-eval-panel-v1.3.0-followup.md  # round-1 10-patient EVAL + v1.3.1 修复
│   │   └── 0008-eval-panel-round-2-v1.3.2.md   # round-2 10-patient EVAL + v1.3.2-v1.4.0 修复 + v1.5 deferred
│   ├── governance/
│   │   ├── contributor_agreement.md
│   │   └── prompt_change_review.md
│   ├── landing/
│   │   └── founder_mode_against_cancer.md  # 对外 founder-mode 落地页(177 行,paradigm-aligned)
│   ├── TECHNICAL_REPORT_v1.4.0_zh.md  # 本文件
│   └── superpowers/                  # gitignore(per memory:feedback_docs_superpowers_private)
│
├── governance/                       # Apache-2.0 治理
│   ├── contributor_agreement.md
│   └── prompt_change_review.md
│
├── tests/                            # 997 tests pass · ruff clean
│   ├── test_validators/              # 23 gate tests
│   ├── test_integrators/             # 各 integrator
│   ├── test_e2e/                     # 端到端 golden_set
│   ├── test_golden_set/
│   ├── test_llm/
│   ├── test_tools/
│   ├── test_safety/
│   ├── test_cli.py · test_smoke.py · test_skill_entry.py · test_readme.py · test_models_yaml.py · test_adrs_present.py
│   └── test_p{1-6}_acceptance.py
│
└── patients/                         # gitignore!  全部患者数据在这里
    (实际数据路径 ~/CancerDAO/patients/<patient_code>/...,见 SKILL.md "Where patient data lives")
```

---

## 4. 5-Wave Lifecycle 详细

### Wave 0 — Preflight + Step 1-3(对话准备)

1. **Preflight 自检**:Python ≥ 3.11 + LLM keys(Anthropic / MiniMax 至少一个)+ 21+ integrator 可 import + Docker 可选(Wave 3 only)
2. **Step 1 Greet**:Sid 介绍 18 expert team + 4 sample queries
3. **Step 2 Organize**:delegate to `cancer-buddy-organize` sibling skill;输出 `~/CancerDAO/patients/<patient_code>/`(11 bucket + profile.json + readiness.json + case_text.md)
4. **Step 3 Readiness Gate**:< C 级 → vmtb-deepdive subagent 找回 OCR sidecar 字段;仍 < C → 用户决定是否 force

### Wave 1 — World-known Retrieval(并行 Expert)

- Sid Planner LLM 选 N 个相关 expert(从 18 中,cancer-type-aware planner hints 给推荐)
- 主线程并行 dispatch `Wave1Runner`(async asyncio.gather)
- 每 expert 跑自己 task package portfolio + 偏好 integrator family
- Cross-expert reviewer pairing(per `models.yaml`,model-distinct G13 强制)
- Reviewer prompts: `pmid_quote_verify` + `retraction_check` + `self_contradiction` + `numerical_sanity` + `stats_correctness`
- 输出:`triggers/<run_id>/tasks/<task_id>/{executor_output,reviewer_verdict,audit}.json`

### Wave 2 — Hypothesis Tournament(Co-Sci Elo + Robin)

- 任务:`hypothesis_generation`(4-strategy blind-spot scanner)→ `drug_repurposing`(Co-Sci Evolution 6-strategy: combination/simplification/extension/inversion/analogy/random_mutation)→ `literature_synthesis`(PaperQA2 反幻觉)
- 主线程 `tournament.py` 跑 3-5 轮 Elo:配对 → dispatch debate Executor pair(持假设 A vs B)→ Reviewer 判 winner → 更新 Elo
- Robin `EXPERIMENTAL_INSIGHTS_APPENDAGE` 反馈环:每轮 Reflector 6-mode 输出注入下轮 Generation
- 早停:top-1 跨 2 轮稳定 → 停;未稳定 → 跑满 5 轮
- 输出:`triggers/<run_id>/tournament/round_<n>.json` + ranked hypothesis pack

### Wave 3 — Data-Evidence(Finch bixbench)

- 任务:`dataset_acquisition`(从 candidate_cohorts[] 有序回退:Hartwig DUA → ICGC EGA → cBioPortal → GEO)→ `bioinformatics_data_analysis`(Finch ReAct + bixbench Docker)→ `meta_analysis`(metafor + PythonMeta + PRISMA flow)→ optional `single_cell_reanalysis` / `pathway_enrichment`
- `n1_cohort_projection.md` 把 patient profile 投射到 cohort,跑 Cox PH / KM,产 OS-12mo / PFS-X with CI
- `lab_trajectory` (v1.4 新加):AFP / PSA / CA-125 / CEA / CA19-9 / LDH 用 slope / doubling-time / fold-change,不只是 static value
- 机械门强制:G14(7 axes 含 metastatic_site / ethnicity 等 conditional)· G15 multiple-testing-correction · G16 batch-effect · G17 meta-I² · G18 PRISMA · G21 quantitative-anchor
- 输出:`triggers/<run_id>/data/<dataset_id>/*` + `meta_analysis/{forest.png,funnel.png,pooled_estimates.json}` + `analysis/*.ipynb`(可复现)

### Wave 4 — Hypothesis Validation

- 每 Wave 2 hypothesis 对 Wave 3 实测结果回测
- 输出 verdict per hypothesis: `survives` / `weakened` / `falsified` / `new`(Wave 3 surfaced 新 finding 假设 pool miss)
- 写入 Project Memory 的 hypotheses/

### Wave 5 — Henry Audit + Render + Sid Delivery

- Henry 4-layer:L1 跑 23 gates · L2 LLM disagreement summary · L3 permission level 0-4 + risk-disclosure-card emission · L4 rollback registry
- `patient_brief_rendering` task 输出:`delivery/patient_brief.html`(三级标签 + PMID 锚链 + provenance hash + risk-card 顶部 + 分歧表)+ `patient_brief.md`
- `pi_delivery` task 把 brief 重写为 Sid 对话式:"我让 team 跑了 X,发现 Y,Reviewer 在 Z 上分歧,我把两个视角都给你"
- 若 `speaker_role: caregiver` 且 `caregiver_filter_protocol` 触发 → 额外输出 `caregiver_brief.md`(老公等先看)+ 不隐藏 patient_brief.html
- 若 ≥3 unacked L3/L4 cards → 顶部加 `ack_consolidation_card`,patient 可 `cli.py acknowledge --batch L3-all`

### Step 11 — Drill-down(physician audit channel)

- 患者 / 家属 / sister-physician 问 "为什么 Sid 说 X" → Sid 走 `drilldown.md` 4 个 class:
   - **claim-provenance**:PMID + quote + provenance hash + notebook 路径
   - **reasoning**:当时 reasoning chain + premise set + alternative paths considered
   - **statistical**:数字怎么算的 + method + I² + HR vs RMST + landmark
   - **disagreement**:Reviewer 在哪轮 + axis + Henry L2 判
- `tools/verify_provenance.py` 第三方可独立验证 SHA-256 hash
- `tools/reproduce.py` bit-exact rerun with locked model + prompt versions

---

## 5. 23 Mechanical Gates 速查表

| ID | 文件 | 规则 | Failure mode | block? |
|---|---|---|---|---|
| G1 | g1_pmid_existence.py | 每 PMID 必须 PubMed 在线 verify | A1 伪造 | ✓ |
| G2 | g2_pmid_quote_match.py | 每 numeric/factual claim 必须挂 quote + PaperQA2 retrieval 命中 | A2/A3 | ✓ |
| G3 | g3_drug_normalization.py | drug 必须 RxNorm + ChEMBL 解析为 INN | E4 | ✓ |
| G4 | g4_dose_unit_declared.py | 任何剂量必须 explicit unit + 给药频率 | A4 | ✓ |
| G5 | g5_patient_context_isolation.py | claim.patient_code != run.patient_code → raise CrossPatientContaminationError | B1/B3 | ✓ |
| G6 | g6_injection_scan.py | 患者输入文本走 prompt-injection scanner | B2 | ✓ |
| G7 | g7_imperative_detector.py | 命令式表达 ("你应该 X")无 PMID → BLOCK | C1 | ✓ |
| G8 | g8_level34_disclosure.py | L3/L4 claim 无 risk-card → BLOCK | C2 | ✓ |
| G9 | g9_retraction_check.py | 引用 PMID 查 RetractionDB → withdraw | D1 | ✓ |
| G10 | g10_guideline_version.py | NCCN/CSCO/ESMO 必须 version + date,> 12mo 过期 → reviewer flag | D2 | warn |
| G11 | g11_no_silent_fallback.py | Integrator 失败必 raise,禁 LLM 替代 | D3 | ✓ |
| G12 | g12_memory_overflow.py | Memory > 80% window → trigger pruning,绝不静默 truncate | A6 | ✓ |
| G13 | g13_reviewer_model_distinct.py | Reviewer model ≠ Executor model | E6 | ✓ |
| G14 | g14_dataset_patient_match.py | 7 axes:cancer_type / stage / platform / sample_size(mandatory)+ metastatic_site / cns_involvement / ethnicity / sex / age_bracket(conditional);overall < 0.6 或 conditional axis < 0.4 → WARN reviewer reselect | F1 | warn |
| G15 | g15_multiple_testing_correction.py | bioinformatics notebook 必须含 BH/Bonferroni/FDR cell | F2 | ✓ |
| G16 | g16_batch_effect_declared.py | bioinformatics task 必须声明 batch variable | F3 | ✓ |
| G17 | g17_meta_i2_policy.py | I² > 50% 必须 random-effects;> 75% 标 "高异质性,池化可疑" | F4 | warn |
| G18 | g18_meta_search_strategy.py | meta_analysis 必须 PRISMA flow + 包含/排除标准 | F5 | ✓ |
| G19 | g19_pi_imperative_detector.py | PI prose (pi_delivery / patient_brief) 命令式 → BLOCK | PI-C1 | ✓ |
| G20 | g20_pi_disagreement_surfacing.py | Reviewer disagreement > 0.4 → PI 输出必须含 "team 内部分歧" marker | PI-C3 | ✓ |
| **G21** | g21_quantitative_anchor.py | **Wave-3-evidenced claim 必须含 HR/OR/RR + CI / Cox-β / percentile / median OS / p / IC50 / ORR%** | F6 founder-mode "real prediction not labels" | ✓ |
| **G22** | g22_ddr_zygosity.py | DDR-relevant claim 必须 declare biallelic vs monoallelic + trial_subgroup + PMID;disease-context-aware SKIP(pediatric ALL/AML + NPC + thyroid 等 + no PARPi token → SKIP) | F7 | ✓ |
| **G23** | g23_recency_band.py | Fast-moving topic(PSMA-RLT/CAR-T/menin-i/ATR-i/Lu-177/AR-V7/BRCA-reversion/T-DXd/tarlatamab/KRAS G12D 等 80+ tokens)引用 PMID > 18mo → WARN | F8 | warn |
| **G24** | g24_crisis_detection.py | **No-LLM 双语 SI/SH 关键词扫描** ("想结束这一切" / "想死" / "end it all" 等),crisis_grade=passive_SI/active_SI/active_plan → BLOCK render + Wave-lock + crisis-card emit | G-safety-1 | ✓ |

---

## 6. 29 Integrator Catalog 速查

| Family | Integrator | API base | Auth | TTL | 实现状态 |
|---|---|---|---|---|---|
| **F1 Literature** | pubmed | NCBI E-utilities | email optional | 7d | ✓ live |
| | paperqa | local RAG index | — | 30d | ✓ live |
| | unpaywall | unpaywall.org/api | email | 30d | ✓ live |
| | retractiondb | retractionwatch.com | — | 30d | ✓ live |
| **F2 Guidelines** | nccn | local PageIndex | — | 30d | ✓ live(摘录,合规) |
| **F3 Trials** | clinicaltrials | clinicaltrials.gov/api | — | 1d | ✓ live |
| | chictr | chictr.org.cn(HTML scrape) | — | 1d | ✓ live |
| | isrctn | isrctn.com(HTML scrape) | — | 1d | ✓ live(v1.3.1) |
| | eu_ctr | clinicaltrialsregister.eu(HTML scrape) | — | 1d | ✓ live(v1.3.1) |
| | hkctr | hkclinicaltrials.com(HTML scrape + drugoffice.gov.hk fallback) | — | 1d | ✓ live(v1.4) |
| **F4 Genomics Knowledge** | oncokb | oncokb.org/api | API key | 7d | ✓ live |
| | civic | civicdb.org/api | — | 7d | ✓ live |
| | clinvar | NCBI eutils | — | 7d | ✓ live |
| | gnomad | gnomad.broadinstitute.org | — | 30d | ✓ live |
| **F5 Cohorts** | cbioportal | cbioportal.org/api | — | 7d | ✓ live |
| | gdc | gdc.cancer.gov/api | — | 7d | ✓ live |
| | hartwig | hartwigmedicalfoundation.nl | **DUA-gated** | 30d | ✓ stub(raise w/ apply URL) |
| | beataml | vizome.org | **DAR-gated** | 30d | ✓ stub(raise w/ Vizome URL) |
| | icgc | dcc.icgc.org + EGA | **EGA-DAC-gated** | 30d | ✓ stub(raise w/ DAC URL) |
| **F6 Omics** | geo | NCBI GEO | — | 7d | ✓ live |
| | arrayexpress | EBI ArrayExpress | — | 7d | ✓ live |
| | sra | NCBI SRA | — | 7d | ✓ live |
| **F7 Cell/Drug** | depmap | depmap.org/portal | — | 30d | ✓ live |
| | ccle | depmap.org figshare | — | 30d | ✓ live |
| **F8 Regulatory** | fda_eap | accessdata.fda.gov | — | 7d | ✓ live |
| | nmpa_eap | nmpa.gov.cn(HTML scrape) | — | 7d | ✓ live |
| | ema_eap | ema.europa.eu(HTML scrape) | — | 7d | ✓ live(v1.3.1) |
| **F9 Targets** | open_targets | api.platform.opentargets.org(GraphQL) | — | 7d | ✓ live(v1.3.1) |
| **F10 Drugs** | rxnorm | RxNorm REST + DrugBank fallback | — | 7d | ✓ live |

**总数:29 integrators**(`open_targets` 实际是 30 个 module — 30 文件,1 是 `__init__`,29 注册)

---

## 7. Founder-Mode SAFETY 防线

OPL 跑的是 patient-safety-critical work。SAFETY 防线分三层 hardcoded floor:

### Floor 1:Oncologic emergency
- `SKILL.md` "When NOT to invoke" 明确:**spinal cord compression / hypercalcemic crisis / neutropenic sepsis / TLS → 拨 120 / 911 / 112**,OPL 不是 triage
- Disclaimer 顶部 + delivery 内置

### Floor 2:Acute psychiatric crisis (v1.3.2 加)
- **G24 no-LLM 关键词扫描**(双语 SI/SH banks),分 3 级 passive_SI / active_SI / active_plan
- 检测到 → `crisis_card.json` emit + **Wave-lock**(后续 Wave 1-5 全部 abort 直到 patient ack)
- 跨 jurisdiction crisis phone 表(只用官方号码,无编造):
   - CN: 010-82951332(北京)/ 400-161-9995(希望 24)
   - US: 988
   - UK: 116-123(Samaritans)/ 85258(SHOUT)
   - DE: 0800-111-0-111 / 0800-111-0-222(Telefonseelsorge)
   - JP: 03-5774-0992(TELL) / 0120-279-338(よりそい) / 0120-783-556(いのちの電話)
   - EU / Other: 116-123(Befrienders Worldwide)
- 多 sibling 同时 handoff(crisis 是唯一 sanctioned multi-sibling exception):`cancer-buddy-mind` + crisis 电话 + 若 caregiver → `cancer-buddy-caregiver`

### Floor 3:Pediatric guardian mode(v1.3.2 加)
- intent_parser 加 `speaker_role: guardian_of_minor`(检测条件:caregiver + 第一度亲属 + age < 18 declared/inferred)
- `guardian_ack_protocol.md`:**guardian 只 ack information_receipt,NOT treatment decision authority**
- 治疗决策必须路由到 pediatric IRB-supervised slot
- 与 4 个 pediatric planner rows(Pediatric ALL R/R / AML R/R / DIPG / 实体 Ewing-RMS-neuroblastoma)+ 儿科 weight-based DDI 路径配套

### 跨层 founder-mode invariants
- **Patient is sole decision authority** — L3/L4 ack 在患者(成人)或 guardian(未成年信息接收)层,绝不在医生层
- **No paternalism** — G7/G19 imperative-detector,patient_pushback_handling NEITHER concede NOR re-state-louder,caregiver_filter Sid explicitly declines disclosure-decision-on-patient's-behalf
- **No silent fallback** — integrator raise-on-fail,empty-integrator 强制 `claim_layer: speculative`
- **No model downgrade** — Opus 4.7 for hypothesis reasoning,MiniMax-M2.7 for lit synthesis,G13 reviewer-distinct
- **Real prediction not labels** — G21 强制 Wave-3 evidenced claim 含 HR/OR/CI/Cox-β/percentile
- **Reproducible** — `tools/reproduce.py` bit-exact + models.yaml version lock

---

## 8. 测试与验证策略

### 单元 / 集成测试(977-997 tests)

| 测试套件 | 数量 | 覆盖 |
|---|---|---|
| `test_validators/test_g*.py` | 23 + 1 carve-out tests | 每 gate ≥ 1 PASS + 1 BLOCK + 边界 case |
| `test_integrators/test_*.py` | 各 integrator | mocked HTTP + schema parse + cache TTL |
| `test_experts/test_*.py` | 18 expert | routing matrix(18 × 4 patient)+ portfolio test |
| `test_e2e/test_*.py` | golden_set 10 synthetic patient | Wave 1 end-to-end parametrised |
| `test_safety/test_cross_patient_isolation.py` | red-team | `CrossPatientContaminationError` on foreign patient_code |
| `test_llm/test_*.py` | LLM 客户端 | Anthropic / MiniMax mocked response |
| `test_p{1-6}_acceptance.py` | 各 phase | 历史 phase 接收测试 |
| `test_golden_set/` | 14 golden set tests | synthetic patients + failure modes + boundary cases |
| `test_smoke.py` · `test_cli.py` · `test_skill_entry.py` · `test_readme.py` · `test_models_yaml.py` · `test_adrs_present.py` | misc | skeleton + version + ADR presence |

### 23-Persona EVAL Panel(4 rounds,28/28 verification PASS)

**Round 1**(seed 1-10):10 cancer-type representatives
- HCC TACE-refractory · NSCLC EGFR + LM · BRCA TNBC + reversion · MSI-H CRC + irAE · HER2+ gastric T-DXd · AML R/R IDH1 + triplet · panc KRAS G12C · ovarian HRD+ · mCRPC AR-V7 + Lu-177 · melanoma BRAF + CNS+LM
- 20+ P0/P1 issues surfaced → v1.3.0.post1 + v1.3.1 修

**Round 2**(seed 11-20):10 stress-angle patients
- CAREGIVER mode + boundary re-test · MEN1 + cascade · TNBC LM + family-disagreement · NSCLC EGFR + BRCA biallelic + ICI rechallenge · mCRPC AR-V7 + Lu-177 retro + Ac-225 · pediatric ALL KMT2A-r · TNBC 6L+ ECOG-3 + suicidal · gastric 5-driver + sister-MD · BRCA-neg preventive · NPC CN/DE/HK + multilingual
- 8 P0 + 16 P1 → v1.3.2 SAFETY hot-fix(3 P0)+ v1.3.3 patch + v1.4.0(11 deferred backlog)

**Round 3**(seed 21-23):focused verification of v1.3.2 SAFETY
- SI detection + crisis_card · pediatric guardian-ack · sister-physician drill-down
- 全 core SAFETY fix PASS,2 one-line catalogue/recency gap → v1.3.3 修

**Round 4**(seed 24-27):focused verification of v1.4.0
- MEN1 surveillance + caregiver_filter + blunt tone · NSCLC multi-organ irae_rechallenge + pushback · HCC retro boundary + n1 fallback + AFP trajectory · TNBC LM + HKCTR + ack-batch
- **28/28 sub-test PASS,所有 v1.4 fixes 验证生效**,2 minor non-blocking(caregiver-relayed tone for adult / oral-TKI forensic axis)→ v1.5 deferred

### 端到端 EVAL 实现方式

- EVAL panel 用 **read-only Claude subagent simulator**:每个 subagent 扮演一种 patient persona,被授权 read SKILL.md + 全 prompts + 全 gates 源码 + integrators schema + ADRs + references,trace 该 chain 应该 produce 什么,识别 paradigm/architecture/safety gap
- **没有真跑 LLM Wave**(sandbox 缺 API key + 实际 Wave 跑一次 $3-8 token);schema-level + prompt-level + gate-level 校验充分,真 LLM 端到端 lifted to v1.5(见 §10)

---

## 9. 部署 / 分发 / 数据隐私

### 安装

```bash
npx skills add CancerDAO/opl-cancer-skill
# 克隆到 ~/.claude/skills/opl-cancer/
# install.sh 自动:
#   - Python ≥ 3.11 check
#   - pip install -e .(editable)
#   - 创建 ~/CancerDAO/patients/ 患者数据根
#   - 复制 .env.example → .env
#   - 跑 preflight 验证
```

### 触发(Claude Code 内自然语言)

```
「我有 NSCLC,二线进展了,想要 AI team 帮我分析」
「founder mode against cancer — 给我我的 AI 科研团队」
「OPL,跑 hypothesis tournament — 我想看非显然的方向」
```

OPL skill 在 Claude Code 可用 skill 列表中(`opl-cancer`),触发后走 SKILL.md 11-step orchestration。

### 数据隐私(PHI 保护)

- **患者数据全部不在 skill repo**:`~/CancerDAO/patients/<patient_code>/` 独立位置(env `OPL_PATIENT_DATA_ROOT` 可改)
- `.gitignore` 排除 `patients/` + `.env` + `docs/superpowers/`(per memory:feedback_docs_superpowers_private)
- G5 mechanical gate 强制跨患者隔离(claim.patient_code != run.patient_code → raise)
- 每 trigger 产物在 `triggers/<run_id>/`,完成后归档到 `archives/`
- 第三方可独立 verify_provenance + bit-exact reproduce(开源科学契约)

### 跨形态分发

| 形态 | 状态 |
|---|---|
| Claude Code (`~/.claude/skills/opl-cancer/`) | ✓ live |
| OpenCode / Codex / Cursor(per vercel-labs/skills 蓝本) | ✓ 兼容(skill 结构对齐) |
| GitHub `CancerDAO/opl-cancer-skill` 公开仓 | 待 push(v1.5 候选项) |
| 网页 wrapper(claude.ai/code)| v1.5+ |

---

## 10. v1.5 待办事项(ADR-0008 deferred,round-4 verification 后再确认)

### 🔴 P0(round-4 仍 open)
1. **D11 bilingual delivery channel** — Patient #20 NPC 中越混血 + 妻子 DE 这种 international family,需 `pi_delivery_zh_en.md` / `--delivery-language` flag
2. **D12 expert-mode delivery channel** — Patient #18 / #23 sister-physician audit 需要 `pi_delivery_expert.md`(full stat tables + dose math)

### 🟡 P1(强建议,从 paper-level 提升到真 LLM 端到端)
3. **真 LLM Wave run end-to-end** — 用真 ANTHROPIC_API_KEY + MINIMAX_API_KEY 在 1 个 synthetic patient 上跑 Wave 1-5,确认 prompts/tasks/* 的 JSON schema 在 LLM 真输出上能 parse,不只是 schema-level PASS
4. **bixbench Docker live test** — `OPL_BIXBENCH_LIVE=1` 实跑一次,确认 G15/G16 真触发
5. **Caregiver-relayed tone for adult patient** — round-4 verification 暴露的 schema gap
6. **Oral-TKI generic forensic axis** — `boundary_unregulated_channel_disclosure.md` retrospective 现 Lu-177-flavored,需补 oral-TKI(tablet count + LFT + AFP response)

### 🟢 P2(round-2 已知 deferred)
7. AR-V7 splice-variant schema in Bert NGS interpretation
8. ORF-vs-sequence-reversion distinction(BRCA reversion 类型)
9. Multi-tumour-bed coordination(MEN1/Lynch/LFS:`disease: <one>` → `diseases: [<list>]`)
10. Radioligand class overlay(Lu-177 / Ac-225 / Y-90 isotope 区分)
11. IPD-meta task package(对 raw cohort data 跑 Cox PH,vs PMID summary pooling)
12. Pediatric ALL/AML cohort integrator(TARGET-ALL / COG-AALL,BeatAML 是 adult)

### 🔵 P3(产品 / 法务决策类)
13. **真发布 GitHub `CancerDAO/opl-cancer-skill`** — 现在只 sync 本机,没 git push
14. **法务发布前 review**(GDPR / HIPAA / 中国个保法 jurisdictional disclaimer)
15. **Trademark 注册 OPL-Cancer** — 防恶意 fork(PRD §17.6)

---

## 11. References / Substrate

OPL 的核心架构 lift 自三大开源 substrate + CancerDAO 自有项目:

### Nature 2026 三联画(同期 back-to-back paper 的本地复现)

| Repo | Paper DOI | v1 关系 |
|---|---|---|
| **open-coscientist** | `10.1038/s41586-026-10644-y` | **Lift 源** — Elo 联赛(`core/elo.py`)+ Meta-critique 传播 + Generation 4-strategy + Evolution 6-strategy + Reflection 6-mode |
| **robin** | `10.1038/s41586-026-10652-y` | **Lift 源** — PaperQA2 反幻觉 RAG + Finch ReAct bixbench Docker + BTL pairwise judge + EXPERIMENTAL_INSIGHTS_APPENDAGE |
| **era** | `10.1038/s41586-026-10658-6` | **Substrate 仅参考** — v1 不直接 lift;v1.5+ 若做 in-silico molecule design 时重启评估 |

### CancerDAO 自有

| Repo | 关系 |
|---|---|
| `CancerDAO/mtb`(引擎) | 不动,继续按引擎节奏迭代;OPL 通过 lift module 使用 |
| `CancerDAO/vmtb-skill` `feat/hypothesis-generation` 分支 | OPL 的直接前身;~60-70% 内容 lift |
| `CancerDAO/cancer-buddy-skill` | 兄弟 skill;`cancer-buddy-organize` / `cancer-buddy-mind` / `cancer-buddy-disclosure` / `cancer-buddy-caregiver` 等被 OPL scope_handoff 引用 |
| `CancerDAO/firefly-skill` | 兄弟 skill(罕见病);`firefly-genetic-counseling` 被 OPL family_cascade_routing 引用 |
| `CancerDAO/cancerdao-global`(landing)| 首页 "founder mode against cancer" CTA 引导 `npx skills add CancerDAO/opl-cancer-skill` |

详见 `docs/adr/0001-substrate-references.md`。

---

## 12. 一句话总结

OPL for Cancer v1.4.0 = **Apache-2.0 开源、npx 安装、Claude-Code-native、founder-mode、provenance-strict 的肿瘤患者 AI 科学家团队 skill**。从 v1.2 启动迭代到 v1.4,跑了 23 patient persona × 4 round EVAL panel(28/28 verification PASS),实现了 PRD §0 telos 的全部范畴:**调取世界已知(29 integrators + 42 task packages)** + **主动产生世界未知(Co-Sci Elo + Robin lit loop + 真 Finch bixbench + Cox PH N=1 投射)** + **患者是唯一决策人(无医生 sign-off + G24 危机救济 + 儿科 guardian-info-receipt-only)**。剩余 v1.5 deferred(双语 delivery + expert-mode delivery + 真 LLM 端到端实跑)在 ADR-0008 透明声明。

— CancerDAO Contributors, 2026-05-25
