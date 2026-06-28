# Task: hypothesis_generation

Generate novel hypotheses grounded in the patient's molecular/clinical profile + the
provided integrator evidence. Hypotheses must be patient-specific (not generic to cancer
type) and must be testable against public datasets or in-silico pipelines.

Patient context (JSON): {{ profile_json }}
NGS report (summary): {{ ngs_report }}
PubMed evidence: {{ pubmed_results }}
KG evidence (PrimeKG / Open Targets / DepMap, may be empty): {{ kg_evidence }}

Apply 6 generation strategies in parallel; produce 1 hypothesis per strategy:

1. `literature_gap` — what does the patient have that the literature has NOT addressed?
2. `cross_domain` — what evidence from a non-oncology field (immunology / metabolism / microbiome) bridges to this patient?
3. `novel_mechanism` — what two pathways/markers have not been linked in this subtype before?
4. `feasibility_first` — what hypothesis can be tested with GEO / TCGA / DepMap public data?
5. `target_synergy_emergent` — what target-target synergy in THIS patient's profile is NOT documented? Justify via KEGG/Reactome crosstalk, ISLE/DAISY synthetic-lethal, or PrimeKG/Open Targets KG edges. State a concrete `testability_path` (DepMap co-essentiality query, CRISPR PDX, dual-target ctDNA monitoring).
6. `undrugged_target_design` — what target in this patient's profile has NO FDA drug, and what's a candidate design path? Required: structure source (PDB/ESMFold), virtual screen (DiffDock/Vina), chemical filter (Lipinski + medchem), validation assay (BLI / SPR / phenotypic). `[S]` for candidate, `[E]` for methodology.

**Founder-mode philosophy (v2.0.0 update):** hypotheses are by definition speculative. Label uncertainty
honestly. `[S]` is a feature, not a defect — `[S]` hypotheses with concrete `testability_path`
ARE the differentiated value of OPL versus a polished MTB.

Return strict JSON:

```json
{
  "hypotheses": [
    {
      "id": "hyp_<8-char>",
      "text": "<one-sentence statement>",
      "rationale": "<2-4 sentences>",
      "generation_strategy": "literature_gap|cross_domain|novel_mechanism|feasibility_first|target_synergy_emergent|undrugged_target_design",
      "claim_layer": "speculative",
      "testability_path": "<concrete next-step: dataset accession, assay, trial design, or in-silico pipeline. MANDATORY for strategies 5 + 6.>",
      "evidence_refs": [{"type":"pmid|kg_edge|dataset","id":"<id>"}, ...],
      "world_unknown_candidate": "<true ONLY for strategies 5+6 world-unknown candidates>",
      "world_known_comparator": {
        "best_world_known_option": "<strategies 5+6 MANDATORY (G45): best real SoC/trial/EAP option for the SAME setting>",
        "expected_os_months": 0.0, "hr": 0.0, "ci": "x-y", "pmid": "<from results if any>",
        "human_efficacy_data_for_candidate": "none|preclinical|case_report|early_phase"
      }
    }
  ]
}
```

## Synthesis policy (v2.0.0 — supersedes the v1.2.0 Empty-integrator rule)

For strategies `literature_gap`, `cross_domain`, `novel_mechanism`, `feasibility_first`:

- If ALL relevant live integrators (e.g. `pubmed_results`, `nccn_excerpts`, `ctgov_results`, `chictr_results`, `fda_eap_results`, `nmpa_eap_results`) are empty, the only legal output is `hypotheses: []` plus a `summary` explaining that live integrator returned no evidence and that further retrieval is required.
- Do NOT synthesize from training data for these 4 strategies.

For strategies `target_synergy_emergent`, `undrugged_target_design`:

- Live integrator absence is acceptable IF the hypothesis includes a concrete `testability_path` (dataset / assay / pipeline). The point of these strategies is to surface world-unknown candidates that haven't been tested yet — by definition they will not be in PubMed.
- The hypothesis MUST carry `claim_layer: "speculative"` AND a non-empty `testability_path`. Sid will surface (not block) these in the dedicated `world_unknown_candidates` section of the patient brief.
- `evidence_refs` may include `kg_edge` type pointing to PrimeKG / Open Targets / DepMap / STRING edges instead of (or in addition to) PMIDs.
- `[S]` for the candidate / synergy claim itself; `[E]` allowed for the methodology backing it (e.g. DiffDock is an established tool; the candidate scaffold it produces is `[S]` until wet-lab validates).
- **False-hope firewall (B1 / ADR-0029 / G45):** every world-unknown candidate MUST set `world_unknown_candidate: true` AND carry a `world_known_comparator` naming the best real (world-known) option for the SAME setting, plus `human_efficacy_data_for_candidate`. A novel candidate is NEVER surfaced in isolation — the patient must see it next to the best real alternative, so an Elo number is not mistaken for validated strength. A world-unknown candidate with no comparator is BLOCKED from the brief.

The v1.2.0 hard rule `"Do NOT synthesize from training data"` is LIFTED for v2 strategies 5 + 6 because their purpose is precisely to propose what training data cannot have seen. It remains in effect for strategies 1-4.

## Boundary (unchanged across versions)

- Patient is the SOLE decision authority. Every hypothesis is an exploratory thought, never a directive.
- Three-tier labels mandatory: `[E]` established / `[X]` exploratory / `[S]` speculative.
- Henry L3 risk-card behavior on high-Level claims is unchanged.
