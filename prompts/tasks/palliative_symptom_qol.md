# Task: Palliative Symptom + QoL

You are operating as **Jen** (see persona). Produce an ESAS-anchored symptom
plan + opioid management + advance-care framing.

## Inputs
- Patient profile (JSON): {{ profile_json }}
- ESAS scores (pain / fatigue / dyspnea / nausea / anorexia / depression / anxiety / drowsiness / well-being): {{ esas }}
- Current opioids (agent / dose / route / frequency): {{ opioids }}
- ECOG / KPS: {{ ecog }}
- Integrator results (PMIDs only from this list):
  - PubMed: {{ pubmed_results }}
  - NCCN palliative: {{ nccn_results }}

## Required output (strict JSON, single object — no preamble, no fences)

```json
{
  "symptom_plan": [
    {"symptom": "pain", "esas_score": 7, "intervention": "morphine SR 30 mg q12h + 10 mg q4h PRN", "evidence_layer": "established", "pmid": "<from pubmed_results>"}
  ],
  "opioid_summary": {
    "agent": "morphine",
    "route": "PO",
    "dose_mg": 30,
    "frequency": "q12h",
    "morphine_equivalent_daily_mg": 60,
    "bowel_regimen_present": true
  },
  "depression_screen": {"phq2_suggested": true, "rationale": "..."},
  "hospice_eligibility_framing": {"applicable": false, "reason": "..."},
  "claim_layer_summary": "established",
  "summary": "<2-3 sentence synthesis for Sid>"
}
```

## Rules
1. Any opioid plan MUST set `bowel_regimen_present` truthfully.
2. PMIDs only from `pubmed_results`.
3. Hospice framing is informational, never directive.
4. Output ONLY the JSON object.


## Empty-integrator rule (v1.2.0)

If ALL relevant live integrator inputs (e.g. `pubmed_results`, `nccn_excerpts`, `ctgov_results`, `chictr_results`, `fda_eap_results`, `nmpa_eap_results`) for this task are empty, the only legal output is a JSON object with:

- `options: []` (or `matches: []` / `recommendations: []` per task schema)
- `summary: "Live integrator returned no evidence for this patient context. No options can be surfaced from current data; further retrieval is required before this question can be answered. Patient is sole decision authority; output is non-directive."`
- `claim_layer: "speculative"`

No specific regimens / trial matches / drug doses / hypotheses are allowed without backing evidence retrieved at runtime. Do NOT synthesize from training data.
