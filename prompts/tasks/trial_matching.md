# Task: Clinical Trial Matching

You are operating as **Rick** (see persona). This task scores a candidate
clinical-trial list against the patient profile, producing per-trial
eligibility verdicts with explicit inclusion + exclusion deltas.

## Inputs

- Patient profile (JSON): {{ profile_json }}
- Patient biomarker summary (from Bert): {{ biomarker_summary }}
- Patient treatment history: {{ treatment_history }}
- Patient location / geographic constraints: {{ location }}
- Integrator results (pre-fetched):
  - ClinicalTrials.gov: {{ ctgov_results }}
  - ChiCTR: {{ chictr_results }}
  - ISRCTN: {{ isrctn_results }}  # NOTE (v1.2.0): ISRCTN integrator not yet wired — empty list means UK/EU trials not searched yet
  - FDA Expanded Access Programs: {{ fda_eap_results }}
  - NMPA Expanded Access Programs: {{ nmpa_eap_results }}

## Required output (strict JSON, single object — no preamble, no fences)

```json
{
  "matches": [
    {
      "trial_id": "NCT01234567",
      "source": "ClinicalTrials.gov",
      "title": "<from registry>",
      "phase": "Phase 2",
      "status": "Recruiting",
      "intervention": "<from registry>",
      "biomarker_filter": "EGFR L858R / T790M",
      "inclusion_delta": [
        {"criterion": "ECOG ≤ 1", "patient_value": "ECOG 1", "met": true}
      ],
      "exclusion_delta": [
        {"criterion": "no prior osimertinib", "patient_value": "received osimertinib 1L",
         "met": false}
      ],
      "verdict": "ineligible",
      "verdict_reason": "patient received osimertinib 1L (exclusion 3.2)",
      "nearest_site": {"city": "Shanghai", "country": "CN", "distance_km": 180},
      "claim_layer": "established"
    }
  ],
  "expanded_access_routes": [
    {
      "program": "NMPA EAP — drug X",
      "patient_likely_eligible": true,
      "notes": "<short>",
      "claim_layer": "exploratory"
    }
  ],
  "summary": "<2-3 sentence synthesis for Sid>"
}
```

## Rules

1. Every `trial_id` MUST come from the integrator results above (do not invent
   NCT or ChiCTR IDs).
2. `verdict` ∈ {`eligible`, `ineligible`, `likely_eligible_pending_review`}.
3. If `status` is not `"Recruiting"` or `"Active, not recruiting"`, set
   `verdict: "ineligible"` with `verdict_reason` citing the closed status.
4. ALWAYS surface BOTH inclusion AND exclusion deltas — never one without
   the other.
5. Drug names: generic INN only (G3 will block brand-only).
6. Output ONLY the JSON object — no preamble, no markdown fences.


## Empty-integrator rule (v1.2.0)

If ALL relevant live integrator inputs (e.g. `pubmed_results`, `nccn_excerpts`, `ctgov_results`, `chictr_results`, `fda_eap_results`, `nmpa_eap_results`) for this task are empty, the only legal output is a JSON object with:

- `options: []` (or `matches: []` / `recommendations: []` per task schema)
- `summary: "Live integrator returned no evidence for this patient context. No options can be surfaced from current data; further retrieval is required before this question can be answered. Patient is sole decision authority; output is non-directive."`
- `claim_layer: "speculative"`

No specific regimens / trial matches / drug doses / hypotheses are allowed without backing evidence retrieved at runtime. Do NOT synthesize from training data.
