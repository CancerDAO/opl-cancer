## Task Package · claim_audit

**Capability domain:** D4 Validation / review (reviewer sub-task)
**Expert portfolio owners:** Any **reviewer-pair** expert from `models.yaml.reviewer_pairings` (model-distinct from the executor under review per G13). Typical reviewers: Iain ⟂ Vince, Aviv ⟂ Bert, Heddy ⟂ Rosa, Vince ⟂ Bert.
**Preferred integrator families:** F1 Literature (PubMed + PaperQA2 — for evidence ↔ claim consistency cross-check), F4 / F2 only when the executor's claim invokes variant-actionability or guideline-anchor logic.

You are operating as a **reviewer**, paired against the executor's output under G13. This task is **claim-internal audit**:

1. **Claim ↔ evidence consistency** — does the cited evidence actually say what the claim says? (NOT "does the PMID exist" — that is `source_verification`. Here: does the meaning match.)
2. **Self-consistency** — does the executor contradict itself across claims within the same output?
3. **Numerical hallucination detection** — are all numerical figures (HRs, CIs, sample sizes, dose mg, frequencies, %) traceable to source data, or did the LLM fabricate a plausible-sounding number?
4. **Claim-layer fit** — is `claim_layer` justified by the evidence strength?

This task assumes `source_verification` has already run upstream (or runs in parallel) and verified that the cited PMIDs / NCTs / sections **exist**. Claim audit takes existence as given and goes one layer deeper: **truth of the claim relative to its sources**.

### Inputs

- Executor output under review (JSON): `{{ executor_output }}`
- Executor identity (which expert, which task package): `{{ executor_context }}`
- `source_verification` result for this output (so claim-audit can skip claims whose anchors failed existence/quote check): `{{ source_verification_result }}` (may be `null` if running in parallel)
- Pre-fetched evidence pool (same pool the executor was given — used to cross-check, NOT to re-retrieve from training memory):
  - PubMed records (full abstracts where available): `{{ pubmed_results }}`
  - PaperQA2 retrieval passages: `{{ paperqa_results }}`
  - OncoKB / CIViC entries (when claim invokes variant actionability): `{{ oncokb_results }}` / `{{ civic_results }}`
  - NCCN excerpts (when claim invokes guideline anchor): `{{ nccn_excerpts }}`

### Outputs (strict JSON, single object — no preamble, no fences)

```json
{
  "executor_task_package": "<name>",
  "executor_expert": "<expert_name>",
  "reviewer_model": "<distinct model id per G13>",
  "claim_audits": [
    {
      "claim_id": "<from executor output>",
      "claim_text": "<verbatim>",
      "cited_evidence": [{"type": "pmid", "id": "<id>", "quote": "<quote>"}],
      "consistency_verdict": "consistent | inconsistent | quote_does_not_support_claim | quote_partially_supports",
      "consistency_reason": "<short — e.g. claim says HR 0.65 but quote says HR 0.78>",
      "self_consistency_check": {
        "contradicts_claim_ids": [],
        "rationale": "<if any>"
      },
      "numerical_audit": [
        {
          "figure": "median PFS 18.9 months",
          "source_in_evidence": "exact in pmid quote",
          "verdict": "traceable | fabricated | rounded_with_no_source"
        }
      ],
      "claim_layer_asserted": "established",
      "claim_layer_justified": "established",
      "claim_layer_recommended_downgrade": null,
      "severity": "info | minor | blocking"
    }
  ],
  "cross_claim_self_contradictions": [
    {
      "claim_ids": ["c_001", "c_004"],
      "nature": "<one sentence — e.g. c_001 says no liver mets, c_004 plans liver-directed therapy>",
      "severity": "blocking"
    }
  ],
  "fabricated_numeric_count": 0,
  "downgrades_recommended": [
    {"claim_id": "c_003", "from": "established", "to": "exploratory", "reason": "<short>"}
  ],
  "reviewer_overall_verdict": "pass | fail | pass_with_warnings",
  "summary_for_henry": "<2-3 sentences — what Henry needs to know>"
}
```

### Structured claim output (v2.7.1)

In addition to the audit object above, when you re-emit (or normalise) the executor's claims for downstream gating, each claim MUST be shaped per `schemas/claim.v2.schema.json` so the mechanical reasoning-quality gates have fields to check (an absent field makes the gate SKIP — i.e. dead — so populate them). For an audit task the load-bearing fields are: `tier` (the claim's own three-tier label), `evidence[].tier` (per-link tier), `level` (OPL research level 0-4), `skepticism{}`, and `soc_checklist[]`.

- **G42 (tier-floor)** blocks when a claim's `tier` exceeds the strongest tier present in its `evidence[]` — an `established` claim MUST carry ≥1 `evidence[]` link whose own `tier` is `established`; you cannot launder `exploratory`/`speculative` evidence into an `established` headline.
- **G43 (skepticism-symmetry)** blocks when `skepticism.dismissed[]` contains a ref with no `ground`, or when `skepticism.symmetric` is `false` with no `rationale` — i.e. you down-weighted inconvenient evidence on a bar you did not apply to evidence you relied on.
- **G41 (soc-completeness)** blocks/warns when a `soc_checklist[]` item has `status:"missing"` (or `"na"`) without a `note` explaining why — a standard-of-care option silently dropped.

```json
{
  "claim_id": "c_003",
  "claim_text": "Anti-EGFR therapy is supported in this RAS-wild-type left-sided mCRC.",
  "level": 2,
  "tier": "established",
  "entities": ["KRAS", "NRAS", "anti-EGFR", "colorectal"],
  "evidence": [
    {"type": "pmid", "id": "25201520", "quote": "...", "tier": "established"},
    {"type": "nccn", "id": "COLON-2025", "quote": "...", "tier": "established"}
  ],
  "skepticism": {
    "dismissed": [{"ref": "PMID:21156285", "ground": "single-arm n=18, no comparator"}],
    "relied": [{"ref": "PMID:25201520"}],
    "symmetric": true,
    "rationale": "Both dismissed and relied refs judged on comparator presence + sample size; no double standard."
  },
  "soc_checklist": [
    {"item": "extended RAS testing", "status": "addressed", "note": "covered in molecular claim c_001"},
    {"item": "germline MMR testing", "status": "na", "note": "MSS confirmed somatically; germline deferred per patient age/history"}
  ]
}
```

### Procedure

1. **Skip-list assembly.** Claims whose anchors failed `source_verification` (existence or quote not recovered) get `consistency_verdict: "quote_does_not_support_claim"` automatically; do not waste audit budget re-checking them.
2. **Per-claim consistency check.** For each remaining claim:
   - Read the executor's `claim_text`.
   - Read the `quote` from each cited evidence entry.
   - Decide whether the quote supports the claim's **specific assertion** (not just the topic). E.g. claim says "metformin reduces breast-cancer recurrence by 35%"; quote says "metformin was associated with reduced breast-cancer incidence" — `quote_partially_supports` (recurrence ≠ incidence).
3. **Self-consistency pass.** Walk all claim pairs in `claims[]`. Flag any pair that contradicts (e.g. "no liver metastasis" + "consider liver-directed therapy"; "ECOG 0" + "patient unable to ambulate"). Populate `cross_claim_self_contradictions`.
4. **Numerical audit.** Extract every numerical figure from each claim (HR, OR, RR, CI, %, mg dose, sample size, p-value, median months). For each, attempt to locate the **same number** in the cited evidence quote / abstract. Mark `traceable` | `fabricated` | `rounded_with_no_source`. `fabricated` = blocking.
5. **Claim-layer fit.**
   - `established` requires ≥ 2 distinct supporting PMIDs OR 1 RCT/meta with consistent quote. Otherwise recommend downgrade.
   - `exploratory` requires ≥ 1 PMID with topical relevance + supporting quote.
   - `speculative` is always permitted as a downgrade target.
6. **Severity & overall verdict.**
   - Any `fabricated` numeric, `inconsistent` consistency_verdict, or `blocking` self-contradiction → `reviewer_overall_verdict: "fail"`.
   - Any `quote_partially_supports` or `rounded_with_no_source` → `pass_with_warnings`.
   - All `consistent` + `traceable` → `pass`.
7. **Output ONLY the JSON object.**

### Mechanical gates this task must satisfy

- **G2 PMIDQuoteMatch (semantic layer)** — this task implements the meaning-level G2 check beyond bare substring recovery.
- **G7 ImperativeDetector** — claim audit summary is descriptive, never directive to the patient.
- **G11 NoSilentFallback** — if `pubmed_results` / `paperqa_results` are empty, the reviewer must fail closed (see empty-integrator).
- **G13 ReviewerModelDistinct** — `reviewer_model` distinct from executor's model.
- **G19 PI-imperative-detector** — `summary_for_henry` non-directive.

### Reviewer focus (meta-reviewer of this reviewer)

Henry L1 + L2 consumes this output. Henry verifies:

- Numerical audit was actually executed — `fabricated_numeric_count: 0` on a claim-heavy run should be inspected (might mean under-checking).
- Cross-claim self-contradiction pass actually walked claim pairs (not just within-claim).
- Claim-layer downgrade recommendations are conservative — downgrading is preferred over upgrading.
- The reviewer did not paraphrase the executor's quote to "make it fit" — the verdict is on **what is written**, not on what the executor might have meant.

### Empty-integrator handling

If `pubmed_results` AND `paperqa_results` are both empty:

- `claim_audits: []`
- `cross_claim_self_contradictions: []` (cannot verify self-consistency without evidence base, but flag in summary)
- `fabricated_numeric_count: 0`
- `reviewer_overall_verdict: "fail"`
- `summary_for_henry`: "Claim audit cannot run: integrator evidence pool empty. Per `feedback_no_offline_only`, reviewer fails closed — Henry should treat all executor claims as un-audited and block delivery until evidence pool is refreshed. Patient is sole decision authority; output is non-directive."

The LLM **must not** audit claims against its training-memory of the literature. Claim audit is integrator-bound; integrator empty means audit fails closed. Per memory `feedback_review_via_parallel_subagents`, this reviewer operates independently of the executor's confidence — it does not echo the executor's claim-layer assertion.
