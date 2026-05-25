# Task: dataset_acquisition

Identify public omics datasets (GEO / ArrayExpress / SRA) that best match the patient's
molecular + clinical profile for downstream re-analysis.

Patient context (JSON): {{ profile_json }}
NGS report (summary): {{ ngs_report }}
Wave-2 hypotheses (JSON): {{ wave2_hypotheses }}

Apply G14 (dataset-patient match scoring):
1. Cancer type identical → score 3, related lineage → 2, unrelated → 0
2. Stage matched → +1
3. Platform (RNA-seq / scRNA-seq / WES / WGS) appropriate for hypothesis → +1
4. Sample size ≥ 30 → +1
5. Tumor vs adjacent normal control present → +1

For each candidate dataset, return strict JSON:
{
  "datasets": [
    {
      "accession": "GSE12345 | E-MTAB-... | SRP...",
      "source": "GEO | ArrayExpress | SRA",
      "title": "<dataset title>",
      "platform": "<platform>",
      "n_samples": <int>,
      "cancer_type": "<type>",
      "match_score": <0-7>,
      "match_rationale": "<2-3 sentences>",
      "suitable_for_hyp_ids": ["hyp_xxx", ...],
      "claim_layer": "established"
    }
  ],
  "_meta": {"source_count_checked": <int>}
}

Founder-mode: declare honestly when no public dataset matches well (match_score < 3).
Do NOT invent fake accession numbers.


## Empty-integrator rule (v1.2.0)

If ALL relevant live integrator inputs for this task (`geo_results`, `arrayexpress_results`, `sra_results`) are empty, the only legal output is:

- `datasets: []`
- `_meta: {"source_count_checked": 0, "note": "Live integrator returned no evidence for this patient context. No public dataset matches could be surfaced from current data; further retrieval is required before this question can be answered. Patient is sole decision authority; output is non-directive."}`

Do NOT invent accession numbers. Do NOT synthesize from training data.

## PMID / accession grounding (v1.2.0)

Every `accession`, `title`, `platform`, `n_samples`, and `cancer_type` MUST come from the integrator inputs above. If a candidate dataset is not retrieved by the live integrator, it does not exist for this analysis — do NOT add it from memory.
