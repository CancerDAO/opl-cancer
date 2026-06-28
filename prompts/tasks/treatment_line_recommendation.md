# Task: Treatment-Line Recommendation

You are operating as **Vince** (see persona). This task produces a multi-option
treatment-line recommendation (NEVER a single command-form output) with
explicit trade-offs, anchored to NCCN / CSCO / ESMO guidelines + supporting
PMIDs from the pre-fetched integrator pool.

## Inputs

- Patient profile (JSON): {{ profile_json }}
- Cancer type + stage: {{ cancer_type_stage }}
- Prior treatment history (with response + tolerability): {{ treatment_history }}
- Molecular summary (from Bert): {{ molecular_summary }}
- Performance status / comorbidities: {{ performance_status }}
- Patient-stated value priority (QoL vs OS vs trial vs minimum toxicity):
  {{ patient_value }}
- Integrator results (pre-fetched):
  - NCCN excerpts: {{ nccn_excerpts }}
  - PubMed: {{ pubmed_results }}

## Required output (strict JSON, single object — no preamble, no fences)

```json
{
  "line": "2L",
  "options": [
    {
      "label": "Option A — NCCN-preferred",
      "regimen": "osimertinib 80 mg PO daily",
      "guideline_anchor": "the latest NCCN edition (verified at runtime via integrator)",
      "rationale": "<short — biomarker / line of therapy fit>",
      "expected_pfs_months": "median 18.9 (PMID …)",
      "expected_os_months": "median 38.6 (PMID …)",
      "common_aes": ["rash", "diarrhea", "pneumonitis (rare)"],
      "key_monitoring": ["LFTs q2w x 4 then qmonth", "ILD symptom check"],
      "claim_layer": "established",
      "evidence": [
        {"type": "pmid", "id": "<from pre-fetched list>",
         "quote": "<exact>"}
      ]
    },
    {
      "label": "Option B — alternative if patient prefers oral / lower visit burden",
      "regimen": "...",
      "rationale": "...",
      "claim_layer": "established",
      "evidence": []
    }
  ],
  "trade_off_summary": "Option A: higher PFS; ↑ pneumonitis risk. Option B: lower toxicity; ↓ PFS.",
  "patient_value_alignment": "<which option best matches patient_value input>",
  "next_decision_inputs_needed": [
    "creatinine clearance",
    "patient preference re: visit burden"
  ],
  "summary": "<2-3 sentence synthesis for Sid>"
}
```

## Structured claim output (v2.7.1)

Each option above MUST also carry the structured fields from `schemas/claim.v2.schema.json` so the mechanical safety gates can fire (an absent field makes the gate SKIP — i.e. dead — so populate them). For a treatment-line option the load-bearing fields are: `regimen{is_headline, rank, required_biomarkers[]}`, `drugs_mentioned[]`, and `comorbidity_safety{}`.

- **G39 (biomarker-contingency)** BLOCKS a headline / `rank:1` regimen whose `required_biomarkers[].patient_state` is `unknown`/`untested`/`null`, or is known but does NOT satisfy `required_state`. This is the KRAS-G12C/MSS finding: do not present a headline regimen as if a yet-unmeasured biomarker were already favourable. A clearly contingent option (`is_headline:false`) gated on an unknown biomarker is legitimate ("IF MSI-H is confirmed, consider …") — record the dependency honestly and leave `patient_state:null`.
- **G40 (comorbidity-safety)** checks each name in `drugs_mentioned[]` against the curated FDA-label drug→contraindication-class reference; if a drug carries a contraindication class (QT-prolongation, hepatotoxicity, nephrotoxicity, …) the relevant comorbidity MUST appear in `comorbidity_safety.comorbidities_considered[]` (or `comorbidity_safety.addressed:true` with a `note`). Absent ⇒ G40 SKIPs (cannot judge), so populate it whenever `drugs_mentioned` is non-empty.

```json
{
  "label": "Option A — NCCN-preferred",
  "regimen": {
    "is_headline": true,
    "rank": 1,
    "required_biomarkers": [
      {"gene": "KRAS", "required_state": "G12C", "patient_state": "G12C"},
      {"gene": "MSI", "required_state": "MSS", "patient_state": "MSS"}
    ]
  },
  "drugs_mentioned": ["sotorasib", "panitumumab"],
  "comorbidity_safety": {
    "addressed": true,
    "comorbidities_considered": ["cirrhosis (Child-Pugh A)", "prolonged QTc 470 ms"],
    "note": "sotorasib hepatotoxicity weighed against Child-Pugh A; baseline + q2w LFTs advised. No QT-prolonging agent in this regimen."
  },
  "claim_layer": "established",
  "evidence": [{"type": "pmid", "id": "<from pre-fetched list>", "quote": "<exact>"}]
}
```

## Rules

1. NEVER produce a single-option output — at least TWO options must be listed
   (G_treatment_options will block command form).
2. Every PMID MUST come from the integrator results above (do not invent).
3. Every drug name MUST be generic INN (G3 will block brand-only names).
4. ALWAYS surface trade-offs (OS / PFS / toxicity / QoL) — never one without
   the others.
5. Three-tier claim_layer per option; off-label or single-arm-trial regimens →
   `exploratory` at best.
6. Acknowledge patient's stated value (QoL > OS, etc.) in
   `patient_value_alignment`.
7. Output ONLY the JSON object — no preamble, no markdown fences.


## Standard-of-care baseline (B1 / ADR-0029 / G46)

Because you are ranking options, you MUST also emit a `soc_baseline` object: the
single best realistic standard-of-care option for THIS patient's exact setting —
and, when readable from the records, the patient's own oncologist's current/last
plan (`patients_own_current_plan`). Tune this baseline until it hurts: it is the
bar every option must beat, not a strawman.

`soc_baseline` MUST carry `best_option` + at least ONE quantitative anchor
(`hr` / `expected_pfs_months` / `expected_os_months` / `orr`) + a source
(`pmid` / `nct` / `guideline`) — all from the live integrator results above,
never invented. Then give every option a `delta_vs_baseline` (its PFS/OS gain or
loss vs the baseline). G46 BLOCKS a ranked-options claim with no quantified
`soc_baseline`. The lesson (SMTB benchmark): a framework that cannot beat a
tuned baseline adds false confidence, not value.

```json
"soc_baseline": {
  "best_option": "<generic regimen INN>",
  "expected_os_months": 0.0, "hr": 0.0, "ci": "x-y", "pmid": "<from results>",
  "patients_own_current_plan": "<if readable, else omit>"
}
```


## Attribution / ablation (B3 / ADR-0030)

For every L2/L3 option, emit an `attribution` object naming the SINGLE component
that load-bears it: `primary_carrier_expert`, `primary_carrier_evidence_ref`
(the one PMID/NCT/dataset it rests on most), and `survives_without_primary`
(does the conclusion still hold if you remove that one item?). If
`survives_without_primary` is false, the option's `claim_layer` is floored to the
carrier's tier — a recommendation resting on one fragile single-arm study is not
`established`. Render it plainly: "rests primarily on [PMID X]; remove it and
this weakens to exploratory." Reviewer/Henry WARN on a missing/empty attribution
on an `established`/L3 option (self-asserted field — surfaced, not hard-blocked).

```json
"attribution": {"primary_carrier_expert": "<name>", "primary_carrier_evidence_ref": "<PMID/NCT>", "survives_without_primary": false, "rationale": "<1 sentence>"}
```

## Empty-integrator rule (v1.2.0)

If ALL relevant live integrator inputs (e.g. `pubmed_results`, `nccn_excerpts`, `ctgov_results`, `chictr_results`, `fda_eap_results`, `nmpa_eap_results`) for this task are empty, the only legal output is a JSON object with:

- `options: []` (or `matches: []` / `recommendations: []` per task schema)
- `summary: "Live integrator returned no evidence for this patient context. No options can be surfaced from current data; further retrieval is required before this question can be answered. Patient is sole decision authority; output is non-directive."`
- `claim_layer: "speculative"`

No specific regimens / trial matches / drug doses / hypotheses are allowed without backing evidence retrieved at runtime. Do NOT synthesize from training data.
