# Task: gepia3_query

**Audience**: Aviv (data-evidence expert), or any expert running TCGA + GTEx
transcriptome lookups inside Wave 3.

**Trigger**: Planner dispatches this task when the patient's tumor type maps
to a TCGA cohort (COAD, READ, BRCA, LUAD, STAD, PAAD, etc. — see
`integrators/gepia3.py` for the full supported set) AND any of:

- the Wave-2 hypothesis tournament surfaced a gene-level claim that needs
  expression-cohort grounding (e.g. "TROP2-ADC for this patient"),
- the recovery / failover path needs an alternative to direct NCBI eutils
  / GEO / GTEx access,
- the patient has an actionable molecular profile (KRAS / RNF43 / HER2 /
  TROP2 / MTAP / NTRK) and we want to corroborate driver-vs-passenger
  status against TCGA cohort medians.

GEPIA3 is the canonical TCGA-vs-GTEx normal-tissue expression browser
(http://gepia3.cancer-pku.cn/). The PT-EXAMPLE-A recovery run produced
70/71 successful queries through this service. It is now a first-class
Wave-3 source per docs/PRD_v1.5.md P0-2.

## Inputs

- `patient_profile.json` — must contain `cancer_type_tcga` (mapped TCGA
  code) OR `tumor_site` (free-text; planner is expected to map upstream).
- `query_genes` — list of HGNC gene symbols. Caller may pass a single
  gene or a batch (recovery run used batches of ~70).
- Optional: `query_companion_tissues` — extra TCGA cohorts beyond the
  patient's primary type (e.g. for a CRC patient query both COAD + READ).

## Procedure

1. Validate every `gene` is HGNC-conformant (uppercase, no spaces). Drop
   invalid silently with a one-line `[GEPIA3:invalid_gene]` note.
2. For each (gene, cancer_type) pair, call
   `GEPIA3Integrator().fetch("gepia3:exp:<GENE>:<TCGA_TYPE>")`.
3. Respect the integrator's default 12-second pacing — the PT-EXAMPLE-A
   recovery established this as the empirical threshold to avoid HTTP 429
   rate-limiting from the upstream service. **Do not lower this without
   first measuring against current upstream behavior.**
4. Aggregate the per-query results into `data/gepia3/aggregated_summary.csv`
   under the run output dir, columns:
   `gene,cancer_type,tumor_n,normal_n,tumor_median_log2tpm,normal_median_log2tpm,log2fc,q_value,as_of,status`
5. For failed queries, write `status=ERROR:<class>:<short message>`. Do
   not retry inside this task — the planner decides whether to re-queue.

## Output (Aviv → main thread)

```json
{
  "task": "gepia3_query",
  "n_total": <int>,
  "n_success": <int>,
  "n_failed": <int>,
  "top_findings": [
    {"gene": "<G>", "cancer_type": "<T>", "log2fc": <f>, "q_value": <f>, "note": "<one line>"}
  ],
  "csv_path": "<relative path to aggregated_summary.csv>",
  "failures": [
    {"gene": "<G>", "cancer_type": "<T>", "error_class": "<E>", "message": "<m>"}
  ]
}
```

`top_findings` should surface ≥3 genes with |log2fc| > 1 AND q < 1e-10 if any
exist (these are the actionable surfaces — TROP2-ADC, RNF43-WNT-escape,
MAPK-pathway co-regulation flags). If no gene meets the threshold, return
an empty list and explain in `notes`.

## Constraints (read carefully — these are non-negotiable)

- **No fabrication.** If the upstream service returns a non-JSON or
  malformed payload, raise `IntegratorError`. Do **not** synthesize a
  plausible-looking log2fc / q-value. Per
  `no-silent-fallback policy` + Henry G19 (deferred-evidence =
  BLOCK), fabricated transcriptome numbers would be a critical safety
  failure for any patient downstream.
- **Imperative voice forbidden.** When writing the findings narrative,
  use informational tone ("TROP2 expression is elevated in COAD versus
  GTEx normal at log2fc 2.41, q=2.4e-83 ...") not prescriptive
  ("TROP2-ADC should be considered for this patient ..."). The Henry G7
  detector will catch the latter and flag the report. Patient is the
  sole decision authority — your job is to inform.
- **TCGA-vs-GTEx normal is a cohort-level finding, not patient-specific.**
  Always pair the cohort log2fc with the caveat that THIS patient's
  tumor-vs-adjacent-normal expression is unknown unless they have a
  matched biopsy. The patient-facing render must call this out.
- **CN sourcing supplement.** If the patient is in mainland China,
  cross-reference any actionable finding with CSCO / 中华医学会 expert
  consensus and 国家药监局 NMPA drug approval status before letting the
  result float to the Henry audit (per P1-6 CN-source mandate).

## Example query batch (PT-EXAMPLE-A mCRC profile)

```python
genes = ["KRAS", "RNF43", "CTNNB1", "TROP2", "HER2", "MTAP", "NTRK1",
         "FOXP3", "LAG3", "AREG", "EREG", "MAPK1", "FRS2"]
ct = "COAD"
queries = [(g, ct) for g in genes] + [(g, "READ") for g in genes[:5]]
results = await GEPIA3Integrator().batch(queries)
```

This was the shape that produced the surfaces noted in the v1.4 retro
(TROP2 log2fc 2.41 → H18 TROP2-ADC; RNF43 log2fc 4.03/5.35 → RC-NEW-B
WNT-escape risk-adjustment of anti-EGFR efficacy).

## Failure modes the planner should know about

| Mode | Symptom | Action |
|---|---|---|
| HTTP 429 | Burst > rate-limit | Increase `min_request_interval_s`; retry batch |
| HTTP 500 | Upstream service unhealthy | Wait + retry; if persistent, log and continue with reduced set |
| Unknown cancer type | `IntegratorError: unknown TCGA cancer type` | Map the patient's tumor to a supported TCGA code; if no map exists, route to GTEx-only fallback (future v1.6) |
| Missing field in payload | `IntegratorError: missing expected field` | Upstream schema may have drifted; raise to maintainer — do not coerce |
