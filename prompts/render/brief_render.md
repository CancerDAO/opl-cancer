# Patient-Brief Assembly (deterministic) — replaces the renderer LLM path

This prompt replaces the rendering reasoning that used to be reachable through
the Python LLM path feeding `src/opl_cancer/glue/renderer.py`
(`PatientBriefRenderer`). **Rendering itself is deterministic** — the original
`renderer.py` performs pure local Jinja2 templating with **no `LLMClient`, no
`.complete()`, no network** (it loads `prompts/delivery/patient_brief.{html,md}.j2`
and calls `.render(context)`). So this is an **assembly spec**, not a generative
writing task: a host-agent assembling the brief MUST produce output structurally
identical to what those Jinja2 templates emit from the same context. Do not
paraphrase, embellish, reorder, or "improve" the wording of the source claims.

---

## Authority boundary (RED LINE)

- You do **not** decide whether a claim is allowed. The 42 deterministic gates in
  `src/opl_cancer/validators/gates/` already ran in Python during
  `_collect_claims`. A blocked claim arrives with its text already replaced by
  `[BLOCKED by <gate>] <message>` and a corresponding Level-3 `risk_card`. You
  render those verbatim — **never** un-block, soften, rewrite, or hide a blocked
  claim or a risk card. Gate verdicts are Python's; your job is layout only.
- You do not invent claims, evidence, PMIDs, or summaries. Every rendered element
  comes from the provided context object.

---

## Inputs (the render context, identical keys to `wave1_runner._collect_claims`)

```json
{
  "patient_code": "<string>",
  "run_id": "<string>",
  "created_at": "<ISO8601>",
  "language": "zh-CN | en | ...",
  "sid_summary": "<PI summary string>",
  "risk_cards": [{"level": 3, "message": "...", "requires_ack": true}],
  "experts": [
    {
      "name": "<expert>",
      "role": "<task_package>",
      "claims": [
        {
          "layer": "established | exploratory | speculative",
          "text": "<claim text, possibly already [BLOCKED by ...]>",
          "evidence": [{"type": "pmid|nct|url|...", "id": "...", "quote": "..."}],
          "reviewer_challenges": ["..."],
          "provenance_hash": "<sha>"
        }
      ]
    }
  ],
  "world_unknown_candidates": [ { ... } ]
}
```

---

## Output: two artifacts, byte-faithful to the Jinja templates

Produce both, writing to the run's `delivery/` directory:

- `patient_brief.md` — match `prompts/delivery/patient_brief.md.j2` exactly.
- `patient_brief.html` — match `prompts/delivery/patient_brief.html.j2` exactly
  (same `<style>` block, same tier badge classes `established/exploratory/speculative`,
  same `.risk-card` / `.world-unknown` structure).

### Assembly order (NON-NEGOTIABLE — mirrors the templates)

1. **Header** — title + `Run {{ run_id }} · {{ created_at }}` for `patient_code`.
2. **Incomplete-run notice** — if `run_incomplete_notice` is present and truthy,
   render the red INCOMPLETE-RUN banner. Otherwise omit.
3. **Risk disclosures** — render every entry in `risk_cards` as a red-bordered
   card, **before** the Summary section. This ordering preserves the
   acknowledgement requirement (`permission_levels` semantics). Never move risk
   cards below the findings.
4. **Summary** — `sid_summary`, verbatim.
5. **Findings by Expert** — for each expert in `experts` (in order), a section
   `<Name capitalized> — <role>`, then each claim as:
   - a 3-tier badge `[{{ claim.layer }}]` + the claim `text` **verbatim**
     (including any `[BLOCKED by ...]` prefix);
   - each `evidence` item: if `type == "pmid"`, a PubMed hyperlink
     `https://pubmed.ncbi.nlm.nih.gov/<id>/` plus the exact `"quote"`; otherwise
     `<type>:<id>` plus the quote. Render the `[[src:...]]` patient-record anchors
     present in the text verbatim — they are part of the provenance chain.
   - if `reviewer_challenges` is non-empty, a "Reviewer challenges:" line joining
     them with `; `;
   - the `provenance: <provenance_hash>` line.
6. **World-Unknown / Speculative Candidates** — only if
   `world_unknown_candidates` is non-empty. Render the full strong-disclaimer
   block ("这不是治疗建议 / THIS IS NOT A TREATMENT RECOMMENDATION"), then each
   candidate with its `[S] speculative` tag, strategy, optional Elo, testability
   path, and anchors marked "未独立校验 / NOT independently verified". If any
   `redacted_drug_names` are present, render the redaction note instead of the
   names.

### Fidelity rules

- Preserve the patient's `language` setting; do not translate source text.
- Do not drop a claim, a piece of evidence, a reviewer challenge, or a risk card
  for brevity. Completeness is the delivery guarantee
  (`tests/test_e2e/test_pipeline_non_bypassable.py` depends on it).
- Do not add commentary, headers, or sections not in the templates.
- If a field is absent, follow the template's `{% if %}` guard (omit that block);
  do not fabricate a placeholder value.

---

## Note for the executing host-agent

This step is layout, not analysis. If you find yourself wanting to reword a claim,
re-rank findings, or judge a risk card, stop — that reasoning belongs to the
expert/reviewer/gate stages upstream, not to rendering. The brief must read as a
faithful transcription of the validated artifacts.
