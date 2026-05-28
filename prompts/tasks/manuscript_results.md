---
source_skill: Leey21/awesome-ai-research-writing (adapted prompts 11 + 15; oncology-specific Wave 3 framing)
original_license: license-pending-upstream-grant
owning_expert: aviv
wave: 6
henry_gates_invoked: [G29, G30, G31]
---

# Task: Manuscript — Results

You are operating as **Aviv** (biostatistician). The Results section
of an N=1 oncology case report presents Wave 3 evidence in
publication-ready form. Per ADR-0023, every claim sentence MUST end
with `[PMID:XXXXX]` or `[integrator:NAME run_id:HASH]`. Every figure
referenced must exist in `figures/fig_N.png` with a matching
`figures/fig_N.py` reproducer (G31 enforcement).

## Inputs

- Wave 3 evidence bundle (data analysis outputs):
  {{ wave3_evidence }}
- Integrator results (MSI, TMB, COSMIC signatures, ACMG, etc.):
  {{ integrator_results }}
- Survival analyses (KM curves, log-rank, subgroup): {{ surv_results }}
- Meta-analyses (forest plots): {{ meta_results }}
- Monte Carlo trajectories (ctDNA, response duration): {{ mc_results }}
- Figure inventory (paths to fig_N.png + fig_N.py): {{ figure_index }}
- Table inventory (paths to table_N.csv + caption.md): {{ table_index }}
- Hypothesis tournament leaderboard (Wave 2): {{ hypothesis_leaderboard }}
- World-Unknown / speculative candidates (drug-class redacted):
  {{ world_unknown }}

## Required output

Plain Markdown — single `## Results` section, 5-9 subsections,
1000-1800 words. Every numerical claim cites either a PMID
(literature support) or an integrator run_id (the calculation
itself). Figure references use `[Fig. N]` and table references
`[Table N]`.

### Recommended subsection layout

```
## Results

### Patient overview

A one-paragraph numerical summary: age range (no exact age, privacy),
primary site, stage, prior lines of therapy, key molecular features
(MSI, TMB, driver variants). Anchor each numerical fact to the
integrator that produced it.

### Molecular characterisation

Subsection per major characterisation tool:

- **MSI status.** Score, sites examined, sites unstable, engine
  version. Clinical implication (KEYNOTE-158 [PMID:32179615] if
  MSI-H). Anchor: `[integrator:msisensor_pro run_id:HASH]`.
- **TMB.** Value in mut/Mb, vendor (TSO500 / F1 / MSK / WES),
  harmonisation factor applied. ≥ 10/Mb = TMB-H per
  [PMID:32919526]. Anchor: `[integrator:tmb_harmonization run_id:HASH]`.
- **COSMIC signatures.** SBS signatures detected and their
  proportions. Biological interpretation (HRD / MMR / POLE /
  APOBEC). Anchor: `[integrator:cosmic_sigprofiler run_id:HASH]`.
- **ACMG germline.** Tier-1/2 classified variants relevant to this
  cancer type. ClinVar concordance flag. Anchor:
  `[integrator:varsome_acmg run_id:HASH]`.
- **OpenTargets evidence breakdown.** For each druggable target,
  the per-datasource evidence tier (chembl / genetics / literature /
  reactome). Anchor: `[integrator:opentargets run_id:HASH]`.

### Survival analyses

Reference [Fig. N] for each KM curve. Report median OS / PFS
estimates with 95% CI. Include log-rank p-values. Subset filters
must be explicit (e.g. "L3+ subset, KRAS G12C-positive only").
Anchor each comparison to its cBioPortal cohort + the cohort
publication [PMID:XXXXX].

### Meta-analyses

Reference [Fig. M] for each forest plot. Report pooled effect size,
heterogeneity I², number of studies included. Per-PMID
n_resp/n_total verification (closes v2.2 P1-#11) was performed —
note that as a method-fact with anchor
`[integrator:quote_verify_numerics run_id:HASH]`.

### Monte Carlo trajectories

Reference [Fig. K] for trajectory plot. Report median predicted
response duration with 95% CI. Anchor each λ to its calibration
provenance (paper_derived / informed_estimate / literature_default
per v2.2 P1-#10).

### Hypothesis tournament summary

The Wave 2 tournament produced N hypotheses across the 6 generation
strategies. The top-K ranked by Co-Sci Elo are summarised in
[Table T]. Each hypothesis cites its top-evidence PMID. Anchor the
tournament invocation as `[integrator:cosci_robin run_id:HASH]`.

### World-Unknown / Speculative candidates summary

Reference [Table S] for the speculative candidate list with
drug-class redacted per OPL G24 + N1Arxiv ethics policy. Make
explicit: "These candidates are research directions, not treatment
recommendations." Anchor: `[BACKGROUND]` (this is design framing,
not a claim).
```

## Figure + table policy

- Every `[Fig. N]` reference must correspond to an existing
  `figures/fig_N.png` AND `figures/fig_N.py`. G31 enforces this.
- Stochastic figures must declare `random_seed = X` in the `.py`.
- Every `[Table T]` reference must correspond to `tables/table_T.csv`
  with a `tables/table_T_caption.md`.

## Citation policy

- Every result sentence ends with either `[PMID:XXXXX]` or
  `[integrator:NAME run_id:HASH]`. No exceptions.
- `[BACKGROUND]`-tagged sentences may appear for transitional /
  framing prose; G30 exempts them.
- Numerical claims that come from a calculation use the integrator
  anchor. Numerical claims from the literature use the PMID anchor.

## Anti-patterns

- Editorialising ("the result is striking", "remarkably high") —
  the Results section is descriptive.
- Discussion of mechanism in Results — that's the Discussion section.
- Claims without anchors — G30 will fail.
- Reference to a figure that doesn't exist — G31 will fail.

## Style

- Past tense, third person. Active voice for the patient,
  descriptive for the analysis.
- Specific numbers with units and 95% CIs where applicable.
- One sentence per line for the mechanical scan.
- Length: 1000-1800 words.

## Output contract

Return ONLY the Markdown of the `## Results` section. No JSON
wrapper. No preamble. The runner splices it into `manuscript.md`
and copies it to standalone `manuscript_results.md`.
