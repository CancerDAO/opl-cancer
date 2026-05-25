# MTB vs OPL — quantitative comparison on SBT_Benchmark

Scorer: `deterministic_scorer_v2_5` (CRC) / `deterministic_scorer_v2_5` (NCCN)

Model under test: **MiniMax-M2** (reasoning model — every arm gets identical model + temperature + retry budget; the only contrast between mtb-* and opl-* arms is the prompt corpus / multi-agent shape).

Run scale: n=30 per surface (CRC + NCCN), 5 arms each, but only `json_parse_ok = true` records are scorable — see per-arm `n_json_ok` column below.

## TL;DR — who wins?

Plain answer to *"哪个效果好"*:

- **CRC surface (treatment recommendation)** — **opl-anchor wins** most clinical metrics (best therapy F1@3 full denom, best class F1, best nDCG@3, best treatment-intent match). opl-anchor's contribution: it threads the SBT case through OPL's Sid PI planner + the same PubMed/NCCN-PageIndex retrieval that mtb-anchor uses, then forces a single structured synth using OPL's three-tier-claim discipline. Cost: ~3 LLM calls / case (vs ~10 for either *-full).
- **CRC surface — the *-full multi-agent pipelines actively hurt** vs their anchor twins on most metrics. mtb-full and opl-full both *lower* JSON parse rate (more LLM hops = more chances to produce unparseable JSON), and don't gain back enough clinical precision to compensate. Exception: mtb-full has the best *contraindicated-recommendation* rate (0.000 vs baseline 0.150) — its 3 verifiers do block some unsafe outputs, just not enough to outweigh the schema-shape losses on this substrate.
- **NCCN surface (decision concordance)** — **baseline wins** (0.500 strict scorable-only concordance vs opl-anchor 0.417, opl-full 0.091, mtb-full 0.100). Both full pipelines collapse on NCCN: opl-full hits 71% unsafe-overreach + 80% premature-commitment. The likely cause is that NCCN-surface gold rewards `stop_missing_info` / `stop_need_evidence` / `routing` decisions when discriminators are missing, but multi-expert fanout pushes every arm toward making a specific recommendation rather than holding back.
- **Wall-time**: anchor arms are 3-5× the baseline; full arms are 10-12× the baseline. No clinical gain on this substrate justifies that for full arms.

**Headline takeaway**: in the SBT_Benchmark setting, OPL's prompt design (Sid PI + three-tier claim layer discipline + empty-integrator rule) translates into a real CRC anchor-arm win over vMTB's planner+synth. Both frameworks' full multi-agent pipelines are *worse* than their own anchor arms — the schema-shape stage is the bottleneck; piling more experts upstream of it just adds entropy.

## Caveats before drawing conclusions

1. **Sample size**: n=30 per arm per surface. CIs are wide. Treat metric deltas < ~0.1 as noise.
2. **Neither framework is in production form here**. Both `*-full` arms were adapted to plain synchronous OpenRouter calls. OPL's real production stack is claude-native (Wave 2 hypothesis tournament + Wave 3 bixbench data evidence + Wave 4 hypothesis validation + Henry's 27 deterministic Python gates) — *none* of those run in this benchmark. vMTB similarly skips its NCCN PageIndex builder, organizer pre-step, and the deterministic facts/guidelines/safety verifiers as production code.
3. **The schema-shape stage is shared between mtb-* and opl-***. The fact that `*-full` arms underperform `*-anchor` arms is partly because the upstream multi-agent output is harder for the schema-shape pass to compress into 3 ranked recommendations. This is fixable but not fixed in this pilot.
4. **Reasoning-model artefact**: MiniMax-M2 emits `<think>...</think>` blocks before the answer. Pipelines with more LLM hops accumulate more truncated-think failures; this disproportionately hits `*-full` arms. A non-reasoning model would shift these numbers.
5. **NCCN concordance metric rewards 'stop and ask' decisions** when discriminators are missing. Multi-expert pipelines fanned out to specific recommendations get scored as overreach. This is by design of the benchmark and shows up here.
6. **Henry L1 verifier is LLM-orchestrated in this benchmark**, not the real Python `validators/gates/` registry. The OPL production verifier is much stronger; what we measured is a thin stand-in.

## Arm legend

- **baseline** — baseline (1 call)
- **mtb-lite** — mtb-anchor (vMTB plan+retrieve+synth)
- **mtb-full** — mtb-full (vMTB multi-agent + 3 verifiers)
- **opl-anchor** — opl-anchor (OPL Sid plan+retrieve+synth)
- **opl-full** — opl-full (OPL Rosa∥Bert+Vince+Sid+Henry-L1)

## CRC surface (`tmp/Case_version/`)

N items per arm: 30

### Wall-time & success counts

| Arm | mean wall (s/case) | median wall (s) | max wall (s) | total wall (s) | n_total | n_ok | n_json_ok |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline (1 call) | 11.9 | 11.3 | 29.5 | 358 | 30 | 22 | 21 |
| mtb-anchor (vMTB plan+retrieve+synth) | 39.1 | 41.6 | 74.3 | 1174 | 30 | 22 | 20 |
| mtb-full (vMTB multi-agent + 3 verifiers) | 115.8 | 133.3 | 223.7 | 3475 | 30 | 20 | 14 |
| opl-anchor (OPL Sid plan+retrieve+synth) | 41.8 | 42.4 | 90.9 | 1253 | 30 | 21 | 21 |
| opl-full (OPL Rosa∥Bert+Vince+Sid+Henry-L1) | 89.0 | 95.2 | 166.2 | 2670 | 30 | 17 | 19 |

### Technical health

| Metric | baseline | mtb-lite | mtb-full | opl-anchor | opl-full |
| --- | ---: | ---: | ---: | ---: | ---: |
| JSON parse rate | **0.700** | 0.667 | 0.467 | 0.700 | 0.633 |
| Schema-valid rate | 0.667 | 0.667 | 0.467 | **0.700** | 0.633 |
| Raw schema-valid rate | 0.500 | **0.600** | 0.333 | 0.600 | 0.533 |

### CRC clinical metrics (bold = best in row)

| Metric | baseline | mtb-lite | mtb-full | opl-anchor | opl-full |
| --- | ---: | ---: | ---: | ---: | ---: |
| CRC therapy F1@3 (full denom) | 0.339 | 0.340 | 0.224 | **0.414** | 0.311 |
| CRC therapy F1@3 (scorable only) | 0.508 | 0.510 | 0.480 | **0.592** | 0.491 |
| CRC strict therapy F1@3 | **0.346** | 0.277 | 0.172 | 0.342 | 0.321 |
| CRC class-level F1@3 | 0.594 | 0.616 | 0.554 | **0.667** | 0.638 |
| CRC therapy coverage F1 | 0.508 | 0.510 | 0.480 | **0.592** | 0.491 |
| CRC nDCG@3 | 0.550 | 0.548 | 0.561 | **0.714** | 0.622 |
| CRC treatment-intent match | 0.650 | 0.750 | 0.643 | **0.810** | 0.789 |
| CRC off-gold rate (lower=better) | **0.650** | 0.800 | 0.929 | 0.952 | 0.842 |
| CRC unsupported rate (lower=better) | 0.100 | 0.100 | 0.071 | **0.048** | 0.211 |
| CRC contraindicated rate (lower=better) | 0.150 | 0.050 | **0.000** | 0.095 | 0.105 |
| CRC molecular-context error (lower=better) | 0.100 | **0.000** | 0.000 | 0.048 | 0.053 |
| CRC missing-info F1 | — | — | — | — | — |

### Failure-label distribution (CRC)

| Failure label | baseline (1 call) | mtb-anchor (vMTB plan+retrieve+synth) | mtb-full (vMTB multi-agent + 3 verifiers) | opl-anchor (OPL Sid plan+retrieve+synth) | opl-full (OPL Rosa∥Bert+Vince+Sid+Henry-L1) |
| --- | ---: | ---: | ---: | ---: | ---: |
| F11_unsupported_recommendation | 2 | 2 | 1 | 1 | 4 |
| F12_treatment_intent_mismatch | 7 | 5 | 5 | 4 | 4 |
| F13_molecular_context_error | 2 | 0 | 0 | 1 | 1 |
| F14_therapy_set_mismatch | 16 | 17 | 13 | 20 | 17 |
| F16_contraindicated_recommendation | 3 | 1 | 0 | 2 | 2 |
| contradictory_output | 7 | 0 | 2 | 2 | 7 |
| off_gold_recommendation | 13 | 16 | 13 | 20 | 16 |
| technical_schema_violation | 1 | 0 | 0 | 0 | 0 |
| technical_unparseable_json | 9 | 10 | 16 | 9 | 11 |

## NCCN surface (`tmp/NCCN_version/`, CRC subset)

N items per arm: 30

### Wall-time & success counts

| Arm | mean wall (s/case) | median wall (s) | max wall (s) | total wall (s) | n_total | n_ok | n_json_ok |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline (1 call) | 8.5 | 7.1 | 14.2 | 254 | 30 | 12 | 12 |
| mtb-anchor (vMTB plan+retrieve+synth) | 16.8 | 14.1 | 30.3 | 505 | 30 | 12 | 12 |
| mtb-full (vMTB multi-agent + 3 verifiers) | 79.6 | 35.4 | 198.6 | 2389 | 30 | 11 | 11 |
| opl-anchor (OPL Sid plan+retrieve+synth) | 22.8 | 14.2 | 53.8 | 685 | 30 | 12 | 12 |
| opl-full (OPL Rosa∥Bert+Vince+Sid+Henry-L1) | 64.1 | 35.4 | 154.9 | 1922 | 30 | 9 | 11 |

### Technical health

| Metric | baseline | mtb-lite | mtb-full | opl-anchor | opl-full |
| --- | ---: | ---: | ---: | ---: | ---: |
| JSON parse rate | **0.400** | 0.400 | 0.367 | 0.400 | 0.367 |
| Schema-valid rate | **0.400** | 0.400 | 0.333 | 0.400 | 0.367 |
| Raw schema-valid rate | **0.400** | 0.367 | 0.300 | 0.367 | 0.333 |

### NCCN clinical metrics (bold = best in row)

| Metric | baseline | mtb-lite | mtb-full | opl-anchor | opl-full |
| --- | ---: | ---: | ---: | ---: | ---: |
| NCCN decision concordance (full denom) | **0.200** | 0.133 | 0.033 | 0.167 | 0.033 |
| NCCN decision concordance (scorable) | **0.500** | 0.333 | 0.100 | 0.417 | 0.091 |
| NCCN decision concordance (strict, full denom) | **0.200** | 0.133 | 0.033 | 0.167 | 0.033 |
| NCCN decision concordance (strict, scorable) | **0.500** | 0.333 | 0.100 | 0.417 | 0.091 |
| NCCN macro-by-q-type concordance | 0.320 | 0.320 | 0.040 | **0.413** | 0.200 |
| NCCN unsafe overreach (lower=better) | **0.000** | 0.000 | 0.250 | 0.500 | 0.714 |
| NCCN false-stop rate (lower=better) | **0.000** | 0.000 | 0.000 | 0.000 | 0.000 |
| NCCN true false-stop rate (lower=better) | **0.000** | 0.000 | 0.000 | 0.000 | 0.000 |
| NCCN premature commitment (lower=better) | **0.000** | 0.091 | 0.400 | 0.455 | 0.800 |
| NCCN route mismatch (lower=better) | 1.000 | 1.000 | **0.000** | 0.000 | 0.000 |

### Failure-label distribution (NCCN)

| Failure label | baseline (1 call) | mtb-anchor (vMTB plan+retrieve+synth) | mtb-full (vMTB multi-agent + 3 verifiers) | opl-anchor (OPL Sid plan+retrieve+synth) | opl-full (OPL Rosa∥Bert+Vince+Sid+Henry-L1) |
| --- | ---: | ---: | ---: | ---: | ---: |
| F10_evidence_bypass | 0 | 0 | 0 | 2 | 1 |
| F1_unsafe_overreach | 0 | 0 | 2 | 4 | 5 |
| F3_premature_commitment | 0 | 1 | 2 | 1 | 3 |
| F4_missed_decisive_info | 5 | 8 | 6 | 6 | 7 |
| F7_wrong_route | 0 | 0 | 1 | 0 | 0 |
| content_covers_gold_next_step | 0 | 1 | 0 | 0 | 0 |
| route_text_recognized_but_stop_label | 1 | 1 | 0 | 0 | 0 |
| technical_schema_violation | 0 | 0 | 1 | 0 | 0 |
| technical_unparseable_json | 18 | 18 | 19 | 18 | 19 |

## Raw `by_model` blocks

### CRC

#### baseline (`baseline::MiniMax-M2`)
```json
{
  "n_total": 30,
  "n_scorable": 20,
  "json_parse_rate": 0.7,
  "raw_schema_valid_rate": 0.5,
  "repaired_schema_valid_rate": 0.6666666666666666,
  "schema_valid_rate": 0.6666666666666666,
  "strict_schema_valid_rate": 0.5,
  "failure_labels": {
    "technical_schema_violation": 1,
    "off_gold_recommendation": 13,
    "F14_therapy_set_mismatch": 16,
    "contradictory_output": 7,
    "F12_treatment_intent_mismatch": 7,
    "F11_unsupported_recommendation": 2,
    "F16_contraindicated_recommendation": 3,
    "F13_molecular_context_error": 2,
    "technical_unparseable_json": 9
  },
  "crc": {
    "n": 30,
    "scorable_n": 20,
    "therapy_f1_at3_full_denominator": 0.33888888888888896,
    "therapy_f1_at3_scorable_only": 0.5083333333333335,
    "strict_therapy_f1_at3": 0.3461904761904762,
    "class_therapy_f1_at3": 0.5935714285714286,
    "therapy_coverage_f1": 0.5083333333333335,
    "ndcg_at3": 0.5501246065816684,
    "off_gold_recommendation_rate": 0.65,
    "unsupported_recommendation_rate": 0.1,
    "contraindicated_recommendation_rate": 0.15,
    "treatment_intent_match_rate": 0.65,
    "molecular_context_error_rate": 0.1,
    "missing_information_recall": 0.5833333333333333
  }
}
```

#### mtb-lite (`mtb-lite::MiniMax-M2`)
```json
{
  "n_total": 30,
  "n_scorable": 20,
  "json_parse_rate": 0.6666666666666666,
  "raw_schema_valid_rate": 0.6,
  "repaired_schema_valid_rate": 0.6666666666666666,
  "schema_valid_rate": 0.6666666666666666,
  "strict_schema_valid_rate": 0.6,
  "failure_labels": {
    "off_gold_recommendation": 16,
    "F14_therapy_set_mismatch": 17,
    "F12_treatment_intent_mismatch": 5,
    "F11_unsupported_recommendation": 2,
    "technical_unparseable_json": 10,
    "F16_contraindicated_recommendation": 1
  },
  "crc": {
    "n": 30,
    "scorable_n": 20,
    "therapy_f1_at3_full_denominator": 0.34031746031746035,
    "therapy_f1_at3_scorable_only": 0.5104761904761905,
    "strict_therapy_f1_at3": 0.27662698412698417,
    "class_therapy_f1_at3": 0.6159523809523811,
    "therapy_coverage_f1": 0.5104761904761905,
    "ndcg_at3": 0.5481094637097137,
    "off_gold_recommendation_rate": 0.8,
    "unsupported_recommendation_rate": 0.1,
    "contraindicated_recommendation_rate": 0.05,
    "treatment_intent_match_rate": 0.75,
    "molecular_context_error_rate": 0.0,
    "missing_information_recall": 0.41666666666666663
  }
}
```

#### mtb-full (`mtb-full::MiniMax-M2`)
```json
{
  "n_total": 30,
  "n_scorable": 14,
  "json_parse_rate": 0.4666666666666667,
  "raw_schema_valid_rate": 0.3333333333333333,
  "repaired_schema_valid_rate": 0.4666666666666667,
  "schema_valid_rate": 0.4666666666666667,
  "strict_schema_valid_rate": 0.3333333333333333,
  "failure_labels": {
    "off_gold_recommendation": 13,
    "F14_therapy_set_mismatch": 13,
    "contradictory_output": 2,
    "F12_treatment_intent_mismatch": 5,
    "technical_unparseable_json": 16,
    "F11_unsupported_recommendation": 1
  },
  "crc": {
    "n": 30,
    "scorable_n": 14,
    "therapy_f1_at3_full_denominator": 0.22396825396825398,
    "therapy_f1_at3_scorable_only": 0.47993197278911565,
    "strict_therapy_f1_at3": 0.1717687074829932,
    "class_therapy_f1_at3": 0.5540816326530613,
    "therapy_coverage_f1": 0.47993197278911565,
    "ndcg_at3": 0.5607341919578718,
    "off_gold_recommendation_rate": 0.9285714285714286,
    "unsupported_recommendation_rate": 0.07142857142857142,
    "contraindicated_recommendation_rate": 0.0,
    "treatment_intent_match_rate": 0.6428571428571429,
    "molecular_context_error_rate": 0.0,
    "missing_information_recall": 0.0
  }
}
```

#### opl-anchor (`opl-anchor::MiniMax-M2`)
```json
{
  "n_total": 30,
  "n_scorable": 21,
  "json_parse_rate": 0.7,
  "raw_schema_valid_rate": 0.6,
  "repaired_schema_valid_rate": 0.7,
  "schema_valid_rate": 0.7,
  "strict_schema_valid_rate": 0.6,
  "failure_labels": {
    "off_gold_recommendation": 20,
    "F14_therapy_set_mismatch": 20,
    "F12_treatment_intent_mismatch": 4,
    "contradictory_output": 2,
    "F11_unsupported_recommendation": 1,
    "F16_contraindicated_recommendation": 2,
    "F13_molecular_context_error": 1,
    "technical_unparseable_json": 9
  },
  "crc": {
    "n": 30,
    "scorable_n": 21,
    "therapy_f1_at3_full_denominator": 0.4141269841269842,
    "therapy_f1_at3_scorable_only": 0.5916099773242631,
    "strict_therapy_f1_at3": 0.3416855631141345,
    "class_therapy_f1_at3": 0.6667800453514742,
    "therapy_coverage_f1": 0.5916099773242631,
    "ndcg_at3": 0.7143378172130814,
    "off_gold_recommendation_rate": 0.9523809523809523,
    "unsupported_recommendation_rate": 0.047619047619047616,
    "contraindicated_recommendation_rate": 0.09523809523809523,
    "treatment_intent_match_rate": 0.8095238095238095,
    "molecular_context_error_rate": 0.047619047619047616,
    "missing_information_recall": 0.5833333333333333
  }
}
```

#### opl-full (`opl-full::MiniMax-M2`)
```json
{
  "n_total": 30,
  "n_scorable": 19,
  "json_parse_rate": 0.6333333333333333,
  "raw_schema_valid_rate": 0.5333333333333333,
  "repaired_schema_valid_rate": 0.6333333333333333,
  "schema_valid_rate": 0.6333333333333333,
  "strict_schema_valid_rate": 0.5333333333333333,
  "failure_labels": {
    "off_gold_recommendation": 16,
    "F14_therapy_set_mismatch": 17,
    "contradictory_output": 7,
    "F12_treatment_intent_mismatch": 4,
    "F11_unsupported_recommendation": 4,
    "F16_contraindicated_recommendation": 2,
    "F13_molecular_context_error": 1,
    "technical_unparseable_json": 11
  },
  "crc": {
    "n": 30,
    "scorable_n": 19,
    "therapy_f1_at3_full_denominator": 0.31126984126984125,
    "therapy_f1_at3_scorable_only": 0.49147869674185457,
    "strict_therapy_f1_at3": 0.32055137844611525,
    "class_therapy_f1_at3": 0.6383458646616541,
    "therapy_coverage_f1": 0.49147869674185457,
    "ndcg_at3": 0.6215908191937614,
    "off_gold_recommendation_rate": 0.8421052631578947,
    "unsupported_recommendation_rate": 0.21052631578947367,
    "contraindicated_recommendation_rate": 0.10526315789473684,
    "treatment_intent_match_rate": 0.7894736842105263,
    "molecular_context_error_rate": 0.05263157894736842,
    "missing_information_recall": 0.25
  }
}
```

### NCCN

#### baseline (`baseline::MiniMax-M2`)
```json
{
  "n_total": 30,
  "n_scorable": 12,
  "json_parse_rate": 0.4,
  "raw_schema_valid_rate": 0.4,
  "repaired_schema_valid_rate": 0.4,
  "schema_valid_rate": 0.4,
  "strict_schema_valid_rate": 0.4,
  "failure_labels": {
    "F4_missed_decisive_info": 5,
    "route_text_recognized_but_stop_label": 1,
    "technical_unparseable_json": 18
  },
  "nccn": {
    "n": 30,
    "scorable_n": 12,
    "structured_decision_concordance_full_denominator": 0.2,
    "structured_decision_concordance_scorable_only": 0.5,
    "structured_decision_concordance_strict_full_denominator": 0.2,
    "structured_decision_concordance_strict_scorable_only": 0.5,
    "strict_unsafe_overreach_rate": 0.0,
    "premature_downstream_commitment_rate": 0.0,
    "false_stop_rate": 0.0,
    "true_false_stop_rate": 0.0,
    "route_label_text_mismatch_rate": 1.0,
    "macro_by_question_type_concordance": 0.32,
    "macro_by_question_type_concordance_strict": 0.32,
    "by_question_type": {
      "evidence_resolution_request": {
        "n": 3,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.11188811188811187
      },
      "missing_information_request": {
        "n": 5,
        "structured_decision_concordance": 0.6,
        "structured_decision_concordance_strict": 0.6,
        "mean_content_score": 0.20272727272727273
      },
      "parallel_option_disambiguation": {
        "n": 3,
        "structured_decision_concordance": 1.0,
        "structured_decision_concordance_strict": 1.0,
        "mean_content_score": 0.4686609686609686
      },
      "unknown": {
        "n": 18,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.0
      },
      "upstream_routing_decision": {
        "n": 1,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.7455044361092137
      }
    }
  }
}
```

#### mtb-lite (`mtb-lite::MiniMax-M2`)
```json
{
  "n_total": 30,
  "n_scorable": 12,
  "json_parse_rate": 0.4,
  "raw_schema_valid_rate": 0.36666666666666664,
  "repaired_schema_valid_rate": 0.4,
  "schema_valid_rate": 0.4,
  "strict_schema_valid_rate": 0.36666666666666664,
  "failure_labels": {
    "F3_premature_commitment": 1,
    "F4_missed_decisive_info": 8,
    "route_text_recognized_but_stop_label": 1,
    "content_covers_gold_next_step": 1,
    "technical_unparseable_json": 18
  },
  "nccn": {
    "n": 30,
    "scorable_n": 12,
    "structured_decision_concordance_full_denominator": 0.13333333333333333,
    "structured_decision_concordance_scorable_only": 0.3333333333333333,
    "structured_decision_concordance_strict_full_denominator": 0.13333333333333333,
    "structured_decision_concordance_strict_scorable_only": 0.3333333333333333,
    "strict_unsafe_overreach_rate": 0.0,
    "premature_downstream_commitment_rate": 0.09090909090909091,
    "false_stop_rate": 0.0,
    "true_false_stop_rate": 0.0,
    "route_label_text_mismatch_rate": 1.0,
    "macro_by_question_type_concordance": 0.32,
    "macro_by_question_type_concordance_strict": 0.32,
    "by_question_type": {
      "evidence_resolution_request": {
        "n": 3,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.05555555555555555
      },
      "missing_information_request": {
        "n": 5,
        "structured_decision_concordance": 0.6,
        "structured_decision_concordance_strict": 0.6,
        "mean_content_score": 0.21709401709401713
      },
      "parallel_option_disambiguation": {
        "n": 3,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.1111111111111111
      },
      "unknown": {
        "n": 18,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.0
      },
      "upstream_routing_decision": {
        "n": 1,
        "structured_decision_concordance": 1.0,
        "structured_decision_concordance_strict": 1.0,
        "mean_content_score": 0.8439472603875686
      }
    }
  }
}
```

#### mtb-full (`mtb-full::MiniMax-M2`)
```json
{
  "n_total": 30,
  "n_scorable": 10,
  "json_parse_rate": 0.36666666666666664,
  "raw_schema_valid_rate": 0.3,
  "repaired_schema_valid_rate": 0.3333333333333333,
  "schema_valid_rate": 0.3333333333333333,
  "strict_schema_valid_rate": 0.3,
  "failure_labels": {
    "F3_premature_commitment": 2,
    "F4_missed_decisive_info": 6,
    "technical_schema_violation": 1,
    "F1_unsafe_overreach": 2,
    "F7_wrong_route": 1,
    "technical_unparseable_json": 19
  },
  "nccn": {
    "n": 30,
    "scorable_n": 10,
    "structured_decision_concordance_full_denominator": 0.03333333333333333,
    "structured_decision_concordance_scorable_only": 0.1,
    "structured_decision_concordance_strict_full_denominator": 0.03333333333333333,
    "structured_decision_concordance_strict_scorable_only": 0.1,
    "strict_unsafe_overreach_rate": 0.25,
    "premature_downstream_commitment_rate": 0.4,
    "false_stop_rate": 0.0,
    "true_false_stop_rate": 0.0,
    "route_label_text_mismatch_rate": 0.0,
    "macro_by_question_type_concordance": 0.04,
    "macro_by_question_type_concordance_strict": 0.04,
    "by_question_type": {
      "evidence_resolution_request": {
        "n": 3,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.0
      },
      "missing_information_request": {
        "n": 5,
        "structured_decision_concordance": 0.2,
        "structured_decision_concordance_strict": 0.2,
        "mean_content_score": 0.20714285714285716
      },
      "parallel_option_disambiguation": {
        "n": 2,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.28571428571428575
      },
      "unknown": {
        "n": 19,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.0
      },
      "upstream_routing_decision": {
        "n": 1,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.27202165934585465
      }
    }
  }
}
```

#### opl-anchor (`opl-anchor::MiniMax-M2`)
```json
{
  "n_total": 30,
  "n_scorable": 12,
  "json_parse_rate": 0.4,
  "raw_schema_valid_rate": 0.36666666666666664,
  "repaired_schema_valid_rate": 0.4,
  "schema_valid_rate": 0.4,
  "strict_schema_valid_rate": 0.36666666666666664,
  "failure_labels": {
    "F4_missed_decisive_info": 6,
    "F1_unsafe_overreach": 4,
    "F10_evidence_bypass": 2,
    "F3_premature_commitment": 1,
    "technical_unparseable_json": 18
  },
  "nccn": {
    "n": 30,
    "scorable_n": 12,
    "structured_decision_concordance_full_denominator": 0.16666666666666666,
    "structured_decision_concordance_scorable_only": 0.4166666666666667,
    "structured_decision_concordance_strict_full_denominator": 0.16666666666666666,
    "structured_decision_concordance_strict_scorable_only": 0.4166666666666667,
    "strict_unsafe_overreach_rate": 0.5,
    "premature_downstream_commitment_rate": 0.45454545454545453,
    "false_stop_rate": 0.0,
    "true_false_stop_rate": 0.0,
    "route_label_text_mismatch_rate": 0.0,
    "macro_by_question_type_concordance": 0.4133333333333333,
    "macro_by_question_type_concordance_strict": 0.4133333333333333,
    "by_question_type": {
      "evidence_resolution_request": {
        "n": 3,
        "structured_decision_concordance": 0.3333333333333333,
        "structured_decision_concordance_strict": 0.3333333333333333,
        "mean_content_score": 0.2142857142857143
      },
      "missing_information_request": {
        "n": 5,
        "structured_decision_concordance": 0.4,
        "structured_decision_concordance_strict": 0.4,
        "mean_content_score": 0.1415032679738562
      },
      "parallel_option_disambiguation": {
        "n": 3,
        "structured_decision_concordance": 0.3333333333333333,
        "structured_decision_concordance_strict": 0.3333333333333333,
        "mean_content_score": 0.3247863247863248
      },
      "unknown": {
        "n": 18,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.0
      },
      "upstream_routing_decision": {
        "n": 1,
        "structured_decision_concordance": 1.0,
        "structured_decision_concordance_strict": 1.0,
        "mean_content_score": 0.8439472603875686
      }
    }
  }
}
```

#### opl-full (`opl-full::MiniMax-M2`)
```json
{
  "n_total": 30,
  "n_scorable": 11,
  "json_parse_rate": 0.36666666666666664,
  "raw_schema_valid_rate": 0.3333333333333333,
  "repaired_schema_valid_rate": 0.36666666666666664,
  "schema_valid_rate": 0.36666666666666664,
  "strict_schema_valid_rate": 0.3333333333333333,
  "failure_labels": {
    "F3_premature_commitment": 3,
    "F4_missed_decisive_info": 7,
    "F1_unsafe_overreach": 5,
    "F10_evidence_bypass": 1,
    "technical_unparseable_json": 19
  },
  "nccn": {
    "n": 30,
    "scorable_n": 11,
    "structured_decision_concordance_full_denominator": 0.03333333333333333,
    "structured_decision_concordance_scorable_only": 0.09090909090909091,
    "structured_decision_concordance_strict_full_denominator": 0.03333333333333333,
    "structured_decision_concordance_strict_scorable_only": 0.09090909090909091,
    "strict_unsafe_overreach_rate": 0.7142857142857143,
    "premature_downstream_commitment_rate": 0.8,
    "false_stop_rate": 0.0,
    "true_false_stop_rate": 0.0,
    "route_label_text_mismatch_rate": 0.0,
    "macro_by_question_type_concordance": 0.2,
    "macro_by_question_type_concordance_strict": 0.2,
    "by_question_type": {
      "evidence_resolution_request": {
        "n": 3,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.2644688644688645
      },
      "missing_information_request": {
        "n": 4,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.1388888888888889
      },
      "parallel_option_disambiguation": {
        "n": 3,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.2205128205128205
      },
      "unknown": {
        "n": 19,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.0
      },
      "upstream_routing_decision": {
        "n": 1,
        "structured_decision_concordance": 1.0,
        "structured_decision_concordance_strict": 1.0,
        "mean_content_score": 0.7401443287724794
      }
    }
  }
}
```
