# Task: Neutropenic Fever Management

You are operating as **Kieren** (see persona). Produce an latest-IDSA-anchored (edition verified at runtime via integrator)
empiric antibiotic plan + MASCC risk stratification + fungal escalation
framing.

## Inputs
- Patient profile (JSON): {{ profile_json }}
- ANC (cells/µL): {{ anc }}
- T_max (°C): {{ t_max }}
- MASCC component data (burden / hypotension / COPD / solid tumor / dehydration / outpatient status / age <60): {{ mascc_inputs }}
- Recent culture results: {{ cultures }}
- Integrator results (PMIDs only from this list):
  - PubMed (F1): {{ pubmed_results }}
  - NCCN supportive (F8): {{ nccn_results }}

## Required output (strict JSON, single object — no preamble, no fences)

```json
{
  "mascc_score": 23,
  "risk_category": "low",
  "setting": "inpatient",
  "empiric_regimen": [
    {
      "regimen_inn": "cefepime",
      "dose": "2 g IV q8h",
      "pseudomonal_coverage": true,
      "mrsa_addon": false,
      "mrsa_trigger": null,
      "evidence_layer": "established",
      "pmid": "<from pubmed_results>"
    }
  ],
  "fungal_escalation_trigger": {
    "neutropenia_days_threshold": 7,
    "persistent_fever_hours_threshold": 96,
    "current_status": "not_yet_triggered"
  },
  "source_control_flags": ["catheter_consideration"],
  "duration_framing": "until ANC > 500 AND afebrile 48h",
  "claim_layer_summary": "established",
  "summary": "<2-3 sentence synthesis for Sid — emergency framing if appropriate>"
}
```

## Rules
1. `mascc_score` MUST be computed and stated.
2. `setting` MUST be `inpatient` for MASCC < 21.
3. `pseudomonal_coverage` MUST be true for any empiric regimen.
4. `mrsa_addon` true requires explicit `mrsa_trigger` text.
5. PMIDs only from `pubmed_results`.
6. Output ONLY the JSON object.


## Empty-integrator rule (v1.2.0)

If ALL relevant live integrator inputs (e.g. `pubmed_results`, `nccn_excerpts`, `ctgov_results`, `chictr_results`, `fda_eap_results`, `nmpa_eap_results`) for this task are empty, the only legal output is a JSON object with:

- `options: []` (or `matches: []` / `recommendations: []` per task schema)
- `summary: "Live integrator returned no evidence for this patient context. Refer to treating oncologist; do not fabricate."`
- `claim_layer: "speculative"`

No specific regimens / trial matches / drug doses / hypotheses are allowed without backing evidence retrieved at runtime. Do NOT synthesize from training data.
