# MTB vs OPL — quantitative comparison on SBT_Benchmark

Scorer: `deterministic_scorer_v2_5` (CRC) / `deterministic_scorer_v2_5` (NCCN)

Model under test: **MiniMax-M2.7** (reasoning model — every arm gets identical model + temperature + retry budget; the only contrast between mtb-* and opl-* arms is the prompt corpus / multi-agent shape).

Run scale: n=30 per surface (CRC + NCCN), 5 arms each, max_tokens floor=80000 to fit reasoning blocks. Only `json_parse_ok = true` records are scorable — see per-arm `n_json_ok` column below.

## TL;DR — who wins?

Plain answer to *"哪个效果好"* on this n=30 pilot:

- **CRC surface (treatment recommendation)** — **opl-anchor wins clearly**. Best in 6/12 CRC metrics: therapy F1@3 (full denom 0.463 / scorable 0.555), nDCG@3 (0.679), strict therapy F1@3 (0.358), therapy coverage F1 (0.555), contraindicated rate (0.040), molecular-context-error rate (0.040). mtb-anchor takes class-level F1 (0.697 vs opl-anchor 0.677) and unsupported rate (0.000). opl-full leads treatment-intent match (0.750). Baseline holds off-gold rate (0.760) — i.e. it makes fewer recommendations period.
- **CRC surface — the *-full multi-agent pipelines underperform their anchor twins on F1-style metrics** (mtb-full 0.281 vs mtb-anchor 0.399; opl-full 0.364 vs opl-anchor 0.463 on therapy F1@3 full denom). The extra Rosa∥Bert∥Vince / pathologist∥geneticist∥oncologist hops add reasoning loops but the schema-shape stage cannot recover the upstream variance. mtb-full does get to 0.048 contraindicated (vs baseline 0.080) — verifiers do catch some unsafe outputs.
- **NCCN surface (decision concordance)** — **baseline wins decisively**. 0.400 strict scorable concordance vs mtb-anchor 0.250 / opl-anchor 0.160 / opl-full 0.125 / mtb-full 0.120. NCCN gold rewards `stop_missing_info` / `stop_need_evidence` / `routing` when discriminators are missing; multi-expert pipelines fan out into specific recommendations and score as overreach. opl-full 0.375 + opl-anchor 0.438 unsafe overreach vs baseline 0.125. mtb-full + opl-full do get false-stop rate to 0.000 (vs baseline 0.250) — but the cost is they push past 'need more info' too aggressively.
- **Wall-time** (M2.7 + 80K tokens): baseline 25-27s, anchor arms 53-87s, full arms 187-268s. *-full arms are 7-10× baseline. No clinical gain on this substrate justifies that for full arms.
- **Technical health is excellent at 80K tokens**: JSON parse rate 0.77-0.83 on CRC, 0.83 across all NCCN arms. The earlier M2 + 8K-token attempt had 0.4-0.7 parse rates because reasoning blocks truncated — fixed.

**Headline**: on this SBT_Benchmark n=30 pilot, **OPL's prompt design wins CRC, baseline wins NCCN**. Neither framework's full multi-agent shape pays off here — the schema-shape stage is the bottleneck, and NCCN's 'know-when-to-stop' rubric actively penalises multi-expert recommendation fanout. The anchor arms (planner + retrieve + 1-call synth) sit in the sweet spot for this benchmark substrate.

## Caveats before drawing conclusions

1. **Sample size**: n=30 per arm per surface. CIs are wide. Treat metric deltas < ~0.1 as noise.
2. **Neither framework is in production form here**. Both `*-full` arms were adapted to plain synchronous OpenRouter calls. OPL's real production stack is claude-native (Wave 2 hypothesis tournament + Wave 3 bixbench data evidence + Wave 4 hypothesis validation + Henry's 27 deterministic Python gates) — *none* of those run in this benchmark. vMTB similarly skips its NCCN PageIndex builder, organizer pre-step, and the deterministic facts/guidelines/safety verifiers as production code.
3. **The schema-shape stage is shared between mtb-* and opl-***. The fact that `*-full` arms underperform `*-anchor` arms is partly because the upstream multi-agent output is harder for the schema-shape pass to compress into 3 ranked recommendations. This is fixable but not fixed in this pilot.
4. **Reasoning-model artefact**: MiniMax-M2.7 emits `<think>...</think>` blocks before the answer. We bumped max_tokens floor to 80000 to fit; a smaller budget (e.g. M2 + 8K) caused 40-60% truncation on `*-full` arms in an earlier run. A non-reasoning model would shift these numbers and shrink the wall-time gap.
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
| baseline (1 call) | 26.7 | 26.2 | 60.1 | 802 | 30 | 25 | 25 |
| mtb-anchor (vMTB plan+retrieve+synth) | 87.2 | 89.1 | 147.1 | 2616 | 30 | 25 | 25 |
| mtb-full (vMTB multi-agent + 3 verifiers) | 267.5 | 262.6 | 473.9 | 8024 | 30 | 25 | 23 |
| opl-anchor (OPL Sid plan+retrieve+synth) | 83.8 | 79.4 | 166.3 | 2514 | 30 | 25 | 25 |
| opl-full (OPL Rosa∥Bert+Vince+Sid+Henry-L1) | 187.0 | 191.5 | 304.5 | 5611 | 30 | 25 | 24 |

### Technical health

| Metric | baseline | mtb-lite | mtb-full | opl-anchor | opl-full |
| --- | ---: | ---: | ---: | ---: | ---: |
| JSON parse rate | **0.833** | 0.833 | 0.767 | 0.833 | 0.800 |
| Schema-valid rate | **0.833** | 0.833 | 0.700 | 0.833 | 0.800 |
| Raw schema-valid rate | 0.767 | **0.800** | 0.700 | 0.767 | 0.800 |

### CRC clinical metrics (bold = best in row)

| Metric | baseline | mtb-lite | mtb-full | opl-anchor | opl-full |
| --- | ---: | ---: | ---: | ---: | ---: |
| CRC therapy F1@3 (full denom) | 0.393 | 0.399 | 0.281 | **0.463** | 0.364 |
| CRC therapy F1@3 (scorable only) | 0.472 | 0.478 | 0.402 | **0.555** | 0.455 |
| CRC strict therapy F1@3 | 0.332 | 0.317 | 0.221 | **0.358** | 0.323 |
| CRC class-level F1@3 | 0.579 | **0.697** | 0.539 | 0.677 | 0.675 |
| CRC therapy coverage F1 | 0.472 | 0.478 | 0.402 | **0.555** | 0.455 |
| CRC nDCG@3 | 0.556 | 0.539 | 0.461 | **0.679** | 0.540 |
| CRC treatment-intent match | 0.520 | 0.680 | 0.667 | 0.720 | **0.750** |
| CRC off-gold rate (lower=better) | **0.760** | 0.920 | 1.000 | 0.880 | 0.958 |
| CRC unsupported rate (lower=better) | 0.040 | **0.000** | 0.095 | 0.040 | 0.125 |
| CRC contraindicated rate (lower=better) | 0.080 | 0.120 | 0.048 | **0.040** | 0.083 |
| CRC molecular-context error (lower=better) | 0.080 | 0.120 | 0.048 | **0.040** | 0.083 |
| CRC missing-info F1 | — | — | — | — | — |

### Failure-label distribution (CRC)

| Failure label | baseline (1 call) | mtb-anchor (vMTB plan+retrieve+synth) | mtb-full (vMTB multi-agent + 3 verifiers) | opl-anchor (OPL Sid plan+retrieve+synth) | opl-full (OPL Rosa∥Bert+Vince+Sid+Henry-L1) |
| --- | ---: | ---: | ---: | ---: | ---: |
| F11_unsupported_recommendation | 1 | 0 | 2 | 1 | 3 |
| F12_treatment_intent_mismatch | 12 | 8 | 7 | 7 | 6 |
| F13_molecular_context_error | 2 | 3 | 1 | 1 | 2 |
| F14_therapy_set_mismatch | 24 | 23 | 21 | 23 | 23 |
| F16_contraindicated_recommendation | 2 | 3 | 1 | 1 | 2 |
| contradictory_output | 7 | 0 | 6 | 1 | 7 |
| model_acknowledged_data_conflict | 0 | 0 | 2 | 0 | 0 |
| off_gold_recommendation | 19 | 23 | 21 | 22 | 23 |
| technical_schema_violation | 0 | 0 | 2 | 0 | 0 |
| technical_unparseable_json | 5 | 5 | 7 | 5 | 6 |

## NCCN surface (`tmp/NCCN_version/`, CRC subset)

N items per arm: 30

### Wall-time & success counts

| Arm | mean wall (s/case) | median wall (s) | max wall (s) | total wall (s) | n_total | n_ok | n_json_ok |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline (1 call) | 24.8 | 21.0 | 61.2 | 743 | 30 | 25 | 25 |
| mtb-anchor (vMTB plan+retrieve+synth) | 53.0 | 49.8 | 91.3 | 1589 | 30 | 25 | 25 |
| mtb-full (vMTB multi-agent + 3 verifiers) | 226.8 | 222.7 | 432.7 | 6804 | 30 | 25 | 25 |
| opl-anchor (OPL Sid plan+retrieve+synth) | 71.9 | 75.9 | 131.1 | 2158 | 30 | 25 | 25 |
| opl-full (OPL Rosa∥Bert+Vince+Sid+Henry-L1) | 186.6 | 187.5 | 274.4 | 5599 | 30 | 24 | 25 |

### Technical health

| Metric | baseline | mtb-lite | mtb-full | opl-anchor | opl-full |
| --- | ---: | ---: | ---: | ---: | ---: |
| JSON parse rate | **0.833** | 0.833 | 0.833 | 0.833 | 0.833 |
| Schema-valid rate | **0.833** | 0.800 | 0.833 | 0.833 | 0.800 |
| Raw schema-valid rate | **0.833** | 0.800 | 0.767 | 0.800 | 0.733 |

### NCCN clinical metrics (bold = best in row)

| Metric | baseline | mtb-lite | mtb-full | opl-anchor | opl-full |
| --- | ---: | ---: | ---: | ---: | ---: |
| NCCN decision concordance (full denom) | **0.367** | 0.233 | 0.100 | 0.167 | 0.100 |
| NCCN decision concordance (scorable) | **0.440** | 0.292 | 0.120 | 0.200 | 0.125 |
| NCCN decision concordance (strict, full denom) | **0.333** | 0.200 | 0.100 | 0.133 | 0.100 |
| NCCN decision concordance (strict, scorable) | **0.400** | 0.250 | 0.120 | 0.160 | 0.125 |
| NCCN macro-by-q-type concordance | **0.239** | 0.214 | 0.131 | 0.167 | 0.200 |
| NCCN unsafe overreach (lower=better) | **0.125** | 0.125 | 0.647 | 0.438 | 0.375 |
| NCCN false-stop rate (lower=better) | 0.250 | 0.250 | **0.000** | 0.250 | 0.000 |
| NCCN true false-stop rate (lower=better) | 0.250 | 0.250 | **0.000** | 0.250 | 0.000 |
| NCCN premature commitment (lower=better) | **0.095** | 0.143 | 0.667 | 0.524 | 0.524 |
| NCCN route mismatch (lower=better) | 0.750 | 0.500 | **0.000** | 0.250 | 0.750 |

### Failure-label distribution (NCCN)

| Failure label | baseline (1 call) | mtb-anchor (vMTB plan+retrieve+synth) | mtb-full (vMTB multi-agent + 3 verifiers) | opl-anchor (OPL Sid plan+retrieve+synth) | opl-full (OPL Rosa∥Bert+Vince+Sid+Henry-L1) |
| --- | ---: | ---: | ---: | ---: | ---: |
| F10_evidence_bypass | 1 | 1 | 4 | 1 | 2 |
| F1_unsafe_overreach | 2 | 2 | 11 | 7 | 6 |
| F3_premature_commitment | 0 | 1 | 3 | 4 | 5 |
| F4_missed_decisive_info | 10 | 13 | 12 | 12 | 12 |
| F5_false_stop | 1 | 1 | 0 | 1 | 0 |
| F6_overcautious | 1 | 1 | 0 | 1 | 0 |
| F7_wrong_route | 0 | 0 | 3 | 1 | 1 |
| content_covers_gold_next_step | 1 | 1 | 0 | 1 | 0 |
| route_text_recognized_but_stop_label | 3 | 2 | 0 | 1 | 3 |
| schema_invalid_extra_fields | 0 | 0 | 0 | 0 | 1 |
| technical_schema_violation | 0 | 1 | 0 | 0 | 1 |
| technical_unparseable_json | 5 | 5 | 5 | 5 | 5 |

## Raw `by_model` blocks

### CRC

#### baseline (`baseline::MiniMax-M2.7`)
```json
{
  "n_total": 30,
  "n_scorable": 25,
  "json_parse_rate": 0.8333333333333334,
  "raw_schema_valid_rate": 0.7666666666666667,
  "repaired_schema_valid_rate": 0.8333333333333334,
  "schema_valid_rate": 0.8333333333333334,
  "strict_schema_valid_rate": 0.7666666666666667,
  "failure_labels": {
    "off_gold_recommendation": 19,
    "F14_therapy_set_mismatch": 24,
    "F12_treatment_intent_mismatch": 12,
    "contradictory_output": 7,
    "F11_unsupported_recommendation": 1,
    "F16_contraindicated_recommendation": 2,
    "F13_molecular_context_error": 2,
    "technical_unparseable_json": 5
  },
  "crc": {
    "n": 30,
    "scorable_n": 25,
    "therapy_f1_at3_full_denominator": 0.3933333333333334,
    "therapy_f1_at3_scorable_only": 0.4720000000000001,
    "strict_therapy_f1_at3": 0.33215873015873015,
    "class_therapy_f1_at3": 0.5790476190476191,
    "therapy_coverage_f1": 0.4720000000000001,
    "ndcg_at3": 0.5559898159883795,
    "off_gold_recommendation_rate": 0.76,
    "unsupported_recommendation_rate": 0.04,
    "contraindicated_recommendation_rate": 0.08,
    "treatment_intent_match_rate": 0.52,
    "molecular_context_error_rate": 0.08,
    "missing_information_recall": 0.6
  }
}
```

#### mtb-lite (`mtb-lite::MiniMax-M2.7`)
```json
{
  "n_total": 30,
  "n_scorable": 25,
  "json_parse_rate": 0.8333333333333334,
  "raw_schema_valid_rate": 0.8,
  "repaired_schema_valid_rate": 0.8333333333333334,
  "schema_valid_rate": 0.8333333333333334,
  "strict_schema_valid_rate": 0.8,
  "failure_labels": {
    "off_gold_recommendation": 23,
    "F12_treatment_intent_mismatch": 8,
    "F14_therapy_set_mismatch": 23,
    "F16_contraindicated_recommendation": 3,
    "F13_molecular_context_error": 3,
    "technical_unparseable_json": 5
  },
  "crc": {
    "n": 30,
    "scorable_n": 25,
    "therapy_f1_at3_full_denominator": 0.39857142857142863,
    "therapy_f1_at3_scorable_only": 0.47828571428571437,
    "strict_therapy_f1_at3": 0.3169206349206349,
    "class_therapy_f1_at3": 0.696952380952381,
    "therapy_coverage_f1": 0.47828571428571437,
    "ndcg_at3": 0.539243552954984,
    "off_gold_recommendation_rate": 0.92,
    "unsupported_recommendation_rate": 0.0,
    "contraindicated_recommendation_rate": 0.12,
    "treatment_intent_match_rate": 0.68,
    "molecular_context_error_rate": 0.12,
    "missing_information_recall": 0.6666666666666666
  }
}
```

#### mtb-full (`mtb-full::MiniMax-M2.7`)
```json
{
  "n_total": 30,
  "n_scorable": 21,
  "json_parse_rate": 0.7666666666666667,
  "raw_schema_valid_rate": 0.7,
  "repaired_schema_valid_rate": 0.7,
  "schema_valid_rate": 0.7,
  "strict_schema_valid_rate": 0.7,
  "failure_labels": {
    "off_gold_recommendation": 21,
    "F14_therapy_set_mismatch": 21,
    "F12_treatment_intent_mismatch": 7,
    "F11_unsupported_recommendation": 2,
    "F16_contraindicated_recommendation": 1,
    "F13_molecular_context_error": 1,
    "model_acknowledged_data_conflict": 2,
    "technical_unparseable_json": 7,
    "technical_schema_violation": 2,
    "contradictory_output": 6
  },
  "crc": {
    "n": 30,
    "scorable_n": 21,
    "therapy_f1_at3_full_denominator": 0.28111111111111114,
    "therapy_f1_at3_scorable_only": 0.4015873015873016,
    "strict_therapy_f1_at3": 0.22089947089947087,
    "class_therapy_f1_at3": 0.5392290249433106,
    "therapy_coverage_f1": 0.4015873015873016,
    "ndcg_at3": 0.46102089428622567,
    "off_gold_recommendation_rate": 1.0,
    "unsupported_recommendation_rate": 0.09523809523809523,
    "contraindicated_recommendation_rate": 0.047619047619047616,
    "treatment_intent_match_rate": 0.6666666666666666,
    "molecular_context_error_rate": 0.047619047619047616,
    "missing_information_recall": 0.4444444444444444
  }
}
```

#### opl-anchor (`opl-anchor::MiniMax-M2.7`)
```json
{
  "n_total": 30,
  "n_scorable": 25,
  "json_parse_rate": 0.8333333333333334,
  "raw_schema_valid_rate": 0.7666666666666667,
  "repaired_schema_valid_rate": 0.8333333333333334,
  "schema_valid_rate": 0.8333333333333334,
  "strict_schema_valid_rate": 0.7666666666666667,
  "failure_labels": {
    "off_gold_recommendation": 22,
    "F14_therapy_set_mismatch": 23,
    "F12_treatment_intent_mismatch": 7,
    "F11_unsupported_recommendation": 1,
    "technical_unparseable_json": 5,
    "contradictory_output": 1,
    "F16_contraindicated_recommendation": 1,
    "F13_molecular_context_error": 1
  },
  "crc": {
    "n": 30,
    "scorable_n": 25,
    "therapy_f1_at3_full_denominator": 0.46253968253968264,
    "therapy_f1_at3_scorable_only": 0.5550476190476191,
    "strict_therapy_f1_at3": 0.3581904761904762,
    "class_therapy_f1_at3": 0.6770476190476191,
    "therapy_coverage_f1": 0.5550476190476191,
    "ndcg_at3": 0.679012063215014,
    "off_gold_recommendation_rate": 0.88,
    "unsupported_recommendation_rate": 0.04,
    "contraindicated_recommendation_rate": 0.04,
    "treatment_intent_match_rate": 0.72,
    "molecular_context_error_rate": 0.04,
    "missing_information_recall": 0.6
  }
}
```

#### opl-full (`opl-full::MiniMax-M2.7`)
```json
{
  "n_total": 30,
  "n_scorable": 24,
  "json_parse_rate": 0.8,
  "raw_schema_valid_rate": 0.8,
  "repaired_schema_valid_rate": 0.8,
  "schema_valid_rate": 0.8,
  "strict_schema_valid_rate": 0.8,
  "failure_labels": {
    "off_gold_recommendation": 23,
    "F14_therapy_set_mismatch": 23,
    "F12_treatment_intent_mismatch": 6,
    "contradictory_output": 7,
    "F11_unsupported_recommendation": 3,
    "F16_contraindicated_recommendation": 2,
    "F13_molecular_context_error": 2,
    "technical_unparseable_json": 6
  },
  "crc": {
    "n": 30,
    "scorable_n": 24,
    "therapy_f1_at3_full_denominator": 0.36412698412698413,
    "therapy_f1_at3_scorable_only": 0.45515873015873015,
    "strict_therapy_f1_at3": 0.32268518518518513,
    "class_therapy_f1_at3": 0.6746031746031745,
    "therapy_coverage_f1": 0.45515873015873015,
    "ndcg_at3": 0.5401630843110978,
    "off_gold_recommendation_rate": 0.9583333333333334,
    "unsupported_recommendation_rate": 0.125,
    "contraindicated_recommendation_rate": 0.08333333333333333,
    "treatment_intent_match_rate": 0.75,
    "molecular_context_error_rate": 0.08333333333333333,
    "missing_information_recall": 0.5333333333333333
  }
}
```

### NCCN

#### baseline (`baseline::MiniMax-M2.7`)
```json
{
  "n_total": 30,
  "n_scorable": 25,
  "json_parse_rate": 0.8333333333333334,
  "raw_schema_valid_rate": 0.8333333333333334,
  "repaired_schema_valid_rate": 0.8333333333333334,
  "schema_valid_rate": 0.8333333333333334,
  "strict_schema_valid_rate": 0.8333333333333334,
  "failure_labels": {
    "F4_missed_decisive_info": 10,
    "F1_unsafe_overreach": 2,
    "F10_evidence_bypass": 1,
    "route_text_recognized_but_stop_label": 3,
    "content_covers_gold_next_step": 1,
    "technical_unparseable_json": 5,
    "F5_false_stop": 1,
    "F6_overcautious": 1
  },
  "nccn": {
    "n": 30,
    "scorable_n": 25,
    "structured_decision_concordance_full_denominator": 0.36666666666666664,
    "structured_decision_concordance_scorable_only": 0.44,
    "structured_decision_concordance_strict_full_denominator": 0.3333333333333333,
    "structured_decision_concordance_strict_scorable_only": 0.4,
    "strict_unsafe_overreach_rate": 0.125,
    "premature_downstream_commitment_rate": 0.09523809523809523,
    "false_stop_rate": 0.25,
    "true_false_stop_rate": 0.25,
    "route_label_text_mismatch_rate": 0.75,
    "macro_by_question_type_concordance": 0.2388888888888889,
    "macro_by_question_type_concordance_strict": 0.19722222222222222,
    "by_question_type": {
      "evidence_resolution_request": {
        "n": 4,
        "structured_decision_concordance": 0.25,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.19047619047619047
      },
      "in_guide_handoff_resolution": {
        "n": 2,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.4890800077460124
      },
      "missing_information_request": {
        "n": 12,
        "structured_decision_concordance": 0.5833333333333334,
        "structured_decision_concordance_strict": 0.5833333333333334,
        "mean_content_score": 0.2313926813926814
      },
      "parallel_option_disambiguation": {
        "n": 5,
        "structured_decision_concordance": 0.6,
        "structured_decision_concordance_strict": 0.6,
        "mean_content_score": 0.35595238095238096
      },
      "unknown": {
        "n": 5,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.0
      },
      "upstream_routing_decision": {
        "n": 2,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.4857499173651965
      }
    }
  }
}
```

#### mtb-lite (`mtb-lite::MiniMax-M2.7`)
```json
{
  "n_total": 30,
  "n_scorable": 24,
  "json_parse_rate": 0.8333333333333334,
  "raw_schema_valid_rate": 0.8,
  "repaired_schema_valid_rate": 0.8,
  "schema_valid_rate": 0.8,
  "strict_schema_valid_rate": 0.8,
  "failure_labels": {
    "F1_unsafe_overreach": 2,
    "F10_evidence_bypass": 1,
    "F4_missed_decisive_info": 13,
    "route_text_recognized_but_stop_label": 2,
    "content_covers_gold_next_step": 1,
    "F3_premature_commitment": 1,
    "technical_unparseable_json": 5,
    "F5_false_stop": 1,
    "F6_overcautious": 1,
    "technical_schema_violation": 1
  },
  "nccn": {
    "n": 30,
    "scorable_n": 24,
    "structured_decision_concordance_full_denominator": 0.23333333333333334,
    "structured_decision_concordance_scorable_only": 0.2916666666666667,
    "structured_decision_concordance_strict_full_denominator": 0.2,
    "structured_decision_concordance_strict_scorable_only": 0.25,
    "strict_unsafe_overreach_rate": 0.125,
    "premature_downstream_commitment_rate": 0.14285714285714285,
    "false_stop_rate": 0.25,
    "true_false_stop_rate": 0.25,
    "route_label_text_mismatch_rate": 0.5,
    "macro_by_question_type_concordance": 0.21388888888888888,
    "macro_by_question_type_concordance_strict": 0.1722222222222222,
    "by_question_type": {
      "evidence_resolution_request": {
        "n": 4,
        "structured_decision_concordance": 0.25,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.12179487179487178
      },
      "in_guide_handoff_resolution": {
        "n": 2,
        "structured_decision_concordance": 0.5,
        "structured_decision_concordance_strict": 0.5,
        "mean_content_score": 0.45545854057373414
      },
      "missing_information_request": {
        "n": 12,
        "structured_decision_concordance": 0.3333333333333333,
        "structured_decision_concordance_strict": 0.3333333333333333,
        "mean_content_score": 0.15529100529100529
      },
      "parallel_option_disambiguation": {
        "n": 5,
        "structured_decision_concordance": 0.2,
        "structured_decision_concordance_strict": 0.2,
        "mean_content_score": 0.22412358882947117
      },
      "unknown": {
        "n": 5,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.0
      },
      "upstream_routing_decision": {
        "n": 2,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.47448206960870715
      }
    }
  }
}
```

#### mtb-full (`mtb-full::MiniMax-M2.7`)
```json
{
  "n_total": 30,
  "n_scorable": 25,
  "json_parse_rate": 0.8333333333333334,
  "raw_schema_valid_rate": 0.7666666666666667,
  "repaired_schema_valid_rate": 0.8333333333333334,
  "schema_valid_rate": 0.8333333333333334,
  "strict_schema_valid_rate": 0.7666666666666667,
  "failure_labels": {
    "F1_unsafe_overreach": 11,
    "F10_evidence_bypass": 4,
    "F4_missed_decisive_info": 12,
    "F3_premature_commitment": 3,
    "F7_wrong_route": 3,
    "technical_unparseable_json": 5
  },
  "nccn": {
    "n": 30,
    "scorable_n": 25,
    "structured_decision_concordance_full_denominator": 0.1,
    "structured_decision_concordance_scorable_only": 0.12,
    "structured_decision_concordance_strict_full_denominator": 0.1,
    "structured_decision_concordance_strict_scorable_only": 0.12,
    "strict_unsafe_overreach_rate": 0.6470588235294118,
    "premature_downstream_commitment_rate": 0.6666666666666666,
    "false_stop_rate": 0.0,
    "true_false_stop_rate": 0.0,
    "route_label_text_mismatch_rate": 0.0,
    "macro_by_question_type_concordance": 0.13055555555555556,
    "macro_by_question_type_concordance_strict": 0.13055555555555556,
    "by_question_type": {
      "evidence_resolution_request": {
        "n": 5,
        "structured_decision_concordance": 0.2,
        "structured_decision_concordance_strict": 0.2,
        "mean_content_score": 0.2830769230769231
      },
      "in_guide_handoff_resolution": {
        "n": 2,
        "structured_decision_concordance": 0.5,
        "structured_decision_concordance_strict": 0.5,
        "mean_content_score": 0.32709651810368157
      },
      "missing_information_request": {
        "n": 12,
        "structured_decision_concordance": 0.08333333333333333,
        "structured_decision_concordance_strict": 0.08333333333333333,
        "mean_content_score": 0.1560185185185185
      },
      "parallel_option_disambiguation": {
        "n": 4,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.14835164835164835
      },
      "unknown": {
        "n": 5,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.0
      },
      "upstream_routing_decision": {
        "n": 2,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.06613143757867045
      }
    }
  }
}
```

#### opl-anchor (`opl-anchor::MiniMax-M2.7`)
```json
{
  "n_total": 30,
  "n_scorable": 25,
  "json_parse_rate": 0.8333333333333334,
  "raw_schema_valid_rate": 0.8,
  "repaired_schema_valid_rate": 0.8333333333333334,
  "schema_valid_rate": 0.8333333333333334,
  "strict_schema_valid_rate": 0.8,
  "failure_labels": {
    "F1_unsafe_overreach": 7,
    "F10_evidence_bypass": 1,
    "F4_missed_decisive_info": 12,
    "F3_premature_commitment": 4,
    "route_text_recognized_but_stop_label": 1,
    "content_covers_gold_next_step": 1,
    "technical_unparseable_json": 5,
    "F5_false_stop": 1,
    "F6_overcautious": 1,
    "F7_wrong_route": 1
  },
  "nccn": {
    "n": 30,
    "scorable_n": 25,
    "structured_decision_concordance_full_denominator": 0.16666666666666666,
    "structured_decision_concordance_scorable_only": 0.2,
    "structured_decision_concordance_strict_full_denominator": 0.13333333333333333,
    "structured_decision_concordance_strict_scorable_only": 0.16,
    "strict_unsafe_overreach_rate": 0.4375,
    "premature_downstream_commitment_rate": 0.5238095238095238,
    "false_stop_rate": 0.25,
    "true_false_stop_rate": 0.25,
    "route_label_text_mismatch_rate": 0.25,
    "macro_by_question_type_concordance": 0.16666666666666666,
    "macro_by_question_type_concordance_strict": 0.125,
    "by_question_type": {
      "evidence_resolution_request": {
        "n": 4,
        "structured_decision_concordance": 0.25,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.15512820512820513
      },
      "in_guide_handoff_resolution": {
        "n": 2,
        "structured_decision_concordance": 0.5,
        "structured_decision_concordance_strict": 0.5,
        "mean_content_score": 0.34955875752396404
      },
      "missing_information_request": {
        "n": 12,
        "structured_decision_concordance": 0.25,
        "structured_decision_concordance_strict": 0.25,
        "mean_content_score": 0.16492673992673992
      },
      "parallel_option_disambiguation": {
        "n": 5,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.2333333333333333
      },
      "unknown": {
        "n": 5,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.0
      },
      "upstream_routing_decision": {
        "n": 2,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.46143792201322387
      }
    }
  }
}
```

#### opl-full (`opl-full::MiniMax-M2.7`)
```json
{
  "n_total": 30,
  "n_scorable": 24,
  "json_parse_rate": 0.8333333333333334,
  "raw_schema_valid_rate": 0.7333333333333333,
  "repaired_schema_valid_rate": 0.8,
  "schema_valid_rate": 0.8,
  "strict_schema_valid_rate": 0.7333333333333333,
  "failure_labels": {
    "F4_missed_decisive_info": 12,
    "F3_premature_commitment": 5,
    "F1_unsafe_overreach": 6,
    "F10_evidence_bypass": 2,
    "technical_schema_violation": 1,
    "schema_invalid_extra_fields": 1,
    "route_text_recognized_but_stop_label": 3,
    "technical_unparseable_json": 5,
    "F7_wrong_route": 1
  },
  "nccn": {
    "n": 30,
    "scorable_n": 24,
    "structured_decision_concordance_full_denominator": 0.1,
    "structured_decision_concordance_scorable_only": 0.125,
    "structured_decision_concordance_strict_full_denominator": 0.1,
    "structured_decision_concordance_strict_scorable_only": 0.125,
    "strict_unsafe_overreach_rate": 0.375,
    "premature_downstream_commitment_rate": 0.5238095238095238,
    "false_stop_rate": 0.0,
    "true_false_stop_rate": 0.0,
    "route_label_text_mismatch_rate": 0.75,
    "macro_by_question_type_concordance": 0.19999999999999998,
    "macro_by_question_type_concordance_strict": 0.19999999999999998,
    "by_question_type": {
      "evidence_resolution_request": {
        "n": 5,
        "structured_decision_concordance": 0.2,
        "structured_decision_concordance_strict": 0.2,
        "mean_content_score": 0.30085470085470084
      },
      "in_guide_handoff_resolution": {
        "n": 2,
        "structured_decision_concordance": 0.5,
        "structured_decision_concordance_strict": 0.5,
        "mean_content_score": 0.377931761196034
      },
      "missing_information_request": {
        "n": 11,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.08658008658008659
      },
      "parallel_option_disambiguation": {
        "n": 5,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.2321266968325792
      },
      "unknown": {
        "n": 5,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.0
      },
      "upstream_routing_decision": {
        "n": 2,
        "structured_decision_concordance": 0.5,
        "structured_decision_concordance_strict": 0.5,
        "mean_content_score": 0.46745841078985195
      }
    }
  }
}
```
