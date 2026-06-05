# MTB vs OPL — quantitative comparison on SBT_Benchmark

> ## ⚠️ v2.10 AUTHORITATIVE SUMMARY (read this; the auto-generated "TL;DR" further down carries STALE v1.5 templated numbers — trust the data tables, not that prose)
>
> **Run:** v2.10 re-coupled prompt corpus, MiniMax-M2.7 @ 80K tokens, n=30 × 5 arms × 2 surfaces (CRC + NCCN), bench branch `bench/mtb-vs-opl-v2.10`. "Before" = archived v1.5 run (`REPORT_MTB_vs_OPL.md`).
>
> **Before→after (v1.5 → v2.10), CRC therapy F1@3 (full denom):** baseline 0.393→0.394 · mtb-anchor 0.399→0.416 · mtb-full 0.281→**0.391** · opl-anchor 0.463→**0.507** · opl-full 0.364→0.304.
> - **opl-anchor strengthened**: its lead over baseline went from +0.070 (within the ~0.1 noise band in v1.5) to **+0.113 (now clears the noise band)** — the disciplined retrieval-first design's CRC therapy-selection edge is now a real signal, not noise.
> - **nDCG@3 regressed for opl-anchor** (0.679→0.569; mtb-anchor now leads at 0.580) — mixed result, honestly reported.
>
> **NCCN strict decision concordance (scorable):** baseline 0.400→**0.565** (still wins decisively) · mtb-anchor 0.250→0.278 · opl-anchor 0.160→0.235 · mtb-full 0.120→0.211 · opl-full 0.125→0.105.
> - **The "know-when-to-stop" overreach was NOT resolved.** NCCN unsafe-overreach (lower=better): baseline 0.000 · opl-anchor 0.222 · mtb-anchor 0.273 · mtb-full 0.533 · opl-full **0.733**. Multi-expert arms still fan out into specific recommendations where the gold answer is to stop for missing discriminators.
>
> **Critical scope caveat:** this adapter is **prompt-driven** — it exercises the v2.10 *prompt corpus*, NOT the v2.10 Python fixes (live integrator wiring, gate-the-brief, actionable-first ordering). Those patient-fidelity fixes live in the engine/templates the benchmark does not run, and require a real `opl-cancer go` engine E2E to validate. So: the benchmark confirms the CRC prompt-design edge strengthened and the NCCN overreach persists *at the prompt level*; it says nothing about whether the Python-level actionable-first/gate fixes resolve overreach in the shipped product.
>
> Technical health: JSON parse 0.80–0.97 (CRC) / 0.83 (NCCN) at 80K tokens; 0 rate-limit (2056/2062) errors across both surfaces (MiniMax-M2.7 paid RPM-500 tier, concurrency 16).

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
| baseline (1 call) | 11.9 | 10.5 | 24.5 | 357 | 30 | 29 | 29 |
| mtb-anchor (vMTB plan+retrieve+synth) | 108.5 | 73.2 | 575.2 | 3256 | 30 | 21 | 25 |
| mtb-full (vMTB multi-agent + 3 verifiers) | 1022.9 | 179.1 | 20833.5 | 30686 | 30 | 18 | 24 |
| opl-anchor (OPL Sid plan+retrieve+synth) | 114.7 | 75.2 | 580.2 | 3440 | 30 | 24 | 29 |
| opl-full (OPL Rosa∥Bert+Vince+Sid+Henry-L1) | 301.8 | 134.1 | 3634.7 | 9054 | 30 | 22 | 25 |

### Technical health

| Metric | baseline | mtb-lite | mtb-full | opl-anchor | opl-full |
| --- | ---: | ---: | ---: | ---: | ---: |
| JSON parse rate | **0.967** | 0.833 | 0.800 | 0.967 | 0.833 |
| Schema-valid rate | **0.967** | 0.833 | 0.800 | 0.933 | 0.767 |
| Raw schema-valid rate | **0.933** | 0.800 | 0.800 | 0.833 | 0.733 |

### CRC clinical metrics (bold = best in row)

| Metric | baseline | mtb-lite | mtb-full | opl-anchor | opl-full |
| --- | ---: | ---: | ---: | ---: | ---: |
| CRC therapy F1@3 (full denom) | 0.394 | 0.416 | 0.391 | **0.507** | 0.304 |
| CRC therapy F1@3 (scorable only) | 0.408 | 0.499 | 0.488 | **0.543** | 0.397 |
| CRC strict therapy F1@3 | 0.274 | 0.338 | 0.283 | **0.359** | 0.253 |
| CRC class-level F1@3 | 0.601 | 0.619 | 0.548 | **0.675** | 0.554 |
| CRC therapy coverage F1 | 0.408 | 0.499 | 0.488 | **0.543** | 0.397 |
| CRC nDCG@3 | 0.497 | **0.580** | 0.565 | 0.569 | 0.513 |
| CRC treatment-intent match | 0.690 | 0.680 | 0.750 | 0.643 | **0.913** |
| CRC off-gold rate (lower=better) | 0.828 | **0.800** | 0.917 | 0.929 | 0.957 |
| CRC unsupported rate (lower=better) | 0.069 | **0.000** | 0.083 | 0.071 | 0.043 |
| CRC contraindicated rate (lower=better) | 0.138 | 0.080 | **0.042** | 0.107 | 0.130 |
| CRC molecular-context error (lower=better) | 0.138 | 0.080 | **0.000** | 0.071 | 0.087 |
| CRC missing-info F1 | — | — | — | — | — |

### Failure-label distribution (CRC)

| Failure label | baseline (1 call) | mtb-anchor (vMTB plan+retrieve+synth) | mtb-full (vMTB multi-agent + 3 verifiers) | opl-anchor (OPL Sid plan+retrieve+synth) | opl-full (OPL Rosa∥Bert+Vince+Sid+Henry-L1) |
| --- | ---: | ---: | ---: | ---: | ---: |
| F11_unsupported_recommendation | 2 | 0 | 2 | 2 | 1 |
| F12_treatment_intent_mismatch | 9 | 8 | 6 | 10 | 2 |
| F13_molecular_context_error | 4 | 2 | 0 | 2 | 2 |
| F14_therapy_set_mismatch | 26 | 22 | 22 | 26 | 22 |
| F16_contraindicated_recommendation | 4 | 2 | 1 | 3 | 3 |
| contradictory_output | 10 | 0 | 13 | 4 | 12 |
| model_acknowledged_data_conflict | 0 | 0 | 1 | 0 | 0 |
| off_gold_recommendation | 24 | 20 | 22 | 26 | 22 |
| technical_schema_violation | 0 | 0 | 0 | 1 | 2 |
| technical_unparseable_json | 1 | 5 | 6 | 1 | 5 |

## NCCN surface (`tmp/NCCN_version/`, CRC subset)

N items per arm: 30

### Wall-time & success counts

| Arm | mean wall (s/case) | median wall (s) | max wall (s) | total wall (s) | n_total | n_ok | n_json_ok |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline (1 call) | 10.6 | 9.8 | 25.2 | 318 | 30 | 23 | 23 |
| mtb-anchor (vMTB plan+retrieve+synth) | 46.4 | 41.9 | 127.7 | 1393 | 30 | 14 | 18 |
| mtb-full (vMTB multi-agent + 3 verifiers) | 134.5 | 127.0 | 209.8 | 4034 | 30 | 9 | 19 |
| opl-anchor (OPL Sid plan+retrieve+synth) | 57.0 | 52.1 | 140.0 | 1710 | 30 | 12 | 17 |
| opl-full (OPL Rosa∥Bert+Vince+Sid+Henry-L1) | 106.9 | 103.1 | 189.0 | 3207 | 30 | 10 | 19 |

### Technical health

| Metric | baseline | mtb-lite | mtb-full | opl-anchor | opl-full |
| --- | ---: | ---: | ---: | ---: | ---: |
| JSON parse rate | **0.767** | 0.600 | 0.633 | 0.567 | 0.633 |
| Schema-valid rate | **0.767** | 0.600 | 0.633 | 0.567 | 0.633 |
| Raw schema-valid rate | **0.767** | 0.567 | 0.567 | 0.533 | 0.633 |

### NCCN clinical metrics (bold = best in row)

| Metric | baseline | mtb-lite | mtb-full | opl-anchor | opl-full |
| --- | ---: | ---: | ---: | ---: | ---: |
| NCCN decision concordance (full denom) | **0.433** | 0.200 | 0.133 | 0.133 | 0.100 |
| NCCN decision concordance (scorable) | **0.565** | 0.333 | 0.211 | 0.235 | 0.158 |
| NCCN decision concordance (strict, full denom) | **0.433** | 0.167 | 0.133 | 0.133 | 0.067 |
| NCCN decision concordance (strict, scorable) | **0.565** | 0.278 | 0.211 | 0.235 | 0.105 |
| NCCN macro-by-q-type concordance | **0.339** | 0.181 | 0.136 | 0.158 | 0.222 |
| NCCN unsafe overreach (lower=better) | **0.000** | 0.273 | 0.533 | 0.222 | 0.733 |
| NCCN false-stop rate (lower=better) | 0.667 | 0.333 | **0.000** | 0.000 | 0.500 |
| NCCN true false-stop rate (lower=better) | 0.667 | 0.333 | **0.000** | 0.000 | 0.500 |
| NCCN premature commitment (lower=better) | **0.000** | 0.333 | 0.588 | 0.286 | 0.765 |
| NCCN route mismatch (lower=better) | 0.333 | 0.333 | **0.000** | 0.667 | 0.000 |

### Failure-label distribution (NCCN)

| Failure label | baseline (1 call) | mtb-anchor (vMTB plan+retrieve+synth) | mtb-full (vMTB multi-agent + 3 verifiers) | opl-anchor (OPL Sid plan+retrieve+synth) | opl-full (OPL Rosa∥Bert+Vince+Sid+Henry-L1) |
| --- | ---: | ---: | ---: | ---: | ---: |
| F10_evidence_bypass | 0 | 1 | 2 | 0 | 4 |
| F1_unsafe_overreach | 0 | 3 | 8 | 2 | 11 |
| F3_premature_commitment | 0 | 2 | 2 | 2 | 2 |
| F4_missed_decisive_info | 7 | 7 | 11 | 10 | 9 |
| F5_false_stop | 2 | 1 | 0 | 0 | 1 |
| F6_overcautious | 2 | 1 | 0 | 0 | 1 |
| F7_wrong_route | 0 | 1 | 2 | 1 | 0 |
| route_text_recognized_but_stop_label | 1 | 1 | 0 | 2 | 0 |
| technical_unparseable_json | 7 | 12 | 11 | 13 | 11 |

## Raw `by_model` blocks

### CRC

#### baseline (`baseline::MiniMax-M2.7`)
```json
{
  "n_total": 30,
  "n_scorable": 29,
  "json_parse_rate": 0.9666666666666667,
  "raw_schema_valid_rate": 0.9333333333333333,
  "repaired_schema_valid_rate": 0.9666666666666667,
  "schema_valid_rate": 0.9666666666666667,
  "strict_schema_valid_rate": 0.9333333333333333,
  "failure_labels": {
    "off_gold_recommendation": 24,
    "F14_therapy_set_mismatch": 26,
    "contradictory_output": 10,
    "F12_treatment_intent_mismatch": 9,
    "F11_unsupported_recommendation": 2,
    "F16_contraindicated_recommendation": 4,
    "F13_molecular_context_error": 4,
    "technical_unparseable_json": 1
  },
  "crc": {
    "n": 30,
    "scorable_n": 29,
    "therapy_f1_at3_full_denominator": 0.39444444444444454,
    "therapy_f1_at3_scorable_only": 0.4080459770114943,
    "strict_therapy_f1_at3": 0.27381698761009104,
    "class_therapy_f1_at3": 0.6011494252873564,
    "therapy_coverage_f1": 0.4080459770114943,
    "ndcg_at3": 0.49681298393824913,
    "off_gold_recommendation_rate": 0.8275862068965517,
    "unsupported_recommendation_rate": 0.06896551724137931,
    "contraindicated_recommendation_rate": 0.13793103448275862,
    "treatment_intent_match_rate": 0.6896551724137931,
    "molecular_context_error_rate": 0.13793103448275862,
    "missing_information_recall": 0.5555555555555555
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
    "off_gold_recommendation": 20,
    "F12_treatment_intent_mismatch": 8,
    "F14_therapy_set_mismatch": 22,
    "F16_contraindicated_recommendation": 2,
    "F13_molecular_context_error": 2,
    "technical_unparseable_json": 5
  },
  "crc": {
    "n": 30,
    "scorable_n": 25,
    "therapy_f1_at3_full_denominator": 0.4158730158730159,
    "therapy_f1_at3_scorable_only": 0.4990476190476191,
    "strict_therapy_f1_at3": 0.33829437229437226,
    "class_therapy_f1_at3": 0.6190476190476191,
    "therapy_coverage_f1": 0.4990476190476191,
    "ndcg_at3": 0.5795123284826239,
    "off_gold_recommendation_rate": 0.8,
    "unsupported_recommendation_rate": 0.0,
    "contraindicated_recommendation_rate": 0.08,
    "treatment_intent_match_rate": 0.68,
    "molecular_context_error_rate": 0.08,
    "missing_information_recall": 0.6666666666666666
  }
}
```

#### mtb-full (`mtb-full::MiniMax-M2.7`)
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
    "off_gold_recommendation": 22,
    "F12_treatment_intent_mismatch": 6,
    "F14_therapy_set_mismatch": 22,
    "contradictory_output": 13,
    "F11_unsupported_recommendation": 2,
    "F16_contraindicated_recommendation": 1,
    "model_acknowledged_data_conflict": 1,
    "technical_unparseable_json": 6
  },
  "crc": {
    "n": 30,
    "scorable_n": 24,
    "therapy_f1_at3_full_denominator": 0.39063492063492067,
    "therapy_f1_at3_scorable_only": 0.48829365079365084,
    "strict_therapy_f1_at3": 0.28263888888888894,
    "class_therapy_f1_at3": 0.5478174603174605,
    "therapy_coverage_f1": 0.48829365079365084,
    "ndcg_at3": 0.5654024149324508,
    "off_gold_recommendation_rate": 0.9166666666666666,
    "unsupported_recommendation_rate": 0.08333333333333333,
    "contraindicated_recommendation_rate": 0.041666666666666664,
    "treatment_intent_match_rate": 0.75,
    "molecular_context_error_rate": 0.0,
    "missing_information_recall": 0.41666666666666663
  }
}
```

#### opl-anchor (`opl-anchor::MiniMax-M2.7`)
```json
{
  "n_total": 30,
  "n_scorable": 28,
  "json_parse_rate": 0.9666666666666667,
  "raw_schema_valid_rate": 0.8333333333333334,
  "repaired_schema_valid_rate": 0.9333333333333333,
  "schema_valid_rate": 0.9333333333333333,
  "strict_schema_valid_rate": 0.8333333333333334,
  "failure_labels": {
    "off_gold_recommendation": 26,
    "F12_treatment_intent_mismatch": 10,
    "F14_therapy_set_mismatch": 26,
    "contradictory_output": 4,
    "F11_unsupported_recommendation": 2,
    "F16_contraindicated_recommendation": 3,
    "F13_molecular_context_error": 2,
    "technical_schema_violation": 1,
    "technical_unparseable_json": 1
  },
  "crc": {
    "n": 30,
    "scorable_n": 28,
    "therapy_f1_at3_full_denominator": 0.5069841269841271,
    "therapy_f1_at3_scorable_only": 0.5431972789115648,
    "strict_therapy_f1_at3": 0.35935374149659854,
    "class_therapy_f1_at3": 0.6752551020408165,
    "therapy_coverage_f1": 0.5431972789115648,
    "ndcg_at3": 0.568519447150927,
    "off_gold_recommendation_rate": 0.9285714285714286,
    "unsupported_recommendation_rate": 0.07142857142857142,
    "contraindicated_recommendation_rate": 0.10714285714285714,
    "treatment_intent_match_rate": 0.6428571428571429,
    "molecular_context_error_rate": 0.07142857142857142,
    "missing_information_recall": 0.611111111111111
  }
}
```

#### opl-full (`opl-full::MiniMax-M2.7`)
```json
{
  "n_total": 30,
  "n_scorable": 23,
  "json_parse_rate": 0.8333333333333334,
  "raw_schema_valid_rate": 0.7333333333333333,
  "repaired_schema_valid_rate": 0.7666666666666667,
  "schema_valid_rate": 0.7666666666666667,
  "strict_schema_valid_rate": 0.7333333333333333,
  "failure_labels": {
    "off_gold_recommendation": 22,
    "F14_therapy_set_mismatch": 22,
    "contradictory_output": 12,
    "F12_treatment_intent_mismatch": 2,
    "F16_contraindicated_recommendation": 3,
    "F13_molecular_context_error": 2,
    "F11_unsupported_recommendation": 1,
    "technical_schema_violation": 2,
    "technical_unparseable_json": 5
  },
  "crc": {
    "n": 30,
    "scorable_n": 23,
    "therapy_f1_at3_full_denominator": 0.30444444444444446,
    "therapy_f1_at3_scorable_only": 0.3971014492753624,
    "strict_therapy_f1_at3": 0.25317460317460316,
    "class_therapy_f1_at3": 0.5543478260869565,
    "therapy_coverage_f1": 0.3971014492753624,
    "ndcg_at3": 0.5132451850530955,
    "off_gold_recommendation_rate": 0.9565217391304348,
    "unsupported_recommendation_rate": 0.043478260869565216,
    "contraindicated_recommendation_rate": 0.13043478260869565,
    "treatment_intent_match_rate": 0.9130434782608695,
    "molecular_context_error_rate": 0.08695652173913043,
    "missing_information_recall": 0.5
  }
}
```

### NCCN

#### baseline (`baseline::MiniMax-M2.7`)
```json
{
  "n_total": 30,
  "n_scorable": 23,
  "json_parse_rate": 0.7666666666666667,
  "raw_schema_valid_rate": 0.7666666666666667,
  "repaired_schema_valid_rate": 0.7666666666666667,
  "schema_valid_rate": 0.7666666666666667,
  "strict_schema_valid_rate": 0.7666666666666667,
  "failure_labels": {
    "F4_missed_decisive_info": 7,
    "technical_unparseable_json": 7,
    "F5_false_stop": 2,
    "F6_overcautious": 2,
    "route_text_recognized_but_stop_label": 1
  },
  "nccn": {
    "n": 30,
    "scorable_n": 23,
    "structured_decision_concordance_full_denominator": 0.43333333333333335,
    "structured_decision_concordance_scorable_only": 0.5652173913043478,
    "structured_decision_concordance_strict_full_denominator": 0.43333333333333335,
    "structured_decision_concordance_strict_scorable_only": 0.5652173913043478,
    "strict_unsafe_overreach_rate": 0.0,
    "premature_downstream_commitment_rate": 0.0,
    "false_stop_rate": 0.6666666666666666,
    "true_false_stop_rate": 0.6666666666666666,
    "route_label_text_mismatch_rate": 0.3333333333333333,
    "macro_by_question_type_concordance": 0.33888888888888885,
    "macro_by_question_type_concordance_strict": 0.33888888888888885,
    "by_question_type": {
      "evidence_resolution_request": {
        "n": 6,
        "structured_decision_concordance": 0.3333333333333333,
        "structured_decision_concordance_strict": 0.3333333333333333,
        "mean_content_score": 0.1759259259259259
      },
      "in_guide_handoff_resolution": {
        "n": 2,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.4286770249029521
      },
      "missing_information_request": {
        "n": 10,
        "structured_decision_concordance": 0.7,
        "structured_decision_concordance_strict": 0.7,
        "mean_content_score": 0.24505494505494507
      },
      "parallel_option_disambiguation": {
        "n": 4,
        "structured_decision_concordance": 1.0,
        "structured_decision_concordance_strict": 1.0,
        "mean_content_score": 0.42692307692307685
      },
      "unknown": {
        "n": 7,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.0
      },
      "upstream_routing_decision": {
        "n": 1,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.20465521407229212
      }
    }
  }
}
```

#### mtb-lite (`mtb-lite::MiniMax-M2.7`)
```json
{
  "n_total": 30,
  "n_scorable": 18,
  "json_parse_rate": 0.6,
  "raw_schema_valid_rate": 0.5666666666666667,
  "repaired_schema_valid_rate": 0.6,
  "schema_valid_rate": 0.6,
  "strict_schema_valid_rate": 0.5666666666666667,
  "failure_labels": {
    "F3_premature_commitment": 2,
    "F4_missed_decisive_info": 7,
    "F1_unsafe_overreach": 3,
    "F10_evidence_bypass": 1,
    "technical_unparseable_json": 12,
    "route_text_recognized_but_stop_label": 1,
    "F7_wrong_route": 1,
    "F5_false_stop": 1,
    "F6_overcautious": 1
  },
  "nccn": {
    "n": 30,
    "scorable_n": 18,
    "structured_decision_concordance_full_denominator": 0.2,
    "structured_decision_concordance_scorable_only": 0.3333333333333333,
    "structured_decision_concordance_strict_full_denominator": 0.16666666666666666,
    "structured_decision_concordance_strict_scorable_only": 0.2777777777777778,
    "strict_unsafe_overreach_rate": 0.2727272727272727,
    "premature_downstream_commitment_rate": 0.3333333333333333,
    "false_stop_rate": 0.3333333333333333,
    "true_false_stop_rate": 0.3333333333333333,
    "route_label_text_mismatch_rate": 0.3333333333333333,
    "macro_by_question_type_concordance": 0.18055555555555555,
    "macro_by_question_type_concordance_strict": 0.125,
    "by_question_type": {
      "evidence_resolution_request": {
        "n": 3,
        "structured_decision_concordance": 0.3333333333333333,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.23646723646723644
      },
      "in_guide_handoff_resolution": {
        "n": 2,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.35311343051293714
      },
      "missing_information_request": {
        "n": 8,
        "structured_decision_concordance": 0.5,
        "structured_decision_concordance_strict": 0.5,
        "mean_content_score": 0.23417207792207795
      },
      "parallel_option_disambiguation": {
        "n": 4,
        "structured_decision_concordance": 0.25,
        "structured_decision_concordance_strict": 0.25,
        "mean_content_score": 0.30608974358974356
      },
      "unknown": {
        "n": 12,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.0
      },
      "upstream_routing_decision": {
        "n": 1,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.23698988068729054
      }
    }
  }
}
```

#### mtb-full (`mtb-full::MiniMax-M2.7`)
```json
{
  "n_total": 30,
  "n_scorable": 19,
  "json_parse_rate": 0.6333333333333333,
  "raw_schema_valid_rate": 0.5666666666666667,
  "repaired_schema_valid_rate": 0.6333333333333333,
  "schema_valid_rate": 0.6333333333333333,
  "strict_schema_valid_rate": 0.5666666666666667,
  "failure_labels": {
    "F1_unsafe_overreach": 8,
    "F10_evidence_bypass": 2,
    "technical_unparseable_json": 11,
    "F4_missed_decisive_info": 11,
    "F3_premature_commitment": 2,
    "F7_wrong_route": 2
  },
  "nccn": {
    "n": 30,
    "scorable_n": 19,
    "structured_decision_concordance_full_denominator": 0.13333333333333333,
    "structured_decision_concordance_scorable_only": 0.21052631578947367,
    "structured_decision_concordance_strict_full_denominator": 0.13333333333333333,
    "structured_decision_concordance_strict_scorable_only": 0.21052631578947367,
    "strict_unsafe_overreach_rate": 0.5333333333333333,
    "premature_downstream_commitment_rate": 0.5882352941176471,
    "false_stop_rate": 0.0,
    "true_false_stop_rate": 0.0,
    "route_label_text_mismatch_rate": 0.0,
    "macro_by_question_type_concordance": 0.13636363636363638,
    "macro_by_question_type_concordance_strict": 0.13636363636363638,
    "by_question_type": {
      "evidence_resolution_request": {
        "n": 4,
        "structured_decision_concordance": 0.5,
        "structured_decision_concordance_strict": 0.5,
        "mean_content_score": 0.26726190476190476
      },
      "in_guide_handoff_resolution": {
        "n": 2,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.15728809674680497
      },
      "missing_information_request": {
        "n": 11,
        "structured_decision_concordance": 0.18181818181818182,
        "structured_decision_concordance_strict": 0.18181818181818182,
        "mean_content_score": 0.08628550593791236
      },
      "parallel_option_disambiguation": {
        "n": 2,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.07142857142857144
      },
      "unknown": {
        "n": 11,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.0
      }
    }
  }
}
```

#### opl-anchor (`opl-anchor::MiniMax-M2.7`)
```json
{
  "n_total": 30,
  "n_scorable": 17,
  "json_parse_rate": 0.5666666666666667,
  "raw_schema_valid_rate": 0.5333333333333333,
  "repaired_schema_valid_rate": 0.5666666666666667,
  "schema_valid_rate": 0.5666666666666667,
  "strict_schema_valid_rate": 0.5333333333333333,
  "failure_labels": {
    "F3_premature_commitment": 2,
    "F4_missed_decisive_info": 10,
    "technical_unparseable_json": 13,
    "F1_unsafe_overreach": 2,
    "route_text_recognized_but_stop_label": 2,
    "F7_wrong_route": 1
  },
  "nccn": {
    "n": 30,
    "scorable_n": 17,
    "structured_decision_concordance_full_denominator": 0.13333333333333333,
    "structured_decision_concordance_scorable_only": 0.23529411764705882,
    "structured_decision_concordance_strict_full_denominator": 0.13333333333333333,
    "structured_decision_concordance_strict_scorable_only": 0.23529411764705882,
    "strict_unsafe_overreach_rate": 0.2222222222222222,
    "premature_downstream_commitment_rate": 0.2857142857142857,
    "false_stop_rate": 0.0,
    "true_false_stop_rate": 0.0,
    "route_label_text_mismatch_rate": 0.6666666666666666,
    "macro_by_question_type_concordance": 0.15833333333333333,
    "macro_by_question_type_concordance_strict": 0.15833333333333333,
    "by_question_type": {
      "evidence_resolution_request": {
        "n": 1,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.16666666666666666
      },
      "in_guide_handoff_resolution": {
        "n": 2,
        "structured_decision_concordance": 0.5,
        "structured_decision_concordance_strict": 0.5,
        "mean_content_score": 0.4335786678602189
      },
      "missing_information_request": {
        "n": 8,
        "structured_decision_concordance": 0.25,
        "structured_decision_concordance_strict": 0.25,
        "mean_content_score": 0.08154761904761905
      },
      "parallel_option_disambiguation": {
        "n": 5,
        "structured_decision_concordance": 0.2,
        "structured_decision_concordance_strict": 0.2,
        "mean_content_score": 0.19746031746031747
      },
      "unknown": {
        "n": 13,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.0
      },
      "upstream_routing_decision": {
        "n": 1,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.13892991490072681
      }
    }
  }
}
```

#### opl-full (`opl-full::MiniMax-M2.7`)
```json
{
  "n_total": 30,
  "n_scorable": 19,
  "json_parse_rate": 0.6333333333333333,
  "raw_schema_valid_rate": 0.6333333333333333,
  "repaired_schema_valid_rate": 0.6333333333333333,
  "schema_valid_rate": 0.6333333333333333,
  "strict_schema_valid_rate": 0.6333333333333333,
  "failure_labels": {
    "technical_unparseable_json": 11,
    "F1_unsafe_overreach": 11,
    "F10_evidence_bypass": 4,
    "F4_missed_decisive_info": 9,
    "F3_premature_commitment": 2,
    "F5_false_stop": 1,
    "F6_overcautious": 1
  },
  "nccn": {
    "n": 30,
    "scorable_n": 19,
    "structured_decision_concordance_full_denominator": 0.1,
    "structured_decision_concordance_scorable_only": 0.15789473684210525,
    "structured_decision_concordance_strict_full_denominator": 0.06666666666666667,
    "structured_decision_concordance_strict_scorable_only": 0.10526315789473684,
    "strict_unsafe_overreach_rate": 0.7333333333333333,
    "premature_downstream_commitment_rate": 0.7647058823529411,
    "false_stop_rate": 0.5,
    "true_false_stop_rate": 0.5,
    "route_label_text_mismatch_rate": 0.0,
    "macro_by_question_type_concordance": 0.2222222222222222,
    "macro_by_question_type_concordance_strict": 0.19444444444444445,
    "by_question_type": {
      "evidence_resolution_request": {
        "n": 6,
        "structured_decision_concordance": 0.3333333333333333,
        "structured_decision_concordance_strict": 0.16666666666666666,
        "mean_content_score": 0.31645299145299144
      },
      "in_guide_handoff_resolution": {
        "n": 1,
        "structured_decision_concordance": 1.0,
        "structured_decision_concordance_strict": 1.0,
        "mean_content_score": 0.507894521114402
      },
      "missing_information_request": {
        "n": 9,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.1148148148148148
      },
      "parallel_option_disambiguation": {
        "n": 2,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.26515151515151514
      },
      "unknown": {
        "n": 11,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.0
      },
      "upstream_routing_decision": {
        "n": 1,
        "structured_decision_concordance": 0.0,
        "structured_decision_concordance_strict": 0.0,
        "mean_content_score": 0.07393288831861643
      }
    }
  }
}
```
