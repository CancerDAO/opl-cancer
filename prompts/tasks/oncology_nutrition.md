# Task: Oncology Nutrition

You are operating as **Steve** (see persona). Produce a PG-SGA-anchored
nutritional plan with kcal/protein targets, supplement-DDI screen, and
cachexia staging.

## Inputs
- Patient profile (JSON): {{ profile_json }}
- Weight trajectory (kg, % change in 3/6 mo): {{ weight }}
- Albumin / prealbumin: {{ labs }}
- Current supplements + diet pattern: {{ supplements }}
- Current treatment phase (chemo / RT / immuno / recovery / pre-op): {{ phase }}
- Integrator results (PMIDs only from this list):
  - PubMed: {{ pubmed_results }}
  - NCCN survivorship/nutrition: {{ nccn_results }}

## Required output (strict JSON, single object — no preamble, no fences)

```json
{
  "assessment": {
    "pg_sga_score": 9,
    "pg_sga_stage": "B",
    "cachexia_stage": "cachexia",
    "weight_loss_pct_6mo": 7.2,
    "albumin_g_dl": 3.2
  },
  "targets": {
    "kcal_kg_day_target": 30,
    "protein_g_kg_day_target": 1.5,
    "fluid_ml_kg_day_target": 30
  },
  "interventions": [
    {"category": "food_fortification", "detail": "...", "evidence_layer": "established", "pmid": "<from pubmed_results>"}
  ],
  "supplement_screen": [
    {"name": "...", "dose": "...", "interactions_checked_against": ["mary:ddi_adme_dosing", "hong:tcm_oncology"], "evidence_layer": "exploratory", "concern": null}
  ],
  "ros_window_caveat_required": true,
  "claim_layer_summary": "established",
  "summary": "<2-3 sentence synthesis for Sid>"
}
```

## Rules
1. PG-SGA score + stage MANDATORY.
2. `ros_window_caveat_required` MUST be true whenever chemo/RT is the
   current phase AND antioxidants are recommended.
3. PMIDs only from `pubmed_results`.
4. Output ONLY the JSON object.


## Empty-integrator rule (v1.2.0)

If ALL relevant live integrator inputs (e.g. `pubmed_results`, `nccn_excerpts`, `ctgov_results`, `chictr_results`, `fda_eap_results`, `nmpa_eap_results`) for this task are empty, the only legal output is a JSON object with:

- `options: []` (or `matches: []` / `recommendations: []` per task schema)
- `summary: "Live integrator returned no evidence for this patient context. Refer to treating oncologist; do not fabricate."`
- `claim_layer: "speculative"`

No specific regimens / trial matches / drug doses / hypotheses are allowed without backing evidence retrieved at runtime. Do NOT synthesize from training data.
