# Task: meta_analysis

Synthesize pooled evidence across the studies provided. Apply Cochrane discipline:
heterogeneity (I²), random-effects when I² > 50%, fixed-effects only when I² ≤ 50%,
PRISMA search-strategy declaration, inclusion/exclusion criteria.

Patient context (JSON): {{ profile_json }}
Cancer type/stage: {{ cancer_type_stage }}
Question: {{ sub_goal }}
Candidate studies (PMIDs + summaries from PubMed integrator):
{{ pubmed_results }}

Return strict JSON:
{
  "studies": [
    {
      "pmid": "string",
      "design": "RCT|observational|case-control|case-series",
      "effect_size": "HR/OR/RR + 95% CI",
      "n": <int>,
      "quality_rating": "low|moderate|high",
      "summary": "<one sentence>"
    }
  ],
  "pooled_estimate": "string (e.g. 'HR 0.78 (95% CI 0.65-0.94)')",
  "i2_squared": "<percent>",
  "heterogeneity_judgment": "low|moderate|high",
  "model_used": "fixed|random",
  "claim_layer": "established|exploratory|speculative",
  "rationale": "<3-5 sentences>",
  "search_strategy": "<one paragraph>",
  "inclusion_criteria": "<bulleted>",
  "exclusion_criteria": "<bulleted>",
  "evidence": [{"type":"pmid","id":"<id>","quote":"<exact quote>"}]
}


## Structured claim output (v2.7.1)

In addition to the legacy fields above, when this synthesis pools effect estimates across multiple sources/agents you MUST emit a `pooled_estimate{}` object per `schemas/claim.v2.schema.json` so the mechanical gate has fields to check (an absent field makes the gate SKIP — i.e. dead). The load-bearing fields are `pooled_estimate{agents[], i2, heterogeneity_flagged}`.

- **G43/G17 (hidden-heterogeneity)** require `pooled_estimate.heterogeneity_flagged:true` whenever ≥2 `agents`/sources were pooled AND `i2` is high (>50/75). Reporting a single pooled point estimate across heterogeneous sources without surfacing the heterogeneity to the reader is the failure this catches. `i2` accepts either 0.0-1.0 or 0-100 (the consumer normalises).

```json
{
  "pooled_estimate": {
    "agents": ["PMID:25201520", "PMID:23158724", "PMID:21156285"],
    "i2": 68,
    "heterogeneity_flagged": true
  }
}
```

## Empty-integrator rule (v1.2.0)

If ALL relevant live integrator inputs (e.g. `pubmed_results`, `nccn_excerpts`, `ctgov_results`, `chictr_results`, `fda_eap_results`, `nmpa_eap_results`) for this task are empty, the only legal output is a JSON object with:

- `options: []` (or `matches: []` / `recommendations: []` per task schema)
- `summary: "Live integrator returned no evidence for this patient context. No options can be surfaced from current data; further retrieval is required before this question can be answered. Patient is sole decision authority; output is non-directive."`
- `claim_layer: "speculative"`

No specific regimens / trial matches / drug doses / hypotheses are allowed without backing evidence retrieved at runtime. Do NOT synthesize from training data.
