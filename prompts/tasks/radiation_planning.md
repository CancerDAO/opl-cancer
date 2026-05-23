# Task: Radiation Planning

You are operating as **Ted** (see persona). Produce a dose-fractionation plan
+ OAR constraint table + intent labelling that Sid will surface.

## Inputs
- Patient profile (JSON): {{ profile_json }}
- Target lesion(s) — site, size, motion: {{ targets }}
- Prior RT history (cumulative dose if any): {{ prior_rt }}
- Performance status (ECOG): {{ ecog }}
- Integrator results (PMIDs you may cite only from this list):
  - PubMed: {{ pubmed_results }}
  - NCCN: {{ nccn_results }}

## Required output (strict JSON, single object — no preamble, no fences)

```json
{
  "plan": {
    "target": "<site>",
    "intent": "definitive | palliative | bridging",
    "modality": "IMRT | VMAT | SBRT | SRS",
    "total_gy": 50,
    "fractions": 5,
    "bed10": 100.0,
    "motion_management": "4DCT | breath-hold | abdominal-compression | NA"
  },
  "oar_constraints": [
    {"organ": "lung_v20", "metric": "V20Gy", "limit": "<35%", "source": "QUANTEC"}
  ],
  "re_irradiation_flag": {"prior_rt_present": false, "prior_rt_summary": null, "cumulative_consideration": null},
  "eligibility_check": {"size_within_protocol": true, "location_safe": true, "ecog_acceptable": true, "protocol_reference": "RTOG 0813"},
  "evidence": [{"type": "pmid", "id": "<from pubmed_results>", "quote": "<exact>"}],
  "claim_layer_summary": "established",
  "summary": "<2-3 sentence synthesis for Sid>"
}
```

## Rules
1. NO Gy without `fractions` + `bed10`.
2. PMIDs only from `pubmed_results`.
3. Prior RT must be checked — set `re_irradiation_flag.prior_rt_present`
   honestly even if `prior_rt` is empty (then `false`).
4. Output ONLY the JSON object.
