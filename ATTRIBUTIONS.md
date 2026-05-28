# Attributions

OPL for Cancer is Apache-2.0 licensed (see `LICENSE`). It vendors and adapts
material from a number of open-source upstreams; this file lists every
upstream credit. See `docs/adr/0022-bio-skills-vendoring.md` for the
v2.2 bio-skills governance rationale, and
`docs/adr/0023-wave6-manuscript-and-n1a-bundle.md` for the v2.3 Wave 6
+ `.n1a` rationale.

---

## v2.3.0 — Wave 6 Manuscript + `.n1a` Bundle (2026-05-28)

### Leey21 / awesome-ai-research-writing

* Upstream: <https://github.com/Leey21/awesome-ai-research-writing>
  (25.9K stars — widely-used research-writing prompt collection)
* License: **license-pending-upstream-grant** — we have opened a
  request issue with the upstream for explicit MIT or CC0 grant;
  fallback if no response by v2.4 ship: rewrite borrowed prompts
  from scratch. The borrowed prompts as shipped in v2.3 are
  **paraphrased + oncology-adapted**, not verbatim, which we
  understand to be transformative use; but the explicit license
  grant is still pending.
* Borrowed prompts (4): (1) Zh→En LaTeX translation prompt
  (adapted for the introduction's bilingual framing where present),
  (2) general polish prompt (adapted into the abstract self-check
  loop), (3) chart-type recommendation prompt (adapted into
  `figure_caption.md`'s figure-type-specific rules), (4)
  reviewer-style critique prompt 16 (inverted and adapted into
  `manuscript_discussion.md`'s mechanistic-interpretation framing).
* Each borrow is acknowledged in the corresponding task-package
  frontmatter via `source_skill:` + `original_license:` fields.

### Tool chain credits (v2.3 additions)

* **jsonschema (Python)** — Berman 2024;
  <https://github.com/python-jsonschema/jsonschema>. MIT.
  Used by `n1a_bundle_writer` to validate the manifest against
  `schemas/n1a_bundle.v0.1.schema.json` before zipping.
* **zipfile (Python stdlib)** — used by `n1a_bundle_writer` to pack
  the bundle. No external dep; Python license.

The Wave 6 manuscript task packages (`manuscript_introduction`,
`_methods`, `_results`, `_discussion`, `_limitations`, `_abstract`,
`citation_assembly`, `figure_caption`) are otherwise original
authoring by the OPL maintainers, with each frontmatter declaring
either `source_skill: original` or the specific upstream borrow.

---

## v2.2.0 — Equipped Experts (2026-05-28)

### BioTender-max / awesome-bio-agent-skills

* Upstream: <https://github.com/BioTender-max/awesome-bio-agent-skills>
* License: **CC0-1.0** (Public Domain Dedication)
* Adaptation: vendored as OPL **task packages** under `prompts/tasks/` plus
  deterministic Python wrappers under `src/opl_cancer/integrators/`. Each
  task-package frontmatter carries `source_skill:` + `original_license:`
  fields referencing the original path.

Sourced skills (v2.2):

| OPL task package | Upstream source skill |
|---|---|
| `prompts/tasks/msi_detection.md` | `bio-msi-detection` |
| `prompts/tasks/tmb_calculation.md` | `bio-tumor-mutational-burden` |
| `prompts/tasks/cosmic_signature_extraction.md` | `bio-somatic-signatures` |
| `prompts/tasks/acmg_germline_classification.md` | `bio-acmg-classification` |
| `prompts/tasks/opentargets_evidence.md` | `query-opentarget` |
| `prompts/tasks/biostats_survival.md` | `bio-clinical-biostatistics-survival-analysis` |
| `prompts/tasks/biostats_subgroup.md` | `bio-clinical-biostatistics-subgroup-analysis` |
| `prompts/tasks/pharmacogenomics_cpic.md` | `bio-pharmacogenomics` |

OPL re-implements the numerical layer (samtools / lifelines /
SigProfilerAssignment wrappers etc.) deterministically; only the
*interpretation* prompt is adapted from the upstream skill.

### Tool chain credits

The integrators wrap (or depend on the existence of) the following tools.
None are vendored into the repo; they are referenced by API:

* **MSIsensor / MSIsensor-pro** — Niu 2014 (PMID: 24371154);
  <https://github.com/xjtu-omics/msisensor-pro>. GPL-3.0.
* **SigProfilerAssignment** — Alexandrov 2020 (PMID: 32025018);
  <https://github.com/AlexandrovLab/SigProfilerAssignment>. BSD-2-Clause.
* **lifelines** — Davidson-Pilon 2019 (JOSS 10.21105/joss.01317);
  <https://github.com/CamDavidsonPilon/lifelines>. MIT.
* **CPIC guidelines** — <https://cpicpgx.org/>. Each guideline is its own
  citation (see `src/opl_cancer/integrators/cpic.py` for per-guideline
  PMID anchors).
* **Open Targets Platform** — Ochoa 2023 (PMID: 36399499);
  <https://platform.opentargets.org/>. Apache-2.0 platform + CC0 data.
* **ClinVar** — NCBI; public-domain US government data.
* **PubMed / PMC OA** — NCBI; public-domain US government data.
* **VarSome** — Saphetor; queried at runtime via API. Vendored interpretation
  is the ACMG 2015 (Richards PMID: 25741868) decision table only.
* **matplotlib** — Hunter 2007; <https://matplotlib.org/>. PSF-style license.

---

## v2.1.0 — Truthful Execution (2026-05-28)

No new upstream vendoring; v2.1 was internal-only (CLI executor split,
goal-router, reviewer pairing, fakery sniffer).

---

## v2.0.0 — Paradigm Shift (2026-05-22)

* PrimeKG schema (Chandak 2023 PMID: 36702940) — Maya uses the PrimeKG
  topology for KG-synergy reasoning. PrimeKG is CC0-1.0; OPL references
  it via the `integrators/primekg.py` integrator (live wiring in progress).
* Co-Scientist Elo tournament loop (Google AI 2024-2025) — concept only.

---

## Pre-v2.0

See individual ADRs under `docs/adr/` for per-feature attribution.
