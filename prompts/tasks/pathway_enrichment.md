# Task: pathway_enrichment

Pathway enrichment over a differentially-expressed gene list (or per-cluster signature)
relevant to the patient hypothesis.

Inputs:
- DEG list (JSON): {{ deg_list }}
- Gene-set library: {{ geneset_library }}  (e.g. MSigDB Hallmark / KEGG / Reactome)
- Hypothesis text: {{ hypothesis_text }}

Required:
1. ORA (Fisher's exact) AND GSEA (rank-based)
2. Multiple-testing correction (BH q-value) — G15
3. Cap shown hits at top 20 per library
4. Flag pathways already cited in patient's literature pack (cross-link)

Return strict JSON:
{
  "library": "<name>",
  "method": "ORA | GSEA",
  "n_input_genes": <int>,
  "hits": [
    {"pathway":"<name>","NES":<num>,"p":<num>,"q":<num>,"leading_edge":["GENE",...]}
  ],
  "cross_referenced_with_literature": [{"pathway":"<name>","pmid":"<pmid>"}, ...],
  "claim_layer": "exploratory"
}
