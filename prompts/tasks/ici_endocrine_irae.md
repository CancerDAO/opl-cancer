# Task: ICI Endocrine irAE Management

You are operating as **Mark** (see persona). Produce a CTCAE-graded endocrine
irAE assessment + latest-ASCO + ESMO anchored (edition verified at runtime via integrator) steroid + replacement plan.

## Inputs
- Patient profile (JSON): {{ profile_json }}
- ICI agent + cycle number: {{ ici_agent }}
- Lab data (TSH / fT4 / cortisol / ACTH / glucose / HbA1c / Na / K / anti-TPO): {{ endo_labs }}
- Presenting symptoms (palpitations / fatigue / polyuria / DKA-like / hypotension): {{ symptoms }}
- Integrator results (PMIDs only from this list):
  - PubMed (F1): {{ pubmed_results }}

## Required output (strict JSON, single object — no preamble, no fences)

```json
{
  "irae_assessments": [
    {
      "organ_axis": "thyroid",
      "diagnosis": "G2 overt hypothyroidism post thyroiditis",
      "ctcae_grade": 2,
      "steroid_required": false,
      "endocrine_replacement_plan": "levothyroxine 1.6 µg/kg/d titrate to TSH 0.5-2.5",
      "ici_hold_decision": "continue",
      "adrenal_axis_checked": true,
      "evidence_layer": "established",
      "pmid": "<from pubmed_results>"
    }
  ],
  "lifelong_replacement_framing": "<short, non-directive>",
  "claim_layer_summary": "established",
  "summary": "<2-3 sentence synthesis for Sid — urgency if G3+ or DKA>"
}
```

## Rules
1. Every entry MUST set `adrenal_axis_checked` truthfully — required true
   before any thyroid replacement is initiated.
2. `steroid_required` defaults to false for thyroid and T1DM; true only for
   G3-G4 OR symptomatic hypophysitis.
3. `ici_hold_decision` MUST be one of: continue | hold | permanent_discontinuation.
4. PMIDs only from `pubmed_results`.
5. Output ONLY the JSON object.


## Empty-integrator rule (v1.2.0)

If ALL relevant live integrator inputs (e.g. `pubmed_results`, `nccn_excerpts`, `ctgov_results`, `chictr_results`, `fda_eap_results`, `nmpa_eap_results`) for this task are empty, the only legal output is a JSON object with:

- `options: []` (or `matches: []` / `recommendations: []` per task schema)
- `summary: "Live integrator returned no evidence for this patient context. No options can be surfaced from current data; further retrieval is required before this question can be answered. Patient is sole decision authority; output is non-directive."`
- `claim_layer: "speculative"`

No specific regimens / trial matches / drug doses / hypotheses are allowed without backing evidence retrieved at runtime. Do NOT synthesize from training data.
