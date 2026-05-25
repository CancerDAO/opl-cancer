# vmtb-skill `feat/hypothesis-generation` vs OPL for Cancer v1.4.0 — Diff

> 调研日期: 2026-05-25
> vmtb-skill commit: `42dee82` (CancerDAO/vmtb-skill, branch `feat/hypothesis-generation`, HEAD)
> OPL commit: `2981beb` (opl-for-cancer-skill, branch `main`, latest tag `v1.2.0`, 但 `docs/TECHNICAL_REPORT_v1.4.0_zh.md` 标记目标版本为 v1.4.0)
> 范围: 把 vmtb-skill 当前分支的每一个 feature 文件,对照 OPL v1.4.0 target 形态,标 ✓ Full / ⚠️ Partial / ❌ Missing / ♻️ Sibling-delegated。

---

## 1. 高层结论

OPL v1.4.0 已经把 **vmtb-skill `feat/hypothesis-generation` 的核心证据/假设/多源 integrator 范式 完整 lift 进来,但故意把 vMTB 的 "8-doc HTML 交付 + 5-dim verifier + chair finalize + NCCN PageIndex builder + china_pipeline + patient_education + organizer" 等 deliverable-shaped 模块拆给了 sibling skill(cancerdao-vmtb-verify / vmtb-patient-education / cancer-buddy-organize / firefly-* )**,而 OPL 自己保留的是 "1 PI + 18 expert + 5-Wave 研究 lifecycle + 23 gates + 29 integrators" 的 research-grade core。粗略口径:

- ✓ Full ≈ **16** 项 (literature 多源 / molecular_annotator / hypothesis_generator / NCCN searcher / oncologist / trial_recruiter / geneticist / pathologist / completeness / convergence / plan_agent / web_researcher / china drug-access / 等核心研究 agent 都有等价 expert 或 task package)
- ⚠️ Partial ≈ **10** 项 (vmtb 的 chair finalize / 5-dim verifier / evidence_graph_merger / NCCN-builder / 8-doc renderer / iterated_verifier / hypothesis_safety §3.9 bucket 等形态不同或精度不同)
- ❌ Missing ≈ **6** 项 (NCCN PageIndex builder 全链路 / 8-doc HTML renderer / iterated_verifier 闭环 / chair-as-synthesizer 多 writer / china_pipeline 模板合成 / pmid_online_verify 在线复核)
- ♻️ Sibling-delegated ≈ **8** 项 (organizer → cancer-buddy-organize; patient_education → vmtb-patient-education; 5-dim verifier → cancerdao-vmtb-verify; 7 doc renderer → vmtb-html2pdf;遗传咨询/家系/disclosure → firefly-genetic-counseling/disclosure;心理/disclosure → cancer-buddy-mind/disclosure)

简短判断: **OPL v1.4.0 含 vmtb 的"科研管线" 80%+,但 vmtb 的"患者交付管线"(8 doc + verifier + organizer + education)走 sibling delegation,不在 OPL 主仓内。**

---

## 2. 对照表

### 2.1 Agents — vmtb `agents/vmtb-*.md` × 25

| vmtb path | OPL 状态 | OPL 对应路径 | 备注 |
|---|---|---|---|
| `agents/vmtb-pathologist.md` | ✓ Full | `prompts/experts/rosa/persona.md` + `prompts/tasks/pathology_interpretation.md` | Rosa = pathologist。OPL 走 6-grammar (planner/executor/reviewer/auditor/integrator/feedback),vmtb 走单文件 forked subagent。 |
| `agents/vmtb-geneticist.md` | ✓ Full | `prompts/experts/bert/persona.md` + `prompts/tasks/molecular_ngs_interpretation.md` | Bert = molecular。 |
| `agents/vmtb-oncologist.md` | ✓ Full | `prompts/experts/vince/persona.md` + `prompts/tasks/treatment_line_recommendation.md` | Vince = treatment line。 |
| `agents/vmtb-recruiter.md` | ✓ Full | `prompts/experts/rick/persona.md` + `prompts/tasks/trial_matching.md` | Rick = trials。 |
| `agents/vmtb-chair.md` | ⚠️ Partial | `prompts/pi/persona.md` + `prompts/pi/delivery.md` + Henry L2 disagreement | OPL 把 chair 拆成 PI (Sid) 对话化重写 + Henry L2 分歧聚合; vmtb 的 "chair-as-synthesizer 多 writer 合并 evidence graph fragments" 范式在 OPL 没单独 module。 |
| `agents/vmtb-verifier.md` | ♻️ Sibling | sibling skill `cancerdao-vmtb-verify` (5-dim verifier) | OPL v1.4.0 把 5-dim post-chair verifier (facts/guidelines/trials/safety/dose) 完全 delegate 给 sibling; OPL 内只有 G1-G24 mechanical gates,无 5-dim verdict panel。 |
| `agents/vmtb-convergence-judge.md` | ⚠️ Partial | `src/opl_cancer/orchestrator/tournament.py` (Co-Sci Elo) + Henry L2 | OPL 用 Co-Sci tournament + Elo 自然收敛,无"再来一轮"的显式 judge agent。 |
| `agents/vmtb-completeness.md` | ✓ Full | `prompts/pi/intent_parser.md` + `src/opl_cancer/orchestrator/pi_session.py` (readiness check) | OPL 在 PI session 入口直接做 readiness; vmtb 用独立 subagent。 |
| `agents/vmtb-deepdive.md` | ✓ Full | `prompts/pi/drilldown.md` | OPL 的 drilldown = vmtb 的 deepdive (从 OCR sidecar 拉低就绪度字段)。 |
| `agents/vmtb-plan-agent.md` | ✓ Full | `prompts/pi/persona.md` (Sid 派单) + `prompts/pi/intent_parser.md` | Sid 直接做 plan-agent 角色。 |
| `agents/vmtb-hypothesis-generator.md` | ✓ Full | `prompts/tasks/hypothesis_generation.md` (4-strategy) + `src/opl_cancer/orchestrator/generation.py` | OPL 完整 Co-Sci port,且额外加了 evolution/reflection/debate/meta_critique。 |
| `agents/vmtb-literature.md` | ✓ Full | `prompts/tasks/literature_synthesis.md` + integrators `pubmed.py` + `paperqa.py` + `unpaywall.py` | OPL 用 PaperQA2 反幻觉,vmtb 用 PubMed+EuropePMC+SemanticScholar+bioRxiv 并行 dedupe。功能等价。 |
| `agents/vmtb-molecular-annotator.md` | ✓ Full | `prompts/experts/bert` + integrators `oncokb.py` + `civic.py` + `clinvar.py` + `cbioportal.py` + `open_targets.py` | OPL 通过 Bert + 5 integrators 等价覆盖。 |
| `agents/vmtb-nccn-searcher.md` | ✓ Full | integrators `nccn.py` (PageIndex tree-search) | OPL 在 integrator 层直接做 NCCN tree search。 |
| `agents/vmtb-nccn-builder.md` | ❌ Missing | — | OPL 的 NCCN integrator 假定 PageIndex 已存在,**没有 builder 子链** (从 NCCN PDF native PDF vision 抽 chapter tree → cache to disk)。vmtb 的 `references/pageindex/` 已建好 26 个 cancer type 树。这是 OPL 的真空白。 |
| `agents/vmtb-web-researcher.md` | ✓ Full | `references/integrator-catalog.md` + integrators (NMPA/FDA/EMA EAP 子集) + sibling skill `web-access` | OPL 把 JS-heavy + auth 页爬取走 web-access skill delegation; integrator 层已含 nmpa_eap/fda_eap/ema_eap。 |
| `agents/vmtb-research-orchestrator.md` | ✓ Full | `src/opl_cancer/orchestrator/{tournament,evolution,reflection,debate,meta_critique}.py` | OPL 拆成 5 个 orchestrator module。 |
| `agents/vmtb-china-access.md` | ⚠️ Partial | `prompts/tasks/cross_border_navigation.md` + `prompts/tasks/expanded_access_navigation.md` + integrators (`nmpa_eap.py`) | OPL 含 NMPA/cross-border task,**但没有 vmtb 的 "国家医保 NRDL + 中华慈善总会 PAP + 药企 PAP + 城惠保" 完整中国本地药物 access 综合**。 |
| `agents/vmtb-organizer.md` | ♻️ Sibling | sibling skill `cancer-buddy-organize` / `cancer-buddy-organize-v2` | OPL 的入站 readiness 检查直接调 sibling; 不在 OPL 内重做 OCR + 11-bucket 病历整理。 |
| `agents/vmtb-doc-000-readme.md` | ♻️ Sibling | `prompts/delivery/patient_brief.html.j2` + sibling skill `vmtb-html2pdf` | OPL 只保留单个 `patient_brief` 渲染,不复用 vmtb 的 8-doc 框架 (000_README/001 brief/002 detailed/003 general/004 deep/005 trials/006 china/007 founder)。 |
| `agents/vmtb-doc-001-brief.md` | ⚠️ Partial | `prompts/delivery/patient_brief.md.j2` + `prompts/delivery/patient_brief.html.j2` | 等价 = OPL 的 `patient_brief` 渲染; OPL 不区分 brief / detailed / deep / founder。 |
| `agents/vmtb-doc-002-detailed.md` | ❌ Missing | — | OPL 没有 "detailed report" 这层。 |
| `agents/vmtb-doc-003-general.md` | ❌ Missing | — | 同上,治疗方案综合报告无独立 renderer。 |
| `agents/vmtb-doc-004-deep.md` | ❌ Missing | — | 同上。 |
| `agents/vmtb-doc-005-trials.md` | ⚠️ Partial | `prompts/tasks/trial_matching.md` + Rick expert | OPL 把 trial 列表当 task 输出,不再单独渲染。 |
| `agents/vmtb-doc-006-china.md` | ♻️ Sibling | sibling skill `cancerdao-treatment-landscape` + OPL `cross_border_navigation` task | 中国深度报告 delegate。 |
| `agents/vmtb-doc-007-founder.md` | ♻️ Sibling | sibling skill `beacon` / `cancer-buddy` "founder mode" 入口 + `references/founder-mode-philosophy.md` (理念已 internalize) | 创始人寄语作为对外 narrative 走外层 skill,OPL 内 reference 文件保留 founder-mode 哲学。 |

### 2.2 Task Packages / Prompts — vmtb (SKILL.md inline + scripts/config/prompts/) vs OPL `prompts/tasks/*.md` × 42

vmtb 没有 `prompts/tasks/` 独立目录,任务指令分布在:
- `scripts/config/prompts/hypothesis_generator_prompt.txt`
- `scripts/config/schemas/hypothesis_directions.json`
- `agents/vmtb-*.md` frontmatter + body

OPL 反向覆盖 vmtb 缺失的 prompt 工程化更彻底。下表反向:OPL 任务 → vmtb 是否含。

| OPL prompts/tasks | vmtb 对应 | 备注 |
|---|---|---|
| `hypothesis_generation.md` | `agents/vmtb-hypothesis-generator.md` + `scripts/config/prompts/hypothesis_generator_prompt.txt` | ✓ |
| `hypothesis_validation.md` | (隐含在 chair / verifier 流程) | ⚠️ vmtb 无独立 validation task |
| `literature_synthesis.md` | `agents/vmtb-literature.md` | ✓ |
| `trial_matching.md` | `agents/vmtb-recruiter.md` + integrators | ✓ |
| `pathology_interpretation.md` | `agents/vmtb-pathologist.md` | ✓ |
| `molecular_ngs_interpretation.md` | `agents/vmtb-geneticist.md` | ✓ |
| `recist_progression.md` | (隐含 oncologist) | ⚠️ vmtb 无独立 task |
| `staging_workup.md` | (隐含 oncologist / pathologist) | ⚠️ |
| `treatment_line_recommendation.md` | `agents/vmtb-oncologist.md` | ✓ |
| `expanded_access_navigation.md` | `agents/vmtb-china-access.md` + landscape EAP | ⚠️ partial |
| `cross_border_navigation.md` | `references/centers/china_specialty_centers.md` + chairs | ⚠️ partial |
| `china_rwe_adjustment.md` | `references/china_pipeline/` | ⚠️ |
| `drug_repurposing.md` | (隐含 hypothesis generator) | ⚠️ vmtb 无独立 Co-Sci evolution port |
| `bioinformatics_data_analysis.md` | — | ❌ vmtb 无 Wave-3 Finch bixbench Docker 真跑统计 |
| `meta_analysis.md` | — | ❌ vmtb 无 meta task (metafor / I²) |
| `single_cell_reanalysis.md` | — | ❌ |
| `pathway_enrichment.md` | — | ❌ |
| `n1_cohort_projection.md` | — | ❌ vmtb 无 N=1 cohort projection (走 sibling cancer-buddy-vault) |
| `dataset_acquisition.md` | — | ❌ vmtb 不含 GEO/ArrayExpress/SRA 数据集获取 |
| `irae_rechallenge.md` / `ici_endocrine_irae.md` | — | ❌ vmtb 无独立 irAE 处理 (sibling cancer-buddy 接) |
| `ddi_adme_dosing.md` | — | ❌ vmtb 无 DDI/ADME 任务 |
| `tcm_oncology.md` / `oncology_nutrition.md` | — | ♻️ vmtb sibling (cancer-buddy-nutrition) |
| `palliative_symptom_qol.md` | — | ♻️ sibling |
| `claim_audit.md` / `source_verification.md` / `cross_source_consistency.md` | `scripts/validators/citation_grounding.py` / `pmid_online_verify.py` / `nccn_verification.py` | ⚠️ vmtb 用代码层实现,OPL 用 task package + Henry |
| `crisis_card_emission.md` / `guardian_ack_protocol.md` / `caregiver_filter_protocol.md` / `family_cascade_routing.md` / `scope_handoff_routing.md` / `patient_pushback_handling.md` | — | ❌ vmtb 完全没有 (走 sibling firefly-disclosure / cancer-buddy-mind) |
| `intrathecal_therapy_navigation.md` / `interventional_oncology.md` / `radiation_planning.md` / `neutropenic_fever_management.md` | — | ❌ vmtb 没有这类专科 task |
| `boundary_unregulated_channel_disclosure.md` | `references/policies/` (drug landscape policies) | ⚠️ |
| `surveillance_schedule.md` | — | ❌ |
| `patient_brief_rendering.md` / `pi_delivery.md` | `agents/vmtb-doc-001-brief.md` + chair finalize | ⚠️ |

### 2.3 Integrators / API Clients

vmtb `skills/cancerdao-vmtb/scripts/tools/api_clients/` × 22 vs OPL `src/opl_cancer/integrators/` × 29。

| vmtb api_client | OPL integrator | 状态 |
|---|---|---|
| `ncbi_client.py` (PubMed/Europe PMC/Semantic Scholar/bioRxiv) | `pubmed.py` + `paperqa.py` + `unpaywall.py` | ✓ (OPL 拆得更细) |
| `clinicaltrials_client.py` | `clinicaltrials.py` | ✓ |
| `eu_ctr_client.py` | `eu_ctr.py` | ✓ |
| `isrctn_client.py` | `isrctn.py` | ✓ |
| (无 hkctr) | `hkctr.py` | OPL extra |
| (无 ChiCTR client) | `chictr.py` | OPL extra |
| `civic_client.py` | `civic.py` | ✓ |
| `clinvar_client.py` | `clinvar.py` | ✓ |
| `clingen_client.py` | (OPL 无独立 ClinGen) | vmtb extra |
| `cosmic_client.py` | (OPL 无 COSMIC) | vmtb extra |
| `cbioportal_client.py` | `cbioportal.py` | ✓ |
| `gnomad_client.py` | `gnomad.py` | ✓ |
| `oncotree_client.py` | (隐含 oncokb) | vmtb extra |
| `dgidb_client.py` | (OPL 无 DGIdb) | vmtb extra |
| `rxnorm_client.py` | `rxnorm.py` | ✓ |
| `fda_client.py` | `fda_eap.py` | ✓ |
| (无 EMA EAP) | `ema_eap.py` | OPL extra |
| (无 NMPA EAP) | `nmpa_eap.py` | OPL extra |
| `gdc_client.py` | `gdc.py` | ✓ |
| (无 BeatAML/Hartwig/ICGC) | `beataml.py` + `hartwig.py` + `icgc.py` | OPL extra (DUA-gated) |
| (无 ArrayExpress/GEO/SRA) | `arrayexpress.py` + `geo.py` + `sra.py` | OPL extra (Wave-3 数据集) |
| (无 DepMap/CCLE) | `depmap.py` + `ccle.py` | OPL extra |
| `opentargets_client.py` | `open_targets.py` | ✓ |
| `crossref_abstracts_client.py` | (隐含 paperqa+unpaywall) | vmtb extra |
| `retraction_watch_client.py` | `retractiondb.py` | ✓ |
| `hgvs_validator_client.py` | (OPL 无独立 HGVS 校验) | vmtb extra |
| `fault_injection_validate.py` | (OPL 无 fault injection harness) | vmtb extra (audit) |
| `local_db.py` | `cache.py` (SQLite per-patient) | ✓ |

### 2.4 Validators / Gates

vmtb `scripts/validators/` × 11 vs OPL `src/opl_cancer/validators/gates/g1..g24`。

| vmtb validator | OPL gate(s) | 状态 |
|---|---|---|
| `citation_grounding.py` | `g1_pmid_existence.py` + `g2_pmid_quote_match.py` | ✓ |
| `evidence_provenance.py` | `g11_no_silent_fallback.py` + provenance SHA-256 in `henry.py` | ✓ |
| `format_checker.py` | (隐含 in renderer) | ⚠️ |
| `geneticist_audit.py` | `g22_ddr_zygosity.py` (zygosity-aware) + Bert expert reviewer | ⚠️ vmtb 单文件做 audit,OPL 拆 |
| `hypothesis_safety.py` (§3.9 EXPLORATORY bucket + supportive-care exempt) | `g21_quantitative_anchor.py` (Wave-3-evidenced 必须含 HR/OR/CI/p) + tournament tier-label | ⚠️ vmtb 更激进的 §3.9 隔离 bucket;OPL 走 tier-label (established/exploratory/speculative) |
| `nccn_verification.py` | `g10_guideline_version.py` (time-pinned) | ✓ |
| `number_grounding.py` | `g21_quantitative_anchor.py` | ✓ |
| `pmid_online_verify.py` (实跑 PubMed/CT.gov 在线复核) | `g1_pmid_existence.py` (offline ID 存在性) | ⚠️ vmtb 更强:在线复核 abstract 一致 |
| `source_coverage.py` | `g18_meta_search_strategy.py` (PRISMA) | ✓ |
| `verified_claims.py` | (隐含 in Henry L1) | ⚠️ |

OPL 含 vmtb 没有的 gates: G3 drug-norm / G4 dose-unit / G5 patient-isolation / G6 injection-scan / G7 imperative-detector / G8 L3-4 risk-card / G12 memory-overflow / G13 reviewer-model-distinct / G14 dataset-patient-match / G15-G17 (statistical) / G19-G20 (PI gates) / G23 recency / G24 crisis-detection。

### 2.5 References / Knowledge

| vmtb references | OPL 等价 | 状态 |
|---|---|---|
| `references/pageindex/` (26 cancer NCCN trees) | (OPL 无 pre-built PageIndex; integrator 假定 cache 存在) | ❌ OPL missing |
| `references/landscapes/{CRC,PDAC}/` | `references/integrator-catalog.md` (源说明) | ⚠️ 不是 landscape md |
| `references/china_pipeline/{CRC,PDAC}/` | `prompts/tasks/cross_border_navigation.md` + `cross_border` | ⚠️ vmtb 是 reference md 模板,OPL 是 task prompt |
| `references/centers/china_specialty_centers.md` | (OPL 无 centers reference) | ❌ |
| `references/drug_database.md` | integrators `rxnorm.py` + `knowledge/serious_risks_per_drug.json` | ⚠️ |
| `references/policies/` | (OPL 无) | ❌ |
| `references/external/` | `references/integrator-catalog.md` | ⚠️ |
| `references/_legacy_llm_landscape/` | — | (legacy 不计) |

OPL 含的 vmtb 没有的 references: `architecture.md` / `expert-roster.md` / `founder-mode-philosophy.md` / `mechanical-gates.md` / `permission-levels.md` / `troubleshooting.md` / `wave-lifecycle.md` (7 篇 doc-as-substrate)。

### 2.6 Key Feature Files

| vmtb feature file | OPL 等价 | 状态 |
|---|---|---|
| `scripts/delivery/evidence_graph_merger.py` (multi-writer fragments → unified graph) | `src/opl_cancer/orchestrator/{tournament,reflection,meta_critique}.py` + Henry L2 | ⚠️ OPL 没有显式 evidence-graph merger;Co-Sci tournament 自然合并 |
| `scripts/iterated_verifier/run.py` | (OPL 不闭环 verify→fix→re-verify;Henry L4 rollback 是不同语义) | ❌ |
| `scripts/finalize.py` (chair-as-synthesizer) | `prompts/pi/delivery.md` + Henry L2 | ⚠️ |
| `scripts/graph/state_graph.py` (langgraph) | `src/opl_cancer/orchestrator/pi_session.py` (state machine) | ✓ |
| `scripts/landscape/{fanout,china_fanout}.py` | `prompts/tasks/cross_border_navigation.md` + integrators | ⚠️ |
| `scripts/organizer/` | sibling skill `cancer-buddy-organize` | ♻️ |
| `scripts/patient_education/` | sibling skill `vmtb-patient-education` | ♻️ |
| `scripts/preflight.py` + `preflight_constants.py` | `prompts/pi/intent_parser.md` + `prompts/safety/crisis_detection.md` + g24 | ✓ |
| `scripts/etl/` | integrator `cache.py` + Henry provenance | ⚠️ |
| `scripts/observability/` | (OPL 无 OTel/log structuring 模块) | ❌ |
| `scripts/config/schemas/hypothesis_directions.json` | (隐含 in hypothesis_generation task) | ⚠️ |

### 2.7 Tests

| vmtb tests | OPL tests | 备注 |
|---|---|---|
| `skills/cancerdao-vmtb/tests/api_clients/` | `tests/integrators/` | OPL 997 tests pass; vmtb tests dir 存在但规模未数 |
| `tests/` 子目录 (validators/etl/finalize 等) | `tests/{validators,orchestrator,delivery}/` | 等价 |

---

## 3. ❌ Missing 清单 — OPL v1.4.0 完全没有,但 vmtb 有

| # | vmtb feature | 功能描述 | 为什么 OPL 没含 | 入 v1.5? |
|---|---|---|---|---|
| M1 | `agents/vmtb-nccn-builder.md` + `references/pageindex/*` | NCCN PDF → PageIndex chapter tree builder (native PDF vision) + 26 cancer type 预建树 | OPL 假定 PageIndex 已存在,但 build pipeline 没 ship;v1.4.0 文档 §6 NCCN 整段假设 cache 已 warm | **P0 yes** (无 builder = 新 cancer type 无 NCCN tree) |
| M2 | `agents/vmtb-doc-{002,003,004}` × 3 (detailed/general/deep report renderers) | 8-doc 交付里的 3 个 mid-tier renderer (002 病情详细 / 003 治疗综合 / 004 治疗深度) | OPL 只保留 patient_brief.html.j2 单 template; deeper view 当成 drilldown task 处理 | P2 (走 sibling vmtb-html2pdf 可顶) |
| M3 | `scripts/iterated_verifier/run.py` | 5-dim verifier → 反馈 → chair 修订 → 再 verify 的闭环 | OPL 把 5-dim verifier 整个 delegate 给 `cancerdao-vmtb-verify` sibling,本仓内只有 Henry rollback (不同语义) | P1 (Henry L4 rollback 不能闭环修订) |
| M4 | `references/policies/` + `references/centers/china_specialty_centers.md` | 国家医保 NRDL / 中华慈善总会 PAP / 城惠保 / 中国专科中心目录 reference 库 | OPL 走 task prompt + integrator,没有静态 reference md;vmtb-china-access 的中国本地知识没完全 lift | **P0 yes** (中国患者 cross-border 需要这层) |
| M5 | `scripts/observability/` | OTel tracing + structured log + Wave 内 timing | OPL 文档 §8 提到 test panel,但 observability 模块没在 src 体现 | P2 |
| M6 | `scripts/validators/pmid_online_verify.py` 的"在线 abstract 一致性复核" | 不只 PMID 存在性,还要拉 abstract 比对 quote | OPL G1 只 verify PMID 存在,G2 verify quote match,但**没有去 PubMed 拉 abstract 实跑一致性** | **P0 yes** (AI-safety reviewer must-fix #2 in vmtb,OPL 必须补) |

(其他被 task package 隐式覆盖的 / 走 sibling 的不计 missing。)

---

## 4. ⚠️ Partial 清单 — OPL 等价存在但差异显著

| # | vmtb feature | OPL 等价 | 差异 | 补齐到 Full? |
|---|---|---|---|---|
| P1 | `agents/vmtb-chair.md` (chair-as-synthesizer multi-writer) | `prompts/pi/delivery.md` + Henry L2 | OPL 的 Sid delivery 是"对话化重写",没有 vmtb 的"多 expert evidence-fragment → unified graph"合并步骤 | P1 — 把 evidence_graph_merger 当 task package lift 进 OPL `prompts/tasks/evidence_graph_synthesis.md` |
| P2 | `agents/vmtb-verifier.md` (5-dim verdict) | OPL 23 gates + Henry L1 | gates 是 mechanical no-LLM 规则,无 5-dim panel 综合 verdict | P1 — 但用 sibling delegation 已经够,不需要 lift |
| P3 | `agents/vmtb-china-access.md` 完整中国 access 综合 | `cross_border_navigation` + `expanded_access_navigation` + `nmpa_eap.py` | OPL 没有 NRDL/PAP/慈善总会/城惠保整合 | **P0 — 必须扩 china_drug_access task package** (memory: longitudinal_health_data 泛化要求中国患者 path 全) |
| P4 | `scripts/validators/hypothesis_safety.py` §3.9 EXPLORATORY bucket | G21 quantitative-anchor + tier-label | vmtb 把无定量证据的假设直接关在 §3.9 隔离 bucket;OPL 只打 tier-label (内联) | P1 — 加 `prompts/safety/exploratory_bucket.md` |
| P5 | `scripts/finalize.py` chair finalize stage | `prompts/pi/delivery.md` | OPL 走 PI 对话重写,不写"final report markdown";deliverable 形态不同 | P2 |
| P6 | `scripts/landscape/{fanout,china_fanout}.py` (并行多 source landscape 合成) | task package 串行 | OPL 没显式 fanout orchestrator | P2 |
| P7 | `references/landscapes/` + `references/china_pipeline/` template md | reference 文件 + task prompt | 形态:vmtb 是 reference markdown 直接给 chair 用; OPL 把 reference 提炼成 task prompt | P2 — 加 cancer-type-specific landscape reference md 进 `references/landscapes/{HCC,NSCLC,...}/` |
| P8 | `scripts/validators/geneticist_audit.py` 独立审计 | Bert reviewer + G22 DDR-zygosity | 单一审计 vs 拆成 reviewer + gate;OPL 形态更解耦 | P3 — 不补 |
| P9 | `agents/vmtb-convergence-judge.md` | tournament Elo 自然收敛 + Henry L2 | OPL 无显式 "再来一轮"判官;tournament 跑完即停 | P3 — 不补 |
| P10 | `scripts/delivery/evidence_graph_merger.py` | tournament + reflection + meta_critique | 形态差异巨大;vmtb 是 graph fragments → unified entity/edge graph;OPL 是 Elo + reflection | **P1 — 把 evidence graph 当一等公民 引进 OPL,加 `src/opl_cancer/graph/` 模块** |

---

## 5. OPL v1.4.0 新增 (vmtb 没有)

| # | OPL feature | vmtb 状态 |
|---|---|---|
| N1 | G24 crisis-detection (SI/SH 关键词扫描 + Wave-lock) + `prompts/safety/crisis_detection.md` | vmtb 完全没有 |
| N2 | `prompts/pi/persona.md` Sid PI (单一对话 surface) | vmtb 是 plan-agent + chair 二段 |
| N3 | `prompts/tasks/guardian_ack_protocol.md` + `caregiver_filter_protocol.md` + `family_cascade_routing.md` + `scope_handoff_routing.md` | 全部 missing 在 vmtb |
| N4 | G19/G20 PI-imperative + PI-disagreement-surfacing gates | vmtb 无 PI 层 |
| N5 | `prompts/tasks/{ici_endocrine_irae,irae_rechallenge,intrathecal_therapy_navigation,interventional_oncology,radiation_planning,neutropenic_fever_management,palliative_symptom_qol}` (7 个专科 task) | vmtb 走 sibling cancer-buddy |
| N6 | `prompts/tasks/{bioinformatics_data_analysis,meta_analysis,single_cell_reanalysis,pathway_enrichment,dataset_acquisition,n1_cohort_projection}` Wave-3 数据-evidence | vmtb 完全无 Wave-3 |
| N7 | Co-Sci 完整 port (evolution + reflection + debate + meta_critique + experimental_insights) | vmtb 只 port 了 generation/reflection |
| N8 | `references/founder-mode-philosophy.md` + `references/wave-lifecycle.md` + 8 ADRs (doc-as-substrate) | vmtb 散在 README/CHANGELOG |
| N9 | 18 命名 expert (含 Heddy 影像 / Ted 放疗 / Iain meta / Kieren ID / Mark irAE / Hong 中医 / Frances EAP / Dennis 跨境 / Steve 营养 / Tyler 湿实验 / Aviv 生信 / Jen 缓和 / Riad 介入) | vmtb 只 5 main agent |
| N10 | G13 reviewer-model-distinct (models.yaml pairing 强制不同 model 互审) | vmtb 无 |
| N11 | G14 dataset-patient-match (7-axis 含 conditional) + G15 multiple-testing-correction + G16 batch-effect-declared + G17 meta-I²-policy + G18 PRISMA-search-strategy (5 个统计/dataset gate) | vmtb 无 Wave-3 ⇒ 这层不需要 |
| N12 | DUA-gated integrator (Hartwig/BeatAML/ICGC 申请 URL raise) | vmtb 无 |
| N13 | `tests/eval_panel/` 23-persona × 4-round EVAL panel | vmtb 走 6-perspective PR review |
| N14 | `prompts/tasks/n1_cohort_projection.md` (N=1 → 类病人队列投影) | vmtb 走 sibling cancer-buddy-vault |

---

## 6. v1.5 推荐

### P0 (must in v1.5)

1. **P0-A: 把 vmtb 的 `pmid_online_verify` 升进 OPL G1/G2 — 在线 abstract 一致性复核**
   - 当前 G1 只 verify PMID 存在,G2 quote 匹配是本地字符串;vmtb 已实跑 PubMed eutils 拉 abstract 比对。
   - 文件: 新增 `src/opl_cancer/validators/gates/g2b_pmid_abstract_consistency.py` + extend `tests/validators/`
   - Memory hit: `feedback_no_offline_only.md` (禁止 LLM 直接合成证据) + `project_vmtb_global_evidence.md`
2. **P0-B: NCCN PageIndex builder 链路 + 26 cancer pre-built tree commit**
   - 当前 integrator 假定 cache 存在,新 cancer type 时 cold start 全卡死。
   - 文件: 新增 `src/opl_cancer/integrators/nccn_builder.py` + 把 vmtb `references/pageindex/` 整个目录搬到 OPL `knowledge/nccn_pageindex/`
   - 走 sub-skill prompt (Claude native PDF vision) 不写 keyword 解析
3. **P0-C: 扩 china_drug_access task package 含 NRDL/PAP/城惠保/中华慈善总会**
   - 现在 `cross_border_navigation.md` 只覆盖跨境;中国患者 90% scenarios 是国内 access,vmtb 已有完整 `china_pipeline` + `centers/china_specialty_centers.md`。
   - 文件: 新增 `prompts/tasks/china_drug_access.md` + integrators `chinese_charity_pap.py` (or scrape via web-access sibling) + `references/centers/china_specialty_centers.md` lift
   - 不写硬编码 keyword list,走 sub-skill prompt (memory: `feedback_default_prompt_over_script.md`)

### P1

4. **P1-A: Evidence Graph 升一等公民** — lift `scripts/delivery/evidence_graph_merger.py` + `scripts/models/evidence_graph.py` 进 OPL `src/opl_cancer/graph/`,挂在 PI session 输出层;Wave 1-4 的 claim 都进 graph (entity/edge w/ provenance SHA-256)。
5. **P1-B: hypothesis_safety §3.9 EXPLORATORY bucket** — 新增 `prompts/safety/exploratory_bucket.md` + 在 tournament 输出加 §3.9 隔离 section (vmtb 的 supportive-care exempt 规则也带过来)。
6. **P1-C: iterated_verifier 闭环** — OPL 当前 Henry L4 是 rollback (回退),没有 "5-dim verifier flag → chair 修订 → re-verify" 闭环。或 ADR-0009 明确 delegate 给 sibling `cancerdao-vmtb-verify`。

### P2

7. **P2-A: observability** — OTel tracing + Wave 内 timing structured log
8. **P2-B: landscape fanout orchestrator** — 把 vmtb `scripts/landscape/fanout.py` 范式 (多 source 并行) 引入 OPL,目前 task package 串行慢
9. **P2-C: cancer-type-specific landscape reference md** — 给 HCC/NSCLC/TNBC/AML/CRC/HCC/PDAC 等 14 cancer type 各加一篇 `references/landscapes/{type}.md` (从 vmtb landscapes 翻译/适配)

### Sibling delegation 不 lift

- ❌ 不 lift: `agents/vmtb-organizer.md` → `cancer-buddy-organize` 已经做了
- ❌ 不 lift: `agents/vmtb-doc-000..007` 8 doc renderer → sibling `vmtb-html2pdf` + `vmtb-patient-education` 已做
- ❌ 不 lift: `agents/vmtb-verifier.md` 5-dim panel → sibling `cancerdao-vmtb-verify` 已 ship
- ❌ 不 lift: `agents/vmtb-doc-007-founder.md` 创始人寄语 → sibling `beacon` / `cancer-buddy` "founder mode" 入口

---

## 7. Memory Trail (供 zwbao 追溯)

- `project_vmtb_architecture.md`: vMTB P0-P2 已修 (NoneType, parse_verdict, readiness mtime-cache, RxNorm 弃用);P1 verify 时序前移待做
- `project_vmtb_global_evidence.md`: 17 源决策矩阵 + PR-1 已开 #7
- `project_mtb_ownership.md`: CancerDAO/mtb 仍活跃;与 zwbao/vmtb-skill 分化为引擎 vs 插件
- `feedback_no_offline_only.md`: 医疗 agent 默认实时联网,网络不可达就报错不静默 (= P0-A 立项依据)
- `feedback_default_prompt_over_script.md`: 需要 LLM 判断的工具 (命名/分类/抽取) 走 prompt 不写 Python keyword list (= P0-B/P0-C 必须遵守)
- `feedback_no_self_capped_scope.md`: 路线图全量列出按 P0/P1/P2 排,不自截断 (= 本报告全 6+3+3 项格式)

> 本报告由 vmtb-skill `42dee82` × OPL `2981beb` 静态对照生成,未跑端到端验证;v1.5 P0 立项前需 zwbao 二次审阅 sibling-delegation 边界。
