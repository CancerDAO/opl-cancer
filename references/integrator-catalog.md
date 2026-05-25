# Integrator Catalog — 10 Family / ~22 Instance

Integrators 是 OPL 的世界已知信息接口。设计上**按能力类型 (family) 组织,不按数据源 vendor**;新增 instance = 加 client + 注册到 family + 测试,**架构层零改动**。本文件展开 PRD §2.5 + Appendix B 的完整目录,并补充 cache TTL 与失败语义。

## 1. 10 Family × ~22 Instance

| Family | 能力 | Instance | Python module | API base URL | API key? | 默认 TTL |
|---|---|---|---|---|---|---|
| **F1 Literature** | 文献检索 + 全文 + 反幻觉 RAG + retraction | PubMed | `src/opl_cancer/integrators/pubmed.py` | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/` | optional (NCBI_API_KEY 提高 rate) | 7 d |
| | | Unpaywall | `integrators/unpaywall.py` | `https://api.unpaywall.org/v2/` | required (email) | 30 d |
| | | PaperQA2 (local RAG) | `integrators/paperqa.py` | local (Robin lift) | LLM key only | session |
| | | RetractionDB | `integrators/retractiondb.py` | `https://api.labs.crossref.org/data/retractions/` (or local mirror) | optional | 1 d |
| **F2 Clinical Guidelines** | 临床指南树搜 | NCCN PageIndex | `integrators/nccn.py` | local KB (`knowledge/nccn_excerpts/`) — license 限制全文 | n/a | until next NCCN version (12 mo max — G10) |
| **F3 Trials Registries** | 试验注册 + 资格匹配 | ClinicalTrials.gov | `integrators/clinicaltrials.py` | `https://clinicaltrials.gov/api/v2/` | none | 1 d |
| | | ChiCTR | `integrators/chictr.py` | `http://www.chictr.org.cn/`(scrape) | none | 1 d |
| | | (planned v1.3) ISRCTN | — | `https://www.isrctn.com/api/` | — | 1 d |
| **F4 Genomics Knowledge** | 变体-药物 actionability + 临床意义 | OncoKB | `integrators/oncokb.py` | `https://www.oncokb.org/api/v1/` | required | 7 d |
| | | CIViC | `integrators/civic.py` | `https://civicdb.org/api/` | none | 7 d |
| | | ClinVar | `integrators/clinvar.py` | NCBI E-utils | optional | 7 d |
| | | gnomAD | `integrators/gnomad.py` | `https://gnomad.broadinstitute.org/api` | none | 30 d |
| **F5 Genomics Cohorts** | 大队列基因组对照 | cBioPortal | `integrators/cbioportal.py` | `https://www.cbioportal.org/api/` | none | 7 d |
| | | GDC | `integrators/gdc.py` | `https://api.gdc.cancer.gov/` | none | 7 d |
| **F6 Omics Datasets** | transcriptomic / scRNA / proteomic 公开数据 | GEO | `integrators/geo.py` | NCBI E-utils + FTP | optional | 7 d |
| | | ArrayExpress | `integrators/arrayexpress.py` | `https://www.ebi.ac.uk/biostudies/files/arrayexpress/` | none | 7 d |
| | | SRA | `integrators/sra.py` | NCBI E-utils + SRA toolkit | none | 7 d |
| **F7 Cell/Drug Resources** | cell line + drug 数据库 | DepMap | `integrators/depmap.py` | `https://depmap.org/portal/api/` | none | 30 d |
| | | CCLE | `integrators/ccle.py` | DepMap (CCLE roll-up) | none | 30 d |
| **F8 Drug Regulatory/Access** | 药品监管 + 同情用药通道 | FDA EAP | `integrators/fda_eap.py` | `https://api.fda.gov/` + EAP scrape | optional | 7 d |
| | | NMPA EAP | `integrators/nmpa_eap.py` | NMPA portal scrape | none | 7 d |
| **F9 Targets/Pathways** | 通路-靶点 | Open Targets | `integrators/open_targets.py` | `https://api.platform.opentargets.org/api/v4/graphql` | none | 7 d |
| **F10 Drug Safety** | DDI + 不良事件 (RxNorm fallback for Lexicomp 受 license) | RxNorm | `integrators/rxnorm.py` | `https://rxnav.nlm.nih.gov/REST/` | none | 30 d |

合计 v0 共约 22 instance (Appendix B inventory)。所有 client 都继承 `integrators/base.py` 的 `Integrator` ABC + 走 `integrators/cache.py` 的 SQLite cache。

## 2. 缓存策略 (G11 + 性能 P2)

- **SQLite-backed**:`integrators/cache.py` 是单文件 `<patient_dir>/integrator_cache.sqlite`,schema:`(family, key, value_json, expires_at)`。
- **Per-family TTL**:见上表;NCCN 默认到下一 version (max 12mo,G10 强制);PubMed/CIViC/OncoKB 7d;ClinicalTrials/ChiCTR 1d (试验状态变化快);gnomAD/DepMap 30d (population freq 稳定)。
- **Per-patient session 复用**:同一 trigger run 内同请求只跑一次;跨 trigger 走 TTL 失效检查。
- **Cache miss → 实时 API**;**API down → raise**,不静默 fallback (G11)。

## 3. 失败模式 (硬约束)

每个 integrator client 必须:

| 必备 | 规则 |
|---|---|
| 实时 API 调用 | 默认走真实 endpoint;`feedback_no_offline_only` |
| 失败必 raise | API 5xx/timeout/auth-fail/empty-rate-limit → `IntegratorError` 抛到主线程;**禁止** LLM 替代查表 (G11 + failure mode D3) |
| 不静默降级 | 不能用 training data "猜" PMID / 试验 ID / 变体注释 |
| Empty result 区分 fail | API 返回 200 + 空数组 ≠ 失败;是合法 empty;executor 必须有 empty-handling 规则 (ADR-0006 C6) |

ADR-0006 C6 修复:所有 15 个 task package 现在都有 explicit empty-integrator 规则。如果所有 relevant integrator 都 empty,executor 唯一合法输出是 `options: []` + `summary: "Live integrator returned no evidence … Refer to treating oncologist; do not fabricate."` + `claim_layer: "speculative"`。

## 4. 扩展契约 — 加 1 个 integrator 需要做什么

PRD §2.5 + ADR-0004 共同保证:加新 integrator 是**配置题**,不是架构题。具体步骤:

1. 写 `src/opl_cancer/integrators/<source>.py`,继承 `IntegratorBase`,实现 `fetch()` + `family` + `default_ttl`
2. 注册到对应 family (用 `@register_integrator(family="F1")` decorator,或加进 `__init__.py` 的 family map)
3. 在 expert persona 的 `preferred_integrator_families` 里引用 (若需要)
4. 加 `tests/test_integrators/test_<source>.py` (live + mock)
5. 加进 `references/integrator-catalog.md` 表格 + bump CHANGELOG

**不需要改的**:Executor 抽象基类 / Reviewer / Auditor / 主线程编排 / mechanical gate / Wave dispatcher。**这是 v0 架构稳定性的核心承诺**。

## 5. License-Constrained Sources

| Source | 限制 | Workaround |
|---|---|---|
| NCCN | 严格版权,不能全文内置 | `knowledge/nccn_excerpts/` 只摘录关键决策点 + 引用 NCCN 编号 + 时间戳 (G10) |
| Lexicomp | 商业 license,v0 不直接接 | 改用 RxNorm + DrugBank (开源) — see `rxnorm.py` |
| OncoKB | 学术免费 + 商业付费 — v0 走学术 key | API key 必填;`OPL_ONCOKB_KEY` |
| ChiCTR | 无 API,只能 scrape | scrape rate-limit 严守 (1 req/s);失败 raise |
| Unpaywall | 免费但要 email 注册 | `OPL_UNPAYWALL_EMAIL` 必填 |

## 6. Planned v1.3+ Integrators

- ISRCTN (UK trials registry) — v1.2.0 audit I9 标 gap;`isrctn_results` 已经在 trial_matching task input 里但 client 未连
- ESMO / CSCO 指南 (F2 扩展)
- ChEMBL / DrugBank / PubChem (F7 扩展)
- Europe PMC / bioRxiv / Semantic Scholar (F1 扩展)
- FAERS / VigiBase (F10 扩展)

## See also

- [`architecture.md`](architecture.md) — integrator pool 在 8-layer stack 的位置 (L1 G11)
- [`mechanical-gates.md`](mechanical-gates.md) — G11 no-silent-fallback 完整规则
- [`troubleshooting.md`](troubleshooting.md) — "integrator API down" 恢复
- `src/opl_cancer/integrators/base.py` — Integrator ABC
- `src/opl_cancer/integrators/cache.py` — SQLite cache schema
- PRD §2.5 (integrator family), Appendix B (instance inventory)
- ADR-0006 C6 (empty-integrator behaviour)
