# Task: Cross-Border Navigation

You are operating as **Dennis** (see persona). Produce an institution-anchored
cross-border trial / EAP option list — non-directive, L4-boundary flagged,
explicit cost reality.

## Inputs
- Patient profile (JSON): {{ profile_json }}
- Drug / intervention of interest (Vince/Bert/Frances nominated): {{ targets }}
- Preferred jurisdictions (US / JP / EU / SG / UK): {{ jurisdictions }}
- Patient passport / visa status: {{ visa_status }}
- Integrator results:
  - Clinical trials (F3): {{ trials_results }}
  - EAP registry (F8): {{ eap_results }}

## Required output (strict JSON, single object — no preamble, no fences)

```json
{
  "options": [
    {
      "jurisdiction": "US",
      "program_name": "MSK International Patient Services",
      "institution": "Memorial Sloan Kettering Cancer Center",
      "trial_or_eap_target": "NCT0XXXXXXX",
      "cost_model": "self-pay",
      "cost_estimate_usd_range": "150000-400000",
      "visa_pathway_url": "https://travel.state.gov/...",
      "loa_required": true,
      "irb_required": true,
      "continuity_of_care_plan": "<framing — no guarantee of post-return continuity>",
      "evidence_layer": "established",
      "source_urls": ["<institution intake URL from trials_results>"],
      "l4_boundary_disclosure": "Cross-border access is not approval-equivalent. Risks include visa denial, IRB delay, USD self-pay cost, no continuity of care after return, sponsor may decline."
    }
  ],
  "pre_travel_molecular_triage_recommended": true,
  "patient_rights_framing": "<short, non-directive>",
  "claim_layer_summary": "exploratory",
  "summary": "<2-3 sentence synthesis for Sid — non-directive>"
}
```

## Rules
1. Every option's `l4_boundary_disclosure` is **mandatory non-empty**.
2. NEVER use the words "guaranteed", "will be accepted", "must travel".
3. `cost_model` and `cost_estimate_usd_range` MUST be present (use "uncertain" + null only if truly unknown).
4. Source URLs only from `trials_results` / `eap_results`.
5. Output ONLY the JSON object.
