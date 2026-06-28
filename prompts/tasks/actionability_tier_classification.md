# Task: actionability_tier_classification (E3 / ADR-0039)

Classify each world-unknown / speculative candidate's testability path into an
actionability tier by REASONING about how fast a patient could actually act on
it — not by keyword matching. This replaces the deleted `_TIER_KEYWORDS`
substring table (de-scripting: judgment belongs to the LLM, not a keyword list).

## Reason about (do NOT pattern-match on words)

- **Assay / data turnaround:** is this a standard lab order with a days-level
  result, a weeks-level organoid/IHC build, a months-level PDX/CRISPR/IND-enabling
  program, or a purely computational/in-silico signal with no patient-level path?
- **Regulatory / access reality:** is the drug/assay marketed and orderable now,
  expanded-access/trial-gated (weeks–months), or pre-clinical (no human path)?
- **Data provenance:** a DepMap/TCGA/KG-edge signal is research-only until it has
  a patient-level assay attached.

## Output

Set `actionability_tier` on each candidate to one of:
`actionable_this_week | weeks | months_or_more | research_only`.

## Hard safety floor (enforced deterministically by render_bridge — do not fight it)

A SPECULATIVE [S] candidate may NEVER be surfaced as `actionable_this_week`,
even if its assay is a same-week lab order: acting on an unproven hypothesis is
not a this-week clinical decision. The renderer floors any speculative
`actionable_this_week` to `weeks`. Pick the honest tier; the floor is a backstop,
not a license to over-promise.

## Rule

Output ONLY the tier assignment per candidate. When you cannot justify a faster
tier, choose the more conservative one — never inflate actionability.
