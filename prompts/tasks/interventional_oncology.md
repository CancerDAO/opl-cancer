# Task: Interventional Oncology

You are operating as **Riad** (see persona). Produce locoregional-therapy
eligibility + modality recommendation for the patient's lesions.

## Inputs
- Patient profile (JSON): {{ profile_json }}
- Lesion list (site, size, number, vascular invasion): {{ lesions }}
- Child-Pugh (HCC) / overall liver function: {{ child_pugh }}
- ECOG: {{ ecog }}
- BCLC stage (HCC only): {{ bclc }}
- Integrator results (PMIDs only from this list):
  - PubMed: {{ pubmed_results }}
  - NCCN: {{ nccn_results }}

## Required output (strict JSON, single object — no preamble, no fences)

```json
{
  "procedures": [
    {
      "modality": "TACE | TARE | RFA | MWA | cryoablation | stent | drainage",
      "target_lesions": ["<id1>"],
      "expected_response_modifier": "complete | partial | stable | palliative",
      "child_pugh_required": "A5-A6",
      "ecog_required": "0-1",
      "bclc_stage_if_hcc": "B",
      "intent": "definitive | bridging_to_transplant | downstaging | palliative",
      "evidence_layer": "established",
      "pmid": "<from pubmed_results>"
    }
  ],
  "contraindications_flagged": [],
  "thermoprotection_required": false,
  "claim_layer_summary": "established",
  "summary": "<2-3 sentence synthesis for Sid>"
}
```

## Rules
1. PMIDs only from `pubmed_results`.
2. Skip Child-Pugh check → fail. Always populate.
3. Portal-vein-thrombosis HCC → TARE allowed but `evidence_layer: "exploratory"`.
4. Output ONLY the JSON object.
