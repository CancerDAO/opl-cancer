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


## Empty-integrator rule (v1.2.0)

If ALL relevant live integrator inputs (e.g. `pubmed_results`, `nccn_excerpts`, `ctgov_results`, `chictr_results`, `fda_eap_results`, `nmpa_eap_results`) for this task are empty, the only legal output is a JSON object with:

- `options: []` (or `matches: []` / `recommendations: []` per task schema)
- `summary: "Live integrator returned no evidence for this patient context. No options can be surfaced from current data; further retrieval is required before this question can be answered. Patient is sole decision authority; output is non-directive."`
- `claim_layer: "speculative"`

No specific regimens / trial matches / drug doses / hypotheses are allowed without backing evidence retrieved at runtime. Do NOT synthesize from training data.
