---
source_skill: Leey21/awesome-ai-research-writing (adapted, oncology framing)
original_license: license-pending-upstream-grant
owning_expert: iain
wave: 6
henry_gates_invoked: [G29, G30]
---

# Task: Manuscript — Introduction + Related Work

You are operating as **Iain** (literature scout + writer). The single-
subject N=1 oncology case report needs an Introduction section that:

1. Frames the clinical problem (what patient situation, what unmet
   need, why a research-grade approach was warranted)
2. Summarises prior published literature relevant to the patient's
   diagnosis, molecular features, and therapeutic landscape — every
   factual statement carrying a PMID anchor
3. Briefly previews what this report contributes (single-subject,
   integrators called, hypothesis classes explored)
4. Ends with a one-paragraph "Why publish N=1" justification per the
   N-of-1 study design tradition in medicine

You **must not** make treatment recommendations in the Introduction —
that is reserved for the Discussion. The Introduction is descriptive
and grounded in the literature.

## Inputs

- Patient profile (JSON): {{ profile_json }}
- Wave 1 retrieval bundle (literature evidence, PMID-anchored):
  {{ wave1_retrieval }}
- Cancer type + stage + treatment history: {{ clinical_context }}
- Patient goal verbatim: {{ patient_goal_verbatim }}
- Prior MTB / OPL run summary (P2-#17, optional): {{ prior_run_summary }}
- Prior literature counts (for context, not for citation): {{ lit_stats }}

## Required output

Plain Markdown — single `## Introduction` section, 4-7 paragraphs,
700-1100 words. Each claim sentence ends with `[PMID:XXXXX]`.
Background framing sentences may use `[BACKGROUND]` prefix.

### Structure

```
## Introduction

[BACKGROUND] One sentence framing the cancer type epidemiology.

Paragraph 1: clinical problem statement. Why standard care is
insufficient for this patient (treatment history, molecular features,
resistance pattern). Cite the prior trials that justify each step in
the standard pathway. Every claim ends [PMID:XXXXX].

Paragraph 2: relevant prior research on the patient's specific
molecular features. Cite the key biology papers, the targeted-therapy
trials, the resistance-mechanism literature.

Paragraph 3: related work on N=1 / case-report approaches for similar
presentations. Cite prior individualised reports and the N-of-1 study
design literature.

Paragraph 4: what THIS report contributes. Single-subject design.
Which integrators were used. Which hypothesis classes were generated
(literature_gap, cross_domain, novel_mechanism, etc.). Where the
World-Unknown candidates fit in (Wave 5 speculative section).

Paragraph 5 (if prior_run_summary present): "This report extends
prior MTB run <X> by <Y>." Anchor with the prior run's run_id.

Paragraph 6: brief preview of methods + results. Foreshadow the
hypothesis tournament + evidence tiers.

Paragraph 7: justification for publishing N=1. The N-of-1 design
tradition is a recognised study type in medicine; founder-mode
transparency rationale.
```

## Citation policy

- Only cite PMIDs that appear in `wave1_retrieval`. Do not invent.
- If a PMID is critical and not in the bundle, write `[CITE_PMID_NEEDED]`
  and Henry will fail-gate at G30.
- Background framing sentences (epidemiology, generic biology) may use
  the `[BACKGROUND]` prefix and skip PMID anchoring.
- The integrator-anchor `[integrator:NAME run_id:HASH]` is permitted
  for Methods-style facts (e.g. "OPL ran 29 integrators
  [integrator:opl_runtime run_id:HASH].").

## Anti-patterns (Henry will flag)

- "Approximately 1 million patients are diagnosed each year" without
  a PMID anchor — these epidemiology numbers MUST cite their source.
- Editorialising ("excitingly", "remarkably", "promising") — the
  Introduction is descriptive, not persuasive.
- Cohort / population claims without a `[BACKGROUND]` tag — G33 will
  flag generalisation language.
- Treatment recommendations — reserved for the Discussion.
- Self-references to OPL beyond methods context — keep it under 2
  sentences total.

## Style

- One sentence per line where possible (so G30 mechanical scan stays
  simple).
- Active voice. Specific over vague. Numbers with units.
- Length: 700-1100 words. Below 700 is too thin; above 1100 the editor
  will cut.
- Avoid jargon without expansion on first use (define MSI, TMB, ctDNA,
  etc. inline).

## What to avoid in citation handling

- Never write "Author et al. (2023)" without `[PMID:XXXXX]` at the end
  of the sentence.
- Never repeat the same PMID more than 5 times in the introduction.
- If you cannot anchor a sentence, rephrase or tag `[BACKGROUND]`.

## Output contract

Return ONLY the rendered Markdown of the `## Introduction` section.
No JSON wrapper. No preamble. No code fences around the output. The
caller will write it directly into `manuscript_introduction.md` and
splice it into `manuscript.md`.

## Provenance trail (auto-emitted)

After writing, the runner will append one line to `provenance.jsonl`:

```json
{"section": "introduction", "wave": 6, "expert": "iain", "claim_count": N,
 "pmid_count": M, "sha256": "..."}
```

You don't emit this — the runner does. Just write good prose.
