# OPL-Cancer benchmark adapter (`feat/benchmark-adapter`)

Quantitative comparison of the **OPL for Cancer** 5-Wave / 18-expert / 29-integrator framework against:

1. A 1-call LLM **baseline** (no framework, no retrieval).
2. The sister **cancerdao-vmtb** multi-agent framework (`mtb-anchor` + `mtb-full`).

…on the public `SBT_Benchmark` CRC + NCCN surfaces. Same model, same OpenRouter HTTP path, same retrieval substrate (PubMed E-utilities + NCCN PageIndex tree-search), same output schemas. The only swap between `mtb-*` and `opl-*` arms is the prompt corpus (`cancerdao-vmtb/scripts/config/prompts/` → `opl-cancer/prompts/`).

> **Status:** exploratory pilot work. This branch is **not** intended to merge into `main` until (a) Henry verifier wiring is rebuilt against the real `validators/gates/` Python registry rather than the LLM-orchestrated stand-in used here, and (b) a `baseline-pro` ablation (1-call LLM + same retrieval bundle) is added to isolate framework value from retrieval value.

## Layout

```
benchmark/
├── README.md                         (you are here)
├── .gitignore                        (ignores runs/, keeps reports/)
├── adapter/
│   ├── README.md                     (per-file roles + arm catalog)
│   ├── mtb_lite.py                   (shared baseline + OpenRouter client + PubMed)
│   ├── mtb_full.py                   (vMTB multi-agent — pathologist/geneticist/oncologist/chair/verifiers)
│   ├── nccn_pageindex.py             (NCCN PageIndex tree-search RAG)
│   ├── opl_full.py                   (OPL — Sid plan / Rosa∥Bert / Vince / Sid delivery / Henry L1)
│   ├── run_benchmark.py              (CLI: arms × cases → raw_outputs.jsonl)
│   ├── merge_runs.py                 (combine multiple raw_outputs.jsonl with arm rename)
│   └── compare_scores.py             (summary.json → N-arm comparison markdown table)
└── reports/
    └── REPORT_MTB_vs_OPL.md          (generated after the pilot run)
```

## Quick start

```bash
# Prerequisites:
#   1. mtb-bench checkout (provides SBT_Benchmark dataset + score_model_outputs.py)
#   2. vmtb-skill install (provides NCCN PageIndex artifacts + vMTB prompts for mtb-* arms)
#   3. LLM key: MiniMax M2 (recommended — see ~/.claude memory reference_minimax_llm.md)
#      or OpenRouter (gpt-4o-mini works for compat with the vmtb-skill pilot)

export OPENROUTER_BASE_URL=https://api.minimaxi.com/v1     # MiniMax M2
export OPENROUTER_API_KEY=$MINIMAX_API_KEY
export OPENROUTER_MAX_TOKENS_FLOOR=8000                    # reasoning-model floor
export OPENROUTER_MAX_RETRIES=3                            # transient-network resilience

# Run CRC surface (5 arms, 30 cases)
python benchmark/adapter/run_benchmark.py \
    --benchmark-root /path/to/mtb-bench/SBT_Benchmark \
    --out-dir runs/mtb_vs_opl_n30_crc \
    --model MiniMax-M2 \
    --n 30 \
    --arms baseline,mtb,mtb-full,opl-anchor,opl-full \
    --concurrency 3 \
    --surface crc_case

# Run NCCN surface (same arm set, separate output)
python benchmark/adapter/run_benchmark.py \
    --benchmark-root /path/to/mtb-bench/SBT_Benchmark \
    --out-dir runs/mtb_vs_opl_n30_nccn \
    --model MiniMax-M2 \
    --n 30 \
    --arms baseline,mtb,mtb-full,opl-anchor,opl-full \
    --concurrency 3 \
    --surface nccn_structured

# Score (uses the SBT_Benchmark deterministic scorer v2.5 — gold standard is private)
python /path/to/mtb-bench/SBT_Benchmark/scripts/score_model_outputs.py \
    runs/mtb_vs_opl_n30_crc/raw_outputs.jsonl \
    --out-dir runs/mtb_vs_opl_n30_crc/scores

# Compare arms side-by-side
python benchmark/adapter/compare_scores.py \
    --scores-dir runs/mtb_vs_opl_n30_crc/scores \
    --out runs/mtb_vs_opl_n30_crc/REPORT.md
```

## The five arms

| Arm           | LLM calls / case | Pipeline                                                                                          |
| ------------- | ---------------: | ------------------------------------------------------------------------------------------------- |
| `baseline`    |              ~1  | 1 LLM call. No retrieval, no agents.                                                              |
| `mtb` (anchor)|              ~3  | vMTB planner + PubMed + NCCN PageIndex + 1-call synth → CRC/NCCN schema.                          |
| `mtb-full`    |             ~10  | vMTB pathologist ∥ geneticist → oncologist → chair → schema-shape → 3 verifiers (facts/guides/safety). Reshape on flag. |
| `opl-anchor`  |              ~3  | OPL Sid planner + PubMed + NCCN PageIndex + Sid 1-call synth → CRC/NCCN schema.                   |
| `opl-full`    |              ~8  | OPL Sid plan → Rosa ∥ Bert → Vince → Sid delivery → schema-shape → Henry L1 mechanical-gates audit. Reshape on flag. |

**Arms within a framework share their planner / retrieval substrate** — the contrast between `mtb-full` vs `mtb` (and `opl-full` vs `opl-anchor`) isolates the multi-agent contribution; the contrast between `mtb-full` vs `opl-full` isolates the framework's prompt + role design at matched retrieval.

## How OPL is adapted

OPL's production stack is **claude-native** — the SKILL.md script asks Claude Code's main thread to be the executor LLM, and ADR-0002 forbids the Python CLI subcommands from dispatching child agents. That's incompatible with a per-case batch benchmark where the harness needs to drive thousands of synchronous LLM calls.

So this adapter does **not** instantiate `Wave1Runner` / `Wave2Runner` / `Wave3Runner` / `Wave4Runner`. Instead, it loads the actual OPL prompts from `opl-cancer/prompts/` (Sid intent parser + Sid delivery, Rosa/Bert/Vince personas, the `pathology_interpretation` / `molecular_ngs_interpretation` / `treatment_line_recommendation` task prompts, Henry's L1 mechanical-gates audit prompt) and stitches them into the same 7-stage pipeline shape as `mtb_full.py`. The output is therefore comparable to vMTB on identical retrieval + schema substrates.

**Trade-off you must read before interpreting results:**

- ✅ Apples-to-apples comparison: same model, same OpenRouter HTTP path, same PubMed + NCCN PageIndex, same CRC/NCCN output schemas, same retry policy.
- ⚠️ This is **not OPL's production form**. OPL Wave 2 (hypothesis tournament with Co-Sci Elo + Robin reflections), Wave 3 (data-evidence via bixbench docker / native jupyter + TCGA / cBioPortal / GEPIA3), Wave 4 (hypothesis validation), and the 27 deterministic gates in `validators/gates/` are absent. The "Henry L1" verifier in this adapter is LLM-orchestrated (one prompt running the gate rubric in natural language) — not the real deterministic Python registry.
- ⚠️ Similarly, this is not vMTB's production form — see the sibling `vmtb-skill@feat/benchmark-adapter` README for that branch's known caveats.

## Findings

Will be populated in `reports/REPORT_MTB_vs_OPL.md` after the pilot run completes. The benchmark's gold standard is private (pre-publication of the SBT_Benchmark paper); the scorer summary numbers are reproducible from your own gold file.

## See also

- Sister branch on the vMTB side: <https://github.com/CancerDAO/vmtb-skill/tree/feat/benchmark-adapter>
- Source of the adapter harness: `<mtb-bench>/adapter/` — this benchmark is a direct port of that, with `opl_full.py` added.
- SBT_Benchmark scorer + dataset: `<mtb-bench>/SBT_Benchmark/scripts/score_model_outputs.py` (gold standard is private).
