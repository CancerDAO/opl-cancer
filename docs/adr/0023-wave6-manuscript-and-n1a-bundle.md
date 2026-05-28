# ADR-0023: Wave 6 Manuscript + `.n1a` Bundle

**Status**: Accepted (v2.3.0 ships this)
**Date**: 2026-05-28
**Supersedes**: none (extends ADR-0021 + ADR-0022)
**Superseded by**: none yet
**Authors**: zwbao (鲍志炜, CancerDAO founder)
**Spec**: `/Users/baozhiwei/docs/superpowers/specs/2026-05-28-opl-v2.1-to-v2.4-design.md` §5

---

## Context

Through v2.2, OPL ended a session with the Wave 5 dual brief
(`patient_plain_brief.md` + `patient_pi_brief.md`). That output was
patient-facing and clinician-facing but **not publication-grade**. The
007-zhiqiang post-mortem named "no manuscript surface" as the most
visible gap: the patient invested 90 minutes in the run, the OPL
team produced research-grade evidence, and the final delivery was
prose without:

- A canonical citation set (BibTeX `references.bib`)
- A self-contained reproducibility statement
- A figure inventory with reproducers
- An explicit ethics + AI-authorship declaration
- A bundle format that could be submitted to a preprint platform
- A provenance log linking every claim to its wave, expert, and PMID

v2.3 closes this gap with a **Wave 6** that emits a preprint-style
draft + a self-contained `.n1a` bundle. The bundle format is
intentionally separate from any specific platform (v2.4 will ship
the N1Arxiv platform that consumes `.n1a` bundles).

The "manuscript" framing matters: it forces every claim to be
PMID-anchored or integrator-anchored. The mechanical anchor is the
honesty knob. Without it the LLM writes plausible prose at the cost
of provenance.

## Decision

### Wave 6 architecture (sibling to Wave 5)

Add a new wave under `src/opl_cancer/glue/wave6_runner.py` that:

1. Refuses to start unless Wave 5 has shipped both briefs.
2. Runs **5 new mechanical gates** (G29-G33) against the bundle root.
3. Merges G29-G33 results into `HENRY_AUDIT.json`.
4. Aggregates the session's `cost_log.jsonl` into the manifest.
5. Builds a schema-validated `<id>_<date>.n1a.zip` via the new
   `N1ABundleWriter`.

Wave 6 has three modes:

| Mode | Behavior |
|---|---|
| `dry_run` | Return planned steps; no disk touch. |
| `draft` | Scaffold stubs for any missing artifact; gates may fail but bundle still emits with a draft marker. |
| `final` | Strict; any gate `block=True` raises `Wave6Failure` and rollback fires. |

### 5 new mechanical gates (G29-G33)

| Gate | Failure mode | Check |
|---|---|---|
| **G29** `manuscript_authorship_disclosed` | F-WAVE6-AUTHORSHIP | `ai_authorship_disclosure.md` present + CRediT contribution table + attestation "no human author beyond patient & supervising clinician" |
| **G30** `claim_pmid_anchored` | F-WAVE6-CLAIM-UNANCHORED | Every claim sentence in `manuscript.md` ends with `[PMID:XXXXX]` or `[integrator:NAME run_id:HASH]`; `[BACKGROUND]` exempts framing prose |
| **G31** `figure_reproducible` | F-WAVE6-FIG-REPRO | Each `figures/fig_N.png` has matching `figures/fig_N.py`; stochastic reproducers must declare `random_seed = X` |
| **G32** `data_availability_declared` | F-WAVE6-DATA-AVAILABILITY | `reproducibility.md` lists every data source with tier (`public` / `DUA` / `patient-private`); patient-private must be labelled |
| **G33** `n1_design_transparent` | F-WAVE6-N1-GENERALIZATION | Methods text explicitly declares "single-subject (N=1) design"; cohort/population language without same-sentence caveat is flagged |

Total mechanical gate count: **28 → 33**.

### `.n1a` bundle format (schema v0.1)

New JSON Schema at `schemas/n1a_bundle.v0.1.schema.json`. Required
manifest fields:

```
schema_version: "0.1"
opl_version: "2.3.0"
patient_id_hash: SHA-256(patient_code)[:16]
generated_at: ISO-8601 UTC
data_source: "real_patient" | "reference_case" | "synthetic" | "methodology_demo"
file_index: [<relative paths>]
sha256s: { <relative path>: <sha256> }
```

Optional fields: `run_id`, `cost_summary`, `henry_audit_summary`,
`extends_prior_run`, `banner`.

Bundle required files (writer fails if any missing):
- `manuscript.md`
- `ai_authorship_disclosure.md`
- `reproducibility.md`
- `HENRY_AUDIT.json`

### 8 new Wave 6 task packages

| Package | Owning expert | Gates |
|---|---|---|
| `manuscript_introduction.md` | Iain | G29, G30 |
| `manuscript_methods.md` | Aviv | G29, G30, G32, G33 |
| `manuscript_results.md` | Aviv | G29, G30, G31 |
| `manuscript_discussion.md` | Vince | G29, G30, G33 |
| `manuscript_limitations.md` | Henry | G29, G30, G33 |
| `manuscript_abstract.md` | Iain | G29, G30, G33 |
| `citation_assembly.md` | Henry-adjacent | G1, G2, G30 |
| `figure_caption.md` | Aviv | G30, G31 |

Total package count: **54 → 62**.

### Drug-class redaction in `world_unknown_appendix.md`

The Wave 5 World-Unknown / Speculative Candidates section ships a
copy into Wave 6's `world_unknown_appendix.md` with **drug-class
redacted** (matches the existing G24 + the N1Arxiv ethics policy).
The publication surface treats speculative candidates as research
directions, not treatment suggestions.

### P2 fixes folded into v2.3

| # | Implementation |
|---|---|
| **#17** Prior-run ingestion | `src/opl_cancer/plan/prior_run_ingestion.py` ingests `runs/<prior>/chair_final_report.md`; auto-detected by Wave 6 runner; carried into `manifest.extends_prior_run` |
| **#18** Reference-case banner | `N1ABundleWriter` injects banner into `manuscript.md` header AND `figure_render.watermark_directory()` overlays diagonal banner on every fig PNG |
| **#20** Cost tracking | `src/opl_cancer/memory/cost_tracker.py` append-only `cost_log.jsonl`; aggregated into `manifest.cost_summary` (total_usd + tokens + by_model + by_wave + by_expert) |
| **#21** Patient value hierarchy | `prior_run_ingestion.patient_value_hierarchy_weights()` reads `profile.patient_value_hierarchy` for Wave 2/3 ranking |
| **#22** TaskCreate sync | `src/opl_cancer/plan/task_sync.py` JSONL writer; ON when `OPL_TASKCREATE_INTEGRATION=1` |

## Consequences

### Positive

- **Provenance closure.** Every claim in the manuscript is mechanically
  anchored to either a PubMed identifier or an integrator run hash.
  G30 is the bright-line enforcement.
- **AI authorship transparency.** G29 fails-closed on missing
  attestation. Reviewers and patients always see who/what wrote what.
- **Reproducibility.** G31 + G32 + the `.py` reproducer convention + the
  `manifest.sha256s` map make the bundle audit-trail-complete.
- **Banner discipline.** Non-real_patient bundles cannot ship without
  the banner injected into manuscript header AND every figure PNG.
- **Cost surface.** P2-#20 closes the "session cost was invisible"
  feedback from the 007-zhiqiang post-mortem.
- **Bundle portability.** The schema lives in `schemas/`; v2.4 N1Arxiv
  CI will validate without needing to import opl-cancer.

### Negative

- **G30 aggressiveness.** Every claim sentence requires an anchor.
  Background prose must use the `[BACKGROUND]` tag. New writers will
  need a session or two to internalise the convention.
- **Wave 6 doubles the session cost.** Manuscript generation adds
  ~30% of a Wave 1+2+3+4+5 session's token budget. The `--draft` mode
  uses Sonnet 4.6 to cut cost when the patient does not need
  publication-grade output.
- **No PDF rendering in v2.3.** We do not bundle `any2pdf` (out of scope).
  PDF is best-effort via the user's local `any2pdf` if available;
  otherwise the bundle ships markdown only and the manifest documents
  this.

### Neutral

- **No backward-incompatible CLI removal.** `opl wave6` is additive.
  All existing `opl wave1`-`wave5` / `opl run` / `opl deliver`
  commands remain unchanged.
- **20-expert roster unchanged.** Wave 6 reuses Iain / Aviv / Vince /
  Henry. No new experts introduced (preserves ADR-0019 founder-mode
  scope discipline).

## Alternatives considered

### Alt 1 — Bundle inside `delivery_runner.py` instead of a new runner

Rejected: would have overloaded the v2.2 transactional envelope. Wave
5 and Wave 6 are different commitment surfaces (patient brief vs.
publication). Separating runners keeps each transactional contract
focused.

### Alt 2 — Use an external BibTeX library

Rejected. `references.bib` is generated by emitting BibTeX entries
directly from PubMed esummary JSON (see
`prompts/tasks/citation_assembly.md`). Zero new runtime deps. The
G1+G2 verifiers already run on PMIDs upstream.

### Alt 3 — PDF rendering is mandatory

Rejected for v2.3 (deferred to v2.4 or out-of-scope). Many sessions
will not have `any2pdf` available. Forcing PDF would block bundle
emission for the majority of users. Markdown-only is the v0.1
contract; PDF is best-effort.

### Alt 4 — Put the schema in the n1arxiv repo only

Rejected. The OPL writer must validate before zipping. The schema
must live with the writer. v2.4 will mirror the schema into n1arxiv.

## Implementation surface

| Path | What |
|---|---|
| `src/opl_cancer/glue/wave6_runner.py` | Wave 6 orchestrator (mirrors `wave1_runner` + uses `delivery_runner` envelope) |
| `src/opl_cancer/delivery/n1a_bundle_writer.py` | Bundle writer (SHA-256, manifest, zip, schema validation) |
| `src/opl_cancer/memory/cost_tracker.py` | P2-#20 cost ledger |
| `src/opl_cancer/plan/prior_run_ingestion.py` | P2-#17 + P2-#21 |
| `src/opl_cancer/plan/task_sync.py` | P2-#22 TaskCreate JSONL sync |
| `src/opl_cancer/integrators/figure_render.py` | P2-#18 watermark extension |
| `src/opl_cancer/validators/gates/g29_*.py` ... `g33_*.py` | 5 new gates |
| `prompts/tasks/manuscript_*.md` (6) + `citation_assembly.md` + `figure_caption.md` | 8 new task packages |
| `schemas/n1a_bundle.v0.1.schema.json` | JSON Schema draft-2020-12 |
| `docs/adr/0023-wave6-manuscript-and-n1a-bundle.md` | This ADR |

## Test surface

| Test file | Coverage |
|---|---|
| `tests/test_validators/test_g29_*.py` ... `test_g33_*.py` | 39 unit tests across the 5 new gates |
| `tests/test_validators/test_gate_registry.py` | Updated 28 → 33 gate count |
| `tests/test_integration/test_n1a_bundle_schema.py` | 9 integration tests on bundle writer + 4-bundle schema validation |
| `tests/test_memory/test_cost_tracker.py` | 10 unit tests on cost tracker |
| `tests/test_glue/test_wave6_runner.py` | 10 integration tests on Wave 6 runner |
| `tests/test_v23_wave6_prompts.py` | 41 structural tests on 8 new task packages |
| `tests/test_plan/test_prior_run_ingestion.py` | 8 unit tests on P2-#17 + P2-#21 |
| `tests/test_plan/test_task_sync.py` | 7 unit tests on P2-#22 |
| `tests/test_integrators/test_figure_render_watermark.py` | 4 unit tests on P2-#18 |
| `tests/test_cli.py` | 3 new CLI tests (`opl wave6` help / refuse / dry-run) + status string update |

## Hand-off to v2.4 (N1Arxiv)

- v2.4 will mirror `schemas/n1a_bundle.v0.1.schema.json` into
  `CancerDAO/n1arxiv/schemas/`.
- v2.4 ships `opl wave6 --submit-to-n1arxiv` flag that prints the
  ready-to-PR diff (clone n1arxiv, copy files, print `git push`).
  v2.3 does NOT auto-PR — founder-mode: patient decides.
- v2.4 will add `prompts/tasks/n1arxiv_pr_assembly.md` (Frances drafts
  the PR body referencing ethics + consent + scope).
