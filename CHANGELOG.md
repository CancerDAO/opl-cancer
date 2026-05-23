# Changelog

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
