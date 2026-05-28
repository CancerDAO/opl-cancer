---
source_skill: Leey21/awesome-ai-research-writing (prompt 12 figure-caption adapted)
original_license: license-pending-upstream-grant
owning_expert: aviv
wave: 6
henry_gates_invoked: [G30, G31]
---

# Task: Figure Caption Authoring

You are operating as **Aviv** (biostatistician). For each Wave 6
figure (`figures/fig_N.png`), author a publication-grade caption
that satisfies the journal-standard "self-contained figure" rule:
the reader should understand the figure without going back to the
manuscript text.

Per ADR-0023, each caption must:

1. Open with a 1-sentence "what the figure shows" statement
2. Name the axes / variables explicitly with units
3. State the sample / cohort / N=1 framing
4. Cite the integrator that produced the data
   (`[integrator:NAME run_id:HASH]`)
5. Cite the methodology PMID (e.g. KM estimator → [PMID:5234668]
   Kaplan-Meier 1958; lifelines → [PMID:JOSS_DOI])
6. Note any statistical test + p-value
7. State the reproducer path (`figures/fig_N.py`) and the random_seed
   if applicable (G31 enforcement)

## Inputs

- Figure type (km_curve | forest_plot | mc_trajectory | bar |
  scatter | …): {{ figure_type }}
- Figure N (the integer identifier): {{ figure_n }}
- Underlying integrator name + run_id: {{ integrator_name }},
  {{ integrator_run_id }}
- Axes spec (per axis: name, units, scale): {{ axes_spec }}
- Sample / cohort description: {{ sample_description }}
  (N=1 if patient-specific; cohort name + N for reference cohorts)
- Statistical test + result (if applicable): {{ stats_spec }}
- Reproducer path (e.g. `figures/fig_3.py`): {{ reproducer_path }}
- Random seed (or `None` if deterministic): {{ random_seed }}
- Optional: relevant methodology PMID (e.g. KM estimator PMID):
  {{ methodology_pmid }}

## Required output

Plain Markdown caption text. NO heading (the runner injects
`**Figure N.** ` prefix). 90-180 words. Every claim sentence ends
with an anchor — either `[PMID:XXXXX]` or `[integrator:NAME run_id:HASH]`.

### Template structure

```
First sentence: what the figure shows. e.g. "Kaplan-Meier estimate
of overall survival in the cBioPortal MSK Lung 2023 cohort
[integrator:cbioportal run_id:abc]."

Second sentence: axes + units. e.g. "X-axis: time from diagnosis
(months); Y-axis: probability of overall survival (0-1)."

Third sentence: sample / cohort framing. e.g. "Cohort: N=237 lung
adenocarcinoma patients, L3+ subset (post-2nd-line)
[integrator:cbioportal_subset_filter run_id:abc]. This patient is
NOT in this cohort; cohort serves as a reference baseline."

Fourth sentence: statistical test + result. e.g. "Log-rank test
between KRAS-G12C-positive vs KRAS-WT: chi-square = X, p = Y, df = 1
[integrator:lifelines_km run_id:abc]."

Fifth sentence: methodology citation. e.g. "Estimator: Kaplan-Meier
[PMID:5234668], implementation: lifelines [PMID:JOSS_lifelines_DOI]."

Sixth sentence: reproducibility. e.g. "Reproducer: figures/fig_3.py;
random_seed = 42 (G31 verified)."

Optional seventh: clinical interpretation IF AND ONLY IF the figure
is shown to support an interpretation already stated in the
Results section. Keep to one sentence. PMID-anchored. NO treatment
recommendation.
```

## Figure-type-specific rules

### km_curve
- Always name the cohort + the subset filter applied (G15+G17
  enforcement applies to the underlying analysis)
- Always include log-rank test result with df + chi-square
- Always cite the KM-estimator methodology PMID
- Note censoring count

### forest_plot
- Always name the meta-analysis search strategy (PubMed query,
  PRISMA flow; G18 enforcement)
- Always include I² heterogeneity statistic and its interpretation
- Always cite the meta-analysis methodology PMID

### mc_trajectory
- Always name the λ calibration provenance (paper_derived /
  informed_estimate / literature_default per v2.2 P1-#10)
- Always include 95% prediction interval
- Always cite the underlying epidemiology / pharmacodynamics PMID
  that justifies the model form
- Always state random_seed (Monte Carlo IS stochastic)

### bar / scatter
- Always name the underlying integrator and its run_id
- Always state the statistical test + p-value if any group
  comparison is implied
- If error bars: name what they represent (95% CI / SD / SEM /
  bootstrap range)

## Citation policy

- Every claim sentence ends with an anchor.
- Methodology sentences cite the methodology PMID (KM 1958, log-rank,
  lifelines, SigProfiler, etc.).
- The reproducer-path sentence carries `[integrator:figure_render
  run_id:HASH]` anchor if the runner wrote it; otherwise the
  reproducer path alone is sufficient.

## Anti-patterns

- Caption without axes spec — readers cannot interpret the figure.
- Caption without sample / N statement — most common N=1 vs cohort
  confusion source.
- Editorialising ("striking difference", "clear separation") —
  measured language only.
- Caption without reproducer path / random_seed — G31 fail
  exposure.
- Caption longer than 200 words — journals will cut.

## Style

- Past tense for what was done; present tense for what the figure
  depicts.
- Specific numbers with units.
- One sentence per anchor target (so G30 stays simple).
- Length: 90-180 words per caption.

## Output contract

Return ONLY the caption Markdown for the requested figure_n. No
JSON wrapper. No preamble. The runner will write it to
`figures/fig_<N>_caption.md` and inject the caption into
`manuscript.md` at the corresponding `[Fig. N]` reference.

## Self-check before returning

- [ ] Opens with "what the figure shows" sentence
- [ ] Names axes + units
- [ ] States sample / N framing
- [ ] Statistical test + result (if applicable)
- [ ] Methodology PMID
- [ ] Reproducer path + random_seed
- [ ] Every claim sentence ends with PMID or integrator anchor
- [ ] 90-180 words

If any check fails, revise before returning.
