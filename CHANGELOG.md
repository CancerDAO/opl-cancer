# Changelog

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
