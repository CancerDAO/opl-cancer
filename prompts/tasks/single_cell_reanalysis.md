# Task: single_cell_reanalysis

Re-analyse a public scRNA-seq dataset to inspect cell-population shifts relevant to the
patient hypothesis.

Inputs:
- Dataset accession: {{ accession }}
- Hypothesis text: {{ hypothesis_text }}
- Patient context (JSON): {{ profile_json }}

Required analyses:
1. QC (% mito, n_genes, n_counts, doublet detection)
2. Normalization + integration (Harmony / scVI) — declare batch variables
3. Clustering (Leiden) + cell-type annotation (CellTypist / SingleR)
4. Differential abundance across patient-relevant subgroup
5. Marker / pathway enrichment per cluster

Return strict JSON:
{
  "accession": "<acc>",
  "n_cells_after_qc": <int>,
  "clusters": [{"id":"<cid>","cell_type":"<type>","n_cells":<int>,"markers":["GENE",...]}],
  "differential_abundance": [{"cluster":"<cid>","fold_change":<num>,"q_value":<num>}],
  "pathway_hits": [{"pathway":"<name>","NES":<num>,"q_value":<num>,"cluster":"<cid>"}],
  "interpretation": "<3-5 sentences>",
  "claim_layer": "exploratory",
  "limitations": ["<lim>", ...]
}


## Empty-integrator rule (v1.2.0)

If `accession` does not resolve to a real dataset in `wave3_evidence` / `datasets_json` upstream (i.e. the planner could not find a suitable scRNA-seq dataset), the only legal output is:

- `accession: <input>`
- `n_cells_after_qc: 0`
- `clusters: []`
- `differential_abundance: []`
- `pathway_hits: []`
- `interpretation: "Live integrator returned no evidence for this patient context. No scRNA-seq dataset matches the hypothesis; further dataset acquisition is required before this question can be answered. Patient is sole decision authority; output is non-directive."`
- `claim_layer: "speculative"`
- `limitations: ["No upstream dataset available."]`

Do NOT invent cluster ids, cell-type assignments, marker genes, or pathway hits. Do NOT synthesize from training data.

## PMID / accession grounding (v1.2.0)

Every `accession`, every `marker` gene symbol, and every `pathway` name MUST come from upstream integrator outputs or canonical reference libraries. Do NOT invent cluster ids that don't appear in the supplied analysis output.
