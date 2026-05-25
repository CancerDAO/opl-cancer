# OPL for Cancer

> 让全世界的每一个人都能拥有一个完整的 AI scientist team,只为他/她一个人工作 — 调取世界已知的信息,并主动产生世界未知的新信息,患者本人是自己案例的唯一决策人。

[![CI](https://github.com/CancerDAO/opl-cancer-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/CancerDAO/opl-cancer-skill/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

## Status

**v1.4.0 — Round-2/3 deferred backlog closed. Production-grade founder-mode skill.**

OPL is a true Claude-Code skill, not a pip-CLI. Install with `npx skills add`, trigger by natural language in Claude Code.

```bash
# Install once (clones into ~/.claude/skills/opl-cancer/):
npx skills add CancerDAO/opl-cancer-skill

# Then in Claude Code, just say:
#   「我有 NSCLC,二线进展了,想要 AI team 帮我分析」
#   「OPL,帮我跑一次 hypothesis tournament」
#   「founder mode against cancer — 给我我的 AI 科研团队」
```

`SKILL.md` orchestrates the 11-step Wave lifecycle (preflight → ingest → readiness → plan → Wave 1 retrieval → Wave 2 hypothesis tournament → Wave 3 bioinformatics → Wave 4 validation → Henry IRB audit → render → drill-down). Python codebase under `src/opl_cancer/` is the execution substrate, exposed through `scripts/cli.py` subcommands the SKILL invokes step-by-step.

**v1.4.0 inventory** (validated against 23-persona EVAL panel across 4 rounds, 28/28 verification PASS):

- **18 named experts** + Sid PI + Henry IRB-substitute auditor
- **42 task packages** (D1 临床解读 / D2 假设生成 / D3 数据-evidence / D4 验证 / D5 综合-交付)
- **23 mechanical gates** (G1–G20 PRD-§7 complete + G21 quantitative-anchor + G22 DDR-zygosity + G23 fast-moving-recency + G24 crisis-detection)
- **29 live integrators** (PubMed / NCCN / CT.gov / ChiCTR / ISRCTN / EU-CTR / HKCTR / FDA-EAP / NMPA-EAP / EMA-EAP / OncoKB / CIViC / cBioPortal / GDC / ClinVar / gnomAD / GEO / ArrayExpress / SRA / DepMap / CCLE / Hartwig / BeatAML / ICGC / Open Targets / RxNorm / RetractionDB / PaperQA2 / Unpaywall)
- **34-drug L3 forced-known-serious-risk catalogue** (covers menin-i / ATR-i / CHK1-i / ADC / KRAS-i / IDH-i / FLT3-i / ARSi / radioligand classes with FDA boxed warnings)
- **Safety floor**: G24 crisis detection (bilingual SI/SH keyword banks + jurisdictional crisis-line registry + Wave-lock) · `guardian_ack_protocol.md` for pediatric (guardian acks information-receipt only, NOT treatment authority — treatment routes to pediatric IRB-supervised slot)
- **8 references** + 8 ADRs + 1 safety prompt
- **997 tests pass · ruff clean** · mypy --strict on touched files

**Read first** — `SKILL.md` (orchestration), `docs/landing/founder_mode_against_cancer.md` (founder-mode framing), `references/` (deep architecture / mechanical gates / permission levels / philosophy / troubleshooting), and `DISCLAIMER.md` (not clinical decision support; not for emergencies — call 120/911/112).

### Version history

- **v1.4.0** — Round-2/3 deferred backlog batch fix (ADR-0008 D1–D13 priority A + B). Adds: `surveillance_schedule.md` (MEN1/Lynch/LFS/HBOC syndrome-driven surveillance) · `irae_rechallenge.md` multi-organ schema (prior_irae_record list + cumulative_organ_load_index + myocarditis G2+ STRONG RELATIVE per Mahmood 2018 + Salem 2022) · `boundary_unregulated_channel_disclosure.md` retrospective mode (forensic eval offer for already-used grey-market) · `n1_cohort_projection.md` candidate_cohorts ordered fallback chain + lab_trajectory (AFP/PSA/CA-125/CEA/CA19-9/LDH not just static) · `caregiver_filter_protocol.md` (caregiver preview brief + Sid explicitly declines disclosure decision; patient_brief intact) · `patient_pushback_handling.md` (NEITHER concede NOR paternalism) · HKCTR integrator (28→29) · TNBC+LM planner row · delivery_tone_hint extraction (blunt/warm/clinical) · `acknowledge --batch` + ack_consolidation_card.
- **v1.3.3** — Round-3 verification follow-up. revumenib/ziftomenib/bleximenib/ceralasertib added to serious_risks catalogue; G23 FAST_MOVING_TOPICS extended +30 ATR-i/CHK1-i/WEE1-i/Polθ-i tokens.
- **v1.3.2** — SAFETY hot-fix (round-2 EVAL response). G24 crisis-detection gate + `prompts/safety/crisis_detection.md` + `crisis_card_emission.md` (SI/self-harm Wave-lock + jurisdictional crisis lines) · pediatric guardian mode via `guardian_ack_protocol.md` + 4 pediatric planner rows · full `drilldown.md` 4-class rewrite (claim_provenance / reasoning / statistical / disagreement) · G22 lineage-context SKIP carve-out · cancer-type description list +14 cancer types (NPC / MEN1 / NET / pituitary / GIST / sarcoma / thyroid / cholangiocarcinoma / etc).
- **v1.3.1** — Post-10-patient-EVAL hot-fix. `scope_handoff_routing.md` (for off-scope asks like family genetic counseling → firefly handoff) · `serious_risks_per_drug.json` 5 → 25 drugs · G21 quantitative-anchor gate · G14 conditional axes (metastatic_site / ethnicity / cns_involvement / sex / age_bracket) · `intent_parser.md` with PROGNOSIS_QUERY + CAREGIVER speaker_role + hope_impact.
- **v1.3.0** — Skill-form re-architecture (PRD §0 telos full alignment). SKILL.md completely rewritten as conversational orchestration prompt; `scripts/cli.py` shim + `install.sh` + `.env.example`; 9 new task packages (D1 staging_workup + china_rwe_adjustment; D2 drug_repurposing + literature_synthesis; D4 source_verification + claim_audit + cross_source_consistency; D5 patient_brief_rendering + pi_delivery); 14 new mechanical gates (G4-G6, G8, G10, G12-G20); 8 references/ files; landing rewritten to fix 10 paradigm deviations; v1.3 introduced 7 new integrators (Hartwig DUA-gated / BeatAML / ICGC / ISRCTN / EU-CTR / EMA-EAP / Open Targets).

**v1.2.0 (Audit-fix release). Iterations completed: 20 + audit-fix pass.**

Roster complete (**18/18 experts**). **781 tests + 3 env-gated live**, mypy --strict on touched files + ruff clean.

**v1.0.5–v1.1.0** highlights:
- `ModelRouter.client_for_task()` — per-task model routing (Opus for code/hypothesis reasoning, MiniMax for literature synthesis)
- `tools/observe.py` — trigger-run observability aggregator (token cost / wall-time / claims / reviewer fail rate / gate blocks)
- `Integrator` configurable TTL — class + instance overrides + `family_config_key` reading from `models.yaml.integrator_ttl_seconds` (NCCN 30d / PubMed 7d / CT.gov 1d)
- `DISCLAIMER.md` v1.x release notice + emergency contacts (120/911/112) + jurisdictional notice
- `Wave1Runner.run` emits `triggers/<run_id>/run_metadata.json` (wired for `tools/observe.py` aggregator)
- Cross-patient isolation red-team — Wave1Runner raises `CrossPatientContaminationError` on foreign `patient_code` (`tests/test_safety/test_cross_patient_isolation.py`)

**v1.0.2** highlights (delta from `v1.0.1`):
- `tests/test_integration/test_minimax_live.py` — MiniMax-M2.7 live calls (`live` marker, env-gated)
- `scripts/verify_minimax_setup.py` — manual CLI verification
- `pyproject.toml` declared `live` marker

**v1.0.1** highlights (delta from `v1.0.0-p6`):
- Routing-matrix golden test (`tests/test_experts/test_routing_matrix.py`) — 26 tests, 18 experts × 4 cancer patients
- Henry L2 LLM disagreement-axes summariser (env-gated, `response_format=json_object`, defensive)
- `ProjectMemoryStore.acknowledge_insight()` propagates `patient_acknowledged_at` into `InsightCard`

**v1.0.0-p6** highlights:
- Multi-case Wave 1 E2E parametrised across **8 cancer types** (HCC / NSCLC / CRC / BRCA / Pancreatic / GBM / Pediatric ALL / Multiple Myeloma)
- Legal: `NOTICE` (Apache-2.0 attribution + model-card acknowledgements) + `DISCLAIMER.md` (boundaries + safety pathway)
- `tools/sign_contributor_agreement.py` first-time contributor signing flow
- `docs/landing/founder_mode_against_cancer.md` landing copy for cancerdao-global

Read `DISCLAIMER.md` before using. This is not clinical decision support; patient is sole decision authority.

---

Previous: v0.5.0-p5 (Validation Stack — Henry 4-layer IRB substitute + risk-disclosure-card + patient ack loop + golden set extended).

P5 highlights (CHANGELOG.md for full scope):
- Henry 4-layer auditor with serious-risks catalogue, risk-card emission, model-disagreement surfacing, and patient-acknowledgment loop
- CLI: `opl-cancer acknowledge <card_id>` + `opl-cancer list-pending-acks`
- `reviewer_pairings` populated for all 18 experts (cross-domain rotation)
- `tools/reproduce.py` + `tools/verify_provenance.py` provenance integrity tools
- Golden set: 8 synthetic patients (HCC / NSCLC / CRC / BRCA / Pancreatic / GBM / Pediatric ALL / Multiple Myeloma), 8 failure-mode inputs, 2 regression anchors, 3 boundary cases

Previous: v0.4.5-p4.5 closeout (Batch E: 3 deferred experts + Wave4Runner + G7 ImperativeDetector).

Wave 1 retrieval pipeline (P1) — Sid intent parse → planner → 6 experts
(Rosa/Bert/Vince/Rick/Heddy/Hong) in parallel → reviewer pairing → mechanical gates
(G1/G2/G3/G9/G11) → patient_brief.html with 3-tier labels + PMID links + provenance.

Wave 2 hypothesis pipeline (P2) — Sid `HYPOTHESIS_REQUEST` intent → Wave2Runner
→ HypothesisGenerator (4 strategies) → EvolutionStrategist (6 strategies) → Co-Sci-style
Elo tournament with meta-critique propagation (lift from `open-coscientist`) +
Robin `EXPERIMENTAL_INSIGHTS_APPENDAGE` feedback environment (lift from `robin`) →
Reflector (6 modes) → ranked + reflected hypothesis pack with provenance.

Expert Batch B: **Iain** (Meta-Analyst, Cochrane archetype) + **Aviv** (Bioinformatician,
single-cell archetype) added — portfolio task packages `meta_analysis` /
`hypothesis_generation` / `pathway_enrichment` / `single_cell_reanalysis` /
`cross_source_consistency`.

Wave 3 data-evidence pipeline (P3) — Aviv (extended portfolio) + **Tyler**
(new — Wet-Lab Designer, Tyler Jacks archetype) drive `dataset_acquisition` →
`bioinformatics_data_analysis` → `hypothesis_validation` over Wave-2 hypotheses.
5 new omics integrators: **GEOIntegrator** + **ArrayExpressIntegrator** +
**SRAIntegrator** (F6) + **DepMapIntegrator** + **CCLEIntegrator** (F7).
**bixbench Docker runtime** lifted from `robin/finch/Dockerfile.pinned` —
`compute/bixbench.Dockerfile` + `BixbenchRunner` (env-gated via
`OPL_BIXBENCH_LIVE`; dry-run by default for CI safety).

Expert Batch D (P4) — 6 of 9 shipped: **Mary** (Pharmacologist, DDI/ADME/dosing,
RxNorm + TPMT/DPYD/UGT1A1), **Ted** (Radiation Oncologist, IMRT/SBRT/SRS, BED10
+ QUANTEC), **Riad** (Interventional Oncologist, TACE/RFA/Y90, Child-Pugh +
BCLC), **Jen** (Palliative Specialist, ESAS + opioid MED + mandatory bowel
regimen flag), **Frances** (Expanded Access Navigator, FDA/NMPA/EMA EAP, L4
boundary disclosure mandatory, refuses "guaranteed" framing), **Steve**
(Nutritionist, PG-SGA + cachexia stage + ROS-window caveat). PI
`classify_intent_llm` replaces P0 keyword stub — LLM-backed via
`prompts/pi/intent_parser.md`; raises on bad JSON / unknown intent
(no silent degradation); `IntentClass` extended with `HYPOTHESIS_REQUEST`.

465 tests pass; `ruff check` + `mypy --strict` green.

P4.5+ in flight — Kieren (ID neutropenic fever) + Mark (ICI endocrine irAE) +
Dennis (cross-border coordinator), Wave 4 `hypothesis_validation` runner
(P2 hyp ↔ P3 omics, Aviv + Iain integration), patient-brief polish +
imperative-detector strict gate, full Henry IRB substitute, golden-set expansion,
legal review + open-source launch.

## Quick start

```bash
git clone https://github.com/CancerDAO/opl-cancer-skill
cd opl-cancer-skill
pip install -e .[dev]

# Verify install
opl-cancer status
opl-cancer list-experts
opl-cancer init-patient anon_001 --root ~/opl_patients
```

As a skill plugin (post-P0):

```bash
npx skills add CancerDAO/opl-cancer-skill
```

## Architecture

OPL for Cancer is a two-layer fractal AI scientist team:

**Outer layer — 20 named entities**:

- **Sid** (PI / Chief-of-Staff) — single conversational surface to patient
- **Henry** (Auditor) — global IRB-substitute (4-layer transparency)
- **18 named Experts** — Rosa (pathology), Bert (genetics), Vince (oncology), Rick (trials), Heddy (radiology), Mary (pharmacology), Aviv (bioinformatics), Tyler (wet-lab design), Iain (meta-analysis), Ted (radiation oncology), Riad (interventional), Jen (palliative), Kieren (infectious disease), Mark (endocrinology / irAE), Hong (TCM oncology), Frances (expanded access), Dennis (cross-border), Steve (nutrition)

**Inner layer — task-primitive grammar** (each Expert internally uses):

planner → executor (task package) → reviewer (cross-expert peer) → auditor (intra-expert) → integrator → feedback

## Expert Roster

| Name | Role | Inspiration |
|---|---|---|
| Sid | PI / Chief-of-Staff | Siddhartha Mukherjee (clinician + science communicator) |
| Henry | Auditor | Henry Beecher (informed consent / research ethics) |
| Rosa | Pathologist | Juan Rosai (外科病理学之父) |
| Bert | Geneticist | Bert Vogelstein (TP53/CRC genetics) |
| Vince | Oncologist | Vincent DeVita (combination chemo) |
| Rick | Clinical Trials | Richard Schilsky (ASCO CMO) |
| Heddy | Radiologist | Hedvig Hricak (oncologic imaging) |
| Mary | Pharmacologist | Mary Relling (TPMT) |
| Aviv | Bioinformatician | Aviv Regev (single-cell + Broad) |
| Tyler | Wet-Lab Designer | Tyler Jacks (mouse models) |
| Iain | Meta-Analyst | Iain Chalmers (Cochrane) |
| Ted | Radiation Oncologist | Theodore Lawrence (GI radiation) |
| Riad | Interventional Oncologist | Riad Salem (HCC TARE) |
| Jen | Palliative Specialist | Jennifer Temel (NEJM 2010 PC trial) |
| Kieren | Infectious Disease | Kieren Marr (febrile neutropenia) |
| Mark | Endocrinologist (irAE) | Composite archetype (ASCO + ESMO ICI irAE consensus methodology) |
| Hong | TCM Oncologist | 林洪生 (中国中医肿瘤) |
| Frances | Expanded Access | Frances Kelsey (FDA safety) |
| Dennis | Cross-Border | Dennis Lo 卢煜明 (cfDNA) |
| Steve | Nutritionist | David Heber (UCLA Center for Human Nutrition founder) |

Names are first-name homages — archetype personas, not impersonations of real individuals.

## Roadmap

Planned for v1.1+ (no committed dates — community contributions welcome):

- **v1.1 — Full BioLinkX integration.** Deeper coupling with `BioLinkX` for contribution graph / SBT identity, allowing physicians and patient-advocates to sign sections of a brief and have the signature carried through provenance.
- **Beyond v1.x — Additional cancer types.** The current golden-set corpus (v1.2.0) already covers HCC / NSCLC / CRC / BRCA / PDAC / GBM / ALL / MM. Future iterations expand to head-and-neck, prostate, ovarian, sarcoma, and paediatric solid tumours.
- **v1.3 — Web UI.** A patient- and clinician-facing web layer for browsing the deliberation brief, acknowledging risk-disclosure cards, and tracking the provenance graph interactively. (Today everything ships through CLI + static HTML.)
- **v1.4 — Multi-language briefs.** Native Chinese / Japanese / Spanish patient briefs (not machine-translated post-hoc), with locale-aware regulatory pointers (NMPA / PMDA / COFEPRIS in addition to FDA / EMA).
- **Ongoing — Integrator breadth.** More omics / pharmacology integrators (e.g. cBioPortal study-level pulls, OncoKB level-of-evidence sync, ChEMBL pharmacophore lookups) and continual TTL tuning.

Open issues at https://github.com/CancerDAO/opl-cancer-skill/issues. See `DISCLAIMER.md` — the roadmap does not change the v1.x scope warnings (no warranty, not for emergency use).

## License

Apache-2.0. See [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
