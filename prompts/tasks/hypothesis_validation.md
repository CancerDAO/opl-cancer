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
