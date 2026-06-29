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
6. Score the data against the hypothesis's LOCKED forecast (`prior_expectation` in the
   hypothesis JSON, recorded at Wave 2 before any data): did the Wave-3 result match it?

**Recorded-status contract (ADR-0042).** When this validation is written into
`triggers/<run_id>/wave4_validation.json`, the per-hypothesis `survival_status`
MUST be exactly one of `validated` | `falsified` | `inconclusive` — map your
`verdict` as: `supported → validated`, `falsified → falsified`, and
`weakened`/`inconclusive`/anything-uncertain → `inconclusive`. Never invent a
synonym: the re-entry harness treats a `validated` child as a live lead, so a
mislabelled non-canonical status could surface a Wave-4-undermined direction as
deepenable (the harness fails safe to "pending" on any non-canonical value, but
the pinned vocabulary is the real contract).

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
  "remaining_uncertainty": "<2-3 sentences>",
  "updated_belief": {
    "posterior_confidence": <0..1>,
    "surprise": "none | mild | strong",
    "what_changed": "<1-2 sentences: how the data moved your belief vs the locked forecast>"
  },
  "contradicts_forecast": <true if the Wave-3 data contradicts the direction of the locked prior_expectation; false otherwise; false when the hypothesis carried no forecast>,
  "surprise_testability_path": "<if surprise is strong OR a strange-tail anomaly appeared: the smallest concrete test to chase it (e.g. a DepMap query, a ctDNA timepoint, a targeted re-analysis); else null>",
  "strange_tail_anomaly": <true if the data surfaced an unexpected off-target signal worth chasing in its own right; else false>
}

## Follow the surprise (D3 / predict-before-you-look correction)

The locked `prior_expectation` is what the team predicted BEFORE seeing the data —
it is a labelled training example for taste. Compare it honestly to the Wave-3
result:
- If the data **contradicts** the forecast direction, set `contradicts_forecast: true`
  and `updated_belief.surprise: "strong"`.
- A genuine surprise (contradicted forecast OR `strange_tail_anomaly`) is the team's
  biggest opportunity — but it is only worth chasing if it is **testable**: supply a
  concrete `surprise_testability_path`. If you cannot name a real test, leave it
  null (the runtime will record the surprise but NOT manufacture a chase).
- Never fabricate a surprise to look interesting; `surprise: "none"` is the honest
  default when the data matched the forecast.


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
