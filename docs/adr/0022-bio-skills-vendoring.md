# ADR-0022: Bio-Skills Vendored as Task Packages (v2.2)

**Status:** Accepted (2026-05-28)

**Context:** v2.0/v2.1 OPL ships 20 expert archetypes + 47 task packages.
A 007-zhiqiang real-patient run surfaced concrete missing capability — no
in-tree MSI / TMB / mutational-signature / ACMG-germline / survival /
subgroup analysis. The community repo `BioTender-max/awesome-bio-agent-skills`
(CC0-1.0) aggregates 1,629 small skills; an audit identified 7 that add
genuine net capability beyond OPL's existing roster (+1 optional CPIC
pharmacogenomics).

Three integration shapes were on the table:

1. Install each upstream skill verbatim as a sibling `npx skills add`
   plugin, let the SKILL main thread coordinate.
2. Vendor each upstream skill as an OPL **task package** under
   `prompts/tasks/<name>.md`, with a deterministic Python wrapper in
   `src/opl_cancer/integrators/`.
3. Re-implement everything from scratch.

**Decision:** Shape (2) — vendor as task packages. Each new task package
frontmatter carries `source_skill: BioTender-max/awesome-bio-agent-skills/<path>`
and `original_license: CC0-1.0`. A top-level `ATTRIBUTIONS.md` lists every
upstream credit. Per `feedback_default_prompt_over_script`: only the
*interpretation* layer is LLM-prompt (the task package); numerical work
goes into deterministic Python wrappers around samtools / lifelines /
SigProfilerAssignment / etc. Heavy deps (SigProfilerAssignment) lazy-import
and the wrapper exposes an explicit `--live` flag so unit tests stay fast
without losing the option of real execution.

### Why not (1) — separate skills?

* Each sibling skill would re-load its own roster, mechanical-gate set,
  and integrator stack; OPL's Henry gates (G1-G28) would no longer apply
  uniformly. Reviewer pairing (P0-#7) would also have to be re-wired per
  plugin.
* Cross-task evidence threading (e.g. MSI result feeding TMB
  interpretation feeding Bert's treatment-line ranking) breaks across
  skill boundaries.
* Patient-facing flow becomes "Sid + 20 OPL experts + 7 ad-hoc plugins"
  — diffuses the founder-mode promise of one PI orchestrating a single
  team.

### Why not (3) — re-implement?

* CC0 license already grants the right to vendor; re-implementation is
  net-negative work for zero capability gain.
* Loses the audit trail back to the community source (which matters for
  PMID-grounding claims like "MSIsensor v0.5 is the canonical reference").

### Scope-creep boundary

Vendoring is **bounded**:

* Only task packages that map to an *existing* OPL expert's portfolio
  (Bert / Aviv / Mary / Maya). No new expert archetype added in v2.2.
* No upstream skill that introduces a new safety-critical surface (e.g.
  dosing recommendation) without going through an OPL gate (Henry G3 for
  CPIC).
* No upstream skill whose underlying tool is non-determinstic at the
  numerical layer (e.g. LLM-only "interpretation" skills) — those would
  be re-implemented to OPL prompt-style standards rather than vendored.

### v2.2 task package mapping

| New task package | Source skill | Wave | Owning expert | Integrator | Henry gate(s) |
|---|---|---|---|---|---|
| `msi_detection.md` | bio-msi-detection | 3 | Bert | `msi_sensor.py` | G14 |
| `tmb_calculation.md` | bio-tumor-mutational-burden | 3 | Bert | `tmb_harmonization.py` | G21 |
| `cosmic_signature_extraction.md` | bio-somatic-signatures | 3 | Bert | `cosmic_sigprofiler.py` | G14 |
| `acmg_germline_classification.md` | bio-acmg-classification | 1 | Bert | `varsome_acmg.py` | G2 |
| `opentargets_evidence.md` | query-opentarget | 1, 2 | Maya | `open_targets.py` (extended) | G1, G2 |
| `biostats_survival.md` | bio-clinical-biostatistics-survival-analysis | 3 | Aviv | `lifelines_km.py` | G15 |
| `biostats_subgroup.md` | bio-clinical-biostatistics-subgroup-analysis | 3 | Aviv | shares `lifelines_km.py` | G15, G17 |
| `pharmacogenomics_cpic.md` | bio-pharmacogenomics | 3 | Mary | `cpic.py` | G3 |

### G28 absolute_date

v2.2 adds one new mechanical gate: **G28 absolute_date** (P1-#15). The
prior LLM-computed "5 weeks treated as 5 months" failure mode is removed
by requiring `X mo/week/day ago` claims to carry an explicit `from_date`
+ `to_date` pair (or be tagged `[BACKGROUND]`). G28 FAIL is hard-block;
relative date language without anchor cannot ship to a patient brief.

**Consequences:**

* `prompts/tasks/` count: 47 → 55 (or 54 if CPIC deferred).
* `src/opl_cancer/integrators/` count: +8 modules (msi_sensor,
  tmb_harmonization, cosmic_sigprofiler, varsome_acmg, lifelines_km,
  cpic, figure_render, paperqa_full_text). `open_targets` is extended,
  not new.
* `validators/gates/` count: 27 → 28 (G28).
* Roster portfolio fields populated for Bert / Aviv / Mary / Maya — the
  v2.0 stubs become real.
* Heavy dep (`SigProfilerAssignment`, `lifelines`) are lazy-imported in
  the wrappers; tests use `pytest.importorskip` to skip when absent and
  CI installs them via the `[bio]` extras group.
* `opl deliver` is now atomic — Henry audit, plain brief, and PI brief
  render in one transaction; partial failure rolls back (P1-#16). This
  closes the failure mode where the patient saw only the plain brief
  while Henry hadn't yet finished its gates.

**Out of scope:** Wave 6 manuscript generation (v2.3), N1Arxiv platform
(v2.4), CPIC dose-recommendation engine (Mary remains advisory; CPIC
table is reference-only in v2.2).

**Files affected:**

* `prompts/tasks/msi_detection.md` (new)
* `prompts/tasks/tmb_calculation.md` (new)
* `prompts/tasks/cosmic_signature_extraction.md` (new)
* `prompts/tasks/acmg_germline_classification.md` (new)
* `prompts/tasks/opentargets_evidence.md` (new)
* `prompts/tasks/biostats_survival.md` (new)
* `prompts/tasks/biostats_subgroup.md` (new)
* `prompts/tasks/pharmacogenomics_cpic.md` (new, optional)
* `prompts/auditor/quote_verify_numerics.md` (new — P1-#11)
* `src/opl_cancer/integrators/msi_sensor.py` (new)
* `src/opl_cancer/integrators/tmb_harmonization.py` (new)
* `src/opl_cancer/integrators/cosmic_sigprofiler.py` (new)
* `src/opl_cancer/integrators/varsome_acmg.py` (new)
* `src/opl_cancer/integrators/lifelines_km.py` (new)
* `src/opl_cancer/integrators/cpic.py` (new)
* `src/opl_cancer/integrators/figure_render.py` (new — P1-#14)
* `src/opl_cancer/integrators/paperqa_full_text.py` (new — P1-#10)
* `src/opl_cancer/integrators/open_targets.py` (extended)
* `src/opl_cancer/validators/gates/g28_absolute_date.py` (new — P1-#15)
* `src/opl_cancer/validators/gates/__init__.py` (re-export G28)
* `src/opl_cancer/validators/mechanical_gates.py` (register G28)
* `src/opl_cancer/experts/roster.py` (populate task_package_portfolio
  for Bert / Aviv / Mary / Maya)
* `src/opl_cancer/glue/wave3_runner.py` (calibration provenance — P1-#10)
* `src/opl_cancer/glue/delivery_runner.py` (new — P1-#16)
* `src/opl_cancer/cli.py` (new `opl deliver` command — P1-#16)
* `src/opl_cancer/orchestrator/reviewer_hook.py` (numeric verifier chain
  after Iain meta-analysis — P1-#11)
* `ATTRIBUTIONS.md` (new — top level)
* `pyproject.toml` (version 2.1.0 → 2.2.0; optional `[bio]` extras)
* `SKILL.md` (version frontmatter 2.1.0 → 2.2.0)
* `CHANGELOG.md` (new `## [2.2.0]` section)
* `README.md` (v2.2.0 line in "Recent changes")

**Tests:**

* `tests/test_validators/test_g28_absolute_date.py`
* `tests/test_integrators/test_msi_sensor.py`
* `tests/test_integrators/test_tmb_harmonization.py`
* `tests/test_integrators/test_cosmic_sigprofiler.py`
* `tests/test_integrators/test_varsome_acmg.py`
* `tests/test_integrators/test_lifelines_km.py`
* `tests/test_integrators/test_cpic.py`
* `tests/test_integrators/test_figure_render.py`
* `tests/test_integrators/test_paperqa_full_text.py`
* `tests/test_integrators/test_open_targets_extended.py`
* `tests/test_experts/test_roster_v22_portfolios.py`
* `tests/test_orchestrator/test_quote_verify_numerics.py`
* `tests/test_glue/test_delivery_runner.py`
* `tests/integration/test_subset_filter.py`
* `tests/e2e/test_bio_skills_riaz.py`
* `tests/e2e/test_bio_skills_real_007.py`
