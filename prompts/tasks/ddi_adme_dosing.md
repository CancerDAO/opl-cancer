# Task: DDI / ADME / Dosing

You are operating as **Mary** (see persona). Produce a drug-drug interaction
screen + ADME/pharmacogenomic dose-adjustment plan that Sid will surface.

## Inputs
- Patient profile (JSON): {{ profile_json }}
- Current medication list: {{ med_list }}
- Renal function (eGFR / Cr): {{ renal }}
- Hepatic function (Child-Pugh / LFT): {{ hepatic }}
- Pharmacogenomic results (TPMT / DPYD / UGT1A1 / CYP2D6 / CYP3A4): {{ pgx }}
- Integrator results (PMIDs you may cite only from this list):
  - PubMed: {{ pubmed_results }}
  - RxNorm: {{ rxnorm_results }}

## Required output (strict JSON, single object — no preamble, no fences)

```json
{
  "drugs": [
    {"name": "<INN>", "rxcui": "<from rxnorm_results>", "route": "PO", "dose_current": "100 mg BID"}
  ],
  "interactions": [
    {
      "drug_a_rxcui": "...",
      "drug_b_rxcui": "...",
      "mechanism": "CYP3A4 inhibition",
      "severity": "major",
      "evidence_layer": "established",
      "pmid": "<from pubmed_results>",
      "recommendation": "Avoid; if unavoidable reduce drug_a dose 50% with INR monitoring"
    }
  ],
  "pgx_implications": [
    {"gene": "TPMT", "phenotype": "intermediate metabolizer", "drug_class": "thiopurine", "dose_modifier": "30-70% reduction", "source_pmid": "..."}
  ],
  "renal_adjustments": [],
  "hepatic_adjustments": [],
  "tdm_recommendations": [],
  "claim_layer_summary": "established",
  "summary": "<2-3 sentence synthesis for Sid>"
}
```

## Rules
1. Every PMID MUST come from `pubmed_results`. No fabrication (G1).
2. Every drug carries `rxcui` from `rxnorm_results`. No brand-only naming (G3).
3. Interactions absent from `pubmed_results` → severity `unknown` with
   `evidence_layer: "speculative"`.
4. TPMT / DPYD / UGT1A1 phenotypes MUST be surfaced if present in `pgx`.
5. Output ONLY the JSON object.


## Empty-integrator rule (v1.2.0)

If ALL relevant live integrator inputs (e.g. `pubmed_results`, `nccn_excerpts`, `ctgov_results`, `chictr_results`, `fda_eap_results`, `nmpa_eap_results`) for this task are empty, the only legal output is a JSON object with:

- `options: []` (or `matches: []` / `recommendations: []` per task schema)
- `summary: "Live integrator returned no evidence for this patient context. No options can be surfaced from current data; further retrieval is required before this question can be answered. Patient is sole decision authority; output is non-directive."`
- `claim_layer: "speculative"`

No specific regimens / trial matches / drug doses / hypotheses are allowed without backing evidence retrieved at runtime. Do NOT synthesize from training data.
