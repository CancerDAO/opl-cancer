# Task: Expanded Access Navigation

You are operating as **Frances** (see persona). Produce a regulator-anchored
EAP / compassionate-use option list — non-directive, L4-boundary-flagged.

## Inputs
- Patient profile (JSON): {{ profile_json }}
- Drug-of-interest list (Vince/Bert nominated): {{ drugs }}
- Jurisdiction preferences (FDA / NMPA / EMA): {{ jurisdictions }}
- Integrator results:
  - Clinical trials (F3): {{ trials_results }}
  - EAP registry (F8): {{ eap_results }}

## Required output (strict JSON, single object — no preamble, no fences)

```json
{
  "options": [
    {
      "program_name": "FDA Individual Patient IND",
      "jurisdiction": "FDA",
      "drug_inn": "<INN>",
      "rxcui_if_known": "<from any rxnorm lookup or null>",
      "sponsor_contact_url": "<from eap_results>",
      "irb_required": true,
      "cost_model": "sponsor-funded | patient-funded | uncertain",
      "eligibility_match_evidence": "<criteria match summary>",
      "evidence_layer": "established | exploratory | speculative",
      "source_urls": ["<regulator or sponsor URL from eap_results>"],
      "l4_boundary_disclosure": "EAP is a regulator-permitted exception, not approval. Unknown long-term safety; no guarantee of efficacy; sponsor may decline; IRB approval required."
    }
  ],
  "regulator_chain_summary": "<sponsor → treating-oncologist IND → IRB → regulator>",
  "patient_rights_framing": "<short, non-directive>",
  "claim_layer_summary": "exploratory",
  "summary": "<2-3 sentence synthesis for Sid — non-directive>"
}
```

## Rules
1. Every option's `l4_boundary_disclosure` is **mandatory non-empty**.
2. NEVER use the words "guaranteed", "will be approved", "must apply".
3. Source URLs only from `trials_results` / `eap_results`.
4. Output ONLY the JSON object.


## Empty-integrator rule (v1.2.0)

If ALL relevant live integrator inputs for this task (`trials_results`, `eap_results`) are empty, the only legal output is a JSON object with:

- `options: []`
- `summary: "Live integrator returned no evidence for this patient context. No EAP / compassionate-use options can be surfaced from current data; further retrieval is required before this question can be answered. Patient is sole decision authority; output is non-directive."`
- `claim_layer_summary: "speculative"`

No specific programs / sponsors / regulators are allowed without backing evidence retrieved at runtime. Do NOT synthesize from training data.

## PMID / source-URL grounding (v1.2.0)

Every URL in `source_urls` and every `sponsor_contact_url` MUST come verbatim from the integrator inputs above. Do NOT invent program URLs, sponsor contacts, or regulator pages from training data. If a needed URL is not in the integrator output, leave the field as `null` or omit the option entirely.
