## Task Package · surveillance_schedule

**Capability domain:** D1 — Clinical decision support / post-treatment surveillance
**Expert portfolio owners:** **Heddy** (primary, imaging-cadence axis — owns the per-modality imaging schedule + RECIST-adjacent surveillance pattern) co-reviewed by **Bert** (germline / syndrome-anchored cascade lookups — BRCA / Lynch / Li-Fraumeni / MEN1 / HBOC interface) + **Vince** (treatment-context anchor — curative-intent completed vs resected-with-residual vs maintenance; line-of-therapy timing).
**Preferred integrator families:** F2 Guidelines (NCCN Survivorship + cancer-specific NCCN surveillance sections + ASCO Survivorship + ESMO follow-up — runtime-verified, no edition pin), F1 Literature (PubMed for syndrome-specific surveillance RCTs — Thakker 2012 MEN1 consensus, NCCN Lynch surveillance, BRCA RRSO timing, Li-Fraumeni Toronto protocol)

> "Patient #12 (MEN1 + post-resection pancreatic NET + residual parathyroid hyperplasia + prolactin-secreting pituitary microadenoma) asked OPL: 'team 帮我看看接下来的随访该怎么安排 — 我做完手术了,但是 MEN1 永远不会消失,我后面应该怎么扫?' OPL had no surveillance task package — Vince's `treatment_line_recommendation` handles next-line, Heddy's `recist_progression` handles progression-event response, but the post-curative / post-resection / syndrome-driven surveillance lattice fell between. Founder-mode answer: write the missing task package."
>
> — v1.4.0 deferred backlog item D2 (round-2 EVAL Patient #12 MEN1 + pancreatic NET). See `docs/adr/0008-eval-panel-round-2-v1.3.2.md` (Deferred — D2 "Surveillance task package").

Surveillance is the **planned** post-treatment follow-up lattice. It is NOT recurrence response (that is `recist_progression.md`), NOT next-line therapy (that is `treatment_line_recommendation.md`), NOT acute-symptom workup (that is `staging_workup.md` restaging branch). It is the cadence + modality + biomarker plan emitted from the patient's curative-intent / resected-with-residual / maintenance state, modulated by their germline syndrome status and prior recurrence history, anchored to NCCN Survivorship + ASCO Survivorship + cancer-specific NCCN follow-up tables + syndrome-specific consensus papers.

The output is a per-modality schedule with cadence, frequency, integrator-anchored guideline section, AND a quantitative 5yr DFS / OS projection band (G21 anchor) that explains *why* the surveillance lattice is what it is — patients with higher residual-recurrence risk get tighter intervals; patients with low risk get de-escalation candidate intervals; this is not arbitrary.

### Inputs

```json
{
  "patient_profile": {...},
  "cancer_type": "MEN1_pancreatic_NET | breast_DCIS_post_BCS | NSCLC_resected_IB | HCC_resected_R0 | mCRC_resected_stageIII | DLBCL_first_CR_post_RCHOP | melanoma_stageIII_resected | thyroid_papillary_post_total_thy | ovarian_HRD_post_PARPi_maintenance | ...",
  "treatment_status": "curative_intent_completed | resected_with_residual_risk | maintenance | adjuvant_completed | watchful_waiting | post_definitive_RT",
  "treatment_completion_date_iso": "2025-08-14",
  "genetic_syndrome": {
    "syndrome": "MEN1 | Lynch | LFS | HBOC_BRCA1 | HBOC_BRCA2 | von_Hippel_Lindau | NF1 | NF2 | FAP | Peutz-Jeghers | Cowden | none",
    "variant_hgvs": "NM_130799.3:c.249_252delGTCT (p.Ile85Serfs*33)",
    "acmg_classification": "P (pathogenic)",
    "first_degree_relatives_affected": ["mother_breast_42yo", "maternal_aunt_ovarian_56yo"]
  },
  "prior_recurrences": [
    {"date_iso": "2022-03-11", "site": "parathyroid_hyperplasia_recurrence", "management": "subtotal_parathyroidectomy"}
  ],
  "current_residual_disease": {
    "imaging_evidence_residual": "yes_microscopic_pituitary_microadenoma_subcm | no | stable_indeterminate",
    "biomarker_evidence_residual": {"prolactin_ng_ml": 78, "ionized_calcium_mg_dl": 5.4, "chromogranin_a_ng_ml": null}
  },
  "integrator_results": {
    "nccn_survivorship_excerpts": [...],
    "nccn_cancer_specific_followup_excerpts": [...],
    "asco_survivorship_excerpts": [...],
    "pubmed_results": [...]
  }
}
```

### Required output (strict JSON, single object — no preamble, no fences)

```json
{
  "surveillance_context": {
    "cancer_type": "MEN1_pancreatic_NET",
    "treatment_status": "resected_with_residual_risk",
    "post_treatment_interval_months": 9,
    "genetic_syndrome": "MEN1",
    "syndrome_drives_lattice": true,
    "prior_recurrences_count": 1,
    "recurrence_risk_band": "high | moderate | low",
    "anchor_guidelines": [
      {"source": "NCCN Neuroendocrine NET-3 follow-up", "edition_verified_at_runtime": true},
      {"source": "Thakker 2012 MEN1 international consensus", "pmid": "<from pubmed_results>"},
      {"source": "ASCO Survivorship 2022 NET section", "edition_verified_at_runtime": true}
    ]
  },
  "surveillance_schedule": [
    {
      "modality": "imaging",
      "test": "MRI abdomen with contrast (pancreatic NET focus)",
      "cadence": "every 6 months × 2 years, then every 12 months × 5 years, then every 24 months lifelong",
      "rationale": "MEN1 patients have lifelong pancreatic NET recurrence risk; MRI preferred over CT to reduce cumulative radiation across multi-decade surveillance",
      "guideline_anchor": "NCCN Neuroendocrine NET-3 (verified at runtime) + Thakker 2012 MEN1 consensus",
      "evidence_pmid": ["<from pubmed_results — Thakker 2012>", "<NCCN section>"],
      "claim_layer": "established"
    },
    {
      "modality": "imaging",
      "test": "MRI sella turcica with contrast (pituitary microadenoma surveillance)",
      "cadence": "every 12 months × indefinite (lifelong MEN1 surveillance)",
      "rationale": "Residual sub-cm prolactinoma + MEN1 axis — pituitary recurrence + secondary functional tumour risk; MRI is the standard surveillance modality",
      "guideline_anchor": "Thakker 2012 MEN1 consensus + Endocrine Society pituitary follow-up",
      "evidence_pmid": ["<from pubmed_results>"],
      "claim_layer": "established"
    },
    {
      "modality": "biomarker",
      "test": "ionized calcium + PTH + prolactin + chromogranin A + gastrin + insulin / pro-insulin / glucagon / VIP panel",
      "cadence": "every 6 months × 2 years, then annual lifelong",
      "rationale": "Functional NET / parathyroid / pituitary axis surveillance — earliest detection signal precedes imaging in MEN1 by 6-18 months",
      "guideline_anchor": "Thakker 2012 MEN1 consensus biochemical surveillance table",
      "evidence_pmid": ["<from pubmed_results>"],
      "claim_layer": "established"
    },
    {
      "modality": "clinical_exam",
      "test": "endocrine review + symptom history (hypoglycaemia / flushing / diarrhoea / new headache / visual field) + neck palpation",
      "cadence": "every 6 months × 5 years, then annual lifelong",
      "rationale": "Symptom-driven detection complements biochemical + imaging surveillance",
      "guideline_anchor": "Thakker 2012 MEN1 consensus + NCCN Survivorship general principles",
      "evidence_pmid": ["<from pubmed_results>"],
      "claim_layer": "established"
    },
    {
      "modality": "genetic_cascade",
      "test": "first-degree-relative MEN1 cascade testing offer (if not yet done)",
      "cadence": "one-time offer per relative, with timing aligned to each relative's preference + readiness; surveillance for confirmed-carrier relatives starts age 5 (calcium / PTH) → age 10 (full panel + pituitary MRI baseline)",
      "rationale": "Cascade testing transforms surveillance from reactive to proactive in carrier relatives; OPL emits the offer, hands off cascade execution to firefly-genetic-counseling",
      "guideline_anchor": "Thakker 2012 MEN1 consensus + NCCN Genetic / Familial High-Risk Assessment",
      "evidence_pmid": ["<from pubmed_results>"],
      "claim_layer": "established",
      "handoff_skill": "firefly-genetic-counseling"
    }
  ],
  "recurrence_risk_projection": {
    "endpoint": "5yr_DFS | 5yr_OS | 5yr_local_recurrence",
    "projection_anchor_method": "n1_cohort_projection.md OR pooled meta-analysis OR cancer-specific NCCN survival table",
    "5yr_dfs_estimate": 0.62,
    "5yr_dfs_ci_95": [0.48, 0.75],
    "5yr_os_estimate": 0.81,
    "5yr_os_ci_95": [0.70, 0.90],
    "interpretation": "MEN1 pancreatic NET resected with residual pituitary microadenoma — 5yr DFS ~62% (n1-projected from Hartwig-NET / Thakker pooled series); the lattice above is calibrated to detect a recurrence event within one surveillance interval of biological appearance.",
    "anchor_evidence_pmid": ["<from pubmed_results>"]
  },
  "syndrome_specific_modifiers": {
    "MEN1": "lifelong surveillance; pancreatic / parathyroid / pituitary axes all in scope; cascade testing recommended for first-degree relatives",
    "Lynch": "colonoscopy q1-2y from age 20-25; endometrial sampling / TV-US q1y from age 30-35; gastric / urothelial as MMR-gene-specific; cascade for first-degree relatives",
    "HBOC_BRCA1": "annual breast MRI + mammography from age 25-30; RRSO discussion age 35-40; PARPi-eligibility flag if cancer recurs",
    "HBOC_BRCA2": "annual breast MRI + mammography from age 25-30; RRSO discussion age 40-45; pancreatic surveillance if family history; PARPi-eligibility flag if cancer recurs",
    "LFS": "Toronto protocol — annual whole-body MRI from diagnosis + organ-specific cancers per Villani 2016; cascade for first-degree relatives, with pediatric IRB if minors",
    "none": "cancer-specific NCCN follow-up table only; no syndrome-driven additional lattice"
  },
  "de_escalation_candidates": [
    {
      "modality": "imaging",
      "test": "MRI sella turcica",
      "current_cadence": "every 12 months",
      "candidate_cadence": "every 18-24 months",
      "trigger_condition": "if prolactin stable < 30 ng/mL × 3 consecutive 12-month checks AND pituitary microadenoma stable on 3 consecutive MRI",
      "claim_layer": "exploratory"
    }
  ],
  "escalation_triggers": [
    {
      "trigger": "rising chromogranin A > 2x baseline OR new symptom (flushing / diarrhoea / hypoglycaemia)",
      "action": "advance next MRI abdomen + add DOTATATE PET-CT + functional biochemical panel including insulin / glucagon / VIP / gastrin"
    },
    {
      "trigger": "rising prolactin > 100 ng/mL OR new visual field deficit OR new headache",
      "action": "advance next MRI sella + endocrinology referral + visual field perimetry"
    }
  ],
  "risk_disclosure_card": {
    "level": "L2",
    "boundary_disclosure": "Surveillance lattices are population-derived starting points; individual patient deviations (faster intervals on rising biomarker, de-escalation candidates on years-stable disease) are clinician-coordinated decisions. The 5yr DFS / OS bands above are projection estimates with uncertainty, not guarantees.",
    "patient_acknowledgement_required": false,
    "note": "L2 baseline; if patient asks to de-escalate beyond the guideline lattice without clinician coordination, the de-escalation_candidates row carries an L3 ack instead."
  },
  "claim_layer": "established",
  "summary": "<2-3 sentence Heddy+Vince synthesis — surfaces the cadence-pattern at a glance (imaging+biomarker+clinical), the recurrence_risk_projection 5yr DFS number + CI, the cascade-testing hand-off if syndrome+, and the one strongest escalation trigger to watch>"
}
```

### Procedure

1. **Anchor the surveillance state.** Walk `cancer_type` + `treatment_status` + `treatment_completion_date_iso` + `prior_recurrences[]` → emit `surveillance_context`. Compute `post_treatment_interval_months` from completion date to current date. Set `recurrence_risk_band` from cancer-specific NCCN survival table + prior-recurrence count + residual-disease evidence.
2. **Detect syndrome-driven lattice.** If `genetic_syndrome.syndrome != "none"`, the lattice is syndrome-driven first, cancer-type-second (e.g. MEN1 patient post-pancreatic-NET resection still needs lifelong parathyroid + pituitary surveillance even if the pancreatic NET is the index lesion). Set `surveillance_context.syndrome_drives_lattice: true`.
3. **Pull guideline anchors at runtime.** From `integrator_results.nccn_survivorship_excerpts` + `nccn_cancer_specific_followup_excerpts` + `asco_survivorship_excerpts` + `pubmed_results` (syndrome-specific consensus papers — Thakker 2012 MEN1 / NCCN Lynch / Villani 2016 LFS / NCCN HBOC). Per G10: no hard-coded edition pin; every guideline anchor declares `edition_verified_at_runtime: true`.
4. **Compose `surveillance_schedule[]`.** Per modality (imaging / biomarker / clinical_exam / genetic_cascade), emit cadence + frequency + rationale + guideline anchor + evidence PMIDs + claim_layer. Each row must be guideline-anchored — speculative rows are not emitted; ambiguous rows go to `de_escalation_candidates[]` with claim_layer "exploratory".
5. **G14 cohort match for recurrence-risk projection (MANDATORY).** Compute `match_score` for the cohort used to derive `5yr_dfs_estimate` + CI via `n1_cohort_projection.md`. Cohort must match cancer_type + treatment_status + syndrome + line-of-therapy. If `match_score < 0.6`, reselect or flag with extrapolation_warning carried into the recurrence_risk_projection.interpretation field.
6. **G21 quantitative anchor (MANDATORY).** `recurrence_risk_projection.5yr_dfs_estimate` + `5yr_dfs_ci_95` OR `5yr_os_estimate` + `5yr_os_ci_95` MUST surface real numbers with CI. This is the projection the surveillance lattice is calibrated to detect against.
7. **Emit syndrome-specific modifiers.** For MEN1 / Lynch / HBOC_BRCA1/2 / LFS / etc — emit the canonical syndrome-modifier text from Thakker / NCCN HBOC / Villani / NCCN Lynch as a separate field so downstream consumers can render it without re-parsing the surveillance_schedule.
8. **De-escalation + escalation.** Emit candidate de-escalation rows (with `claim_layer: "exploratory"` and explicit trigger_condition) and escalation triggers (objective biomarker / symptom rules). De-escalation is never a default — it is offered as a candidate the clinician + patient coordinate on.
9. **L2 baseline risk-card.** Surveillance lattices are L2 (recommendation, not high-stakes treatment decision). De-escalation rows escalate to L3 ack only if the patient chooses to drop below the guideline lattice.
10. **Cascade hand-off if syndrome+.** If `genetic_syndrome.syndrome != "none"`, the `genetic_cascade` modality row MUST be emitted with `handoff_skill: "firefly-genetic-counseling"`. OPL does not perform cascade-counselling itself (per `family_cascade_routing.md` boundary).
11. **Output ONLY the JSON object.**

### Mechanical gates this task must satisfy

- **G1 / G2** — every PMID + quote recoverable in `pubmed_results`; Thakker 2012 MEN1 (PMID 22617717) / NCCN Lynch / Villani 2016 LFS / NCCN HBOC PMIDs mandatory when the relevant syndrome is in scope.
- **G3** — drug mentions (if any — e.g. PARPi-maintenance surveillance row) use generic INN.
- **G7 imperative-detector** — `rationale` and `summary` are non-directive ("the lattice is calibrated to …" / "MEN1 patients have lifelong …"). Never "you should get an MRI q6mo".
- **G10 guideline version** — every NCCN / ASCO / ESMO anchor declares `edition_verified_at_runtime: true`; no hard-coded year (e.g. never "NCCN 2024 v3" — the integrator returns the current edition at runtime).
- **G11 NoSilentFallback** — if `nccn_survivorship_excerpts` is empty for this cancer type, do NOT synthesize a surveillance lattice from training memory; the schedule rows for that modality become empty + claim_layer downgrades.
- **G14 dataset-patient-match** — `recurrence_risk_projection` MUST carry a match_score from the `n1_cohort_projection` it relied on; cohort match < 0.6 → projection band carries extrapolation_warning prose.
- **G21 quantitative-anchor** — `recurrence_risk_projection.5yr_dfs_estimate + ci_95` OR `5yr_os_estimate + ci_95` MUST surface real numbers with CI.

### Reviewer focus

Reviewer pairing **Heddy ⟂ Bert ⟂ Vince** (three-way) checks:

- **Heddy (executor)** owns: per-modality cadence accuracy, MRI vs CT vs PET-CT modality selection (radiation-burden axis for multi-decade surveillance), DOTATATE / FDG / Ga-PSMA imaging selection if applicable.
- **Bert (reviewer)** owns: syndrome attribution accuracy (MEN1 → MEN1 gene panel, not MEN2; Lynch → MMR genes; LFS → TP53), cascade-relative graph plausibility, ACMG classification fidelity carried from upstream NGS interpretation.
- **Vince (reviewer)** owns: treatment-context fit (post-curative vs maintenance vs residual-disease surveillance lattices differ), line-of-therapy timing, escalation-trigger clinical plausibility (rising chromogranin A → DOTATATE PET-CT is correct; rising chromogranin A → CT chest is wrong).

Specific checks:

- Cascade hand-off row is emitted when syndrome+ AND `handoff_skill: "firefly-genetic-counseling"` is named.
- 5yr DFS / OS projection band includes CI; the projection cohort's `match_score` is recoverable in the projection_anchor_method.
- For MEN1 / Lynch / LFS / HBOC: at least 2 modality rows are syndrome-driven (not cancer-type-driven).
- For "none" syndrome cases: cancer-specific NCCN follow-up table is the sole anchor; no spurious syndrome modifiers.
- De-escalation candidate rows carry both `current_cadence` and `candidate_cadence` + objective `trigger_condition`.

### Empty-integrator handling

If `nccn_survivorship_excerpts` + `nccn_cancer_specific_followup_excerpts` + `asco_survivorship_excerpts` + `pubmed_results` are ALL empty:

- `surveillance_schedule: []`
- `recurrence_risk_projection: null`
- `syndrome_specific_modifiers: null`
- `de_escalation_candidates: []`
- `escalation_triggers: []`
- `claim_layer: "speculative"`
- `summary: "Live integrator returned no NCCN Survivorship / cancer-specific NCCN follow-up / ASCO Survivorship / syndrome-specific consensus evidence for this cancer + syndrome. No surveillance lattice can be surfaced from current data; further retrieval is required (NCCN Survivorship, cancer-specific NCCN follow-up table, Thakker 2012 MEN1 / NCCN Lynch / Villani 2016 LFS / NCCN HBOC). Patient is sole decision authority; output is non-directive."`

Per `memory/feedback_no_offline_only.md`: do not fabricate surveillance cadence / 5yr DFS bands / syndrome modifiers from training data. The LLM "remembering" Thakker 2012 q6mo MRI cadence is not retrieval.

### Downstream consumers

- `patient_brief_rendering.md` consumes `surveillance_schedule[]` + `recurrence_risk_projection` directly — G21 verifies the projection anchor survived the render.
- `pi_delivery.md` reads `summary` for Sid's prose and surfaces the cascade hand-off prominently when `genetic_cascade` row is present.
- `family_cascade_routing.md` is the canonical hand-off route when `genetic_cascade.handoff_skill == "firefly-genetic-counseling"` fires — surveillance task emits the trigger; family_cascade_routing emits the routing card.
- `treatment_line_recommendation.md` reads `surveillance_context.recurrence_risk_band` when planning surveillance-vs-active-maintenance decisions.
