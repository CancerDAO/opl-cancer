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
