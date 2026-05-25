# OPL-Cancer benchmark adapter — file roles

A self-contained Python adapter that drives 5 arms × 2 surfaces of the
`SBT_Benchmark` suite. No external Python dependencies beyond the standard
library + (optional) `PyPDF2` for NCCN PageIndex re-extraction.

## Files

| File                  | Role                                                                                                                                                              |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `mtb_lite.py`         | Shared layer: `openrouter_chat` (with reasoning-model token floor + retry), `extract_json` (`<think>`-aware), PubMed E-utilities client, CRC/NCCN response templates, **`run_baseline` / `run_mtb` / `run_baseline_nccn` / `run_mtb_nccn`** entry points. |
| `mtb_full.py`         | Loads the 8 real vmtb-skill prompts (`pathologist_prompt.txt`, `geneticist_prompt.txt`, `oncologist_prompt.txt`, `chair_prompt.txt`, 3× `verifier_*_prompt.txt`, `plan_agent_prompt.txt`) and runs the 7-stage vMTB multi-agent pipeline. **`run_full_mtb` / `run_full_mtb_nccn`** entry points. Reshape-on-verifier-flag loop is one pass deep. |
| `nccn_pageindex.py`   | LLM tree-search RAG over the locally-built NCCN PageIndex (结肠癌 + 直肠癌). Two-tier path default: sibling `vmtb-skill/skills/.../references/pageindex` first, then `~/.claude/skills/vMTB/...` fallback. |
| `opl_full.py`         | Loads OPL's actual prompts (`pi/intent_parser.md`, `pi/delivery.md`, Rosa/Bert/Vince personas, `tasks/pathology_interpretation.md`, `tasks/molecular_ngs_interpretation.md`, `tasks/treatment_line_recommendation.md`, `auditor/l1_mechanical_gates.md`) and runs the parallel 7-stage OPL pipeline. **`run_opl_anchor` / `run_opl_full` / `run_opl_anchor_nccn` / `run_opl_full_nccn`** entry points. |
| `run_benchmark.py`    | CLI driver. Reads `SBT_Benchmark/tmp/{Case_version,NCCN_version}/input.jsonl`, fans arms × items over a `ThreadPoolExecutor`, writes `raw_outputs.jsonl` + `manifest.json` to `--out-dir`. |
| `merge_runs.py`       | Combine multiple `raw_outputs.jsonl` files with optional per-arm model-tag rewrite (e.g. when you've split a run across resumes or want to re-tag historical `mtb` outputs as `mtb-anchor`). |
| `compare_scores.py`   | Read SBT scorer's `summary.json` and emit a markdown N-arm comparison table with the key CRC/NCCN metrics + failure-label distribution. |

## Arm catalog (registered in `run_benchmark.run_one`)

### `--surface crc_case`

| Arm            | Function                                       | Model tag                |
| -------------- | ---------------------------------------------- | ------------------------ |
| `baseline`     | `mtb_lite.run_baseline`                        | `baseline::<model>`      |
| `mtb`          | `mtb_lite.run_mtb` (planner + retrieve + synth)| `mtb-lite::<model>`      |
| `mtb-full`     | `mtb_full.run_full_mtb`                        | `mtb-full::<model>`      |
| `opl-anchor`   | `opl_full.run_opl_anchor`                      | `opl-anchor::<model>`    |
| `opl-full`     | `opl_full.run_opl_full`                        | `opl-full::<model>`      |

### `--surface nccn_structured`

| Arm            | Function                                                              | Model tag                |
| -------------- | --------------------------------------------------------------------- | ------------------------ |
| `baseline`     | `mtb_lite.run_baseline_nccn`                                          | `baseline::<model>`      |
| `mtb`          | `mtb_lite.run_mtb_nccn`                                               | `mtb-lite::<model>`      |
| `mtb-full`     | `mtb_full.run_full_mtb_nccn`                                          | `mtb-full::<model>`      |
| `opl-anchor`   | `opl_full.run_opl_anchor_nccn`                                        | `opl-anchor::<model>`    |
| `opl-full`     | `opl_full.run_opl_full_nccn`                                          | `opl-full::<model>`      |

## Environment variables

| Var                            | Default                                                       | Purpose                                                                            |
| ------------------------------ | ------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `OPENROUTER_API_KEY`           | (required)                                                    | Bearer token for the LLM endpoint.                                                 |
| `OPENROUTER_BASE_URL`          | `https://openrouter.ai/api/v1`                                | OpenAI-compatible endpoint. Override to MiniMax (`api.minimaxi.com/v1`), DeepSeek, etc. |
| `OPENROUTER_MAX_TOKENS_FLOOR`  | `0`                                                           | Lift every per-call `max_tokens` to this floor. Use **8000+** with reasoning models (M2, deepseek-r1). |
| `OPENROUTER_MAX_RETRIES`       | `3`                                                           | Retry transient `URLError` / 429 / 5xx with exponential backoff (capped at 30s).  |
| `OPENROUTER_HTTP_REFERER`      | (unset)                                                       | Forwarded as `HTTP-Referer` header (OpenRouter attribution).                       |
| `OPENROUTER_APP_TITLE`         | (unset)                                                       | Forwarded as `X-Title` header (OpenRouter attribution).                            |
| `VMTB_PROMPTS_DIR`             | sibling `vmtb-skill/skills/...` → `~/.claude/...` → mtb-bench cached path | Override the vMTB prompt source dir (`mtb_full.py`).                  |
| `VMTB_PAGEINDEX_ROOT`          | sibling `vmtb-skill/.../references/pageindex` → `~/.claude/...` | Override the NCCN PageIndex artifact dir (`nccn_pageindex.py`).                  |
| `OPL_PROMPTS_DIR`              | `<repo>/prompts`                                              | Override the OPL prompt source dir (`opl_full.py`).                                |
| `BENCH_MODEL`                  | `openai/gpt-4o-mini`                                          | Fallback for `--model`.                                                            |

## Output schema (`raw_outputs.jsonl`)

One JSON object per line, exactly the shape SBT's `score_model_outputs.py` expects:

```json
{
  "model": "<arm>::<model>",
  "surface": "crc_case | nccn_structured",
  "item_id": "...",
  "ok": true,
  "elapsed_seconds": 87.5,
  "finish_reason": "stop",
  "content_present": true,
  "json_parse_ok": true,
  "parsed_json": { ... matches schema_crc.json or schema_nccn.json ... },
  "raw_response": { ... full LLM HTTP response ... },
  "error": null,
  "intermediate": { ... per-stage timing + verifier verdicts + plan dict ... }
}
```

## Reasoning-model gotchas

OPL's recommended default model is **MiniMax-M2** (per the user's
`reference_minimax_llm.md` memory). M2 is a reasoning model — every call
emits a `<think>...</think>` block before the actual answer. Two
implications baked into this adapter:

1. **`OPENROUTER_MAX_TOKENS_FLOOR=8000`** — without it, every call truncates
   inside the think block and `extract_json` finds no JSON. Default `max_tokens`
   per call site (400 / 1200 / 1500 / 2000) was sized for non-reasoning
   models like `gpt-4o-mini` and is too tight for M2.
2. **`extract_json` strips `<think>` blocks** before attempting `json.loads`.
   Also handles stray leading `</think>` when the opener was truncated
   server-side.

If you switch back to a non-reasoning model (gpt-4o-mini, claude-haiku-4-5),
either `unset OPENROUTER_MAX_TOKENS_FLOOR` or set it to `0`.
