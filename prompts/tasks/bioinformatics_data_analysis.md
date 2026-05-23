# Task: bioinformatics_data_analysis

Propose a concrete data-analysis plan for the selected dataset(s). This plan will be
executed by the bixbench Docker runtime (env-gated via OPL_BIXBENCH_LIVE).

Inputs:
- Selected datasets (JSON): {{ datasets_json }}
- Wave-2 hypothesis under test: {{ hypothesis_text }}
- Patient context (JSON): {{ profile_json }}

Plan must include:
1. Data acquisition steps (download URL or accession resolver)
2. QC steps (FastQC / multiQC / scRNA QC thresholds)
3. Normalization + batch-effect strategy (declare batch variables — G16)
4. Statistical test(s) with multiple-testing correction strategy (G15)
5. Visualization output (volcano / UMAP / heatmap / pathway dotplot)
6. Pass/fail criteria for hypothesis (falsification rule)

Return strict JSON:
{
  "analysis_plan_id": "plan_<8-char>",
  "dataset_accessions": ["<acc>", ...],
  "steps": [{"name":"<step>","tool":"<R/python pkg>","params":{...}}, ...],
  "batch_variables": ["<var>", ...],
  "multiple_testing_method": "BH | bonferroni | qvalue",
  "expected_outputs": ["<file/figure>", ...],
  "falsification_rule": "<one sentence: hypothesis is falsified if ...>",
  "compute_estimate": {"cpu_h": <num>, "ram_gb": <num>, "wall_h": <num>},
  "claim_layer": "exploratory"
}

Founder-mode: an analysis without a falsification rule is hand-waving. Always include one.
