# OPL for Cancer

> 让全世界的每一个人都能拥有一个完整的 AI scientist team,只为他/她一个人工作 — 调取世界已知的信息,并主动产生世界未知的新信息,患者本人是自己案例的唯一决策人。

[![CI](https://github.com/CancerDAO/opl-cancer-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/CancerDAO/opl-cancer-skill/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

## Status

**v1.0.2 (Iter 10 patch — MiniMax live integration).**

Roster complete (**18/18 experts**). **710 tests + 3 env-gated live**, mypy --strict on touched files + ruff clean.

**v1.0.2** highlights (delta from `v1.0.1`):
- `tests/test_integration/test_minimax_live.py` — MiniMax-M2.7 live calls (`live` marker, env-gated)
- `scripts/verify_minimax_setup.py` — manual CLI verification
- `pyproject.toml` declared `live` marker

**v1.0.1** highlights (delta from `v1.0.0-p6`):
- Routing-matrix golden test (`tests/test_experts/test_routing_matrix.py`) — 26 tests, 18 experts × 4 cancer patients
- Henry L2 LLM disagreement-axes summariser (env-gated, `response_format=json_object`, defensive)
- `ProjectMemoryStore.acknowledge_insight()` propagates `patient_acknowledged_at` into `InsightCard`

**v1.0.0-p6** highlights:
- Multi-case Wave 1 E2E parametrised across **4 cancer types** (HCC / NSCLC / CRC / BRCA)
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
- Golden set: 4 synthetic patients (HCC/NSCLC/CRC/breast), 8 failure-mode inputs, 2 regression anchors, 3 boundary cases

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
| Mark | Endocrinologist (irAE) | Mark Stelfox (ICI irAE) |
| Hong | TCM Oncologist | 林洪生 (中国中医肿瘤) |
| Frances | Expanded Access | Frances Kelsey (FDA safety) |
| Dennis | Cross-Border | Dennis Lo 卢煜明 (cfDNA) |
| Steve | Nutritionist | Stephen Heber (oncology nutrition) |

Names are first-name homages — archetype personas, not impersonations of real individuals.

## License

Apache-2.0. See [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
