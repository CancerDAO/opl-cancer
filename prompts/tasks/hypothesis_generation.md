# Task: hypothesis_generation

Generate novel hypotheses grounded in the patient's molecular/clinical profile + the
provided integrator evidence. Hypotheses must be patient-specific (not generic to cancer
type) and must be testable against public datasets.

Patient context (JSON): {{ profile_json }}
NGS report (summary): {{ ngs_report }}
PubMed evidence: {{ pubmed_results }}

Apply 4 generation strategies in parallel; produce 1 hypothesis per strategy:
1. literature_gap — what does the patient have that the literature has NOT addressed?
2. cross_domain — what evidence from a non-oncology field (immunology / metabolism / microbiome) bridges to this patient?
3. novel_mechanism — what two pathways/markers have not been linked in this subtype before?
4. feasibility_first — what hypothesis can be tested with GEO/TCGA/DepMap public data?

Founder-mode philosophy: hypotheses are by definition speculative. Label uncertainty
honestly. Do NOT pretend to be established.

Return strict JSON:
{
  "hypotheses": [
    {
      "id": "hyp_<8-char>",
      "text": "<one-sentence statement>",
      "rationale": "<2-4 sentences>",
      "generation_strategy": "literature_gap|cross_domain|novel_mechanism|feasibility_first",
      "claim_layer": "speculative",
      "evidence_refs": [{"type":"pmid","id":"<id>"},...]
    }
  ]
}


## Empty-integrator rule (v1.2.0)

If ALL relevant live integrator inputs (e.g. `pubmed_results`, `nccn_excerpts`, `ctgov_results`, `chictr_results`, `fda_eap_results`, `nmpa_eap_results`) for this task are empty, the only legal output is a JSON object with:

- `options: []` (or `matches: []` / `recommendations: []` per task schema)
- `summary: "Live integrator returned no evidence for this patient context. No options can be surfaced from current data; further retrieval is required before this question can be answered. Patient is sole decision authority; output is non-directive."`
- `claim_layer: "speculative"`

No specific regimens / trial matches / drug doses / hypotheses are allowed without backing evidence retrieved at runtime. Do NOT synthesize from training data.
