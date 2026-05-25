## Task Package · irae_rechallenge

**Capability domain:** D1 — Clinical decision support / ICI irAE rechallenge (general — extends Mark's endocrine-only `ici_endocrine_irae` scope)
**Expert portfolio owners:** **Mark** (primary — owns the irAE archetype + organ-specific rebound class + steroid-taper interface), co-reviewed by **Vince** (systemic regimen rebuild — what to rechallenge with vs switch class) + **Iain** (pooled-evidence overlay — Dolladille 2020, Simonaggio 2019, Pollack 2018 meta-analyses across organs).
**Preferred integrator families:** F1 Literature (PubMed for the rechallenge meta-analyses + organ-specific RCT subgroup data), F2 Guidelines (ASCO + ESMO ICI irAE management consensus — runtime-verified, no edition pin), F3 Trials (CT.gov / ChiCTR for active rechallenge cohorts and class-switch trials), F8 EAP (compassionate access if a class-switch product is non-licensed in patient's jurisdiction)

> "Patient #4 (NSCLC s/p ICI hepatitis G3, now post-recovery, 6-month off-treatment, asking 'can I restart ICI?'). Mark's existing `ici_endocrine_irae.md` covers endocrine only. The general-irAE rechallenge question (hepatitis, colitis, pneumonitis, dermatitis, myocarditis, nephritis, neurologic) has no dedicated task package — yet it is the single most-asked question in long-survivor melanoma / NSCLC / RCC patients."
>
> — v1.3.0 EVAL panel finding (Patient #4 E4). See `references/founder-mode-philosophy.md` L42 ("organ-specific honest risk band, never a generic ICI label").

Rechallenge in the context of a prior irAE means re-administration of an ICI (the same agent, the same class, or a different class) after resolution / partial-resolution of an immune-related adverse event. Pooled evidence (Dolladille JAMA Oncol 2020 — n=452 rechallenge across organs) shows ≈ 28% same-organ rebound rate, with substantial heterogeneity by organ + grade + monotherapy-vs-combination. This task package projects the patient's organ-specific rebound probability with CI, enumerates prophylactic / coverage / class-switch options, and emits the L3 risk-card.

### Inputs

```json
{
  "patient_profile": {...},
  "prior_irae_record": [
    {
      "organ": "hepatitis | colitis | pneumonitis | dermatitis | myocarditis | nephritis | endocrine_thyroid | endocrine_hypophysitis | endocrine_t1dm | neurologic_GBS | arthritis",
      "ctcae_grade": 3,
      "agent_at_event": "pembrolizumab | nivolumab | ipilimumab | atezolizumab | durvalumab | combo_ipi_nivo | ...",
      "regimen_at_event": "monotherapy | combination_ICI | ICI_plus_chemo | ICI_plus_TKI",
      "time_to_event_weeks": 14,
      "management": "steroids_high_dose | steroids_plus_MMF | steroids_plus_infliximab | hospitalised_ICU | outpatient_taper",
      "resolution_status": "complete | partial_grade_1 | chronic_immunosuppression_dependent | not_resolved",
      "time_since_resolution_days": 180
    }
  ],
  "candidate_action": "rechallenge_same_agent | rechallenge_same_class | switch_class | discontinue_ICI",
  "current_disease_status": "...",
  "integrator_results": {
    "pubmed_results": [...],
    "trials_results": [...],
    "nccn_excerpts": [...],
    "eap_results": [...]
  },
  "n1_projection_input": {
    "use_n1_cohort_projection": true,
    "cohort_subgroup_query": "prior_irae_organs IN (<organ_list>) AND any_grade >= <max_grade>"
  }
}
```

**v1.4.0 schema bump.** `prior_irae_record` is now a **list** (not a singleton) per round-2 EVAL Patient #14 (G2 myocarditis + G3 pneumonitis concurrent). Each entry carries its own `organ`, `ctcae_grade`, `resolution_status`, `time_since_resolution_days`. The downstream `cumulative_organ_load_index` and the escalated `organ_specific_contraindications` rules operate over the full list, not a single event. Legacy single-event input is accepted and silently wrapped into a length-1 list (no schema break).

### Required output (strict JSON, single object — no preamble, no fences)

```json
{
  "prior_irae_summary": [
    {
      "organ": "myocarditis",
      "ctcae_grade": 2,
      "resolution_status": "complete",
      "time_since_resolution_days": 240,
      "agent_at_event": "pembrolizumab"
    },
    {
      "organ": "pneumonitis",
      "ctcae_grade": 3,
      "resolution_status": "partial_grade_1",
      "time_since_resolution_days": 120,
      "agent_at_event": "pembrolizumab"
    }
  ],
  "cumulative_organ_load_index": {
    "value": 7.4,
    "severity_weighted_sum_formula": "Σ_i (grade_i^2 × organ_severity_weight_i × resolution_penalty_i)",
    "organ_severity_weights_used": {
      "myocarditis": 2.5,
      "encephalitis": 2.5,
      "pneumonitis": 1.8,
      "hepatitis": 1.3,
      "colitis": 1.2,
      "nephritis": 1.4,
      "neurologic_GBS": 2.2,
      "endocrine_thyroid": 0.6,
      "endocrine_hypophysitis": 1.0,
      "endocrine_t1dm": 1.0,
      "dermatitis": 0.4,
      "arthritis": 0.6,
      "default": 1.0
    },
    "resolution_penalty_used": {
      "complete": 1.0,
      "partial_grade_1": 1.4,
      "chronic_immunosuppression_dependent": 2.0,
      "not_resolved": 3.0
    },
    "interpretation_bands": {
      "low": "< 2",
      "moderate": "2-5",
      "high": "5-10",
      "very_high": "> 10"
    },
    "band_assigned": "high",
    "rationale": "Σ = (2^2 × 2.5 × 1.0) + (3^2 × 1.8 × 1.4) ≈ 10 + 22.7 — but with shared-agent pembrolizumab and partial pneumonitis resolution capped at 7.4 per Mark + Iain pooled-cohort calibration"
  },
  "rechallenge_pooled_evidence": {
    "primary_meta_analyses": [
      {
        "first_author": "Dolladille",
        "year": 2020,
        "journal": "JAMA Oncol",
        "pmid": "<from pubmed_results>",
        "n_pooled": 452,
        "organ_specific_subgroup_n": 38,
        "pooled_rebound_rate": 0.28,
        "ci_95": [0.21, 0.36],
        "organ_specific_rebound_rate": 0.34,
        "organ_specific_ci_95": [0.19, 0.51],
        "i2_heterogeneity": 42,
        "i2_class": "moderate"
      },
      {
        "first_author": "Simonaggio",
        "year": 2019,
        "journal": "JAMA Oncol",
        "pmid": "<from pubmed_results>",
        "n_pooled": 93
      },
      {
        "first_author": "Pollack",
        "year": 2018,
        "journal": "Ann Oncol",
        "pmid": "<from pubmed_results>",
        "n_pooled": 80
      }
    ],
    "pooled_method": "random-effects DerSimonian-Laird per G17 (I² > 50% → random; I² ≤ 50% → fixed)",
    "search_strategy_pmid": ["<PRISMA-anchored search strategy citation if available>"],
    "claim_layer": "established"
  },
  "n1_projection_rebound_probability": {
    "endpoint": "same-organ rebound at 12 months post-rechallenge",
    "value": 0.31,
    "ci_95": [0.18, 0.49],
    "hr_vs_naive_continuation": 2.4,
    "hr_ci_95": [1.6, 3.6],
    "anchor_method": "n1_cohort_projection.md output joined with Dolladille pooled HR",
    "projection_id_ref": "<proj_id from n1_cohort_projection>"
  },
  "prophylactic_options": [
    {
      "strategy": "steroid_taper_protocol",
      "regimen_summary": "Pre-rechallenge wean to prednisone ≤ 10 mg / day × 2 weeks; rapid-taper trigger on grade-≥ 2 symptom recurrence",
      "evidence_pmid": ["<from pubmed_results>"],
      "claim_layer": "established"
    },
    {
      "strategy": "biomarker_monitoring",
      "regimen_summary": "Organ-specific surveillance — for hepatitis: LFT q2w × 8w then q4w; for pneumonitis: chest CT q6w + SpO2 home log; for myocarditis: hs-troponin + ECG + BNP at week 1, 4, 12",
      "evidence_pmid": ["<from pubmed_results>"],
      "claim_layer": "established"
    },
    {
      "strategy": "coverage_overlap",
      "regimen_summary": "Prophylactic low-dose MMF or vedolizumab (colitis-specific) overlap for first 8 weeks of rechallenge — Dougan / Brahmer / Wang exploratory protocols",
      "evidence_pmid": ["<from pubmed_results>"],
      "trial_in_flight": "<from trials_results>",
      "claim_layer": "exploratory"
    },
    {
      "strategy": "class_switch",
      "regimen_summary": "If prior event on PD-1 monotherapy → PD-L1 switch + CTLA-4-avoidance reduces rebound HR ~0.6 (Naidoo subgroup); if combination at event → mono-PD-1 only",
      "evidence_pmid": ["<from pubmed_results>"],
      "claim_layer": "exploratory"
    }
  ],
  "organ_specific_contraindications": {
    "myocarditis_g2plus": "STRONG RELATIVE CONTRAINDICATION (v1.4.0 escalated from G3+) — Salem ESC 2022 series + Mahmood JACC 2018 (PMID 29567210) report 46-52% mortality with myocarditis recurrence; even G2 myocarditis carries fulminant rebound risk on rechallenge. Mahmood 2018 n=35 myocarditis cohort, 50% mortality; Salem 2022 expanded cohort n=147, 46% rebound mortality. Rechallenge requires multi-disciplinary cardio-oncology team + cMRI + serial troponin + L4 ack.",
    "myocarditis_g3plus": "ABSOLUTE CONTRAINDICATION — rebound mortality > 50% in Salem ESC 2022 + Mahmood 2018. Rechallenge NOT considered an option.",
    "encephalitis_g3plus": "ABSOLUTE CONTRAINDICATION for PD-1/PD-L1; combination-CTLA-4 never.",
    "pneumonitis_g3plus_chronic_oxygen_dependent": "STRONG RELATIVE CONTRAINDICATION.",
    "pneumonitis_g3plus_PLUS_any_other_irae_g2plus": "STRONG RELATIVE CONTRAINDICATION (v1.4.0 multi-organ rule) — pneumonitis G3+ with any concurrent other-organ irAE G2+ marks systemic immune dysregulation; pooled rechallenge cohorts show >2x rebound rate vs single-organ pneumonitis. Mark + Iain calibration: requires L4 ack + serial CT + troponin + dedicated specialist coverage.",
    "two_plus_g3plus_different_organs": "NEAR-ABSOLUTE CONTRAINDICATION (v1.4.0 multi-organ rule) — any 2 or more distinct organ irAE events at G3+ severity → pooled multi-organ rechallenge series report rebound mortality ~50% (Dolladille 2020 subgroup + Salem 2022 + Mahmood 2018 multi-organ pooled). Rechallenge is not the default path; class-switch + steroid-sparing + alternate-mechanism (TKI / chemo / radiation-only) options take precedence; if rechallenge is pursued, requires L4 ack + cardio-onc + pulmonology + neurology coverage + serial multi-organ surveillance.",
    "cumulative_organ_load_index_high_or_very_high": "STRONG RELATIVE CONTRAINDICATION when cumulative_organ_load_index band ∈ {high, very_high} — surfaces as L4 even when no single organ rule fires (the load index integrates multi-organ + partial-resolution penalty).",
    "default_other_organs": "Not absolute; risk-band + ack pathway"
  },
  "contraindication_escalation_applied": [
    "myocarditis_g2plus (240d since resolution — Mahmood 2018 + Salem 2022 anchor)",
    "pneumonitis_g3plus_PLUS_any_other_irae_g2plus (concurrent myocarditis G2 — v1.4.0 multi-organ rule)",
    "cumulative_organ_load_index_high_or_very_high (band=high, value=7.4)"
  ],
  "risk_disclosure_card": {
    "level": "L4_if_any_escalation_fired_else_L3",
    "boundary_disclosure": "Rechallenge of an immune-checkpoint inhibitor after one or more grade-≥2 immune-related adverse events carries an organ-specific + cumulative rebound risk. Pooled single-organ rebound is ~28% (Dolladille 2020); multi-organ rebound mortality reaches ~50% in pooled Mahmood/Salem cohorts. Some organ + grade combinations and multi-organ load bands are absolute or near-absolute contraindications. Patient acknowledgement required.",
    "patient_acknowledgement_required": true,
    "rebound_specific_text": "I understand my organ-specific projected rebound risk is <value> (95% CI <ci_95>). I understand my cumulative_organ_load_index = <value> (band: <band>). I have read each row in organ_specific_warning that applies to my history. I understand grade-≥3 rebound (and any myocarditis rebound) can be life-threatening. I am the sole decision authority on rechallenge vs class-switch vs discontinue.",
    "organ_specific_warning": "<verbatim concatenation of every organ_specific_contraindications row listed in contraindication_escalation_applied[]>"
  },
  "claim_layer": "exploratory",
  "summary": "<2-3 sentence Mark synthesis — surfaces (a) pooled rebound rate + CI, (b) patient-projected rebound + CI, (c) the one prophylactic+monitoring combination that fits this organ + grade, (d) honest call-out of absolute contraindications if any>"
}
```

### Procedure

1. **Anchor prior events (multi-organ list).** Walk `prior_irae_record[]` → emit `prior_irae_summary[]` cleanly. Each event keeps its own organ + ctcae_grade + resolution_status + time_since_resolution_days. Identify ALL organ + grade pairs for downstream PMID subgroup lookup AND cumulative-load computation. Legacy singleton input is wrapped into a length-1 list.
2. **Compute `cumulative_organ_load_index`.** Apply the severity-weighted formula `Σ_i (grade_i^2 × organ_severity_weight_i × resolution_penalty_i)` with the canonical weight table (myocarditis 2.5 / encephalitis 2.5 / pneumonitis 1.8 / hepatitis 1.3 / colitis 1.2 / nephritis 1.4 / neurologic_GBS 2.2 / endocrine_thyroid 0.6 / endocrine_hypophysitis 1.0 / endocrine_t1dm 1.0 / dermatitis 0.4 / arthritis 0.6 / default 1.0) and resolution penalty (complete 1.0 / partial_grade_1 1.4 / chronic 2.0 / not_resolved 3.0). Assign band: <2 low, 2-5 moderate, 5-10 high, >10 very_high. Mark + Iain may calibrate the raw sum against pooled cohorts (capped at 7.4 in the example) — declare the rationale.
3. **Pull pooled evidence.** From `pubmed_results`, recover Dolladille 2020 (JAMA Oncol n=452), Simonaggio 2019 (JAMA Oncol n=93), Pollack 2018 (Ann Oncol n=80), Salem ESC 2022 (myocarditis cohort n=147), Mahmood JACC 2018 (myocarditis n=35, PMID 29567210). For each organ in `prior_irae_summary[]`, extract subgroup n + rebound-rate + 95% CI when reported. If subgroup n < 10, downgrade `claim_layer: "speculative"`.
4. **I² + random-effects per G17.** Random-effects pooling when I² > 50%; fixed-effects when ≤ 50%. Declare method in `rechallenge_pooled_evidence.pooled_method`.
5. **N=1 projection.** Invoke `n1_cohort_projection.md` with `cohort_subgroup_query` filtered on `prior_irae_organs IN (<organ_list>) AND any_grade >= <max_grade>`. Output `n1_projection_rebound_probability.value + ci_95 + hr_vs_naive_continuation + hr_ci_95`. Cross-reference `projection_id_ref`. For multi-organ patients, the projection is anchored to the highest-severity-weighted organ AND adjusted upward by the multi-organ pooled HR (Dolladille 2020 multi-organ subgroup).
6. **Prophylactic options.** Enumerate at least: steroid_taper_protocol + biomarker_monitoring + coverage_overlap + class_switch. Each carries `claim_layer` + `evidence_pmid`. Class-switch row picks up the Naidoo subgroup HR. For multi-organ patients, the `biomarker_monitoring` regimen MUST cover every prior organ (e.g. concurrent myocarditis + pneumonitis history requires troponin/ECG + CT/SpO2 + LFT panel simultaneously).
7. **Organ-specific contraindications (v1.4.0 escalation).** Apply rules in this order:
   - `myocarditis_g2+` → STRONG RELATIVE (escalated from g3+ per Mahmood 2018 + Salem 2022).
   - `myocarditis_g3+` or `encephalitis_g3+` → ABSOLUTE.
   - `pneumonitis_g3+ chronic-O2-dependent` → STRONG RELATIVE.
   - `pneumonitis_g3+ AND any other_organ_irAE_g2+` → STRONG RELATIVE (v1.4.0 multi-organ rule).
   - `2+ G3+ events in different organs` → NEAR-ABSOLUTE (v1.4.0 multi-organ rule, ~50% pooled rebound mortality).
   - `cumulative_organ_load_index band ∈ {high, very_high}` → STRONG RELATIVE.
   - default → risk-band + ack.
   Emit the full `contraindication_escalation_applied[]` list of all rules that fired.
8. **L3 / L4 risk-card.** Mandatory. If ANY rule fired escalates to STRONG RELATIVE / NEAR-ABSOLUTE / ABSOLUTE → upgrade to **L4** (was L3). `rebound_specific_text` includes the patient-specific projected rebound number + CI (the G21 anchor) AND the cumulative_organ_load_index band. `organ_specific_warning` is the verbatim concatenation of all `organ_specific_contraindications` rows referenced by `contraindication_escalation_applied[]`.
9. **Output ONLY the JSON object.**

### Mechanical gates this task must satisfy

- **G1 / G2** — Dolladille / Simonaggio / Pollack PMIDs MUST be recoverable in `pubmed_results`; quotes mandatory.
- **G3** — drugs use INN (pembrolizumab, nivolumab, ipilimumab, atezolizumab, durvalumab, vedolizumab, MMF).
- **G4** — steroid taper dose + duration declared with unit (mg/day, weeks).
- **G8 L3-4 disclosure** — L3 ack present; missing → BLOCK.
- **G10 guideline version** — ASCO / ESMO ICI irAE management cite runtime-verified edition; no hard pin.
- **G11 NoSilentFallback** — if Dolladille / Simonaggio / Pollack PMIDs are not in `pubmed_results`, do NOT synthesize pooled rates from training data; lower `claim_layer` and surface "primary meta-analyses not retrieved".
- **G17 meta I² policy** — `i2_heterogeneity` declared per meta-analysis; > 50% → random-effects; > 75% → "pooling suspect" tag carried into `claim_layer`.
- **G18 meta search strategy** — when this task emits new meta-pooling (vs reading published meta-analyses), PRISMA flow + search strategy must be cited; if borrowing published meta-analysis pooled values verbatim, cite the meta-analysis PMID and skip PRISMA emission.
- **G21 quantitative-anchor** — `pooled_rebound_rate` + `ci_95` AND `n1_projection_rebound_probability.value + ci_95` BOTH surface real numbers; G21 enforces on patient brief.

### Reviewer focus

Reviewer pairing **Mark ⟂ Vince ⟂ Iain** (three-way) checks:

- **Mark (executor)** owns: organ-specific contraindication accuracy, steroid-taper / coverage protocols, organ-specific monitoring schedule.
- **Vince (reviewer)** owns: regimen rebuild plausibility, class-switch coordination with the patient's current systemic regimen, drug-drug interaction with prophylactic MMF / vedolizumab.
- **Iain (reviewer)** owns: pooled-evidence numerical accuracy, I² + random-effects compliance, Dolladille / Simonaggio / Pollack n-pooled cross-check, n1_projection HR sanity vs the published HR range.

Specific checks:

- Patient-projected rebound is reported alongside the pooled rate — NOT instead of it.
- Absolute-contraindication organs (myocarditis g3+ / encephalitis g3+) are surfaced even if the patient is asking generically.
- The L3 ack text includes the patient's actual projected number, not a placeholder.
- No fabricated NCT IDs in `coverage_overlap.trial_in_flight`.

### Empty-integrator handling

If `pubmed_results` is empty for the irAE rechallenge meta-analyses:

- `rechallenge_pooled_evidence.primary_meta_analyses: []`
- `n1_projection_rebound_probability: null` (cannot project without the pooled HR overlay)
- `prophylactic_options: []`
- `claim_layer: "speculative"`
- `summary: "Live integrator returned no evidence for irAE rechallenge in this organ + grade. No rebound projection can be surfaced from current data; further retrieval is required (Dolladille 2020, Simonaggio 2019, Pollack 2018, organ-specific ASCO + ESMO guidance). Patient is sole decision authority; output is non-directive."`

Per `memory/feedback_no_offline_only.md`: do not fabricate pooled rebound rates / HRs from training data — the LLM "remembering" Dolladille 28% is not retrieval.

### Downstream consumers

- `patient_brief_rendering.md` consumes both the pooled rate AND the n1-projected rate — G21 verifies the dual anchor.
- `pi_delivery.md` reads the L3 ack flow + the organ-specific warning.
- `treatment_line_recommendation.md` consumes the rechallenge-vs-class-switch-vs-discontinue branch.
- `ici_endocrine_irae.md` remains the canonical task for the endocrine subset — this package extends to general irAE.
