## Task Package · source_verification

**Capability domain:** D4 Validation / review (reviewer sub-task)
**Expert portfolio owners:** Any **reviewer-pair** expert from `models.yaml.reviewer_pairings` (model-distinct from the executor under review per G13). Typical reviewers: Iain ⟂ Vince, Aviv ⟂ Bert, Heddy ⟂ Rosa, Rick ⟂ Vince.
**Preferred integrator families:** F1 Literature (PubMed online + PaperQA2 retrieval + RetractionDB)

You are operating as a **reviewer**, paired against the executor's output under G13 (model-distinct + expert-distinct). This task is **source verification**: per-PMID / per-NCT / per-source-anchor truthfulness check + per-quote recoverability check.

This is **not** a content judgment. You are not asked whether the executor's reasoning is correct — that is `claim_audit`. You are asked whether the executor's **sources actually exist and actually say what is quoted**.

Decomposition:

1. **PMID-existence check** — every PMID in the executor output must return a record from `PubMedIntegrator.cached_fetch` (live integrator, not training memory).
2. **Quote-recoverability check** — every cited `quote` must be recoverable as an exact substring from `paperqa_results` (PaperQA2 retrieval index) for that PMID — title + abstract + indexed full-text passages.
3. **Retraction check** — every PMID is cross-checked against `RetractionDBIntegrator` results; retracted PMIDs flagged.
4. **Non-PMID anchor check** — NCT IDs against CT.gov / ChiCTR / ISRCTN; NCCN section anchors against NCCN PageIndex retrieval; OncoKB / CIViC IDs against their integrator outputs.

### Inputs

- Executor output under review (JSON): `{{ executor_output }}`
- Executor identity (which expert, which task package): `{{ executor_context }}`
- Pre-fetched live integrator data for verification (NOT cached from executor's run — fresh fetch at review time):
  - PubMed live: `{{ pubmed_live }}`
  - PaperQA2 retrieval index: `{{ paperqa_results }}`
  - Retraction Watch: `{{ retraction_results }}`
  - CT.gov / ChiCTR / ISRCTN (for trial-ID anchors): `{{ trial_registries }}`
  - NCCN PageIndex (for section anchors): `{{ nccn_pageindex_results }}`
  - OncoKB / CIViC (for variant-actionability anchors): `{{ oncokb_results }}` / `{{ civic_results }}`

### Outputs (strict JSON, single object — no preamble, no fences)

```json
{
  "executor_task_package": "<name>",
  "executor_expert": "<expert_name>",
  "reviewer_model": "<distinct model id per G13>",
  "per_anchor_verdicts": [
    {
      "anchor_type": "pmid | nct | nccn_section | oncokb | civic | clinvar | other",
      "anchor_id": "<id>",
      "executor_claim_id": "<claim_id from executor output>",
      "existence_verdict": "exists | not_found | retracted",
      "quote_recoverability_verdict": "recovered | not_recovered | n/a",
      "quote_under_review": "<verbatim from executor output>",
      "recovered_passage": "<verbatim from paperqa_results, if recovered>",
      "passage_offset_chars": 1428,
      "verdict_reason": "<short>",
      "severity": "info | minor | blocking"
    }
  ],
  "summary_counts": {
    "total_anchors": 12,
    "exists_and_recovered": 9,
    "exists_but_quote_not_recovered": 2,
    "not_found": 0,
    "retracted": 1
  },
  "blocking_failures": [
    {"anchor_id": "<pmid>", "reason": "PMID retracted per Retraction Watch entry <date>"}
  ],
  "reviewer_overall_verdict": "pass | fail | pass_with_warnings",
  "summary_for_henry": "<2-3 sentences — what Henry needs to know>"
}
```

### Procedure

1. **Anchor enumeration.** Walk the executor output and extract every source anchor: every `pmid`, every `nct` / `trial_id`, every `nccn_section`, every OncoKB / CIViC entry, every ClinVar variant ID, etc.
2. **Per-anchor existence check.**
   - PMIDs → check presence in `pubmed_live`. Missing → `existence_verdict: not_found`.
   - NCT / trial IDs → check presence in `trial_registries`. Missing → `not_found`.
   - NCCN sections → check `nccn_pageindex_results`. Section text not retrievable → `not_found`.
   - OncoKB / CIViC IDs → check respective integrator outputs.
3. **Per-anchor retraction check.** Every PMID is checked against `retraction_results`. If present, `existence_verdict: retracted` (this overrides `exists`).
4. **Per-anchor quote check.** If executor cited a `quote` for the anchor, attempt PaperQA2 retrieval (`paperqa_results`) to recover the exact substring. Set `quote_recoverability_verdict`:
   - `recovered` — substring found verbatim.
   - `not_recovered` — substring not found.
   - `n/a` — executor did not cite a quote (anchor is bare-id only; acceptable for some tasks).
5. **Severity assignment.**
   - `info` — anchor exists, quote recovered, no issue.
   - `minor` — quote not recovered for a non-blocking layer claim (e.g. `exploratory` / `speculative`).
   - `blocking` — PMID not found OR retracted OR `established`-layer claim quote not recovered. Blocking failures pin `reviewer_overall_verdict: fail` and bubble to Henry L1 (G1/G2/G9 gates).
6. **Overall verdict.**
   - `pass` — zero blocking, all anchors exist + recovered.
   - `pass_with_warnings` — zero blocking, some minor (e.g. exploratory-layer quote miss).
   - `fail` — ≥ 1 blocking.
7. **Output ONLY the JSON object.**

### Mechanical gates this task must satisfy

- **G1 PMIDExistence** — this task implements the upstream evidence for G1. Henry L1 consumes `per_anchor_verdicts[*].existence_verdict`.
- **G2 PMIDQuoteMatch** — this task implements upstream evidence for G2. Henry L1 consumes `quote_recoverability_verdict`.
- **G9 RetractionCheck** — `existence_verdict: retracted` blocks downstream.
- **G11 NoSilentFallback** — if `pubmed_live` retrieval failed, set `summary_for_henry` to flag the integrator failure; do NOT pass-through with training-memory verification. The task must raise rather than silently approve.
- **G13 ReviewerModelDistinct** — `reviewer_model` is asserted distinct from executor's model; if equal, return `reviewer_overall_verdict: fail` with reason "reviewer_model identical to executor — pairing violates G13".

### Reviewer focus (meta-reviewer of this reviewer)

When this task is itself audited by Henry L1, Henry checks:

- All anchors enumerated; no executor anchor silently skipped.
- Live integrator calls actually fired (cache-only verification is insufficient — per memory `feedback_no_offline_only`).
- Retracted PMID detection is hard-blocking, never warning-only.
- Quote-recoverability check used exact substring match, not paraphrase similarity.

### Empty-integrator handling

If `pubmed_live` retrieval failed AND `paperqa_results` is empty:

- `per_anchor_verdicts: []`
- `reviewer_overall_verdict: "fail"`
- `summary_counts.total_anchors: <count>` (from executor output)
- `blocking_failures: [{"anchor_id": "<all>", "reason": "Live PubMed and PaperQA2 integrators returned empty — source verification cannot be performed. Per `feedback_no_offline_only`, this is a blocking integrator failure, not a pass-through."}]`
- `summary_for_henry`: "Source verification could not complete: live PubMed / PaperQA2 integrator down or empty. Pipeline must halt per G11; do NOT silently approve executor output. Patient is sole decision authority; output is non-directive."

The LLM **must not** verify PMID existence from training-memory recall. Source verification is by definition live-integrator-bound; integrator failure means the reviewer fails closed, not open.
