# Task: Molecular NGS Interpretation

You are operating as **Bert** (see persona). This task takes an NGS report plus
pre-fetched variant evidence and produces an actionability-ranked variant list.

## Inputs

- Patient profile (JSON): {{ profile_json }}
- NGS report text: {{ ngs_report }}
- Integrator results (pre-fetched; only PMIDs from this list may be cited):
  - OncoKB: {{ oncokb_results }}
  - CIViC: {{ civic_results }}
  - ClinVar: {{ clinvar_results }}
  - gnomAD: {{ gnomad_results }}
  - PubMed: {{ pubmed_results }}

## Required output (strict JSON, single object — no preamble, no fences)

```json
{
  "variants": [
    {
      "gene": "EGFR",
      "protein_change": "L858R",
      "transcript": "NM_005228.5",
      "vaf": 0.45,
      "germline_or_somatic": "somatic",
      "gnomad_af": 0.0,
      "actionability": {
        "oncokb_level": "LEVEL_1",
        "civic_level": "A",
        "summary": "Sensitises to osimertinib (1L per NCCN v6.2025)"
      },
      "claim_layer": "established",
      "evidence": [
        {"type": "pmid", "id": "<from pre-fetched list>",
         "quote": "<exact from PubMed result>"}
      ]
    }
  ],
  "co_alterations": [
    {
      "primary": "EGFR L858R",
      "modifier": "TP53 R175H",
      "effect": "shorter PFS to 1L osimertinib",
      "claim_layer": "exploratory",
      "evidence": []
    }
  ],
  "resistance_signals": [],
  "germline_findings": [],
  "tmb_msi_hrd": {
    "tmb_mut_per_mb": null,
    "msi_status": null,
    "hrd_score": null
  },
  "summary": "<2-3 sentence synthesis for Sid>"
}
```

## Rules

1. Every PMID listed MUST come from the integrator results above (do not invent).
2. Every drug mentioned MUST use generic INN (G3 will block brand names).
3. If a variant lacks evidence in pre-fetched results, label
   `claim_layer: "speculative"` and `evidence: []` (empty list signals to
   reviewer to flag for further work, NOT a fabrication).
4. If `gnomad_af` is > 1% you MUST set `germline_or_somatic` analysis
   accordingly (likely germline / common polymorphism).
5. Output ONLY the JSON object — no preamble, no markdown fences.
