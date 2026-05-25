# OPL for Cancer — Technical Report

**Version**: 1.5.7 (2026-05-26)
**Repo**: github.com/CancerDAO/opl-cancer
**License**: Apache-2.0
**Status**: Production-running, actively iterated. Not a clinical decision-support device. Not for emergencies. See [`DISCLAIMER.md`](DISCLAIMER.md).

---

## 1 · Purpose in one paragraph

OPL ("One Person Lab") is an open-source agent skill that runs a **multi-expert AI scientist team for a single cancer patient**. The patient hands over a folder of records (PDFs, images, NGS reports, lab CSVs) and a verbatim goal sentence; the skill produces (a) a research-grade `pi_delivery.md` with every claim PMID-anchored, three-tier-labelled (established / exploratory / speculative), and provenance-hashed, and (b) a plain-language `patient_plain_brief` with a conclusion-first three-sentence bottom line in lay vocabulary. Between input and delivery sits a 5-Wave research lifecycle, 18 named experts under one Sid PI, 30 live data integrators (PubMed, cBioPortal, GEPIA3, ChiCTR, ClinicalTrials.gov, etc.), a 27-gate no-LLM safety stack, and Henry — the IRB-substitute auditor. The patient is the sole decision authority; no human-in-the-loop external sign-off, no paternalism.

---

## 2 · First-principles design contract

These are the non-negotiables. Every architectural decision must trace back to one of them; every regression that violates one is a P0 fix.

| # | Contract | Means | Failure mode it prevents |
|---|---|---|---|
| 1 | **Produce *unknown new information*, not summary of known** | Wave 3 must run a real dataset query / cohort projection / Monte Carlo / meta-analysis. Retrieval (Wave 1) alone is **not** OPL output. | The v1.4 false-completion case: rendered a "complete" delivery while Wave 3 had been silently skipped. |
| 2 | **No false completion** | Any "ok / done / 完成" signal is backed by file paths + content + sample-verification | Claiming pipeline ran when only `mkdir -p` happened |
| 3 | **No silent fallback** (G11) | Network unreachable → raise, not LLM-guess; broken `models.yaml` → raise, not empty dict | Hallucinated medical content when API was down |
| 4 | **Every claim PMID-anchored or 3-tier labelled** | If you can't cite, you mark it `speculative` | Confident-sounding unsourced output |
| 5 | **Reviewer ≠ executor** (G13) | Hypothesis-generator LLM family ≠ Reviewer LLM family | Single-model self-confirmation echo chamber |
| 6 | **Patient is sole decision authority** | No imperative voice (G7), no "you must / 必须 / should", no paternalism — only options + their evidence | Skill becoming a doctor-replacement |
| 7 | **Founder-mode** | No external IRB sign-off gate; safety is built in as a separate validator stack, not a human-in-the-loop | Skill dying in compliance theater while patients wait |
| 8 | **Honest about what we don't have** | If Wave 3 fails, Section 0 of the patient brief says so plainly — not "complete" delivery with carry-forward gaps hidden | Hidden uncertainty → patient making a decision they wouldn't make if they knew |
| 9 | **Prompt > Python for generalisation** | LLM judgement (planner / classification / extraction) lives in prompt files; Python is for orchestration, persistence, integrators, gates | Hardcoded keyword lists that don't generalise across patient varieties |

---

## 3 · System architecture

```
                ┌─────────────────────┐
                │  Patient input      │  PDF / images / NGS / labs / verbatim goal
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │  Sid · PI            │  main-thread Claude (orchestrator)
                │  intent_parser →     │  → reads goal, builds profile.json
                │  planner →           │  → emits plan.json (cancer-type row + comorbid triggers)
                └──────────┬──────────┘
                           │
                           ▼
   ┌────────────────────────────────────────────────────────────────┐
   │ Wave 1 · Retrieval (parallel fanout, 10 experts default)         │
   │  Rosa │ Bert │ Vince │ Rick │ Heddy │ Mary │ Iain │ Mark │       │
   │  Frances │ Hong         each → tasks/w1_*/report.md              │
   └────────┬────────────────────────────────────────────────────────┘
            ▼
   ┌────────────────────────────────────────────────────────────────┐
   │ Wave 2 · Hypothesis tournament                                  │
   │  Aviv generates 12-20 H-cards                                   │
   │  Co-Sci Elo pairwise (4 rounds × N pairs, k=32)                 │
   │  Meta-critique aggregator + Robin lit-loop                      │
   │  → tournament/round_*.json + meta_critique_chain + insights     │
   └────────┬────────────────────────────────────────────────────────┘
            ▼
   ┌────────────────────────────────────────────────────────────────┐
   │ Wave 3 · Data-evidence  · NON-SKIPPABLE critical path           │
   │  cBioPortal cohort  │  GEPIA3 TCGA+GTEx  │  ctDNA Monte Carlo   │
   │  DerSimonian-Laird meta-analysis  │  Cox / KM  │ bixbench Docker│
   │  or native Python (DESeq2 / scanpy / lifelines / PythonMeta)    │
   │  → data/cohorts/*.csv  + data/meta_analysis/  + data/figures/   │
   └────────┬────────────────────────────────────────────────────────┘
            ▼
   ┌────────────────────────────────────────────────────────────────┐
   │ Wave 4 · Validation                                              │
   │  Each leading hypothesis re-tested against Wave-3 measured data  │
   │  Confidence delta > 0.4 ⇒ promote/demote three-tier label        │
   │  → tasks/w4_*/report.md (per hypothesis, after-data)             │
   └────────┬────────────────────────────────────────────────────────┘
            ▼
   ┌────────────────────────────────────────────────────────────────┐
   │ Wave 5 · Dual delivery                                           │
   │  patient_plain_brief.html/.md  ← Section 0 conclusion-first      │
   │  pi_delivery.md                ← full PMID-anchored evidence     │
   └─────────────────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────────────────┐
   │ Henry · IRB-substitute auditor  (audits ALL wave outputs)        │
   │  L1 mechanical_gates    27 no-LLM gates G1-G27                   │
   │  L2 disagreement_summariser  surfaces model disagreement         │
   │  L3 permission_gate     risk-card + patient ack flow             │
   │  L4 rollback            claim withdraw + BFS cascade             │
   └─────────────────────────────────────────────────────────────────┘
```

The Mermaid version of this diagram is rendered inline in [`README.md`](README.md#系统架构).

---

## 4 · 5-Wave lifecycle in detail

### Wave 1 — Retrieval (parallel fanout)

**Purpose**: Surface world-known information per the patient's cancer type, line of therapy, and molecular profile. **Not** the deliverable — this is the input to Wave 2.

**Default expert set** (planner expands per cancer-type row in `SKILL.md`):
- **Rosa** — pathology, staging, IHC interpretation
- **Bert** — molecular genomics, NGS variant interpretation
- **Vince** — clinical oncology, lines of therapy, NCCN/CSCO alignment
- **Rick** — trial matching (CT.gov / ChiCTR / ISRCTN / EU-CTR / HKCTR)
- **Heddy** — imaging cadence + RECIST 1.1
- **Mary** — DDI + dosing × CKD / hepatic / cardiac comorbidity
- **Iain** — literature deep-search (PubMed / Europe PMC / Semantic Scholar / bioRxiv + Retraction Watch dedupe)
- **Mark** — irAE / immune-related toxicity + rechallenge schema
- **Frances** — EAP / compassionate use / cross-border (FDA / EMA / NMPA / HK)
- **Hong** — China-specific (NMPA + 医保 reimbursement + CN herb DDI)

**Per-expert task primitives** (`src/opl_cancer/experts/base.py`): `plan`, `execute`, `review`, `audit`, `integrate`, `feedback`. `execute` is real LLM-driven; `plan`, `audit`, `feedback` are P1 stubs that emit `StubMethodWarning` so callers know (spec §2.2 honesty).

**Cross-expert peer review**: every `execute` output goes through `review()` by a different reviewer model (G13 enforced). Per-reviewer prompts are uniform (a known design simplification) — true differentiation would need expert-specific reviewer prompts and is a v1.6 decision.

### Wave 2 — Hypothesis tournament (Co-Sci style)

**Purpose**: Convert Wave 1's retrieval into **falsifiable hypotheses** + rank them. Modeled after [Google's Co-Scientist](https://arxiv.org/abs/2502.18864).

**Pipeline**:
1. Aviv (hypothesis generator) emits 12-20 H-cards from Wave 1 reports.
2. `EloTournament.pair_rotation()` generates round-robin pairs.
3. `DebateJudge.judge_pair()` LLM-judges each pair on novelty / plausibility / patient relevance / falsifiability. Reviewer ≠ executor (G13).
4. `MetaCritiqueAggregator` produces structured JSON critique per round.
5. **Robin lit-loop** (v1.5.7): round-N `experimental_insights` feeds into round-N+1 judge prompt via the `experimental_insights=` arg.
6. Convergence early-stop: top-1 Elo delta < threshold across N consecutive rounds → break.

**Code refs**: `src/opl_cancer/orchestrator/{tournament,tournament_loop,debate,meta_critique,experimental_insights}.py`. Tests: `tests/test_orchestrator/test_{elo_tournament,tournament_loop,debate_judge,experimental_insights}.py`.

### Wave 3 — Data-evidence  **(non-skippable)**

**Purpose**: Produce **new information** — the OPL contract. Retrieval (Wave 1) + hypothesis ranking (Wave 2) without Wave 3 = "thoughtful summary of known", not OPL.

**Operations**:
- **Cohort extraction**: cBioPortal + MSK-IMPACT + TCGA — filter to patient-matched stratum (molecular + line + age).
- **Survival projection**: `lifelines` Cox / Kaplan-Meier with patient covariates.
- **Transcriptomic axes**: GEPIA3 (TCGA + GTEx) — differential expression, survival, correlation queries. Default for any TCGA-mappable cancer.
- **ctDNA Monte Carlo**: 5000 trajectories from baseline VAF, conditioned on responder/non-responder priors from trial literature.
- **DerSimonian-Laird meta-analysis**: random-effects, I² heterogeneity, subgroup ORR.
- **Bioinformatics compute**: bixbench Docker (canonical) or native Python (`NativeAnalysisRunner` fallback — DESeq2 via rpy2 / scanpy / lifelines / PythonMeta).

**Non-skippable enforcement (v1.5.7)**:
- `cli.py wave3` is now a **state-reader**, not a pretend-runner. It probes `triggers/<run_id>/data/` for real artifacts (CSV / JSON / ipynb / PNG). Empty → exit non-zero + `ok: false` + `requires_main_thread_dispatch: true` + `action: "..."` so the LLM orchestrator knows to dispatch the real path.
- `preflight` (`cli.py preflight`) checks Docker + native fallback. G13 reviewer-distinct is a hard-fail unless `--allow-single-model` is explicitly passed.
- The renderer (Wave 5) consults Henry L1's `G25 DeferredEvidenceBlockGate` — if Wave 3 evidence is deferred for an evidence-critical claim, delivery BLOCKs.

**Tests**: `tests/test_cli_honest_failure.py` (5 cases pinning the honest-failure CLI behaviour).

### Wave 4 — Validation

**Purpose**: Re-test each leading hypothesis against the **measured data** Wave 3 produced (not the literature priors from Wave 1).

Per hypothesis:
- Recompute the prior support score using Wave 3 anchors.
- If `|confidence_delta| > 0.4`, promote (e.g. `exploratory → established`) or demote (`established → exploratory`) the three-tier label.
- Emit a per-hypothesis `tasks/w4_*/report.md`.

### Wave 5 — Dual delivery

Two artifacts. Same evidence. Different audience.

- **`patient_plain_brief.md/html`** — lay reader. v1.5.7 mandates 5 sections, **Section 0 (一句话答案) first**: top recommendation + rough effect size + rough risk + ONE next step, ≤ 3 sentences. If Wave 3 didn't produce data, Section 0 says so plainly ("这次分析没有跑到底...").
- **`pi_delivery.md`** — clinician-grade. Every claim PMID-anchored, three-tier-labelled, with provenance SHA-256. Henry's outstanding L3/L4 risk cards rendered as ack tables.

---

## 5 · The 27-gate safety stack

Henry's L1 layer is **no-LLM deterministic gates**. Every claim that goes to delivery passes through them. Definitions in `src/opl_cancer/validators/gates/g{1..27}_*.py`. The registry — `validators.mechanical_gates.all_gate_classes()` — returns all 27 in canonical order.

| Bucket | Gates | What they enforce |
|---|---|---|
| **Citation integrity** | G1 PMID existence · G2 quote match · G9 retraction check | Every PMID exists, every quoted span is in the paper, no retracted source survives |
| **Drug + dose** | G3 INN normalisation · G4 dose unit declared · G22 DDR zygosity · G23 recency band | Brand→INN via RxNorm, mg/m² vs flat-mg explicit, BRCA mono- vs bi-allelic disambiguated |
| **Patient isolation** | G5 patient-context isolation · G27 privacy scrub | No cross-patient contamination; PII never leaves the patient's run-root |
| **Voice & format** | G7 imperative detector (strict on by default since v1.5.7) · G19 PI-imperative detector · G6 injection scan · G12 memory overflow | No "must / 必须" toward patient; no prompt-injection from patient docs; no token-bomb |
| **Epistemic** | G8 Level-3/4 disclosure · G10 guideline version · G11 no silent fallback · G14 dataset-patient match · G15 multiple testing · G16 batch effect · G17 meta-I² policy · G18 meta search strategy · G25 deferred evidence block · G26 evidence-strength ranking | The full "if you can't measure it / cite it / disclose it, you can't render it" stack |
| **System** | G13 reviewer-distinct · G20 PI disagreement surfacing · G21 quantitative anchor | Reviewer ≠ executor, model disagreement surfaced, real numeric prediction not labels |
| **Safety floor** | G24 crisis detection | SI / self-harm keywords (中英双语) → wave lockout + crisis-line surface |

**v1.5.6** moved G21 / G25 / G26 / G27 from "defined-but-not-registered" into the live registry (was 23, now 27). **v1.5.7** flipped G7 strict_imperative_isolation default on — closing the single-sentence bypass `"You must take drug X PMID:12345 — risk of bleeding."`.

Each gate has 5-15 test cases under `tests/test_validators/`.

---

## 6 · The 30 integrators

Concrete classes in `src/opl_cancer/integrators/*.py`. Each subclasses `Integrator` (the abstract base) and provides `family` (F1-F10 per spec §2.5), `ttl_seconds`, and an async `fetch(key) -> dict` that **must raise `IntegratorError` on failure — never silently return mock data** (`memory:feedback_no_offline_only`).

**By family**:

- **F1 Literature** — PubMed (NCBI eutils + `tool=opl-cancer&email=` per NCBI policy v1.5.6) · Europe PMC · PaperQA2 · Unpaywall · Crossref
- **F2 Trials** — ClinicalTrials.gov · ChiCTR · ISRCTN · EU-CTR · HKCTR
- **F3 Guidelines** — NCCN (PageIndex tree-search per cancer type)
- **F4 Variants** — ClinVar · gnomAD · CIViC · OncoKB
- **F5 Genomic cohorts** — cBioPortal · GDC · Hartwig · BeatAML · ICGC
- **F6 Expression / re-analysis** — GEO · ArrayExpress · SRA · GEPIA3 (TCGA + GTEx, v1.5 first-class default)
- **F7 Cell-line / functional genomics** — DepMap · CCLE · Open Targets
- **F8 Expanded access** — FDA-EAP · NMPA-EAP · EMA-EAP
- **F9 Pharmacology** — RxNorm
- **F10 Provenance** — RetractionDB (retraction watch)

**Cache**: shared `IntegratorCache` is **SQLite-backed** (not in-memory) — per-family TTL from `models.yaml` (which now hard-fails on parse error; v1.5.6 P0-1).

**Retry**: v1.5.6 added `_http.py::request_with_retry` — exponential backoff (4 attempts, 0.5→8s), respects `Retry-After`, retries on 429 / 5xx / transport / timeout. Wired into the 4 NCBI integrators (highest 429 risk under wave-concurrent dispatch); other 26 can opt in via the same helper.

---

## 7 · Provenance & reproducibility

Every wave writes to `triggers/<run_id>/`:

```
triggers/<run_id>/
├── plan.json                          # Sid's planning output
├── tasks/
│   ├── w1_<n>_<expert>/report.md      # one per Wave 1 expert
│   ├── w2_aviv/report.md              # hypothesis tournament summary
│   ├── w3_data/report.md              # cohort + Cox/KM
│   ├── w3_meta/report.md              # meta-analysis
│   ├── w3_gepia3/report.md            # GEPIA3 differential expression
│   ├── w4_<hypothesis>/report.md      # validated against Wave 3
│   └── henry/report.md                # IRB-substitute audit
├── tournament/round_*.json            # Elo rounds + Robin insights
├── data/
│   ├── cohorts/*.csv                  # patient-matched cohort tables
│   ├── meta_analysis/pooled_results.json
│   ├── gepia3/aggregated_summary.csv
│   ├── figures/*.png                  # forest plots, KM curves
│   └── analysis/*.ipynb               # reproducible notebooks
├── delivery/
│   ├── patient_plain_brief.html
│   ├── patient_plain_brief.md
│   ├── patient_brief.html             # PI-grade
│   └── pi_delivery.md
└── provenance.jsonl                   # bit-exact reproduction log
```

`provenance.jsonl` records every LLM call (model id + prompt SHA-256 + response SHA-256 + token counts + wall-time) and every integrator query (family + key + result SHA-256 + cache hit/miss + TTL). Patient can re-run with the same `provenance.jsonl` and bit-exact reproduce the run.

---

## 8 · Honest state — what's real, what's stub, what's deferred

OPL is a working system, not a demo. But spec-fidelity matters; mis-marketed claims become technical debt. This is the honest state at v1.5.7:

| Spec promise | Status | Notes |
|---|---|---|
| 18 named experts × 6-primitive grammar | ⚠️ Real for `execute` / `review` / `integrate` / `can_handle`; **stub** for `plan` / `audit` / `feedback` | v1.5.6 added `StubMethodWarning` so callers can detect. Same code path across 18 experts — true persona differentiation is at the prompt level only. |
| 27 mechanical gates | ✅ All registered (v1.5.6) | Was 23 (G21/G25-G27 defined but unregistered); fixed. |
| 30 live integrators | ✅ All real HTTP/MCP, no mock fallback | NCBI 4 have retry+identity (v1.5.6); other 26 will follow. |
| Co-Sci Elo tournament | ✅ Real | Standard Elo math + convergence early-stop + meta-critique structured JSON + Robin lit-loop wired (v1.5.7) |
| Henry 4-layer audit | ✅ Real | L1 mechanical / L2 disagreement / L3 risk-card permission / L4 BFS-cascade rollback all implemented. |
| Wave 3 non-skippable | ✅ As of v1.5.7 | CLI is now a state-reader; refuses to claim ok without artifacts. |
| Cross-border / EAP integrators | ✅ Real | FDA / NMPA / EMA EAP integrators in family F8 |
| Wave 3 bixbench Docker | ✅ Real subprocess invocation | `compute/runner.py` runs `subprocess.run([docker, ...])` with dry-run gate; `compute/bixbench.Dockerfile` + `kernel_requirements.txt` present. |
| `claim withdraw + cascade` (spec §10) | ✅ Real | `validators/rollback.py::withdraw_with_cascade` — BFS over claim graph, ProvenanceJournal-backed |
| Literature signal / Integrator alert event loop | ⚠️ Schema defined | `orchestrator/trigger.py` has the `TriggerSource` enum (FILE_DROP / LITERATURE_SIGNAL / INTEGRATOR_ALERT) but only FILE_DROP scanner is implemented. |
| `models.yaml` lock + reviewer pairing | ✅ Real | G13 enforced at preflight (hard-fail without `--allow-single-model`) |

What we don't claim:
- We don't run new wet-lab experiments. Tyler scaffolds N=1 cohort projections from public data + suggests in-silico assays.
- We don't replace the treating oncologist. Patient brings our brief to a real oncologist.
- We don't hold patient PII outside their machine. Everything runs in `~/CancerDAO/patients/<patient_code>/`; G27 scrubs PII on the way out of any artifact.

---

## 9 · Operating modes

OPL is **main-thread Claude orchestrated** in its reference deployment (Claude Code skill). The `cli.py` surface is a **state reader + dispatcher gate**, not the executor. Mode matrix:

| Mode | Executor | When |
|---|---|---|
| **Skill (recommended)** | Claude Code main-thread Claude orchestrates per `SKILL.md`; subagent fanout for parallel wave work | Patient session with `claude` CLI |
| **Python-runner (CI / batch)** | `glue.wave1_runner.Wave1Runner.run()` / `glue.wave3_runner.Wave3Runner.run()` with injected LLM clients | Eval suites, benchmark adapters, batch reprocessing |
| **CLI (state-reader)** | `cli.py wave1/2/3/4` reads the run-root, reports artifact state | Smoke check whether a run is real-complete vs mkdir-skipped |

The architectural divergence between Skill mode (main-thread Claude executes) and Python-runner mode (Python with LLM client) is acknowledged. v1.6 will pick one canonical path.

---

## 10 · Iteration history (recent)

| Version | Headline | What changed |
|---|---|---|
| v1.5.7 | **Runtime honesty** | CLI `wave1/2/3/4` become honest state-readers (refuse ok without artifacts); G7 strict default on; Henry prompt rule blocks on G7; patient brief mandates Section 0 (conclusion-first); mCRC KRAS G12C MSS L4+ planner row added |
| v1.5.6 | **Independent code-review hardening** | `models.yaml` hard-fail; NCBI tool+email identity; G21/G25-27 registered (23→27); retry+backoff on NCBI; expert stub warnings; G7 strict opt-in; Robin lit-loop wired |
| v1.5.5 | Removed wrong safety email; fixed post-rename DISCLAIMER URLs | |
| v1.5.4 | Sid inline-delivery contract — speak conclusions in chat, not just file paths | |
| v1.5.3 | Public-release prep — PII redaction across git history; README rewrite; docs/internal/ split | |
| v1.5.0-2 | G25/G26/G27 + progress reporter + interrupt handling + persona prefix mandatory | |
| v1.4.0 | Round-2/3 backlog batch — surveillance / irAE-rechallenge / unregulated-channel / N=1 lab-trajectory / caregiver-filter / patient-pushback / TNBC+LM planner row | |

---

## 11 · How to run

```bash
# Install
git clone https://github.com/CancerDAO/opl-cancer
cd opl-cancer
pip install -e ".[dev]"

# Preflight check (Python + LLM keys + Docker / native Python + G13 reviewer-distinct)
opl-cancer preflight --json

# Initialise a patient
opl-cancer init-patient PT-EXAMPLE-A
# Drop their records into ~/CancerDAO/patients/PT-EXAMPLE-A/

# Plan from goal
opl-cancer plan \
  --patient ~/CancerDAO/patients/PT-EXAMPLE-A \
  --goal "我是 mCRC KRAS G12C MSS, 4 线进展, 下一步怎么办" \
  --run-id $(date +run-%Y%m%d-%H%M%S) \
  --out ~/CancerDAO/patients/PT-EXAMPLE-A/triggers/<run_id>/plan.json
```

For Wave 1-4 execution, the recommended path is via the Claude Code skill (`SKILL.md`): the assistant dispatches subagent fanout, the CLI is consulted to verify state, and at each wave the CLI returns `ok: true` only when real artifacts landed.

---

## 12 · References

- Spec §1-§17 (internal — see ADRs)
- ADRs: `docs/adr/0001-0009-*.md`
- Anti-patterns log: `docs/ANTI_PATTERNS_v1.4.md` (the v1.4 retrospective that drove v1.5)
- Run retrospectives (when published): `docs/retrospectives/`
- CHANGELOG: [`CHANGELOG.md`](CHANGELOG.md)
- Disclaimer: [`DISCLAIMER.md`](DISCLAIMER.md)

---

*Open source. Apache-2.0. Not a clinical decision-support device. Not for emergencies. Patient is sole decision authority.*
