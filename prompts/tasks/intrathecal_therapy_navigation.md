## Task Package · intrathecal_therapy_navigation

**Capability domain:** D1 — Clinical decision support / leptomeningeal metastasis (LM) navigation
**Expert portfolio owners:** **Ted** (interventional / radiation — primary, owns the Ommaya / craniospinal / HA-WBRT route axis) co-reviewed by **Vince** (systemic-options overlay — IT methotrexate vs IT trastuzumab vs IT nivolumab depending on systemic regimen integration) + **Jen** (palliative + symptom + prognosis-honest framing — owns the prognosis_band emission and the L3 / L4 disclosure framing).
**Preferred integrator families:** F1 Literature (PubMed for Chamberlain framework, IT-route trials, RANO-LM response criteria), F3 Trials (CT.gov / ChiCTR / ISRCTN / EU-CTR for IT-trastuzumab HER2-LM, IT-nivolumab NCT03025256, proton craniospinal trials), F2 Guidelines (NCCN CNS / ESMO CNS — runtime-verified), F8 EAP (compassionate access to IT-trastuzumab outside FDA label, IT-pembrolizumab off-label)

> "Patient #10 has leptomeningeal mets on top of M1c mCRPC. No single OPL expert owns LM. The 2026 expert roster has Ted for IO/RT, Vince for systemic, Jen for palliative — but the LM route-decision (IT-MTX vs IT-cytarabine vs IT-trastuzumab vs HA-WBRT vs craniospinal proton vs supportive) is not currently owned end-to-end. Founder-mode says: name the gap, write the task package, route through the three reviewers, surface the honest prognosis band."
>
> — v1.3.0 EVAL panel finding (Patient #10 E3). See `references/founder-mode-philosophy.md` L36-L52 ("honest about death window").

LM (leptomeningeal carcinomatosis) is among the most prognostically heavy events in oncology. Untreated median survival is **4-6 weeks** (Chamberlain framework, Le Rhun ESMO-EANO 2017 consensus); treated median survival depends on histology + cytology positivity + KPS + extracranial disease status (Chamberlain stratification good vs poor risk). This task package gives the patient a route-options card grounded in: cytology confirmation status, MRI pattern, CSF flow integrity, primary tumour systemic profile, and an honest prognosis band with CI.

### Inputs

```json
{
  "patient_profile": {...},
  "lm_workup": {
    "csf_cytology": "positive | negative | indeterminate | not_done",
    "csf_cytology_taps": 1,
    "mri_brain_with_contrast": "leptomeningeal_enhancement_diffuse | nodular | hydrocephalus | normal",
    "mri_spine_with_contrast": "leptomeningeal_enhancement_thoracic | lumbar | cauda_equina | normal",
    "csf_flow_study": "patent | block_at_C1 | block_at_thoracic | not_done",
    "kps": 70,
    "extracranial_disease_status": "controlled | progressive | uncontrolled",
    "primary_histology": "mCRPC | NSCLC_EGFR | breast_HER2 | breast_TNBC | melanoma_BRAF | ..."
  },
  "systemic_regimen_in_flight": [...],
  "integrator_results": {
    "pubmed_results": [...],
    "trials_results": [...],
    "nccn_excerpts": [...],
    "eap_results": [...]
  }
}
```

### Required output (strict JSON, single object — no preamble, no fences)

```json
{
  "lm_confirmation": {
    "cytology_status": "positive | negative_with_imaging_consistent | indeterminate",
    "imaging_pattern": "Chamberlain_type_I_linear | type_II_nodular | type_III_hydrocephalus | mixed",
    "csf_flow": "patent | obstructed_at_<level>",
    "diagnostic_confidence": "high | moderate | low",
    "confidence_rationale": "<one line — what supports / undermines the LM diagnosis>"
  },
  "chamberlain_stratification": {
    "risk_group": "good | poor",
    "risk_axes": {
      "kps_ge_60": true,
      "no_major_neurologic_deficits": true,
      "extracranial_disease_controlled": false,
      "csf_flow_patent": true,
      "expected_survival_without_treatment_weeks": 4
    },
    "stratification_pmid": "<PMID for Chamberlain framework — from pubmed_results>"
  },
  "route_options": [
    {
      "route": "IT-methotrexate",
      "delivery": "Ommaya reservoir preferred over LP if hydrocephalus or CSF flow block",
      "regimen_summary": "12 mg twice weekly induction → weekly consolidation → monthly maintenance per RANO-LM 2017",
      "histology_fit": "histology-agnostic salvage (mCRPC included by extension; primary RCT data in breast / NSCLC / lymphoma)",
      "evidence_pmid": ["<from pubmed_results>"],
      "claim_layer": "established",
      "permission_level": 3,
      "iso_risks": ["chemical arachnoiditis", "leukoencephalopathy", "Ommaya infection", "myelosuppression if intrathecal–systemic overlap"]
    },
    {
      "route": "IT-cytarabine (depot liposomal or standard)",
      "delivery": "Ommaya or LP",
      "regimen_summary": "DepoCyt 50 mg q14d × 5 then q28d × 4 maintenance (where available); standard cytarabine 50 mg twice weekly if depot unavailable",
      "histology_fit": "lymphoma > carcinoma; modest activity in solid-tumour LM",
      "evidence_pmid": ["<from pubmed_results>"],
      "claim_layer": "established",
      "permission_level": 3,
      "iso_risks": ["chemical meningitis (24-72h, often steroid-modifiable)", "depot-related arachnoiditis"]
    },
    {
      "route": "IT-trastuzumab",
      "delivery": "Ommaya, dose-escalation per Bonneau / Kumthekar / Stemmler protocols",
      "regimen_summary": "weekly 80-150 mg IT escalation; pair with systemic anti-HER2",
      "histology_fit": "ONLY HER2-positive primaries (breast_HER2, gastric_HER2, NSCLC_HER2_amp/ex20ins)",
      "evidence_pmid": ["<from pubmed_results>"],
      "trial_in_flight": "<from trials_results — IT-trastuzumab LM trials by NCT ID>",
      "claim_layer": "exploratory",
      "permission_level": 4,
      "iso_risks": ["arachnoiditis", "off-label use → EAP / hospital-exemption pathway needed in some jurisdictions"]
    },
    {
      "route": "IT-nivolumab",
      "delivery": "Ommaya per Glitza Oliva protocol",
      "regimen_summary": "1 mg IT q1-2w escalating to 20 mg per Glitza Oliva NCT03025256 phase I",
      "histology_fit": "melanoma LM (primary trial population); broader use experimental",
      "evidence_pmid": ["<from pubmed_results>"],
      "trial_in_flight": "NCT03025256 (verify status in trials_results)",
      "claim_layer": "speculative",
      "permission_level": 4,
      "iso_risks": ["unique intrathecal irAE class (chemical / immune meningitis distinction unclear)", "post-RT field-effect interactions"]
    },
    {
      "route": "ommaya_reservoir_placement",
      "delivery": "Neurosurgical, programmable shunt if hydrocephalus",
      "regimen_summary": "Enables reproducible IT delivery + reduces multiple-tap morbidity; recommended over repeated LP for any IT route used > 2 cycles",
      "histology_fit": "histology-agnostic",
      "evidence_pmid": ["<from pubmed_results>"],
      "claim_layer": "established",
      "permission_level": 3,
      "iso_risks": ["catheter infection (10-15% lifetime)", "malposition", "obstruction by tumour"]
    }
  ],
  "palliative_radiation_alternatives": [
    {
      "modality": "HA-WBRT (hippocampal-avoidance whole-brain RT)",
      "indication": "bulky nodular LM + cognitive preservation priority; NRG-CC003 / NRG-CC001 backbone",
      "regimen_summary": "30 Gy in 10 fractions hippocampal-avoidance with memantine",
      "histology_fit": "histology-agnostic",
      "evidence_pmid": ["<from pubmed_results>"],
      "trial_in_flight": "<from trials_results>",
      "claim_layer": "established",
      "permission_level": 3
    },
    {
      "modality": "craniospinal_proton",
      "indication": "diffuse leptomeningeal disease + good systemic control + KPS ≥ 80",
      "regimen_summary": "30-36 Gy(RBE) craniospinal proton — Yang / Wong protocols; limited-access centres only",
      "histology_fit": "best evidence in solid-tumour LM (breast / NSCLC / melanoma), emerging in mCRPC",
      "evidence_pmid": ["<from pubmed_results>"],
      "trial_in_flight": "<from trials_results>",
      "claim_layer": "exploratory",
      "permission_level": 4
    }
  ],
  "prognosis_band": {
    "untreated_weeks_median": 5,
    "untreated_ci_95_weeks": [4, 6],
    "treated_months_median_with_ci": {
      "good_risk_chamberlain": {"median_mo": 6.2, "ci_95": [4.1, 8.7], "n_pooled": "<from pmid>"},
      "poor_risk_chamberlain": {"median_mo": 2.4, "ci_95": [1.6, 3.4], "n_pooled": "<from pmid>"}
    },
    "histology_modifier": "<one line — e.g. breast_HER2 with IT-trastuzumab achieves median 12-14 mo in pooled IT-trastuzumab series; mCRPC LM cohort small, prognosis closer to base good/poor band>",
    "anchor_method": "Cox / KM via n1_cohort_projection.md OR pooled meta-analysis via meta_analysis.md",
    "anchor_evidence_pmid": ["<from pubmed_results>"]
  },
  "risk_disclosure_card": {
    "level": "L4",
    "boundary_disclosure": "LM-directed therapy is performed at academic CNS-tumour centres with Ommaya placement capability. Off-label IT routes (trastuzumab / nivolumab) cross experimental territory; outcomes uncertain; multi-disciplinary team and patient acknowledgement required.",
    "patient_acknowledgement_required": true,
    "ack_text_for_patient": "I have read the prognosis band — untreated median ~5 weeks; treated median ~2-6 months depending on Chamberlain risk and histology. I understand IT-trastuzumab / IT-nivolumab are off-label or trial-only. I am the sole decision authority on whether to pursue IT, palliative-only, or trial enrolment."
  },
  "claim_layer": "exploratory",
  "summary": "<2-3 sentence Ted+Jen synthesis — surfaces the prognosis_band numbers, the histology-fit-best route, and the palliative-only honest option>"
}
```

### Procedure

1. **Confirm LM.** Walk `lm_workup` → emit `lm_confirmation`. Cytology positive + MRI consistent → `diagnostic_confidence: "high"`. Cytology negative × 1-2 taps but MRI typical → `moderate`. No cytology done → `low`, recommend cytology before IT (L3 disclosure on the cytology recommendation).
2. **Chamberlain stratification.** Apply the canonical 4-axis stratifier (KPS ≥ 60 + no major neuro deficits + extracranial disease controlled + CSF flow patent → "good"; any fail → "poor"). Cite the Chamberlain PMID.
3. **Route options.** Enumerate IT-MTX + IT-cytarabine + IT-trastuzumab (HER2-only) + IT-nivolumab (melanoma / experimental) + Ommaya placement as a separate enabling option. For each, declare `histology_fit` honestly — IT-trastuzumab is NOT a mCRPC option (the patient #10 in the EVAL is mCRPC; the IT-trastuzumab row is included for completeness but flagged `histology_fit: ONLY HER2-positive`).
4. **Palliative-radiation alternatives.** Emit HA-WBRT + craniospinal proton with regimen + protocol PMID + trial in flight.
5. **Prognosis band.** **MANDATORY.** Emit `untreated_weeks_median + ci_95` and `treated_months_median_with_ci.good_risk_chamberlain` + `poor_risk_chamberlain` with `n_pooled`. The anchor method is either `n1_cohort_projection.md` (if cohort available) OR `meta_analysis.md` (pooled IT-trastuzumab series etc). G21 enforces a quantitative anchor.
6. **L4 risk-disclosure-card.** Mandatory. Patient acknowledgement required because IT-route + experimental routes + the prognosis band are high-stakes.
7. **Output ONLY the JSON object.**

### Mechanical gates this task must satisfy

- **G1 / G2** — every PMID + quote recoverable in `pubmed_results`; Chamberlain framework PMID is mandatory.
- **G3** — drugs use INN (methotrexate, cytarabine, trastuzumab, nivolumab); DepoCyt brand mention permitted in the depot-cytarabine-availability note only.
- **G4** — IT-trastuzumab and IT-MTX dose + frequency + unit declared explicitly.
- **G8 Level-3-4 disclosure** — L4 ack present; IT-trastuzumab and IT-nivolumab are L4; Ommaya placement is L3; missing ack → BLOCK.
- **G10 guideline version** — NCCN CNS / ESMO-EANO LM consensus citations must be runtime-verified (no "ESMO 2017" hard-pin; the model must verify via integrator the current edition).
- **G11 NoSilentFallback** — if `pubmed_results` is empty for IT-trastuzumab, the row is dropped (do not invent Bonneau / Kumthekar / Stemmler doses from training data).
- **G19 PI-imperative-detector** — Sid's downstream prose may not contain "you should choose IT-MTX". Frames as options + Chamberlain risk-grouped survival bands.
- **G21 quantitative-anchor** — `prognosis_band.untreated_weeks_median` AND `treated_months_median_with_ci` MUST surface real numbers with CI. G21 enforces on the patient brief.

### Reviewer focus

Reviewer pairing **Ted ⟂ Vince ⟂ Jen** (three-way) checks:

- **Ted (executor)** owns: route options completeness, Ommaya / craniospinal feasibility, RT-modality regimen + dose accuracy.
- **Vince (reviewer)** owns: systemic-overlap safety (IT-MTX + systemic high-dose MTX → toxic; IT-trastuzumab + systemic anti-HER2 → coordination), histology-fit accuracy (mCRPC ≠ breast-HER2).
- **Jen (reviewer)** owns: prognosis_band is honest, palliative-only path is named alongside active routes (not buried), L4 ack-text reads as patient-respecting not paternalistic.

Specific checks:

- `histology_fit` row for IT-trastuzumab matches patient's primary; if mismatched, the row is retained for transparency but flagged "NOT applicable to this patient".
- Untreated weeks AND treated months bands BOTH have CI.
- The palliative-only path appears in `summary` (not just options) when Chamberlain risk-group is "poor" AND extracranial disease is uncontrolled.
- No fabricated NCT IDs.

### Empty-integrator handling

If `pubmed_results` + `trials_results` + `nccn_excerpts` are ALL empty:

- `lm_confirmation` may still be emitted from `lm_workup` (mechanical inference, no integrator needed).
- `chamberlain_stratification.stratification_pmid: null` + `route_options: []`.
- `prognosis_band: null`.
- `claim_layer: "speculative"`.
- `summary: "Live integrator returned no evidence for IT-route navigation in this LM context. No route options can be surfaced from current data; further retrieval is required (NCCN CNS, ESMO-EANO LM consensus, Glitza Oliva IT-nivolumab trial). Patient is sole decision authority; output is non-directive."`

Per `memory/feedback_no_offline_only.md`: do not fabricate IT-MTX / IT-trastuzumab dose / Chamberlain weeks from training data.

### Downstream consumers

- `patient_brief_rendering.md` consumes `prognosis_band` directly — G21 verifies the anchor survived.
- `pi_delivery.md` reads `risk_disclosure_card` to pin the L4 ack flow.
- `palliative_symptom_qol.md` (Jen's existing task) can be invoked in parallel when `chamberlain_stratification.risk_group: "poor"` to deepen the palliative-only branch.
- If the patient asks for an unregulated channel for IT-trastuzumab or IT-nivolumab (off-label in non-MRA jurisdiction), `boundary_unregulated_channel_disclosure.md` is the canonical disclosure route.
