## Task Package · n1_cohort_projection

**Capability domain:** D3 — Data evidence / N=1 projection
**Expert portfolio owners:** **Aviv** (primary, projection methodology — Cox modelling, KM stratification, calibration) + **Iain** (cross-read, pooled-evidence overlay against same-agent meta-analysis), with Tyler optionally invoked when single-cell / multi-omics features must be projected (deferred to Wave 3 sub-task if so).
**Preferred integrator families:** F5 Cohort / dataset (TCGA / Hartwig / ICGC / cBioPortal / GDC / BeatAML for AML / DepMap as needed for cell-line projection), F1 Literature (PubMed for the published cohort's primary descriptor paper), F7 Cell-line dependency (DepMap / CCLE for pharmacology axis if relevant)

> "Patient #10 asked: 'I am M1c castration-resistant prostate cancer with BRCA2 biallelic, ECOG 1, prior abi + enza + docetaxel + cabazitaxel + Pluvicto + olaparib — what does the literature actually predict for my 12-month survival from this state, with my features, against a real cohort?' Founder-mode answers this with a Cox-projected quantitative band, not a label like 'late-line mCRPC'."
>
> — v1.3.0 EVAL panel finding (Patient #10 LM-positive mCRPC). See `references/founder-mode-philosophy.md` L22 ("OPL gives quantitative prediction — pooled HR/OR/RR + 95% CI + p-value + patient-projected scores + Cox / KM survival predictions").

A N=1 projection is the operation:

1. Identify the patient's clinico-genomic signature (`feature_extraction_from_patient`).
2. Choose a cohort whose patients carry the same disease + line-of-therapy + measurable signature axes (`cohort_source` — must pass G14 dataset-match).
3. Fit / re-fit a Cox proportional-hazards model on cohort features.
4. Project the patient onto the cohort's risk distribution → emit `projected_estimate` (OS-12mo / PFS-XX / OR / probability of response) with 95% CI.
5. Stratify cohort into KM groups using the patient's discriminating features → emit `km_groups + log_rank_p`.
6. Enumerate axes where the patient deviates from the cohort beyond the cohort's covariate range (`extrapolation_warnings`) — these are honesty markers, not blockers.

This task is the quantitative-anchor source for any L3-level survival claim and is required by `irae_rechallenge.md` for its rebound-probability projection.

### Inputs

```json
{
  "patient_profile": {...},
  "patient_features_extracted": {
    "disease": "mCRPC",
    "line_of_therapy_ordinal": 7,
    "ecog": 1,
    "biomarkers": {"BRCA2": "biallelic_loss", "AR_V7": "negative", "PSMA_PET": "positive"},
    "metastatic_pattern": ["bone_diffuse", "LN", "leptomeningeal"],
    "labs": {"hb_g_dl": 9.8, "alp_u_l": 412, "ldh_u_l": 380, "alb_g_l": 33},
    "lab_trajectory": {
      "AFP_ng_ml": {
        "slope_per_month": 1670,
        "doubling_time_mo": 0.93,
        "fold_change_x": 35.0,
        "baseline_value": 240,
        "latest_value": 8400,
        "trajectory_span_months": 5,
        "trajectory_class": "rapidly_rising | rising | stable | falling | rapidly_falling"
      },
      "PSA_ng_ml": null,
      "CA15_3_u_ml": null,
      "CA125_u_ml": null,
      "CEA_ng_ml": null,
      "LDH_u_l": null
    }
  },
  "candidate_cohorts": [
    {"dataset_id": "TCGA-PRAD", "filtered_subset_query": "AJCC_M_stage = M1c"},
    {"dataset_id": "Hartwig-PCa", "filtered_subset_query": "treatment_line >= 4 AND BRCA2_LOH = TRUE"},
    {"dataset_id": "ICGC-PROFILE", "filtered_subset_query": "..."}
  ],
  "endpoint": "OS-12mo | PFS-6mo | ORR-RECIST | OS-median",
  "integrator_results": {
    "cohort_data": {"<dataset_id>": {<patient-level table reference>}},
    "pubmed_results": [...]
  }
}
```

### Required output (strict JSON, single object — no preamble, no fences)

```json
{
  "projection_id": "proj_<8-char>",
  "patient_features_used": ["line_of_therapy_ordinal", "ecog", "BRCA2_biallelic", "alp_u_l", "ldh_u_l", "alb_g_l", "PSMA_PET", "metastatic_pattern_LM", "lab_trajectory:AFP_ng_ml:slope_per_month", "lab_trajectory:AFP_ng_ml:doubling_time_mo"],
  "cohort_source": {
    "dataset_id": "Hartwig-PCa",
    "filtered_subset_query": "treatment_line >= 4 AND BRCA2_LOH = TRUE AND AJCC_M = M1c",
    "n_after_filter": 287,
    "median_followup_mo": 18.4,
    "primary_descriptor_pmid": "<PMID>",
    "match_score": 0.74,
    "match_score_axes": {
      "cancer_type_score": 1.0,
      "stage_score": 1.0,
      "platform_score": 0.9,
      "sample_size_score": 0.85,
      "metastatic_site_score": 0.45,
      "ethnicity_score": 0.6
    }
  },
  "cohort_alternatives_attempted": [
    {
      "dataset_id": "Hartwig-PCa",
      "ordinal": 1,
      "selected": true,
      "n_after_filter": 287,
      "match_score": 0.74,
      "reason": "primary candidate; DUA-raised + accessible; match_score above 0.6 floor"
    },
    {
      "dataset_id": "ICGC-PROFILE-PCa",
      "ordinal": 2,
      "selected": false,
      "n_after_filter": null,
      "match_score": null,
      "reason": "fallback_skipped — primary cohort sufficient"
    }
  ],
  "feature_extraction_from_patient": [
    {"patient_feature": "BRCA2 biallelic_loss", "cohort_feature": "BRCA2_LOH = TRUE", "mapping_type": "exact"},
    {"patient_feature": "alp_u_l = 412", "cohort_feature": "alp_above_uln_2x", "mapping_type": "discretised"},
    {"patient_feature": "leptomeningeal mets", "cohort_feature": "LM_positive", "mapping_type": "axis_outside_cohort_distribution"}
  ],
  "cox_model_spec": {
    "endpoint": "OS-12mo",
    "features": ["line_of_therapy_ordinal", "ecog", "BRCA2_biallelic", "alp_above_uln_2x", "ldh_above_uln", "alb_g_l_lt_35"],
    "covariates_adjusted": ["age", "first_diagnosis_to_advanced_mo"],
    "regularization": "l2_ridge_alpha_0.5",
    "ties": "breslow",
    "cox_beta_per_feature": {"BRCA2_biallelic": -0.42, "alp_above_uln_2x": 0.71, "ldh_above_uln": 0.53, "alb_g_l_lt_35": 0.61, "ecog": 0.38, "line_of_therapy_ordinal": 0.22},
    "concordance_index": 0.68,
    "calibration_slope": 0.94
  },
  "km_groups": [
    {"group": "BRCA2 LOH + ALP normal + ALB ≥ 35", "n": 41, "median_os_mo": 18.7, "ci_95": [14.2, 22.9]},
    {"group": "BRCA2 LOH + ALP elevated + ALB < 35", "n": 38, "median_os_mo": 7.3, "ci_95": [5.4, 9.1]},
    {"group": "BRCA2 LOH + LM positive (n < 10)", "n": 9, "median_os_mo": 3.8, "ci_95": [1.9, 6.2]}
  ],
  "log_rank_p": 0.0008,
  "projected_estimate": {
    "endpoint": "OS-12mo",
    "value": 0.31,
    "ci_95": [0.18, 0.46],
    "interpretation": "Patient projected to the 17th percentile of the Hartwig-PCa BRCA2-LOH M1c subcohort. 12-month overall-survival probability 0.31 [95% CI 0.18–0.46]."
  },
  "match_score": 0.74,
  "extrapolation_warnings": [
    {"axis": "leptomeningeal_mets", "axis_status": "outside_cohort_distribution", "cohort_n_at_axis": 9, "warning": "LM-positive subgroup has n=9 in this cohort; CI on KM is wide; this projection should be read as a lower bound on prognosis, not a calibrated estimate."},
    {"axis": "PSMA-RLT post-progression", "axis_status": "covariate_not_modelled", "warning": "Hartwig-PCa pre-dates routine PSMA-RLT use; the cohort baseline survival may under-represent patients who have already received Lu-177 — adjust qualitatively."}
  ],
  "evidence_chain": [
    {"type": "dataset", "ref": "Hartwig-PCa", "summary": "n=287 after filter; Cox C-index 0.68; calibration slope 0.94"},
    {"type": "pmid", "id": "<from pubmed_results>", "quote": "<descriptor paper for Hartwig-PCa cohort>"}
  ],
  "claim_layer": "exploratory",
  "summary": "<2-3 sentence Aviv synthesis — surfaces the projected_estimate.value + CI + the strongest extrapolation_warning so Sid can deliver honestly>"
}
```

### Procedure

1. **G14 with ordered candidate fallback chain (v1.4.0).** Iterate `candidate_cohorts[]` in declared order. For each candidate:
   1. Attempt retrieval via the registered integrator (Hartwig DUA gate / ICGC EGA gate / cBioPortal public / GEO / GDC).
   2. Apply the `filtered_subset_query` and compute `n_after_filter`.
   3. Compute `match_score` per `g14_dataset_patient_match.py`.
   4. Decision:
      - Retrieval raised IntegratorError (DUA-gated / EGA-DAC-gated / not_yet_raised) → record `reason: "DUA-gated"` / `"EGA-DAC-gated"` / `"<specific access path>"`; CONTINUE to next candidate.
      - `n_after_filter == 0` → record `reason: "empty after filter"`; CONTINUE.
      - `n_after_filter < 10` for the patient's projected feature combo → record `reason: "small_n: n_after_filter=<N> below n=10 floor"`; CONTINUE (but stash as a soft-fallback for the empty-candidate tail-case).
      - `match_score < 0.6` overall → record `reason: "match_score_low: <score>"`; CONTINUE.
      - All checks passed → mark `selected: true`; STOP iteration; this is the winning cohort.
   5. Record per-candidate `{dataset_id, ordinal, selected, n_after_filter, match_score, reason}` to `cohort_alternatives_attempted[]` regardless of selection outcome — the evidence trail surfaces in the patient brief so the reader sees every cohort tried.
   6. Example fallback chains (planner hint, not exhaustive):
      - **HCC**: [Hartwig-HCC, ICGC-LIRI-JP, cBioPortal-LIHC, GEO-HCC-TACE-refractory pooled (GSE14520+GSE54236+...)]
      - **mCRPC**: [Hartwig-PCa, ICGC-PROFILE-PCa, cBioPortal-MSK-IMPACT-PCa, SU2C-PCF mCRPC dream-team]
      - **BRCA-NSCLC** (rare combo): [Hartwig-NSCLC-BRCA-subset, cBioPortal-MSK-IMPACT-NSCLC, MSK-IMPACT-pan-cancer-BRCA, AACR-GENIE-BRCA-pan-cancer] — fallback chain is essential because primary cohort yields n<10 for any BRCA-NSCLC combo
      - **AML R/R**: [BeatAML 2.0, Hartwig-AML, TARGET-AML, cBioPortal-OHSU-AML]
   7. If ALL candidates exhaust without selection (every one returned DUA-gated / empty / small_n / low_match), emit `cohort_source: null` + `projected_estimate: null` + `claim_layer: "speculative"` + `summary: "All candidate cohorts (<N>) failed selection — see cohort_alternatives_attempted[] for per-candidate reason. No N=1 projection can be surfaced."` Per `memory/feedback_no_offline_only.md`: do NOT silently fall back to training-data Cox β.
   Conditional-axis weak (e.g. `metastatic_site_score < 0.4`) on the *selected* cohort does NOT block but feeds `extrapolation_warnings`.
2. **Feature extraction.** Walk `patient_profile` + Bert NGS upstream + Vince treatment-line upstream and produce `feature_extraction_from_patient[]`. Each mapping declared `mapping_type: exact | discretised | axis_outside_cohort_distribution`. Outside-distribution features must surface to `extrapolation_warnings`.
   - **v1.4.0 — lab_trajectory features (MANDATORY where applicable).** For cancers where a serum biomarker is the strongest prognostic signal, feature_extraction MUST emit trajectory features (slope_per_month, doubling_time_mo, fold_change_x, baseline_value, latest_value) and NOT just the latest static value. The Cox model picks up the trajectory features as covariates — a static AFP of 8400 in HCC is a different prognostic signal than an AFP that climbed 240→8400 over 5 months (35x rise). Canonical trajectory-eligible biomarkers (per cancer):
     - **HCC**: AFP, AFP-L3, DCP/PIVKA-II
     - **PCa / mCRPC**: PSA
     - **TNBC + ER+/HER2-**: CA15-3
     - **ovarian (HGSOC)**: CA-125
     - **CRC**: CEA
     - **pancreatic**: CA19-9
     - **gastric**: CA72-4, CEA
     - **AML**: WBC, blast %, peripheral blast %
     - **MM**: M-protein, light chains, beta-2 microglobulin
     - **DLBCL / lymphoma**: LDH (trajectory) + soluble IL-2R
     - **HCC / pancreatic NET**: chromogranin A (NET-specific)
     If the patient has ≥2 serial measurements of an eligible biomarker spanning ≥30 days, emit the trajectory features. If only 1 measurement is available, emit `lab_trajectory.<biomarker>: null` and surface "single measurement; trajectory not computable" to `extrapolation_warnings`. The LLM may NOT fabricate a trajectory from a single value — that violates `memory/feedback_no_offline_only.md`.
3. **Cox model.** Fit (or re-fit) a Cox PH model on cohort features. Declare regularisation, ties handling, concordance index, calibration slope. C-index < 0.6 → downgrade `claim_layer: "speculative"`.
4. **KM stratification.** Stratify the cohort into clinically interpretable groups using the patient's discriminating features (NOT a single binarisation of the patient feature). Emit `km_groups[]` with `n`, `median_os_mo`, `ci_95`. Run a log-rank across all groups → emit `log_rank_p`.
5. **Projection.** Compute the patient's risk score = β · x_patient (covariate-adjusted). Map onto cohort risk-distribution → emit `projected_estimate.value` + `ci_95` + percentile interpretation. The interpretation string is the G21 quantitative anchor.
6. **Honesty markers.** For every axis where the patient is outside the cohort's covariate range (e.g. line-of-therapy 7 when cohort max is 4, or LM-positive when cohort has n=9 at that axis), emit `extrapolation_warnings[]`. These do not block — they protect the patient from over-interpreting the band.
7. **Output ONLY the JSON object.**

### Mechanical gates this task must satisfy

- **G1 / G2** — `primary_descriptor_pmid` recoverable in `pubmed_results`; quote required.
- **G11 NoSilentFallback** — if `cohort_data` for the chosen `dataset_id` is empty / unreachable, raise IntegratorError; do not synthesize a Cox fit from training data.
- **G14 dataset-patient-match** — `match_score` MUST be emitted; ≥ 0.6 overall OR Reviewer-endorsed retention with caveats.
- **G15 multiple-testing correction** — if multiple KM strata + multiple cox-feature p-values are reported, Bonferroni / BH must be applied; emit `multiple_testing_correction: "BH_FDR_0.05"` in the model spec.
- **G16 batch-effect declared** — if cohort cuts across batches (e.g. Hartwig multi-site sequencing) the batch variable must be declared as covariate.
- **G21 quantitative-anchor** — `projected_estimate.value` + `ci_95` + `interpretation` MUST surface a real number with CI; G21 enforces this on the downstream patient brief.

### Reviewer focus

Reviewer pairing **Aviv ⟂ Iain** checks:

- **Aviv (executor)** owns: Cox spec, C-index, calibration, KM stratification, projection percentile.
- **Iain (reviewer)** owns: cohort-choice sanity (right cohort for this disease / line / biomarker), pooled-evidence cross-check (is this projection's HR / CI inside the meta-analysis interval for the same agent / line in published RCTs?), extrapolation-warning completeness.

Specific checks:

- All KM groups have `n` reported; subgroups with `n < 10` carry an explicit small-n warning (mandatory in `extrapolation_warnings`).
- The `projected_estimate.interpretation` includes both the absolute number and the percentile context.
- `feature_extraction_from_patient[]` covers every feature actually in `cox_model_spec.features`.
- No invented Hazard Ratios or CIs — every numeric in the output is computable from `integrator_results.cohort_data` and the declared model spec.

### Empty-integrator handling

If `integrator_results.cohort_data` is empty (no cohort retrievable):

- `projection_id: null`
- `cohort_source: null`
- `cox_model_spec: null`
- `km_groups: []`
- `projected_estimate: null`
- `extrapolation_warnings: []`
- `claim_layer: "speculative"`
- `summary: "Live integrator returned no cohort data for this patient's disease + line-of-therapy + biomarker signature. No N=1 projection can be surfaced from current data; further retrieval is required (Hartwig DUA / ICGC controlled-access / cBioPortal study request). Patient is sole decision authority; output is non-directive."`

Per `memory/feedback_no_offline_only.md`: the LLM may not fabricate Cox β / KM median-OS / projection percentiles from training data. N=1 projection without retrieval is not allowed.

### Downstream consumers

- `irae_rechallenge.md` consumes this task's output to project rebound probability with CI.
- `intrathecal_therapy_navigation.md` consumes the LM-positive subgroup KM for the prognosis-band field.
- `treatment_line_recommendation.md` may consume the `projected_estimate` as the L3 quantitative anchor for any line-of-therapy recommendation.
- `patient_brief_rendering.md` reads `projected_estimate.interpretation` directly into the patient brief — G21 verifies the anchor survived the render.
