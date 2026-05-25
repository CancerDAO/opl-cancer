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


## Empty-integrator rule (v1.2.0)

If `deg_list` is empty (zero genes) OR `geneset_library` is empty, the only legal output is:

- `library: "<name>"` (echo input)
- `method: "ORA"`
- `n_input_genes: 0`
- `hits: []`
- `cross_referenced_with_literature: []`
- `claim_layer: "speculative"`

Do NOT invent pathway names or NES / p / q values. Do NOT synthesize hits from training data.

## PMID / pathway grounding (v1.2.0)

Every `pathway` name MUST come from the supplied `geneset_library` (e.g. MSigDB Hallmark / KEGG / Reactome canonical names). Every `pmid` in `cross_referenced_with_literature` MUST come from the patient's upstream literature pack (`pubmed_results` etc.) — do NOT invent PMIDs.
