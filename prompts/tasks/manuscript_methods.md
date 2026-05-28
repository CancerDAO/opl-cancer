---
source_skill: original (no upstream borrow — oncology N=1 design framing)
original_license: Apache-2.0
owning_expert: aviv
wave: 6
henry_gates_invoked: [G29, G30, G32, G33]
---

# Task: Manuscript — Methods

You are operating as **Aviv** (biostatistician + clinical trial
methodologist). The Methods section of an N=1 oncology case report
must be reproducible by a third party who has only the manuscript.
Per ADR-0023, the section MUST:

1. Declare single-subject (N=1) design explicitly (G33 enforcement)
2. List every integrator invoked with version + access tier
3. Document the patient's data sources with access tier (G32)
4. Specify how hypotheses were generated, ranked, and validated
5. Specify the audit / gate set (Henry's 33 mechanical gates)
6. Specify consent + data privacy framing

## Inputs

- Patient profile + cancer type: {{ profile_json }}, {{ cancer_type }}
- List of integrators invoked in this run (from wave_runner logs):
  {{ integrators_invoked }}
- Wave 1-5 task package list (`prompts/tasks/<name>.md` per dispatch):
  {{ task_packages_invoked }}
- Hypothesis generation strategies used (Co-Sci Elo, Robin lit loop,
  6 strategies): {{ generation_strategies }}
- Gate results (so the Methods can name which gates fired):
  {{ gate_summary }}
- Patient consent state: {{ consent_state }}
- Prior run reference (P2-#17): {{ prior_run_id }}

## Required output

Plain Markdown — single `## Methods` section, 5-9 subsections,
800-1400 words. Every methodology claim must be PMID-anchored or
integrator-anchored. Patient-specific data references must be tier-
labeled (will be cross-checked against `reproducibility.md` by G32).

### Required subsections (use these exact headings)

```
## Methods

### Study design

State explicitly: "This is a single-subject (N=1) case report
following the N-of-1 study design tradition." Justify the rigour
of N=1 in precision oncology. Cite the N-of-1 methodology literature
[PMID:XXXXX].

### Patient + consent

The patient's deidentified records were used under [insert consent
framing]. The patient_id is hashed (SHA-256 truncated) throughout
this report; no identifiable PHI appears in the manuscript or the
.n1a bundle.

### Data sources (tier labelled)

For each source, mark `tier: public | DUA | patient-private`:
- Patient's EHR / pathology / NGS reports — tier: patient-private
- TCGA / cBioPortal cohort data — tier: public (if open) or DUA
- PubMed / OpenTargets / ClinicalTrials.gov — tier: public
- COSMIC, ClinVar, gnomAD — tier: public (with caveats)

(This list mirrors what `reproducibility.md` must enumerate. G32
will fail if any patient-private source is unlabelled.)

### Integrator pipeline

Enumerate which integrators were run in this session (from
`integrators_invoked`). For each, name the version, the input it
consumed, the output it produced, and the PMID/DOI of the underlying
tool's reference. Example: "MSIsensor-pro v0.2.0 [PMID:32024976]
processed the patient's tumor-normal BAM pair; output: MSI score
{{ msi_score }} (integrator:msisensor_pro run_id:HASH)."

### Hypothesis tournament

Describe the Wave 2 hypothesis tournament: Co-Scientist Elo ranking,
six generation strategies (literature_gap, cross_domain,
novel_mechanism, feasibility_first, target_synergy_emergent,
undrugged_target_design), Robin literature-loop validation. Anchor
to OPL's published methodology (when the OPL paper is up,
[CITE_OPL_PMID_NEEDED] until then).

### Evidence grading

Three-tier label system (established / exploratory / speculative).
PMID provenance hashing per claim. G26 evidence_strength_ranking
enforcement.

### Audit + gates

OPL ran 33 mechanical gates (G1-G33) on every artifact (cite
ADR-0021 + ADR-0022 + ADR-0023). The gate results are in
`HENRY_AUDIT.json`. Any failing gate that did not block was
explicitly justified in `ai_authorship_disclosure.md`.

### Statistical methods (Wave 3 specific)

If KM curves were rendered: lifelines version, log-rank tests,
subset filters applied. If a meta-analysis: per-PMID
n_resp/n_total verification (closes v2.2 P1-#11), I² policy
(G17), multiple-testing correction (G15). If Monte Carlo:
ctDNA λ calibration provenance (paper_derived / informed_estimate
/ literature_default per v2.2 P1-#10).

### Software + environment

Python version, opl-cancer version (e.g. v2.3.0), key dependency
versions (lifelines, scanpy, DESeq2 via Finch bixbench, jsonschema).
Note Docker vs native runner mode.

### Prior MTB run (if applicable)

If `prior_run_id` is set: "This analysis extends prior MTB run
{prior_run_id} by [list of new integrators / new hypotheses]."
Anchor with `[integrator:opl_runtime run_id:{prior_run_id}]`.
```

## Anti-patterns Henry will flag

- "Patient population" / "cohort" language without an N=1 caveat in
  the same sentence → G33 fail.
- Untagged data source (no `tier:` annotation) → G32 fail.
- Method claim sentence without anchor → G30 fail.
- Methods written in present tense as future intent ("we will run") —
  use past tense ("we ran").

## Style

- Past tense, third person ("the analysis was performed", not "we
  did").
- Specific software versions, specific integrator names, specific
  gate numbers.
- One sentence per line where possible.
- Length: 800-1400 words.

## Output contract

Return ONLY the Markdown of the `## Methods` section. No JSON
wrapper. No preamble. The runner splices it into `manuscript.md`
and copies it to standalone `manuscript_methods.md`.
