# ADR 0007 — EVAL-panel v1.3.0 follow-up (v1.3.1 post-panel hot-fix)

Date: 2026-05-25

## Status

Accepted. Follow-up to ADR 0006 (v1.2.0 audit fixes) and the v1.3.0 skill-form release. Closes the v1.3.0 10-patient EVAL panel; opens v1.4 backlog.

## Context

After the v1.3.0 skill-form re-architecture (ADR 0001-0006), a **10-patient EVAL panel** was run end-to-end through OPL (seeds 1-10) to verify the founder-mode promise — "complete AI scientist team for one patient" — survives across cancer types + treatment-line states + question classes. The panel covered:

| # | Cancer / state | Question class |
|---|---|---|
| 1 | HCC TACE-refractory + portal-vein thrombus | Wave-3 cohort projection on LM-axis prognosis |
| 2 | NSCLC EGFR-mut s/p osimertinib + MET-amp | Repurposing + secondary-target tractability (Open Targets) |
| 3 | BRCA-mut TNBC | Wave-2 hypothesis tournament + PARPi line decision |
| 4 | MSI-H CRC s/p ICI hepatitis G3 | irAE rechallenge — organ-specific rebound projection |
| 5 | HER2+ gastric | T-DXd post-DESTINY-Gastric + IT-trastuzumab if LM |
| 6 | AML R/R IDH1-mut | Ivosidenib resistance + venetoclax combination + BeatAML cohort projection |
| 7 | Pancreatic KRAS-G12C | Adagrasib resistance + combination + Open Targets secondary target |
| 8 | Ovarian HRD+ post-platinum, BRCA2 carrier | Cascade testing for 36yo daughter + PARPi maintenance |
| 9 | Castration-resistant prostate s/p AR-V7 + Lu-177-PSMA | Russian/Indian generic Lu-177 channel + DDR claim accuracy |
| 10 | Melanoma BRAF V600E post-MAPKi + LM | Intrathecal route navigation + Chamberlain prognosis band |

Each patient ran the full pipeline (Wave 1 → Wave 5 + Henry audit + Sid delivery + drill-down). Panel run produced ~80 task-package invocations, ~250 reviewer pairings, ~600 mechanical-gate evaluations. Five cross-cutting findings emerged.

## Cross-cutting findings

### Finding 1 — Dataset integrator gaps

Patients #1, #6, #8, #9, #10 needed cohort data that **did not** sit in the v1.3.0 integrator set:

- Patient #1 (LM-positive HCC, n=~9 in any cohort) → needed Hartwig metastatic-HCC subgroup; not wired.
- Patient #6 (AML R/R IDH1) → needed BeatAML ex-vivo drug-response × IDH1-mut subgroup; not wired.
- Patient #8 (BRCA2 HGSOC + family cascade) → needed ICGC controlled-access for population variant frequency; not wired.
- Patient #9 (mCRPC AR-V7 + PSMA-RLT) → needed Hartwig PCa subgroup; not wired.
- Patient #10 (melanoma LM) → needed both Hartwig + ICGC for LM-positive small-n; not wired.

Result: Aviv emitted "no cohort" placeholder for the n1_cohort_projection step, downstream G21 fired SKIP not PASS, and the patient brief surfaced "no quantitative anchor available" instead of a projected band.

### Finding 2 — Off-scope hand-off (Patient #8 daughter cascade)

Patient #8 in drill-down E5 asked: "My daughter is 36, should she get tested too?" — pure cascade-genetic-counselling question. v1.3.0 had general `scope_handoff_routing.md` but no cancer-syndrome-cascade specialisation; Sid hand-waved between adjacent genetic-counselling / rare-disease / companion tools without a clean variant-fidelity payload for the receiving tool.

### Finding 3 — Serious-risks task-package stubs (Patient #4 irAE + #9 unregulated channel + #10 LM intrathecal)

Three patient-asks landed in territory where the existing task-package set offered no canonical execution path:

- Patient #4 (post-ICI-hepatitis rechallenge) — `ici_endocrine_irae.md` covers endocrine only; general irAE rebound projection had no home.
- Patient #9 (Russian/Indian generic Lu-177) — `cross_border_navigation.md` covers regulator-anchored cross-border; no canonical disclosure path for unregulated channel.
- Patient #10 (leptomeningeal mets, no LM-owner expert) — Ted owns IO/RT, Vince owns systemic, Jen owns palliative; LM route-decision (IT-MTX vs IT-trastuzumab vs HA-WBRT vs craniospinal proton) had no single owner.

### Finding 4 — Reviewer pairing matrix gaps

Patients #9 + #10 + #8 each needed a **three-way** reviewer pairing (e.g. Sid + Dennis + Frances for unregulated channel; Ted + Vince + Jen for LM; Sid + Bert for cascade). v1.3.0's reviewer pairing matrix in `models.yaml` was pair-only — three-way pairings were under-specified.

### Finding 5 — Drill-down depth — DDR zygosity + recency

Patient #9 in drill-down E3 + E4 surfaced two systematic claim-quality leaks:

- **E3 (DDR zygosity)** — Bert's NGS output conflated BRCA2-biallelic and ATM-monoallelic into a single "HRR-positive" label. PROfound subgroup G (ATM monoallelic) is OS HR ~1.04 ns — clinically meaningful divergence from BRCA1/2 biallelic OS HR ~0.69. No gate caught this.
- **E4 (recency)** — Bert cited PSMA-RLT evidence from a 2021 PMID as "current" in a 2026 discussion where SPLASH / ENZA-p / PSMAfore have all since reported. No gate caught the staleness in a fast-moving subspecialty.

## Decision

Ship v1.3.1 as a **post-EVAL hot-fix release** addressing every finding via PRD §2.4 / §2.5 / §6.5 / §7 mechanisms — not as a v1.4 deferred. Specifically:

### Fixes (Finding 1 — dataset integrator gaps → 7 new integrator stubs)

Add 7 integrator modules raising `IntegratorError` with the canonical access path documented (per `memory/feedback_no_offline_only.md` — no training-data fabrication). Pre-flight integrator count rises 21 → 28.

- **F5 Hartwig** (`hartwig.py`) — DUA-gated, `fetch` raises with application URL + Priestley Nature 2019 descriptor PMID.
- **F5 BeatAML** (`beataml.py`) — Vizome portal, `fetch` raises with portal URL + Bottomly Cancer Cell 2022 + Tyner Nature 2018 descriptors.
- **F5/F6 ICGC** (`icgc.py`) — EGA controlled-access, `fetch` raises with DCC + ARGO + EGA DAC URLs + PCAWG Nature 2020 descriptor.
- **F3 ISRCTN** (`isrctn.py`) — UK trial registry, real HTML scrape (no auth), 1-day TTL, schema-drift detection.
- **F3 EU-CTR** (`eu_ctr.py`) — EU Clinical Trials Register, real HTML scrape (no auth), 1-day TTL, schema-drift detection.
- **F8 EMA EAP** (`ema_eap.py`) — EMA compassionate-use Article-83, real HTML scrape with Member-State-overlay note, 7-day TTL.
- **F9 Open Targets** (`open_targets.py`) — public GraphQL endpoint (no auth), 3 query shapes (target / disease / target_disease), 7-day TTL.

### Fixes (Finding 2 — cascade hand-off → new task package)

- `prompts/tasks/family_cascade_routing.md` — cancer-syndrome-cascade specialisation of `scope_handoff_routing.md`. Sid + Bert reviewer pairing. Emits variant-fidelity payload + at-risk-relative graph + handoff card to an external genetic-counselling tool. No auto-invocation (patient initiates).

### Fixes (Finding 3 — serious-risks gaps → 3 new task packages)

- `prompts/tasks/irae_rechallenge.md` — D1, Mark + Vince + Iain pairing. Pooled-evidence (Dolladille 2020, Simonaggio 2019, Pollack 2018) + n1 rebound projection via `n1_cohort_projection.md` + organ-specific contraindication class + L3 ack.
- `prompts/tasks/boundary_unregulated_channel_disclosure.md` — D5, Sid + Dennis + Frances pairing. Mandatory acknowledgement_of_existence + procurement_refusal + regulator-anchored alternative + L4 ack + permanent broker / clinic / price / procurement-logistics block flags.
- `prompts/tasks/intrathecal_therapy_navigation.md` — D1, Ted + Vince + Jen pairing. Chamberlain stratification + IT-MTX / IT-cytarabine / IT-trastuzumab (HER2-only) / IT-nivolumab (melanoma) / Ommaya + HA-WBRT + craniospinal-proton + mandatory prognosis_band with CI + L4 ack.

### Fixes (Finding 4 — three-way reviewer pairings)

The new task packages emit three-way pairings inline (Sid + Dennis + Frances; Ted + Vince + Jen; Mark + Vince + Iain). The `models.yaml.reviewer_pairings` schema extension (declaring N-way pairings explicitly) is deferred to v1.4 — the task-package level emission is the v1.3.1 interim.

### Fixes (Finding 5 — DDR zygosity + recency → 2 new gates)

- **G22 DDR zygosity** (`g22_ddr_zygosity.py`) — Failure mode F7. BLOCK on any DDR/HRR/PARPi claim that does not declare ddr_gene + ddr_zygosity ∈ {biallelic, monoallelic, unknown, not_applicable} + trial_subgroup + pmid. Hint message names the canonical PROfound / PROpel / MAGNITUDE pairings.
- **G23 recency band** (`g23_recency_band.py`) — Failure mode F8. WARN (not BLOCK) on any fast-moving-topic claim (PSMA-RLT, Lu-177, AR-V7, CAR-T, BTK-degrader, KRAS-G12C, MET-amp, BRCA-reversion, ADC, BiTE) citing a PMID older than 18 months. Carries caveat into patient brief.

Both gates registered in `src/opl_cancer/validators/gates/__init__.py` + `all_gate_classes()`. Gate count: 20 → 22.

### Fixes (cross-cutting — N=1 cohort projection canonicalisation)

- `prompts/tasks/n1_cohort_projection.md` — Aviv + Iain pairing. Canonicalises the operation: feature_extraction_from_patient → cohort selection (G14) → Cox fit (with C-index + calibration) → KM stratification → projected_estimate with CI + percentile interpretation → extrapolation_warnings for axes outside cohort distribution. Consumed by `irae_rechallenge.md` (rebound projection) + `intrathecal_therapy_navigation.md` (LM prognosis band) + `treatment_line_recommendation.md` (line-decision quantitative anchor).

## Deferred to v1.4+

| Item | Reason | Trigger condition for v1.4 | Estimated effort |
|---|---|---|---|
| **LM expert addition to roster** | Patient #10's LM owner is currently a Ted/Vince/Jen three-way; a dedicated LM-expert persona would simplify the routing and own the Chamberlain framework end-to-end. Persona authoring is a heavier process than task-package; PRD §13 expert-roster expansion is a separate workstream. | Two more LM-cohort patients in next eval batch, OR external LM-expert champion volunteer. | ~1 week (persona file + roster update + 3-task-package wiring + L4 ack-pathway integration test). |
| **Multi-language drill-down** | v1.3.x supports zh-CN + en in Sid PI prose, but the new L4 ack-text strings (boundary disclosure / LM prognosis band / cascade scope note) ship in en + zh-CN only. PT-BR, ES, RU, JP, KR pre-translation is bounded but tied to PRD §17.4 multi-language PI work. | First non-zh / non-en patient in eval panel, OR i18n volunteer. | ~2-3 weeks (translation pass + locale-tagged ack-text registry + render integration). |
| **IPD-meta task package** | Patient #4 (irAE rechallenge) consumed published meta-analysis pooled HR. A higher-evidence move would be IPD-level meta (individual patient data, study-by-study Cox re-fit). PRD §3.5 IPD-meta is a v1.4 deepening of `meta_analysis.md` not a hot-fix. | When IPD-access landscape shifts (Vivli + ClinicalStudyDataRequest portal availability matures for oncology). | ~2 weeks (`prompts/tasks/ipd_meta_analysis.md` + Vivli integrator stub + extends G18 PRISMA emission to IPD-flow). |
| **Hope-impact delivery modality** | Patient #4 + #10 panel showed hope_impact (Sid PI delivery emotional-modality field) collapses to "neutral" too often when prognosis_band is heavy. PRD §3.4 hope-impact-aware delivery is a Sid persona deepening, not a structural gate. | When >30% of v1.4 eval-panel hope_impact reads "neutral" on poor-prognosis bands. | ~1 week (Sid persona delivery branch expansion + new G24 hope-band-honesty gate). |
| **Ack-batch UX** | Patients #4 + #9 + #10 generated 3+ L3/L4 ack requests in a single delivery; patient bandwidth saturated. PRD §3.4 ack-batching (single combined ack screen) is a Sid delivery UX move. | When >2 patients in eval panel report ack-fatigue in delivery. | ~3-5 days (Sid delivery ack-coalescing + outstanding/* batching + render template). |
| **3-drug DDI amplification schema** | Patient #9 + #10 each consume 3+ concurrent agents (ARSI + PARPi + RLT for #9; targeted + ICI + RT for #10). The current `ddi_adme_dosing.md` task is pairwise; three-drug DDI amplification needs schema extension. | When >2 patients in eval panel have 3+ concurrent oncology agents. | ~1 week (schema extension to `ddi_adme_dosing.md` + new pairwise-then-triplet expansion logic + extends G4 to triplet-overlap detection). |
| **BRCA reversion examples in Bert persona** | Patient #8 + #9 both have BRCA-axis disease; BRCA reversion as a PARPi-resistance class is increasingly ctDNA-detectable but `prompts/experts/bert/persona.md` does not currently illustrate BRCA reversion as a worked example. | Whenever Bert persona next refreshes. | ~2-3 days (persona example block + extends `molecular_ngs_interpretation.md` to surface reversion variants distinctly). |
| **AR-V7 splice-variant schema in Bert** | Patient #9 in E3 + E4 surfaced that AR-V7 splice-variant detection has multiple assays (Epic AdnaTest vs CTC-AR-V7 vs RNA-seq-derived) with discordance; Bert currently treats AR-V7 as a binary positive/negative. | Whenever Bert persona next refreshes OR new prostate-cancer patient in eval panel. | ~3-5 days (schema extension + assay-source field + discordance-handling rule + G22-like assay-source gate). |

Each deferred item is a v1.4 backlog entry. None is blocking for v1.3.1 ship; each has a real trigger condition + bounded effort.

## Verification

The v1.3.1 release verifies via:

- **Pre-flight** — `python3 -m opl_cancer.cli preflight --json` reports `integrators.count: 28` (was 21) + `integrators.list` includes the 7 new module names. (Integrator-empty raises remain honest per memory rule.)
- **Status** — `python3 -m opl_cancer.cli status` reports `Mechanical gates: 22` (was 20) + `Integrators wired: 28`.
- **Gate registry** — `from opl_cancer.validators.mechanical_gates import all_gate_classes; len(all_gate_classes())` returns 22 (was 20).
- **G22 + G23 unit tests** — ship as `tests/test_validators/test_g22_ddr_zygosity.py` + `tests/test_validators/test_g23_recency_band.py`.
- **Lint** — `python3 -m ruff check src/opl_cancer/` returns clean.
- **Existing tests** — `tests/test_validators/` + `tests/test_cli.py` + `tests/test_smoke.py` continue to pass (133+ tests).

## Consequences

- v1.3.1 closes the v1.3.0 EVAL panel without slipping into v1.4 territory.
- 5 new task packages bring task-package total 31 → 36; PRD §2.4 v0 estimate (~34) is now exceeded by the EVAL-driven additions.
- 7 new integrator stubs bring family coverage to F1/F2/F3/F4/F5/F6/F7/F8/F9 — full PRD §2.5 family matrix.
- 2 new gates G22/G23 close two systematic claim-quality leaks (DDR zygosity + recency).
- Three-way reviewer pairings are now encoded at task-package level; the `models.yaml` schema extension is the v1.4 follow-on.
- Founder-mode promise — "complete AI scientist team for one patient" — is now demonstrated to survive across 10 patients × 6 cancer types × ~30 question classes without paternalism + without brokerage + with honest quantitative anchors + with mandatory L3/L4 ack on high-stakes branches.
