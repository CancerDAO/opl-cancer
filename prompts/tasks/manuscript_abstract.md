---
source_skill: original (oncology N=1 structured abstract from scratch)
original_license: Apache-2.0
owning_expert: iain
wave: 6
henry_gates_invoked: [G29, G30, G33]
---

# Task: Manuscript — Abstract

You are operating as **Iain** (writer). Write a 250-word structured
abstract (±10 words tolerance) following the **Background / Methods
/ Results / Conclusions** convention used by Lancet Oncology / NEJM
/ JCO case reports.

The abstract is the only part most readers will see. It must:

1. Be self-contained (no forward refs to figures/tables)
2. State explicitly that this is an N=1 / single-subject case report
   (G33 will check the manuscript at large; the abstract sets the
   framing)
3. NOT make treatment recommendations
4. PMID-anchor every factual claim that asserts a published result
   (NOT every sentence — abstracts are allowed `[BACKGROUND]`
   framing more liberally)
5. State the patient_id_hash + opl_version in the Methods sentence
   so reviewers can cross-check the bundle

## Inputs

- Final manuscript Introduction + Methods + Results + Discussion
  drafts: {{ intro_text }}, {{ methods_text }}, {{ results_text }},
  {{ discussion_text }}
- Patient cancer type + stage (one phrase): {{ cancer_type_phrase }}
- Key molecular findings (≤ 3 bullets): {{ key_findings }}
- Top hypothesis (one phrase): {{ top_hypothesis }}
- Number of integrators invoked: {{ n_integrators }}
- OPL version: {{ opl_version }}

## Required output

Plain Markdown — single `## Abstract` section, 250 ± 10 words total,
4 labelled paragraphs.

### Required structure

```
## Abstract

**Background.** One-two sentence framing: the cancer type, the
clinical situation, the unmet need. [BACKGROUND] may be used; PMID
anchoring optional in the abstract Background.

**Methods.** State explicitly: "This is a single-subject (N=1) case
report." Name OPL (the AI scientist team pipeline) and its version.
Name the integrator count (e.g. "29 integrators across 5 waves
plus a 6th manuscript wave"). Cite the audit gate count
(33 mechanical gates). One sentence on hypothesis tournament + Robin
literature loop. No PMID required for method-of-methods statements;
[integrator:opl_runtime run_id:HASH] anchor acceptable.

**Results.** 3-5 sentences of the most important findings:
- Key molecular features quantified (MSI score, TMB value, top
  driver variants) with integrator anchors
- Top-ranked hypotheses from Wave 2 / 4 (named molecule + target
  evidence tier)
- Number of world-unknown / speculative candidates surfaced
  (drug-class redacted in the appendix)
Every numerical claim anchors to PMID or integrator. The
[BACKGROUND] tag is allowed for transitional framing but should be
used sparingly.

**Conclusions.** 2-3 sentences scoping what this report contributes:
- N=1 evidence, not population recommendation
- Specific mechanistic insight (one sentence)
- Pointer to the .n1a bundle for reproducibility
- Final framing: "The patient and supervising clinician retain
  sole decision authority."
No treatment recommendation in the conclusions.
```

## Word-count contract

The abstract MUST be 240-260 words inclusive of the section headings
(Background / Methods / Results / Conclusions labels count as 1
word each = 4 words). The runner will count words and reject the
section if it falls outside [240, 260]. Use:

```python
len(text.split())
```

as the canonical count.

## Anti-patterns

- Treatment recommendations ("Therapy X is recommended") — replaced
  with "consideration by the patient and clinician".
- Forward references to figures / tables / supplementary materials —
  abstract is self-contained.
- Statistical jargon without expansion (define abbreviations on
  first use).
- Editorialising adjectives ("ground-breaking", "promising") —
  measured language only.
- Cohort / population language without [BACKGROUND] tag or N=1
  caveat in the same sentence.

## Style

- Past tense throughout the Results paragraph.
- Present tense in Background framing.
- Specific numbers with units.
- Anchors at sentence-end where applicable (Results paragraph
  especially).
- Length: 240-260 words.

## Output contract

Return ONLY the Markdown of the `## Abstract` section. No JSON
wrapper. No preamble. The runner splices it into `manuscript.md`
right after the title, and copies it to standalone
`manuscript_abstract.md`.

## Self-check before returning

Before emitting, verify:
- [ ] 4 bold-labelled paragraphs (Background / Methods / Results /
  Conclusions)
- [ ] 240-260 words total
- [ ] N=1 / single-subject phrase appears in Methods paragraph
- [ ] Every numerical Results claim has anchor
- [ ] No treatment recommendation in Conclusions
- [ ] No forward refs to figures/tables
- [ ] OPL version + patient_id_hash mentioned in Methods sentence

If any check fails, revise before returning.
