# Task: hypothesis_validation

Validate (or falsify) a Wave-2 hypothesis against the Wave-3 data evidence + propose
minimal wet-lab confirmation steps.

Inputs:
- Hypothesis (JSON): {{ hypothesis_json }}
- Wave-3 data evidence (JSON): {{ wave3_evidence }}
- Patient context (JSON): {{ profile_json }}

Required:
1. Compare data evidence against falsification_rule from the analysis plan
2. Compute support_score in [-1, 1]: -1 fully falsified, 0 inconclusive, 1 strongly supported
3. Cite specific data hits (cluster id / DEG / pathway hit) as evidence
4. Propose ONE smallest informative wet-lab experiment if support_score ≥ 0.3
5. Decide claim_layer label transition (speculative → exploratory only when support_score > 0.5)

Return strict JSON:
{
  "hyp_id": "<hyp_id>",
  "support_score": <-1..1>,
  "verdict": "supported | weakened | falsified | inconclusive",
  "evidence_cited": [{"type":"deg|pathway|cluster|cell_line","ref":"<id>","direction":"+|-"}],
  "claim_layer_recommended": "speculative | exploratory | established",
  "wet_lab_experiment": {
    "validation_layer": "in_silico_only | cell_line_required | animal_model_required",
    "cell_line_ids": ["ACH-XXXXXX", ...],
    "perturbation": "<knockdown/overexpression/drug>",
    "expected_outcome_positive": "<>",
    "expected_outcome_negative": "<>"
  } | null,
  "remaining_uncertainty": "<2-3 sentences>"
}


## Empty-integrator rule (v1.2.0)

If `wave3_evidence` is empty (or contains zero data hits relevant to the hypothesis under test), the only legal output is:

- `support_score: 0`
- `verdict: "inconclusive"`
- `evidence_cited: []`
- `claim_layer_recommended: "speculative"`
- `wet_lab_experiment: null`
- `remaining_uncertainty: "Live integrator returned no evidence for this patient context. No Wave-3 data evidence available to validate or falsify this hypothesis. Further data retrieval / re-analysis is required before this question can be answered. Patient is sole decision authority; output is non-directive."`

Do NOT synthesize evidence from training data. Do NOT propose wet-lab experiments without supporting data.

## PMID / accession grounding (v1.2.0)

Every `evidence_cited.ref` (cluster id / DEG / pathway hit / cell line) MUST come from the `wave3_evidence` input above. Every `cell_line_id` in the wet-lab plan MUST be a real DepMap ACH identifier present in upstream integrator data. Do NOT invent identifiers.
