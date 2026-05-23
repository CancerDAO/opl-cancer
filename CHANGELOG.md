# Changelog

## [1.0.4] — 2026-05-24 — Iter 12 (4 new synthetic patients + edge cases)

### Added — golden_set/synthetic_patients
- **`anon_pancreatic_001`** — BRCA2 5946delT germline mPDAC post-FOLFIRINOX/Gem-nabP
  PD; KRAS G12D somatic; HRD-high. Profile + readiness + case_text + timeline
  + NGS + pathology.
- **`anon_gbm_001`** — IDH-wildtype, MGMT-methylated, TERT C228T newly-diagnosed
  GBM, gross-total resection, Stupp planning. Full canonical set.
- **`anon_ped_all_001`** — 8yo F Philadelphia+ B-ALL, induction failure Day33
  MRD 8%, T315I emergence. Declares guardian_consent + pediatric depth
  preferences (memory:feedback_no_false_completion — pediatric safeguards).
- **`anon_myeloma_001`** — 64yo M high-risk MM, t(4;14)+del(17p), R-ISS III,
  early biochemical relapse post-VRd/auto-HSCT/maintenance.

### Edge cases covered
- Pediatric guardian-consent + age-appropriate assent declared.
- Germline BRCA2 placed in `comorbidities` for HRD-aware planning.
- High-risk cytogenetics surfaced in `diagnosis.risk_category` + `molecular`.

### Tests
- **`tests/test_golden_set/test_iter12_new_patients.py`** — 25 tests covering
  directory presence, canonical file presence, profile schema, readiness gate,
  ≥2-bucket requirement (NGS+pathology), pediatric safeguards, BRCA germline
  documentation, high-risk cytogenetics, real-name pattern scan, SYNTHETIC
  marker.
- **`tests/test_e2e/test_wave1_e2e.py`** — extended parametrize to all
  **8 patients** (HCC/NSCLC/CRC/BRCA + pancreatic/GBM/ped-ALL/myeloma) with
  canned LLM responses. memory:feedback_multi_case_validation satisfied:
  ≥2 cancer types, ≥2 patients per axis, 4 new histologies.

### Tests total
- 764 passed, 3 skipped. +41 over v1.0.3.

## [1.0.3] — 2026-05-24 — Iter 11 (Quad Independent Evaluator tool)

### Added
- **`tools/run_quad_evaluation.py`** — generates 4 evaluator prompts
  (architecture / safety / code_quality / ux) + JSON result schema for parallel
  third-party subagent dispatch (memory:feedback_review_via_parallel_subagents,
  memory:feedback_third_party_lens). CLI: `--out evaluator_workspace/`
  optionally `--dimension <one>`.
- **`tools/aggregate_evaluator_verdicts.py`** — validates 4 JSON verdicts,
  computes overall verdict (any-fail-dominates, missing-counts-as-conditional)
  + mean score, writes `evaluator_report.html`.
- **`tests/test_tools/test_quad_evaluator.py`** — 13 tests: dimension parity,
  prompt rejection of paternalistic language, schema shape, aggregation rules
  (all-pass / any-fail / conditional / missing), HTML render, end-to-end run,
  bad-verdict rejection, missing-dir handling.

### Notes
- Tool does NOT itself dispatch subagents — operator (or main-thread Claude)
  hands each prompt to an independent evaluator. Keeps CI deterministic.
- mypy --strict + ruff clean on both tools.

### Tests
- 723 passed, 3 skipped (live, env-gated). +13 over v1.0.2.

## [1.0.2] — 2026-05-24 — Iter 10 patch (MiniMax live integration)

### Added
- **`tests/test_integration/test_minimax_live.py`** — live integration tests
  for MiniMax-M2.7 (api.minimaxi.com/v1/chat/completions). Marked `live`,
  skipped by default; runs when `MINIMAX_API_KEY` env var is set. Validates:
  - Endpoint reachable + 200 status
  - LLMResponse parses cleanly (Pydantic)
  - `response_format={"type": "json_object"}` honoured
  - errcode 2056 surfaces as typed `LLMQuotaError`
  - max_tokens=96000 ceiling accepted (per memory:reference_minimax_llm)
- **`tests/test_integration/test_minimax_live_meta.py`** — meta-tests (run
  unconditionally) verifying live test module imports, `live` marker
  registered in pyproject, verify script syntactically valid, skipif
  scaffolding correct.
- **`scripts/verify_minimax_setup.py`** — manual CLI checks: env present,
  endpoint reachable, json_object completion + parse. Exit codes
  (0/1/2/3/4) for env/transport/parse/quota outcomes.
- **`pyproject.toml`** — declared `live` pytest marker.

### Deferred
- **E2E live variant** (`tests/test_e2e/test_wave1_minimax_live.py`) running
  full Wave1Runner with MiniMax as Reviewer — deferred. Requires real
  MiniMax key + paid budget; not safe to enable by default. Manual operator
  run via `scripts/verify_minimax_setup.py` covers the per-call validation.

### Tests
- 710 passed, 3 skipped (live, env-gated). Full suite green.

## [1.0.1] — 2026-05-24 — Iter 9 patch

### Added — P6 deferred items closed
- **Routing-matrix golden test** (`tests/test_experts/test_routing_matrix.py`):
  26 tests covering 18-expert × task_package portfolio + 4-cancer candidate
  coverage (HCC/NSCLC/CRC/BRCA). Documents intentional `hypothesis_validation`
  overlap (aviv in-silico vs tyler wet-lab) via `SHARED_PACKAGES` registry.
- **Henry L2 LLM disagreement summariser** (`HenryAuditor.summarise_disagreement_axes`):
  async, env-gated, accepts any `LLMClient`; returns
  `{"axes": [...], "summary": "..."}`. Defensive against malformed LLM output
  (non-list axes coerced to `[]`). `response_format={"type": "json_object"}`
  honoured per memory:reference_minimax_llm. memory:feedback_no_offline_only —
  raises on network failure, no silent rule-based fallback when caller invokes
  LLM path.
- **`ProjectMemoryStore.acknowledge_insight()`** —
  propagates `patient_acknowledged_at` into `InsightCard` (schema already had
  field). Raises `KeyError` on missing card; preserves all other fields.

### Tests
- 706 total (was 674) → **+32 new tests**
- All `mypy --strict` + `ruff` clean on touched files
- Full suite `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/ -q` green

### Deferred to a later iter (honest scope)
- **Wave1Runner per-claim L3/L4 card emission rewire** — current runner only
  emits L3 placeholder cards via gate-block path; full Henry-driven per-claim
  card emission inside `_collect_claims` remains. (Iter 9 task #1)
- Iter 10 (MiniMax live integration), Iter 11 (quad-evaluator dispatch tool),
  Iter 12 (4 additional cancer patients + edge cases) — deferred to next
  session per context-budget.

## [1.0.0-p6] — 2026-05-24 — v1.0.0 Release

### Added — Multi-case E2E + Legal + Open-Source Polish

- **Multi-case Wave1 E2E** (`tests/test_e2e/test_wave1_e2e.py`):
  - Parametrise list expanded from 2 → **4 cancer types** —
    HCC (CTNNB1 S37F), NSCLC (EGFR C797S in cis L858R), CRC (KRAS G12D
    post-anti-EGFR), BRCA (HER2+ post-T-DM1)
  - All LLM + integrator calls mocked; each patient produces
    `patient_brief.html` + `provenance.jsonl` with sha256 hashes + three-tier
    label + no command-form leakage
  - Satisfies `memory:feedback_multi_case_validation` — ≥2 cancer types
    cross-sample validation matrix
- **`NOTICE`** (root) — Apache-2.0 attribution + third-party model card
  acknowledgements (Claude/Anthropic, MiniMax) + public data source citations
  (PubMed, ClinicalTrials.gov, ChiCTR, NCCN, OpenFDA, CIViC) per spec §17.6
- **`DISCLAIMER.md`** (root) — explicit "not clinical decision support, not
  doctor substitute, patient sole decision authority" per spec §17.6, with
  safety reporting pathway (`safety@cancerdao.org`, 72-hour response)
- **`tools/sign_contributor_agreement.py`** — first-time contributor signing
  flow per spec §16; writes `governance/contributors/<handle>.json` with
  SHA-256 of agreement text, ISO-8601 UTC timestamp; supports `--dry-run` and
  `--force`; idempotent (raises `FileExistsError` without `--force`)
- **`docs/landing/founder_mode_against_cancer.md`** — landing copy ready for
  cancerdao-global homepage integration; covers 为什么造这个 / 与你一起做的事 /
  谁能用 / 怎么开始 / 如何贡献 / 安全与边界 / 我们相信什么
- **P6 acceptance suite** (`tests/test_p6_acceptance.py`) — enumerates the
  v1.0.0 release gates: NOTICE + DISCLAIMER content, signing-tool dry-run +
  persistence + idempotency, landing copy, 4-cancer-type parametrisation,
  18-expert roster integrity, golden_set 4-patient coverage, pyproject and
  CHANGELOG version bumps

### Changed — Versioning

- `pyproject.toml` `version` → **`1.0.0`** (was `0.0.1`)
- `README.md` status block → v1.0.0

### Deferred to v1.x patch series (P5 carry-over not blocking v1.0.0)

- Wave1Runner per-claim Henry risk-card emission rewire (basics live; full
  L2 disagreement-summariser Claude-call gated by env)
- 15-expert routing-matrix golden test (canned data per task package needed)
- Henry L2 LLM disagreement summariser (Claude-call gated by env)
- `patient_acknowledged_at` propagation to `InsightCard` schema

## [v0.5.0-p5] — 2026-05-24

### Added — Validation Stack

- **Henry 4-layer IRB-substitute auditor** (`src/opl_cancer/validators/henry.py`):
  - L1 forced risk-disclosure-card emission for any L3/L4 claim (spec §8.L1)
  - L2 model-disagreement surfacing from reviewer challenges (rule-based; LLM
    summariser deferred to P6)
  - L3 forced known-serious-risk checklist reading
    `knowledge/serious_risks_per_drug.json`; unknown drugs surface as explicit
    `[unknown drug: ...]` warnings (fail-closed per spec §7 G11 spirit)
  - L4 patient acknowledgment loop — writes pending acks to
    `outstanding/<card_id>.json` with ISO-timestamp `patient_acknowledged_at`
    field; `HenryAuditor.acknowledge()` + `list_pending()` helpers
- **Risk-disclosure-card model + renderer** (`src/opl_cancer/delivery/risk_card.py`):
  - Pydantic v2 `RiskDisclosureCard` with fail-closed cross-field validator
    (must declare ≥1 `known_serious_risks` OR `epistemic_gaps`)
  - HTML-safe rendering (escapes `<script>`, `&`, etc) + Markdown renderer
  - `content_hash()` for provenance integrity (excludes ack/created timestamps)
- **Serious-risks knowledge catalogue** (`knowledge/serious_risks_per_drug.json`):
  - 5 drugs stubbed (atezolizumab / bevacizumab / osimertinib / pembrolizumab /
    trastuzumab) with INN + class + ≥2 known serious risks each
- **CLI ack loop** — two new subcommands in `opl-cancer`:
  - `opl-cancer acknowledge <card_id>` — patient marks a pending card
    acknowledged with UTC-ISO timestamp
  - `opl-cancer list-pending-acks` — lists awaiting cards (level + claim preview)

### Added — Reviewer pairings (spec §2.2 rotation)

- `models.yaml.reviewer_pairings` populated for all 18 roster experts:
  - Genomics ↔ Pharmacology: bert↔aviv
  - Bioinformatics ↔ Pharmacology: mary↔tyler
  - Clinical ↔ Trial matching: rosa↔rick
  - Toxicity ↔ Clinical: iain↔heddy
  - Translational ↔ Mechanism: ted→aviv, vince→aviv, hong→bert
  - Supportive ↔ Clinical: jen→rosa, kieren→rosa, mark→iain
  - EAP ↔ Cross-border: frances↔dennis
  - Specialised: riad→ted, steve→tyler
- Acceptance: ≥15 pairings populated; no self-review; all reviewers in roster.

### Added — Operator tools (`tools/`)

- **`tools/reproduce.py`** — given `<patient_dir> <run_id>`, loads the
  per-run provenance.jsonl and verifies recipe is reproducible
  (prompt_versions pinned + claim_hashes present + models recorded). Exits 0 on
  reproducible, 2 on missing artifact / gap.
- **`tools/verify_provenance.py`** — recomputes the sha256 of every entry's
  hashable payload and compares against stored `claim_hash` / `content_hash`.
  Reports `matches`, `mismatches`, `no_hash`. Exits 0 on all-match, 1 on any
  mismatch.

### Added — Golden set expansion (`validators/golden_set/`)

- **+2 synthetic patients** (now 4 distinct cancer types):
  - `anon_crc_001` — colorectal MSS KRAS-G12D, post-FOLFIRI+cetuximab PD
  - `anon_brca_001` — breast HER2+ post-T-DM1 recurrence
- **+5 failure-mode inputs** (now 8 total, ≥6 distinct gates exercised):
  - `drug_name_confusion_input.json` (G3)
  - `dose_unit_input.json` (G4)
  - `batch_effect_input.json` (G15)
  - `cherry_pick_input.json` (G16)
  - `retraction_cascade_input.json` (G9 cascade)
- **New `regression_anchors/`** (≥2 anchors):
  - `cf_pici_co_sci.json` — Co-Sci tournament anchor
  - `ripasudil_robin.json` — Robin drug-repurposing anchor
- **New `boundary_cases/`** (≥3 cases):
  - `empty_ngs.json`, `fifty_plus_files.json`, `contradicting_reports.json`

### Closed — P4.5 deferred items

- **RxNorm → Mary** integrator-dict wiring verified via constructor contract
- **NMPA + FDA EAP → Frances** wiring verified
- **CT.gov + ChiCTR → Dennis + Rick** wiring verified
- All four contract tests in `tests/test_p5_integrator_wiring.py`

### Tests

- **+160 tests** in 4 new files (501 → 661):
  - `tests/test_p5_acceptance.py` (33 — top-level acceptance)
  - `tests/test_p5_golden_set_per_file.py` (49 — per-fixture parametrised)
  - `tests/test_p5_henry_deep.py` (71 — per-drug + per-pairing parametrised)
  - `tests/test_p5_integrator_wiring.py` (7 — async integrator routing)

### Deferred (honest)

- **LLM-backed Henry L2 disagreement summariser** — currently rule-based
  pass-through of reviewer challenges. P6 will add a Claude-summarised
  disagreement-axis renderer.
- **Wave1Runner.run integration of risk_card emission** — Henry can be called
  per-claim, but Wave1Runner does not yet auto-emit risk cards into the brief
  HTML output. P6.
- **15-expert routing-matrix golden test across HCC + NSCLC** — partial; only
  smoke-imports validated. Full routing matrix deferred to P6 wave-runner
  integration work.
- **`patient_acknowledged_at` propagation to memory store schemas** — currently
  written only to `outstanding/` JSON. Memory-store schema field deferred to P6.

### Acceptance criteria met

- 661 tests passing (target ≥600 exceeded by 61).
- `ruff check src tests tools` clean.
- All 4 P5 task buckets (T1-T9) shipped to production-grade.
- memory:feedback_no_offline_only — Henry refuses to construct without serious-
  risks catalogue (fail-loud on missing knowledge).
- memory:feedback_no_false_completion — deferred items above explicitly listed.

## [v0.4.5-p4.5] — 2026-05-24

### Added

- **Expert Batch E — 3 deferred experts shipped** (Kieren / Mark / Dennis):
  - `KierenExpert` (Infectious Disease, Kieren Marr archetype) — portfolio `neutropenic_fever_management`; families F1/F8. Demands MASCC score + IDSA empiric regimen + pseudomonal-coverage invariant + fungal escalation trigger.
  - `MarkExpert` (Endocrinologist irAE) — portfolio `ici_endocrine_irae`; family F1. Demands CTCAE grade + adrenal-axis safety check before T4 replacement + ASCO 2021 / ESMO 2022 anchored steroid algorithm.
  - `DennisExpert` (Cross-Border Coordinator, Dennis Lo 卢煜明 archetype) — portfolio `cross_border_navigation`; families F3/F8. Mandatory L4 boundary disclosure (founder-mode discipline) + cost_model + visa_pathway_url; refuses "guaranteed" framing.

- **3 new persona files** under `prompts/experts/{kieren,mark,dennis}/persona.md` — each with three-tier discipline + Anti-patterns + non-imperative output rules.

- **3 new task prompt files** under `prompts/tasks/`:
  - `neutropenic_fever_management.md` — MASCC + IDSA + pseudomonal + fungal escalation invariants
  - `ici_endocrine_irae.md` — CTCAE grade + adrenal_axis_checked + ici_hold_decision
  - `cross_border_navigation.md` — jurisdiction + cost_model + visa_pathway + L4 disclosure mandatory non-empty

- **`Wave4Runner` hypothesis-validation orchestrator** (`src/opl_cancer/glue/wave4_runner.py`):
  - Mirrors Wave3Runner pattern: Aviv leads data-anchored verdict, Iain meta-validates (Cochrane lens)
  - Classifies each top-K hypothesis as `validated` / `falsified` / `inconclusive`
  - Writes `triggers/<run_id>/wave4_validation.json` + provenance.jsonl (≥2 stages per hypothesis)
  - Main-thread sequential awaits per ADR-2026-04-22

- **`G7ImperativeDetectorGate`** (`src/opl_cancer/validators/gates/g7_imperative_detector.py`):
  - failure_mode_code `C1` — scans recursive walk of all string fields for imperative patterns
  - Detects EN ("you should/must", "must give/start/take/stop", "start immediately") + ZH ("应该", "必须", "建议立即", "立即停用", "立即开始")
  - PASS only if sentence has both PMID/NCT/URL evidence AND a risk caveat keyword ("may"/"risk"/"side effect"/"可能"/"副作用"/"风险"); otherwise FAIL+block=True
  - Catches nested fields like `symptom_plan[].intervention`

- **36 new tests** (501 total, up from 465):
  - `tests/test_experts/test_batch_e.py` — 18 tests (portfolio + persona + L4 boundary on Dennis + adrenal-axis on Mark + MASCC on Kieren + 18-expert roster completeness)
  - `tests/test_validators/test_g7_imperative_detector.py` — 8 tests (clean pass / EN imperative fail / ZH imperative fail / imperative+evidence+risk pass / imperative+evidence-no-risk fail / nested symptom_plan / NCT pass / failure_mode_code = C1)
  - `tests/test_e2e/test_wave4_runner.py` — 4 tests (validated / falsified / inconclusive / artifacts written)
  - `tests/test_p4_5_acceptance.py` — 6 tests (roster=18 / modules importable / G7 wired / Wave4Runner wired / 3 task prompts present / 3 personas present)

### Roster status
- v0 roster now complete: **18/18 experts** wired with portfolios + personas + task templates.

### Deferred to P5 (explicit)
- F10 RxNorm wiring to Mary integrator dict (currently a fake integrator in tests).
- Frances→NMPA+FDA EAP integrator wire (currently fake).
- 15-expert routing matrix golden test across HCC + NSCLC patients (P5 router benchmark).
- BixbenchRunner live-mode (P3 shipped dry-run + env-gated live).

### Acceptance
- 501 pytest passing (PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, ~2.2s wall-time, all LLM + HTTP mocked).
- `mypy --strict src/opl_cancer` — clean (95 source files).
- `ruff check src/ tests/` — clean.
- Tag `v0.4.5-p4.5`.

## [v0.4.0-p4] — 2026-05-24

### Added

- **Expert Batch D — 6 of 9 shipped** (Mary / Ted / Riad / Jen / Frances / Steve):
  - `MaryExpert` (Pharmacologist, Mary Relling archetype) — portfolio `ddi_adme_dosing`; families F1/F10. Demands RxNorm `rxcui` + TPMT/DPYD/UGT1A1 phenotype surfacing.
  - `TedExpert` (Radiation Oncologist, Theodore Lawrence archetype) — portfolio `radiation_planning`; families F1/F2. Demands BED10 + OAR constraint table + QUANTEC/TG-101 anchoring.
  - `RiadExpert` (Interventional Oncologist, Riad Salem archetype) — portfolio `interventional_oncology`; families F1/F2. Demands Child-Pugh + BCLC + thermoprotection flag.
  - `JenExpert` (Palliative Specialist, Jennifer Temel archetype) — portfolio `palliative_symptom_qol`; family F1. Demands ESAS + morphine equivalents + mandatory bowel-regimen flag on opioid plans.
  - `FrancesExpert` (Expanded Access Navigator, Frances Kelsey archetype) — portfolio `expanded_access_navigation`; families F3/F8. Mandatory L4 boundary disclosure on every option; refuses "guaranteed" framing.
  - `SteveExpert` (Nutritionist, Stephen Heber archetype) — portfolio `oncology_nutrition`; families F1/F2. Demands PG-SGA score + cachexia stage + ROS-window caveat for concurrent antioxidants.

- **6 new persona files** under `prompts/experts/{mary,ted,riad,jen,frances,steve}/persona.md` — each ≥30 lines, three-tier discipline, Anti-patterns section, founder-mode no-paternalism stance.

- **6 new task prompt files** under `prompts/tasks/`:
  - `ddi_adme_dosing.md` — RxNorm-anchored DDI screen, severity, pgx implications, renal/hepatic adjustments
  - `radiation_planning.md` — dose / fractions / BED10 / OAR table / re-irradiation flag
  - `interventional_oncology.md` — modality / Child-Pugh / BCLC / intent
  - `palliative_symptom_qol.md` — ESAS scores / opioid mg + MED / mandatory bowel regimen
  - `expanded_access_navigation.md` — L4 boundary mandatory non-empty; jurisdiction explicit
  - `oncology_nutrition.md` — PG-SGA / kcal-protein target / supplement-DDI cross-ref / ROS window caveat

- **PI intent_parser LLM upgrade** (`PISession.classify_intent_llm`):
  - Replaces P0 `classify_intent_stub` for live deployments (memory:feedback_default_prompt_over_script)
  - Loads `prompts/pi/intent_parser.md` via `PromptTemplate`
  - Raises `LLMResponseParseError` on bad JSON / unknown intent / missing key (G11 contract — no silent degradation)
  - `IntentClass` enum extended with `HYPOTHESIS_REQUEST` (routes to Wave 2 tournament per intent_parser.md)
  - Stub retained for offline CI fallback; updated to also detect `HYPOTHESIS_REQUEST` keywords

- **34 new tests** (465 total, up from 431):
  - `tests/test_experts/test_batch_d.py` — 21 tests (portfolio + persona discipline + task template invariants + per-expert anchors)
  - `tests/test_orchestrator/test_pi_session_llm.py` — 8 tests (LLM happy paths for 3 intents + 3 failure modes + enum extension + stub fallback)

### Deferred to P4.5 (honest scope limit per memory:feedback_no_false_completion)

- KierenExpert (Infectious Disease — neutropenic fever)
- MarkExpert (Endocrinologist — ICI irAE endocrine)
- DennisExpert (Cross-Border Coordinator — US/JP/EU)
- Wave 4 `hypothesis_validation` runner (P2 hypotheses ↔ P3 data; Aviv + Iain integration)
- Patient brief polish + imperative-detector strict gate + three-tier strict gate
- F10 RxNorm integrator wiring (persona references it; integrator already exists from P1 — Mary instance not yet auto-wired)

### Plan

- `docs/superpowers/plans/2026-05-24-opl-cancer-p4-pi-integration.md` (~96 lines)

## [v0.3.0-p3] — 2026-05-24

### Added

- **Expert Batch C extensions:**
  - `TylerExpert` (Wet-Lab Designer, Tyler Jacks archetype) — portfolio `hypothesis_validation`, `in_silico_experiment_design`; preferred F6/F7
  - `prompts/experts/tyler/persona.md` (KP/KPC mouse model archetype, falsifiable-experiment-first methodology)
  - `AvivExpert` portfolio extended with `dataset_acquisition`, `bioinformatics_data_analysis`, `hypothesis_validation`; preferred families now F1/F4/F6/**F7**

- **5 new omics integrators:**
  - `GEOIntegrator` (F6) — NCBI GEO via eutils `db=gds` (GSE/GDS/GPL/GSM + `search:` prefix; 7-day TTL)
  - `ArrayExpressIntegrator` (F6) — EBI BioStudies API for E-MTAB / E-GEOD accessions
  - `SRAIntegrator` (F6) — NCBI SRA runinfo via eutils for SRR/SRP/SRX/SRS
  - `DepMapIntegrator` (F7) — Broad DepMap portal CRISPR gene effect + dependency probability (30-day TTL)
  - `CCLEIntegrator` (F7) — DepMap portal CCLE expression (TPM) by gene × DepMap_ID
  - All raise `IntegratorError` on transport / HTTP / empty result (memory:feedback_no_offline_only)

- **bixbench Docker compute runtime (`compute/`):**
  - `compute/bixbench.Dockerfile` — lifted from `robin/finch/src/fhda/Dockerfile.pinned` (miniconda3 + R 4.3.3 + bioconda DESeq2 / EnhancedVolcano / clusterProfiler / gseapy / FastQC / scanpy stack)
  - `compute/runner.py` — `BixbenchRunner` env-gated wrapper (`OPL_BIXBENCH_LIVE=1` for live docker invocation; dry-run otherwise). Returns `BixbenchRunResult` dataclass with mode + image + docker_cmd + workdir + timeout
  - Image tag: `opl-cancer/bixbench:v0.3.0-p3`. CI does NOT build the image — smoke tests only verify Dockerfile presence + runner protocol shape

- **5 new task prompt files** (`prompts/tasks/`):
  - `dataset_acquisition.md` — G14 dataset-patient match scoring (cancer-type / stage / platform / size / control)
  - `bioinformatics_data_analysis.md` — required steps + falsification rule + compute estimate
  - `single_cell_reanalysis.md` — QC + integration + clustering + DA + pathway
  - `pathway_enrichment.md` — ORA + GSEA with BH correction (G15)
  - `hypothesis_validation.md` — support_score / verdict / claim-layer transition + smallest wet-lab experiment

- **Wave 3 data-evidence runner (`Wave3Runner`):**
  - `glue/wave3_runner.py` — sequential `dataset_acquisition` (Aviv) → per-top-hyp `bioinformatics_data_analysis` (Aviv + dry-run BixbenchRunner) → `hypothesis_validation` (Tyler if present, else Aviv)
  - Writes `triggers/<run_id>/wave3_data_evidence.json` + `provenance.jsonl`
  - Per ADR-2026-04-22 main-thread sequential awaits (no asyncio.gather spawning)

- **59 new tests** (431 total, up from 372):
  - `tests/test_integrators/test_geo.py` — 6 tests
  - `tests/test_integrators/test_arrayexpress.py` — 4 tests
  - `tests/test_integrators/test_sra.py` — 4 tests
  - `tests/test_integrators/test_depmap.py` — 4 tests
  - `tests/test_integrators/test_ccle.py` — 4 tests
  - `tests/test_experts/test_tyler.py` — 5 tests (incl. Aviv extension assertion)
  - `tests/test_experts/test_p3_task_prompts.py` — 2 tests
  - `tests/test_compute/test_runner.py` — 7 tests (image tag / dry-run / command shape / live-mode missing-docker / env gate / round-trip / Dockerfile present)
  - `tests/test_e2e/test_wave3_runner.py` — 4 tests
  - `tests/test_p3_acceptance.py` — 19 parametrised tests

### Deferred to P4+

- Live bixbench image build in CI (Dockerfile committed but not built — gated)
- DepMap/CCLE schema-drift adapter (quarterly release tracking)
- meta_analysis Wave-3 data integration extension (Iain) — added in P2 task list but not yet bridged to Wave3 output

## [v0.2.0-p2] — 2026-05-24

### Added

- **Expert Batch B (assumption/repurposing族):**
  - `IainExpert` (Meta-Analyst) — portfolio `meta_analysis`, `cross_source_consistency`; preferred F1/F2/F4
  - `AvivExpert` (Bioinformatician) — portfolio `hypothesis_generation`, `pathway_enrichment`, `single_cell_reanalysis`; preferred F1/F4/F6
  - `prompts/experts/iain/persona.md` + `prompts/experts/aviv/persona.md` (Cochrane / Regev archetypes)
  - New task prompts: `prompts/tasks/meta_analysis.md` + `prompts/tasks/hypothesis_generation.md`

- **Co-Sci-style hypothesis tournament machinery (`orchestrator/`):**
  - `EloTournament` — extends P0 `EloRater` (alias preserved). `pair_rotation`, `apply_round`, `top_k`, `convergence_check` (spec §17.5 P2 early-stop)
  - `DebateJudge` — LLM-driven pairwise comparator (G13 reviewer model); JSON-parse-safe (lift from `open-coscientist/agents/ranking.py`)
  - `MetaCritiqueAggregator` — round-N → round-N+1 critique propagation (lift from `open-coscientist/agents/meta_review.py`)
  - `HypothesisGenerator` — 4 strategies (`literature_gap` / `cross_domain` / `novel_mechanism` / `feasibility_first`); meta-critique + EXPERIMENTAL_INSIGHTS injection points (lift from `open-coscientist/agents/generation.py`)
  - `EvolutionStrategist` — 6 strategies (`combination` / `simplification` / `extension` / `analogy` / `resilience` / `outside_box`); parent_chain preserved (lift from `open-coscientist/agents/evolution.py`)
  - `Reflector` — 6 modes (`basic` / `simulation` / `observation` / `deep_verification` / `full_review` / `falsification`) returning verdict `passes`/`weakened`/`falsified` (lift from `open-coscientist/agents/reflection.py`)
  - `tournament_loop.run_tournament` — multi-round loop with convergence early-stop; mutates Hypothesis Elo + meta_critique_inherited in place

- **Robin lit-loop integration:**
  - `ExperimentalInsightsFeedback` — Robin `EXPERIMENTAL_INSIGHTS_APPENDAGE` adapter (lift from `robin/robin/robin/prompts.py`). Injects round results into next-round Generation prompts
  - `PaperQA2Integrator._paperqa_query` — full PaperQA2 wrapper (replaces P1 LiteRAG-only fallback). Wraps `paperqa.Docs.aadd` + `paperqa.Docs.aquery`. LiteRAG fallback retained when `paper-qa` not installed

- **Wave 2 hypothesis-generation end-to-end orchestrator (`Wave2Runner`):**
  - 4-strategy generation → 2-evolution → tournament loop → top-3 reflection (basic + falsification)
  - Writes `triggers/<run_id>/wave2_hypotheses.json` + provenance.jsonl
  - Per ADR-2026-04-22 main-thread only

- **PI intent extension:** `HYPOTHESIS_REQUEST` added to `prompts/pi/intent_parser.md` — triggers Wave 2 dispatch when patient asks "what novel directions exist?"

- **Memory schema additions (`memory/schemas.py`):**
  - `Hypothesis` (id/text/elo_rating/status/parent_chain/generation_strategy/evidence_refs/meta_critique_inherited/rationale) — defaults to `claim_layer=speculative` per founder-mode philosophy
  - `TournamentRound` (round_id/wave_index/participants/pairings/outcomes/elo_deltas/meta_critique)
  - `TournamentOutcome` (a/b/winner/reason)

- **82 new tests** (372 total, up from 290):
  - `tests/test_memory/test_hypothesis_schema.py` — 6 tests
  - `tests/test_orchestrator/test_elo_tournament.py` — 9 tests
  - `tests/test_orchestrator/test_debate_judge.py` — 5 tests
  - `tests/test_orchestrator/test_meta_critique.py` — 4 tests
  - `tests/test_orchestrator/test_generation.py` — 6 tests
  - `tests/test_orchestrator/test_evolution.py` — 7 tests
  - `tests/test_orchestrator/test_reflection.py` — 7 tests
  - `tests/test_orchestrator/test_experimental_insights.py` — 4 tests
  - `tests/test_orchestrator/test_tournament_loop.py` — 5 tests
  - `tests/test_experts/test_iain_aviv.py` — 8 tests
  - `tests/test_glue/test_wave2_runner.py` — 4 tests
  - `tests/test_integrators/test_paperqa.py` (+2 new for PaperQA2 wrapper)
  - `tests/test_e2e/test_p2_hypothesis_e2e.py` — 1 test
  - `tests/test_p2_acceptance.py` — 14 tests

### Validation

- 372 tests pass (`pytest tests/`)
- `ruff check src/ tests/` green
- `mypy --strict src/` green (75 files)
- All LLM calls mocked (no real network); PaperQA2 paperqa module monkey-patched in tests

### Tag

`v0.2.0-p2`

---

## [v0.1.0-p1] — 2026-05-24

### Added

- **6 Expert Batch A (clinical interpretation D1):** Rosa / Bert / Vince / Rick / Heddy / Hong
  - Each with persona prompt + task-package prompt + LLMBackedExpert wrapper
  - Roster `portfolio` + `preferred_families` declared per expert
- **15 Integrator concrete clients (F1-F5 + F8 partial + F10 backbone):**
  - **F1 Literature:** PubMed / Unpaywall / PaperQA2 (LiteRAG fallback) / RetractionDB
  - **F2 Guidelines:** NCCN PageIndex (HCC + NSCLC 2025 excerpts)
  - **F3 Trials:** ClinicalTrials.gov v2 / ChiCTR
  - **F4 Genomics Knowledge:** OncoKB / CIViC / ClinVar / gnomAD
  - **F5 Cohorts:** cBioPortal / GDC
  - **F8 Drug Access:** NMPA EAP / FDA EAP
  - **F10 Drug Safety (backbone):** RxNorm
- **5 mechanical gates (P1-relevant subset of spec section 7):**
  - G1 PMID-existence (PubMed-resolved)
  - G2 PMID-quote-match (PaperQA2 retrieval-backed)
  - G3 Drug-normalization (RxNorm-backed)
  - G9 Retraction-check (RetractionDB-backed)
  - G11 No-silent-fallback (integrator contract)
- **LLM client infrastructure:**
  - `AnthropicClaudeClient` + `MiniMaxClient`
  - `ModelRouter` enforcing G13 (executor != reviewer model family)
  - `PromptTemplate` (Jinja2 + StrictUndefined) + `find_prompts_root`
- **Wave 1 end-to-end orchestrator (`Wave1Runner`):**
  - intent -> planner -> fanout (parallel experts) -> reviewer audit -> render
  - Writes `delivery/patient_brief.{html,md}` + `provenance.jsonl`
  - Depth <= 1 RuntimeError enforced (closes P0 loop-back)
- **Patient brief renderer (`PatientBriefRenderer`):**
  - HTML + Markdown variants
  - Three-tier labels (established / exploratory / speculative)
  - PMID links -> pubmed.ncbi.nlm.nih.gov/{id}
  - Risk-card-at-top + reviewer-challenges section
  - Provenance hash per claim (sha256: prefix)
- **Patient case loader (`PatientCaseLoader`):**
  - profile.json + readiness.json + 11 buckets -> typed dict
- **2 synthetic golden-set patients (clinically plausible, no real PHI):**
  - `anon_hcc_001` — HCC HBV+ TACE-refractory + Atezo+Bev PD (3L decision)
  - `anon_nsclc_001` — NSCLC EGFR L858R + emergent C797S in cis (post-osimertinib)
- **3 failure-mode golden inputs:**
  - `fake_pmid_input.json` (blocked by G1)
  - `retracted_pmid_input.json` (blocked by G9)
  - `imperative_command_input.json` (G7 deferred to P5, documented)
- **Independent third-party evaluator dispatcher (`scripts/dispatch_e2e_evaluator.py`):**
  - 6-dimension prompt + verdict JSON schema
  - Operator dispatches via `/superpowers:dispatching-parallel-agents`
- **Parametrised E2E test:** Wave1Runner on both synthetic patients (mocked LLM + integrators)

### Changed

- **`dispatch_wave` is now async** with real concurrency via `asyncio.gather` + semaphore
  - Depth <= 1 RuntimeError assert closes P0 loop-back
- **Integrator base class is async** (`async def fetch`) with `cached_fetch` TTL helper
- **CHANGELOG policy:** enumerated per-PR entries (no more empty `[Unreleased]` blocks)
- Acceptance test file renamed: `test_p0_acceptance.py` -> `test_p1_acceptance.py`

### Fixed (P0 loop-back items)

- `test_acceptance_pytest_runs` tautology -> renamed/expanded with real assertions
- `test_dispatch_wave_respects_concurrency_limit` -> augmented with real-concurrency speedup test
- `classify_intent_stub` removed from P0 path: Wave1Runner uses LLM-backed intent parser

### Deferred

- G4-G8 + G10 + G12 / G14-G20 mechanical gates -> P5
- Co-Sci tournament loop (open-coscientist lift) -> P2
- Wave 2-5 hypothesis / data analysis / validation -> P2-P4
- Compute runtime bixbench Docker -> P3
- 12 remaining experts (Mary/Aviv/Tyler/Iain/Ted/Riad/Jen/Kieren/Mark/Frances/Dennis/Steve) -> P2-P4
- TBD MAINTAINERS.md slots -> P6
- Substrate license-compatibility audit (ADR-0001 follow-up) -> P6

### Acceptance criteria met

- >= 150 tests passing (target enforced by `test_acceptance_total_test_count_threshold`)
- All 6 experts importable + portfolio declared
- All 15 integrators importable
- All 5 P1 gates registered + contract-tested
- Wave1Runner end-to-end on 2 patients with 2 distinct cancer types
- Real LLM API integration (Claude executor × MiniMax reviewer) gated on env keys

## [v0.0.1-p0] — 2026-05-23

Initial scaffold (memory + provenance + orchestrator stubs + ADR-0001..0005 + Apache-2.0).
