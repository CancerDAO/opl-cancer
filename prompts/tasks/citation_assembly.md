---
source_skill: original (citation assembly via PubMed esummary; reuses G1+G2 verifiers)
original_license: Apache-2.0
owning_expert: henry-adjacent
wave: 6
henry_gates_invoked: [G1, G2, G30]
---

# Task: Citation Assembly — PMIDs → references.bib

You are the **citation assembler** (Henry-adjacent role — runs
adjacent to Henry's audit pipeline). Take every PMID cited across
Waves 1-5 of the run and produce a `references.bib` BibTeX file
ready for inclusion in the Wave 6 manuscript bundle.

Per ADR-0023 (spec §5.2) you may NOT use a third-party BibTeX
library. You generate the BibTeX entries directly from the PubMed
esummary JSON. This keeps the runtime dependency footprint at zero
beyond `httpx` (already in the OPL dependency set).

You also re-run G1 (PMID existence) and G2 (PMID quote match) on
every citation, so the manuscript-quality citation set matches the
gate-quality citation set.

## Inputs

- Full PMID list extracted from `manuscript.md` + all
  `manuscript_*.md` sections + every wave-1..5 task report:
  {{ pmid_list }}
- Optional first-author hints per PMID (from upstream waves where
  the quote-match gate already ran): {{ author_hints }}
- PubMed esummary results (pre-fetched from `integrators/pubmed.py`,
  keyed by PMID): {{ pubmed_esummary }}
- OPL version: {{ opl_version }}
- Run_id: {{ run_id }}

## Required output

A single `references.bib` file. UTF-8. BibTeX `@article{...}` entries
sorted by PMID ascending. One entry per cited PMID — no duplicates.

### Per-entry BibTeX shape

```bibtex
@article{pmid_32179615,
  title       = {Pembrolizumab in microsatellite instability-high
                 advanced colorectal cancer},
  author      = {Le, Dung T. and Uram, Jennifer N. and Wang, Hao and others},
  journal     = {New England Journal of Medicine},
  year        = {2020},
  volume      = {372},
  pages       = {2509-2520},
  pmid        = {32179615},
  doi         = {10.1056/NEJMoa1500596},
  note        = {Verified by OPL G1+G2; first_author_match = pass}
}
```

Field mapping rules (from esummary JSON):

| BibTeX field | esummary field | Fallback |
|---|---|---|
| `title` | `title` | `articletitle` |
| `author` | join `authors[*].name` w/ " and " (≤ 6 then "and others") | `authorlist` |
| `journal` | `fulljournalname` | `source` |
| `year` | first 4 chars of `pubdate` | `epubdate[:4]` |
| `volume` | `volume` | empty |
| `pages` | `pages` | empty |
| `doi` | `articleids[*]` where `idtype == "doi"` | empty |
| `pmid` | the key from input | required |

Special characters: escape `&` → `\&`, `%` → `\%`, `$` → `\$`,
`_` → `\_`, `#` → `\#`. Replace en-dash / em-dash with `--`.

## G1 + G2 reuse

For each PMID:

1. **G1 existence**: confirm the PubMed esummary returned a non-empty
   `title` field. If empty / 404 / "error", flag the PMID in
   `citation_assembly_report.json` as `g1_fail: PMID_NOT_FOUND` and
   DO NOT include it in references.bib. Henry will see the report and
   force a re-cite or a remove-citation patch.
2. **G2 quote-match**: if `author_hints[pmid]` provides a first-author
   surname, verify it matches `authors[0].name` (case-insensitive,
   surname only). Mismatch → log `g2_fail: AUTHOR_MISMATCH`. Include
   the entry but flag the report.

## Required side output

In addition to `references.bib`, emit
`citation_assembly_report.json`:

```json
{
  "opl_version": "{{ opl_version }}",
  "run_id": "{{ run_id }}",
  "pmid_count": 42,
  "verified": [{"pmid": "32179615", "g1": "pass", "g2": "pass"}, ...],
  "g1_fail": [{"pmid": "99999999", "reason": "PMID_NOT_FOUND"}],
  "g2_fail": [{"pmid": "12345678", "expected_author": "Smith",
               "actual_author": "Wong"}],
  "ts": "2026-05-28T10:11:12.000Z"
}
```

## Anti-patterns

- DO NOT invent PMIDs. If esummary returns 404, the PMID stays out of
  references.bib and is flagged in the report.
- DO NOT silently fix author mismatches — flag them. Henry decides.
- DO NOT include duplicate entries (multiple citations of the same
  PMID → one entry).
- DO NOT include entries for `[CITE_PMID_NEEDED]` placeholders —
  these are intentional gaps that Henry will block at G30.

## Style

- BibTeX entries sorted by PMID ascending.
- 2-space indent on field rows; trailing comma after every field.
- Unicode names allowed; do not LaTeX-escape diacritics. Pandoc /
  biber handle UTF-8.
- Long titles / author lists wrap inside the braces; preserve
  whitespace as-is.

## Output contract

Return TWO files:
1. `references.bib` — full BibTeX text
2. `citation_assembly_report.json` — verification log

The runner writes both into `patients/<id>/triggers/<run_id>/`. The
`.bib` becomes part of the n1a bundle; the report stays alongside
HENRY_AUDIT.json for the audit trail.

## What the runner will check after you return

- `references.bib` parses (open-brace count == close-brace count).
- Every PMID in `pmid_list` is either in `references.bib` OR in
  `g1_fail` / `g2_fail`.
- No entry has empty `title` or empty `author`.

If any of these fails, the runner raises `CitationAssemblyError` and
the wave6 runner rolls back the manuscript commit (matching
v2.2 P1-#16 delivery atomicity).
