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
