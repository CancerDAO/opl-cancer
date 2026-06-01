# Changelog

All notable changes to **OPL for Cancer** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Archive.** Recent major releases (v2.x) are kept inline below. Entries for
> all pre-v2.0 releases (the v0.x scaffold series and the entire v1.x line, from
> `[1.5.7]` down) have been moved to [`docs/CHANGELOG-archive.md`](docs/CHANGELOG-archive.md).

---

## [2.8.0] — 2026-06-01 — Harness-split: dual-brain decoupling (prompt-only reasoning)

Paradigm change (PRD `docs/iteration/HARNESS_SPLIT_PRD.md`). Patient reasoning
moved out of Python-internal LLM calls into the host agent; Python is now a
deterministic harness only. Red line held: the 42 gates keep their `exit≠0`
decision authority in Python.

- **Removed `src/opl_cancer/llm/`** (7 modules). The Python package no longer
  calls any LLM. `git grep` confirms zero LLM usage in the patient path.
- **`experts/_common`, `wave1_runner`, `wave1_live`, `renderer`, `henry`** rewired
  to pure scaffold / validate / deterministic-assembly. The host agent is the sole
  reasoning brain, dispatching expert + reviewer subagents that write report
  artifacts; the CLI state-checks + gates them (two-beat loop).
- **New prompts:** `prompts/experts/expert_task_package.md`,
  `prompts/render/brief_render.md`, `prompts/auditor/henry_axis_naming.md`.
- **G13 redefined** — checks the executor and reviewer report artifacts declare
  distinct model identities (dual-subagent), replacing the Python model-router check.
- **P0 safety fixes folded in** — G36 fires by default (entities auto-derive or
  block, no more self-disarming SKIP); offline (`pubmed=None`) with PMID-claims now
  blocks instead of silent-passing; G35 verifies the asserted value actually appears
  at the `[[src:...#Lnn]]` locator, not just that the file exists.
- **SKILL.md** — added the "Execution model (harness-split)" section; corrected the
  reviewer/provider-key layer (patient path needs no provider key) and the
  wave-runner-execution description. No `ANTHROPIC_API_KEY` for a patient run.
- **orchestrator/* + evolution/*** decoupled from the patient CLI (lazy-guarded);
  slated for extraction to a standalone `opl-cancer-evolution` repo
  (`docs/iteration/EVOLUTION_EXTRACTION_TODO.md`). Their tests are parked via
  `conftest.py` `collect_ignore` pending the move.
- Suite: 1749 passed / 8 skipped on a bare `pytest -q`; non-bypassable suite green.

## [2.7.2] — 2026-05-29 — Skill-quality audit (skill-creator + skill-creator-pro)

Audit-only polish from the skill-creator-pro lint + skill-creator triggering lens.
No behaviour change; discoverability + body-budget improvements.

- **Description rewrite** — 1175 → 833 chars (under the 1024 frontmatter budget).
  Dropped the embedded 5-Wave workflow-summary prose (skill-creator-pro Iron-Law-#2:
  a "what it does" description makes the model shortcut past the body — exactly
  where the v2.7.0 Operating Contract now lives). Kept the full bilingual trigger
  list (skill-creator anti-undertrigger). `FM_DESC_TOO_LONG` lint warning resolved.
- **SKILL.md body** — 500 → 498 lines (back under the ≤500 budget). Moved the
  pre-v2 inline `version 1.3.2` / `version 1.4.0` changelog paragraphs to
  `references/version-history.md` (they were changelog content in the
  always-loaded body, not operating instructions).
- Lint: 0 errors; remaining 5 `SCRIPT_NO_ARGPARSE` warnings are intentional
  (the CLIs use `click`, a valid framework — style-only, not fixed).

## [2.7.1] — 2026-05-29 — Reasoning-Quality Gates + CLI Self-Sufficiency (ADR-0026 P1)

Completes ADR-0026: the P0 release (2.7.0) made delivery non-bypassable; this
adds the reasoning-quality layer that catches the 8 cross-model review findings
from session 0d1017d4, plus Fork B (CLI can self-execute Wave 1).

### Added — 5 reasoning-quality gates (G39-G43, new `reasoning-quality` family)

Each is a MECHANICAL check over structured fields the claim producer emits
(`schemas/claim.v2.schema.json`) — never hardcoded clinical judgment. Wired into
`delivery_gate_runner` so they fire on the live path (not SKIP-only stubs).

- **G39 biomarker_contingency** [BLOCK] — a headline/rank-1 regimen may not be
  gated on a biomarker whose `patient_state` is unknown/untested (Finding 1:
  anti-EGFR headline gated on unknown NRAS/BRAF).
- **G40 drug_comorbidity_safety** [BLOCK] — a recommended drug must reconcile
  its FDA-label contraindication classes against the patient's comorbidities
  (Finding 5: bevacizumab × cardiac). Curated reference
  `references/drug_comorbidity_contraindications.json`.
- **G41 soc_completeness** [WARN] — the SoC-completeness check must be recorded;
  `missing` items surface (Finding 6: re-biopsy/ctDNA, oligoprogression local therapy).
- **G42 tier_discipline** [BLOCK tier-floor + functional-evidence; WARN adjacency]
  — claim tier ≤ weakest evidence-link tier; biallelic/LoF claims need
  same-tumor-type functional data, not IHC alone (Findings 3,4,7).
- **G43 epistemic_symmetry** [WARN] — skepticism applied symmetrically; low-I²
  pooling across non-equivalent agents must flag clinical heterogeneity (Findings 2,8).

The claim-producer prompts (`claim_audit`, `treatment_line_recommendation`,
`meta_analysis`, `molecular_ngs_interpretation`) now mandate the v2 claim schema
so these gates have real fields to check (the connection that keeps them live).

### Added — Fork B: CLI self-sufficient Wave-1 execution

`opl run --wave 1` now drives the real `Wave1Runner` via the LLM router + a
generic 20-persona expert factory (`glue/wave1_live.py`) when an executor key +
G13-distinct reviewer key are set — so a compliant run is third-party
reproducible without a human-LLM main thread. Fails closed honestly
(`requires_main_thread_dispatch`) when no key (e.g. on Claude Code, where the
agent is the executor). Verified offline with mock clients.

### Gates / families / tests

- 37 → 42 gates (G38 reserved — citation-provenance covered by G1/G2/G36).
- 6 → 7 gate families (`reasoning-quality`). RFC-0001 closed-set extended.
- New tests: 5 gate units (g39-g43) + Fork B mock (2). Full suite 1828 passed.
  ruff + mypy(strict) clean on new code.

## [2.7.0] — 2026-05-29 — Delivery Non-Bypassable + Complete-by-Default (ADR-0026)

Root-cause fix for session `0d1017d4` (KRAS-G12C / MSS mCRC), where OPL
**under-delivered** (ran 4 generic agents instead of the planned 20 experts,
skipped Wave 2/3/4 + the Henry audit) **and** shipped **fabricated** content
(invented lab values before OCR; 4 real-but-wrong-paper PMIDs — knee-OA / kefir /
glioma / macrophage). It only became complete because a domain-expert user kept
pushing — a normal patient cannot. Root cause: the apparatus was *computed but
disconnected* — SKILL.md's terminal command (`render`) was a `{"ok":true}` stub
and nothing detected the absence of a real run, the shrinking of the service, or
fabricated content.

### Added — 4 delivery-integrity gates (G34–G37), wired into the live path

- **G34 delivery_attestation** — a brief must be backed by a real run:
  `run_manifest.json` run-token (minted at `plan`) + a `provenance.jsonl` with a
  recomputable-hash record + a real Henry audit + every brief PMID present in the
  provenance record. **Kills free-handing (AP-14).**
- **G35 clinical_fact_provenance** — every measured clinical value (lab / organ
  score / staging / molecular call) must carry a `[[src:...]]` anchor to an
  existing OCR sidecar; unknowns are written `UNKNOWN`, never invented.
  **Kills fabricated labs (AP-16).**
- **G36 pmid_topic_relevance** — each cited PMID's live PubMed record must mention
  one of the claim's entities (complements G1 existence + G2 quote).
  **Kills real-but-wrong-paper citations (AP-16).**
- **G37 service_completeness** — every planned expert must have produced a
  roster-authored report and every warranted wave must have run; narrowing scope
  needs a user-confirmed `replan.json`. **Kills under-delivery (AP-17) + expert
  collapse (AP-15).**

### Added — autonomy: one simple prompt → full professional service

- **`opl-cancer go`** — drives the whole lifecycle (input-guard → readiness →
  plan-full-team → waves → `deliver --finalize` → `attest`) and returns the exact
  next action (with the FULL expert list) until delivery is complete + attested.
  The patient never has to know what to ask for.
- **`opl-cancer attest`** — explicit delivery-integrity proof (exit 2 if not attestable).
- **run-manifest + run-token** minted at `plan` and threaded to delivery.

### Fixed — the stubs that allowed the incident

- `render` and `audit` are no longer `mkdir + {"ok":true}` stubs — they are
  **fail-closed** state-readers that run the integrity gates and refuse (exit 2)
  when a delivery is not backed by a real run. SKILL.md Step 10 routes through
  `deliver --finalize` + `attest`.
- `deliver --finalize` now runs the integrity gates as a final non-bypassable
  checkpoint.
- Dangling doc citations resolved: `docs/ANTI_PATTERNS.md` (was
  `ANTI_PATTERNS_v1.4.md`, never existed) + `references/patient-data-layout.md`
  (`[[src:...]]` grammar) authored; `tests/test_docs_refs.py` guards against
  future drift. Gate-count drift fixed (SKILL.md "G1-G27" → G1-G37; `status`
  derives the count from `all_gate_classes()`).

### Decisions

- **ADR-0026** — delivery non-bypassable + complete-by-default. Hard-block on
  safety gates (G34–G37 + G1/G2/G36), warn-only on quality gates. Lightweight
  forge-resistance now (run-token + recomputable hashes). Revises the 2026-04-22
  CLI-as-state-reader posture: the CLI **may** wire the host LLM into
  `opl run --wave N` so a compliant run is third-party reproducible.

### Tests

- 33 → 37 gates; `test_gate_registry` updated. New: `test_delivery_integrity_gates_v270`
  (15), `test_pipeline_non_bypassable` (8, two cancer types), `test_docs_refs`.
  Full suite green (1778 passed).

## [2.6.1] — 2026-05-29 — Installable + Agent-Agnostic (first-run & portability)

Hotfix making the **`npx skills add CancerDAO/opl-cancer-skill`** install path
actually work on a fresh machine AND on non-Claude-Code agents. Driven by hands-on
multi-round E2E testing (real install across 30+ agent dirs; harness E2E passed
3/3 cancer types: scaffold→`--finalize`→real-audit) + an agent-agnostic skill audit.

### Fixed — first-run (BLOCKER)

- **FR-1** — `scripts/cli.py` shim no longer crashes a fresh user with a raw
  `ModuleNotFoundError: No module named 'click'`. The old shim put `src/` on the
  path (so the *package* imported) then immediately imported `opl_cancer.cli`,
  which needs `click`/`pydantic`/… that a fresh machine lacks. The shim now covers
  package **and** deps in one `_load_main()`, attempts ONE
  `pip install -e <skill_dir>` bootstrap (disable with `OPL_NO_AUTO_BOOTSTRAP=1`),
  and on failure exits cleanly (code 3) with the exact copy-pasteable command —
  never a raw traceback. (SKILL.md's old "auto-runs pip install" claim is now true.)

### Fixed — agent-agnostic portability (BLOCKER)

- **PORT-1** — SKILL.md hardcoded `~/.claude/skills/opl-cancer/scripts/cli.py` in
  12 places; on Codex/Cursor/OpenCode (which install into their *own* skill dirs)
  every step died on a nonexistent path at Step 0. All command refs now use the
  portable **`opl-cancer` console entry point** (path-free after the one-time
  `pip install -e <skill_dir>`).
- **PORT-2** — executor framing was hardcoded to "Claude Code main thread =
  Anthropic, no key". Step 0 is now **host-aware**: executor = the host agent's own
  LLM; non-CC hosts set `OPL_EXECUTOR_PROVIDER`; **G13** distinctness is described
  against the *actual* executor family, not a hardcoded Anthropic constant.
- **PORT-3** — new `references/agent-portability.md`: per-agent install dirs, the
  one-time bootstrap, the executor/reviewer (G13) contract, and a CC→host tool-name
  map (Write/Bash/subagent dispatch). Reconciles the prior `architecture.md` ↔
  SKILL.md contradiction about whether an API key is needed.

### Fixed — skill quality + version drift

- **SK-1** — SKILL.md frontmatter `description` trimmed from **3699 → ~1190 chars**
  (a 439-word wall of triggers hurts skill matching / risks over-triggering). Lean,
  scoped description + a deduplicated trigger set; heavy detail stays in the body.
- **SK-2** — version drift killed: `cli.py` now derives `VERSION` from
  `opl_cancer.__version__` (was a separate hardcoded `"2.5.1"` while `__init__` said
  `0.0.1`). `opl-cancer --version` + `status` track the package. Version → 2.6.1
  across pyproject / `__init__` / SKILL.md metadata.

### Tests

- New `tests/test_skill_portability.py` (shim clean-failure, no hardcoded
  `~/.claude` command paths, agent-portability ref completeness, lean description).
  Updated version-pin + `status` tests. Full suite **1740 passed, 8 skipped**.

## [2.6.0] — 2026-05-29 — Truthful Delivery + Safety Wiring

Iteration following a second independent product+code audit (7 parallel
reviewers + adversarial verification; 63 findings, 38 BLOCKER/HIGH verified,
0 false positives). This release closes the highest-leverage **patient-safety**
and **delivery-truthfulness** findings. The larger architectural items it does
NOT yet close (CLI-vs-SKILL executor wiring, full 33-gate battery on the ship
path, LLM plan-composer replacing the keyword routers) are documented as
v2.7.0+ in `docs/iteration/REVIEW_v2.6.0.md` because they require a maintainer
decision on the engine-vs-skill product boundary.

### Fixed — patient safety

- **CRISIS-1 (BLOCKER)** — `G24CrisisDetectionGate` was fully implemented +
  unit-tested but **never invoked at runtime**; a patient typing self-harm
  language into the goal box was keyword-routed like any other question (worst
  case: a trial-dump on a suicidal patient). `plan/intake_router.route_intake`
  now runs the mechanical G24 gate as **Path 0** — ahead of all keyword routing —
  and returns `crisis_card_emission` with `crisis_block=True` + crisis evidence
  and an empty `method_dag`. The gate stays mechanical by design (no LLM can
  suppress a verbatim SI hit). New `IntakeRoute.crisis_block` / `.crisis_evidence`.
- **REDACT-1 (HIGH)** — patient-facing drug-class redaction
  (`glue/render_bridge._redact_drug_specifics`) was a ~25-entry, mCRC-biased
  dictionary that **failed OPEN**: any speculative drug not in the dict (a novel
  investigational code like `MRTX1133`, a HER2 ADC, a menin inhibitor) rendered
  VERBATIM in the patient brief. Now **fails CLOSED** — a deterministic backstop
  redacts drug-like tokens (INN stems `…ib`/`…mab` + investigational codes) it
  can't class-map to a generic placeholder, recorded as `fail_closed:<token>`.
  (The proper generalization fix — an RxNorm/OncoKB/LLM class resolver — is
  tracked for v2.7.0; this is the mechanical floor behind it.)

### Fixed — delivery truthfulness (the product's core value prop)

- **AUDIT-1 (BLOCKER)** — `opl deliver` reported `status: pass` /
  `henry_real_audit: true` / `gates_run: 4` while `HenryAuditor.audit_claim()`
  (the real L1-L4 audit) was **never called** and the briefs were placeholder
  scaffolds. `DeliveryRunner` now has two honest modes:
  - **scaffold (default)** — renders the template scaffold, runs the (now
    CJK-aware) fakery sniffer over it, and reports
    `status: "scaffold_pending_fill"`, `henry_real_audit: false`,
    `brief_complete: false`, with the detected `placeholder_findings`. It no
    longer claims a real audit or a pass.
  - **`--finalize`** — audits the *already-filled* briefs: refuses
    (`DeliveryFailure`) if any placeholder language remains, then runs the REAL
    `HenryAuditor.audit_claim()` over the LLM-produced `claims.json` manifest and
    only then emits `henry_real_audit: true` + a true `gates_run`/`claims_audited`.
    The runner stays mechanical — it consumes structured claims, it does not
    parse drugs/levels out of free text.
- **B5-SEMANTIC (BLOCKER)** — `verify_upstream_artifacts` checked file
  EXISTENCE only, so an empty `{}` plan + `{"hypotheses": []}` wave file passed
  the "refuses to ship without real evidence" gate. It now also detects **hollow**
  upstream (empty plan / empty wave content arrays / trivial wave-1 report) and
  refuses.
- **FAKERY-CJK** — `validators/fakery_sniffer` was English-only
  (`[speculative`, `approximately \d`, `<insert PMID>`) while OPL is
  Chinese-primary; the delivery scaffold's zh placeholders slipped through every
  ADR-0021 Invariant-3 scan. Added scoped CJK patterns (`占位`, `待补充/待填写`,
  `主线程…填充`, `由 SKILL/LLM…填充`, `TODO/TBD`) that do not over-fire on real
  clinical prose.

### Changed — docs synced to code

- `README.md` delivery section + `cli.py list-experts` corrected (20-expert
  roster; `opl deliver` honestly described as scaffold + `--finalize`).
- Version → 2.6.0.

### Tests

- +20 cases across 5 new test files (TDD, failing-first):
  `test_fakery_sniffer_cjk`, `test_delivery_truthful_v260`,
  `test_intake_crisis_first`, `test_redaction_fail_closed`,
  `test_upstream_semantic_b5`. Updated the v2.5.1 delivery tests that had locked
  in the placeholder-scaffold-as-pass behavior. Full suite: **1734 passed,
  8 skipped** (clean env).

## [2.5.1] — 2026-05-29 — Hotfix (5 BLOCKERS + README rewrite)

Hotfix release closing 5 BLOCKER-grade defects found in an independent
product audit, plus a complete README rewrite and v2.5.1 community-docs
package (CONTRIBUTING / CODE_OF_CONDUCT / SECURITY / issue + PR
templates).

### Fixed — 5 BLOCKERS

- **B1** — `DeliveryRunner` no longer ships a fake Henry audit / 4-line
  brief stubs. `_run_henry_audit` now constructs a real
  `validators.henry.HenryAuditor` against
  `knowledge/serious_risks_per_drug.json` and emits structured
  catalogue / pending-ack / upstream-inventory fields with
  `audit_version: v2.5.1` + `henry_real_audit: true`. Missing catalogue
  raises `DeliveryFailure` instead of returning the v2.5.0 hardcoded
  pass. `_render_plain_brief` + `_render_pi_brief` now scaffold from the
  patient-facing template
  (`prompts/tasks/patient_plain_brief_rendering.md` +
  `prompts/tasks/pi_delivery.md`) — 5 mandatory sections + Henry verdict
  block + ack queue, not 4-line stubs.

- **B2** — `plan/intake_router.py::route_intake` wired into the two
  real plan-emit sites that were missing it through v2.5.0:
  `cli.py plan` and `glue/wave1_runner.py::_build_plan` (new
  `Wave1Runner._apply_intake_router` static method). Substantive-route
  gating ensures the c3195b66 question (literal Chinese AutoML /
  prognosis prompt) produces a plan.json that includes
  `unknown_task_intake` AND `kaplan_meier + conformal_prediction` in
  the plan's `method_dag` field. Plan emit JSON surfaces
  `intake_route` so the SKILL main thread can render acknowledgement
  + decline reasons.

- **B3** — Wave 2 / 3 / 4 / 6 runners now wire the same
  `fakery_sniffer` + `reviewer_hook` discipline as wave1_runner. New
  `glue/_post_write.py` extracts the shared `SnifferHalt` +
  `post_write_safety_check` helpers. Wave 6 adds
  `_run_post_write_safety_sweep` that scans every markdown manuscript
  artifact before G29-G33 fire — fakery surfaces as `SnifferHalt`
  (richer signal than gate block). Wave 1 imports back-compat via
  re-export.

- **B4** — `plan/goal_router.yaml` bilingualised. Every existing
  entry now unions its English keyword set with Chinese synonyms
  (vaccine → 疫苗 / 新抗原 / 个性化新抗原 / 肿瘤疫苗; irae → 免疫相关不良反应
  / 再激发 / 内分泌副作用; etc.). New entry for the c3195b66 family:
  `"automl|machine learning|deep learning|XGBoost|prognostic model|
  机器学习|预后模型|建模预测|自动建模|AutoML|预后预测": [bert, aviv, iain]`.

- **B5** — `opl deliver` and `Wave6Runner` verify upstream artifacts
  before shipping. New `verify_upstream_artifacts(run_root)` helper +
  CLI `--allow-missing-upstream` documented escape hatch for
  debugging. `Wave6Runner._require_wave5` tightened to additionally
  require a non-empty `plan.json` + at least one
  `tasks/w1_*/report.md|wave2_hypotheses.json|wave3_data_evidence.json|wave4_validation.json`.

### Changed — README + community docs

- `README.md` — complete rewrite (819 → 350 lines, Apple-quality
  concise). Hero + 1-paragraph pitch + status badges + honest scope
  table + 30-sec quickstart with expected JSON output + 5-Wave pipeline
  + real example excerpt + 3 scenarios (preserved from v1.5.3) + Why
  N=1 is hard + ASCII architecture diagram + 6-milestone roadmap +
  4-rule discipline + ethics + BibTeX citation + acknowledgements. No
  more 5-blockquote release-note dump before the value-prop.
- `CONTRIBUTING.md` — expanded from 40 → ~150 lines: TDD workflow,
  ADR process, milestone discipline, 4 CLAUDE.md-derived discipline
  rules.
- `CODE_OF_CONDUCT.md` — adopts Contributor Covenant v2.1.
- `SECURITY.md` — separates code-security from patient-safety
  reports; lays out 5/10 day response SLA + founder-mode patient-data
  invariant.
- `.github/ISSUE_TEMPLATE/{bug_report,feature_request,patient_question}.md`
  — patient_question template carries explicit "not a medical-device"
  disclaimer with local emergency numbers (120 / 911 / 112).
- `.github/PULL_REQUEST_TEMPLATE.md` — checklist mirrors the 4
  CLAUDE.md discipline rules + patient-safety self-check.

### Tests

* 11 new test files for the 5 BLOCKERS + README rewrite (≥ 33 new
  test cases). All TDD: failing → confirm fail → implement → pass.
* Updated 3 existing test files
  (`test_delivery_runner.py`, `test_wave6_runner.py`,
  `test_opl_submit_to_n1arxiv.py`, `test_wave6_007_manuscript.py`,
  `test_wave6_riaz_manuscript.py`, `test_readme.py`) to align with the
  v2.5.1 contracts (upstream-artifact requirement,
  `allow_missing_upstream` escape hatch, v2.5.1 README contract).
* Suite: 1693 passing, 27 skipped, 0 failures.

### Bumped

* `pyproject.toml` 2.5.0 → 2.5.1
* `SKILL.md` `metadata.version` 2.5.0 → 2.5.1
* `src/opl_cancer/cli.py::VERSION` 2.5.0 → 2.5.1

### Compatibility

Strict backward-compat: all 33 v2.4 gates still register; 64 v2.5
task packages still resolve; 20-persona roster unchanged. The
`DeliveryRunner` adds `allow_missing_upstream` as a keyword arg
defaulting to False (existing callers without the kwarg get the new
strict behaviour; opt-in to old leniency via the flag). The new
`DeliveryArtifactsMissing` exception is a `DeliveryFailure` subclass
so existing `except DeliveryFailure` blocks still trap it.

---

## [2.5.0] — 2026-05-28 — Compositional Foundation

RFC 0001 + ADR-0025. Paradigm shift from enumeration (hardcoded experts /
task packages / cancer types / integrators / gates) to composition.
v2.5 ships **foundations only**; M1-M6 follow over the next 24 weeks.
The c3195b66 bug fix is release-gating — patient questions outside the
63 hand-written task packages no longer flat-refuse.

### Added — compositional foundations

- **`docs/rfc/0001-compositional-paradigm.md`** — new top-level RFC dir;
  full v2 vision spec committed to repo
- **`src/opl_cancer/methods/`** — `MethodPrimitive` dataclass +
  `MethodRegistry` with `load_all() / find_by_domain() /
  find_by_capability() / find_by_gate_family()`. 8 seed YAML primitives
  in `prompts/methods/` across 4 domains:
    - statistical: `cox_proportional_hazards`, `kaplan_meier`,
      `conformal_prediction`
    - bioinformatics: `deseq2_differential_expression`, `gsea_enrichment`
    - clinical-research: `recist_response_assessment`,
      `acmg_germline_classification` (cross-linked to v2.2 task package)
    - pharmacology: `popPK_NONMEM_proxy`
- **`src/opl_cancer/validators/gate_families.py`** — `GateFamily` ABC +
  6 concrete families (provenance / statistical-validity /
  temporal-recency / scope-isolation / safety-disclosure /
  reproducibility). **Provenance family fully migrated**: G1 + G2 + G30
  inherit + register (`family_id = "provenance"` class attribute; zero
  public-API breakage). Other 30 gates tagged in `gates_registry.yaml`
  for M1 migration.
- **`src/opl_cancer/experts/role_taxonomy.py`** — `ExpertRole` 4-axis
  dataclass + `references/role_taxonomy.yaml` enumeration +
  `prompts/experts/_template.md` parametric persona template. All 20
  v2.4 personas declared in `FAST_PATH_ROLES`. `compose_role()` v2.5
  STUB: matches FAST_PATH first; raises
  `RoleCompositionNotYetImplemented` for novel constraints (real LLM
  composition is M2 / v2.7).
- **`src/opl_cancer/cancer_context/`** —
  `CancerContextGenerator(icdo3, cache_dir, force_refresh)` + 2 seed
  JSONs (`references/cancer_contexts/C22.0.json` HCC +
  `C34.9_EGFR.json` NSCLC EGFR+). New CLI:
  `opl generate-cancer-context --icdo3 <code> [--output] [--force-refresh]`.
  Live PrimeKG + OncoKB + NCCN + CT.gov queries: M6.
- **`src/opl_cancer/integrators/_abc.py`** — `IntegratorABC` (id / query
  / normalize / provenance) + `IntegratorRegistry.discover()` over
  Python entry points. 5 of 44 integrators registered in `pyproject.toml`
  (pubmed / opentargets / clinicaltrials / cbioportal / oncokb);
  `ClinicalTrialsGov` + `OpenTargets` multi-inherit `Integrator` +
  `IntegratorABC` as proof. 39 others tagged for M3.
- **`src/opl_cancer/integrators/universal_adapter.py`** —
  `from_openapi(schema_url, dry_run=True)` parses an OpenAPI schema and
  returns an `AdHocIntegrator`. Live calls raise
  `UniversalAdapterLiveNotEnabled` unless
  `OPL_UNIVERSAL_ADAPTER_LIVE=1` (M3 ships the sanity-probe gate +
  LLM-generated request shaping).
- **`prompts/tasks/unknown_task_intake.md`** + **`src/opl_cancer/plan/intake_router.py`**
  — the c3195b66 bug fix. Any patient question outside the existing 63
  task packages routes through Sid-level `unknown_task_intake`:
  acknowledge → decline naive shortcut → compose method DAG → emit L4
  disclosure card. v2.5 ships keyword-driven stub; M5 swaps for full
  LLM TaskComposer.
- **`src/opl_cancer/orchestrator/best_first_journal.py`** — best-first
  hypothesis-tree journal adapted from SakanaAI/AI-Scientist-v2 (Cong
  Lu et al., ICLR 2025 workshop) under their Responsible-AI v1.0
  license. We adopt the **journal pattern** only; we do NOT use their
  unguarded LLM code-gen sandbox. OPL stays closed-world for drug /
  trial / dose IDs. Wired into Wave 2 tournament as a non-driving
  audit layer.
- **`docs/adr/0025-compositional-paradigm.md`** — ADR memorialising
  the paradigm; cross-references RFC 0001 + lists M1-M6 deferrals.

### Added — tests

- 9 new test modules (`tests/test_methods/test_registry.py`,
  `tests/test_validators/test_gate_families.py`,
  `tests/test_experts/test_role_taxonomy.py`,
  `tests/test_cancer_context/test_generator.py`,
  `tests/test_integrators/test_abc_discovery.py`,
  `tests/test_integrators/test_universal_adapter.py`,
  `tests/test_plan/test_intake_router.py`,
  `tests/test_orchestrator/test_best_first_journal.py`,
  `tests/test_integration/test_v2_5_backward_compat.py`)
- **Release-gating regression** —
  `test_c3195b66_automl_prognosis_routes_to_unknown_task_intake`: feeds
  the literal session-c3195b66 question and asserts
  `unknown_task_intake` route + DAG contains `conformal_prediction` +
  `kaplan_meier` + L4 card emitted
- Backward-compat invariants — 33 gates still register, 64 task packages
  (was 63 + `unknown_task_intake.md`) all resolve, 44 integrators still
  importable, 20-persona roster unchanged, all v2.4 CLI commands
  unchanged

### Changed

- `pyproject.toml`: version `2.4.0` → `2.5.0`; new
  `[project.entry-points."opl_cancer.integrators"]` table
- `src/opl_cancer/cli.py`: `VERSION` bumped to `2.5.0`; new
  `generate-cancer-context` command
- `SKILL.md`: version `2.4.0` → `2.5.0`; tags add `compositional`,
  `method-primitive`, `role-taxonomy`, `n=1`, `automl`, `prognosis`
- `README.md`: new v2.5.0 entry in Recent changes + architecture
  diagram shows the compositional layer above the v2.4 enumerated stack
- `tests/test_v23_wave6_prompts.py`: task-package count expectation
  `63` → `64` (added `unknown_task_intake.md`)
- `src/opl_cancer/orchestrator/tournament_loop.py`: returns a
  `best_first_journal` key (Sakana audit layer)

### Deferred (M1-M6)

- M1 (v2.6): migrate remaining 30 gates to families; EVAL benchmark corpus
- M2 (v2.7): 20-persona roster migration; real LLM `compose_role()`
- M3 (v2.8): migrate 39 integrators to entry points; live UniversalAdapter
- M4 (v2.9): expand method primitives to ~50
- M5 (v3.0-rc1): TaskComposer LLM upgrade; full compositional planner
- M6 (v3.0): live PrimeKG + OncoKB + NCCN + CT.gov cancer-context

## [2.4.0] — 2026-05-28 — N1Arxiv Platform Skeleton

ADR-0024. Cross-repo release: opl-cancer v2.4.0 + new
`CancerDAO/n1arxiv` v0.1.0. Adds the `--submit-to-n1arxiv` flag to
`opl wave6 --final` so a patient who has just shipped a `.n1a` bundle
can stage a PR-ready diff against the public N=1 preprint platform
without leaving the founder-mode flow. The submitter NEVER calls
`git push` or `gh pr create`; the patient triggers publication.

### Added — cross-repo PR assembly

- **`src/opl_cancer/delivery/n1arxiv_submitter.py`** — takes a `.n1a`
  bundle + an optional local clone of `CancerDAO/n1arxiv`, derives a
  deterministic `paper_id` (`YYYY-MM-DD-<slug>`), byte-copies the
  bundle into `static/bundles/`, generates a Hugo content stub into
  `content/papers/` from `manifest.json` (never inlines the manuscript
  prose), and drafts the PR body. `assemble_submission(execute=True)`
  is a hard refusal at the API level — future callers cannot quietly
  enable auto-PRs.
- **`prompts/tasks/n1arxiv_pr_assembly.md`** — Frances-owned task
  package; expands the PR body with ethics + consent + scope-aware
  framing. `henry_gates_invoked: [G29, G30, G32, G33]`.
- **CLI: `opl wave6 --submit-to-n1arxiv [--n1arxiv-repo PATH]`** —
  requires `--final`; refuses in `--draft` mode (G29-G33 not enforced
  for drafts). Without `--n1arxiv-repo` the CLI still produces the PR
  body + suggested commands so the patient can stage the diff later.

### Added — ADR-0024

- **`docs/adr/0024-n1arxiv-platform-skeleton.md`** — documents the
  cross-repo split, the PR-based submission philosophy, the canonical
  schema location, the dual licence (CC-BY 4.0 content + MIT code on
  the n1arxiv side), and the three medical red lines: never auto-PR,
  never edit the bundle, never silently relax a gate.

### Schema mirror discipline

- **`schemas/n1a_bundle.v0.1.schema.json`** now carries a header
  comment naming itself as the canonical copy. `CancerDAO/n1arxiv`
  ships a byte-identical mirror; any schema change is a two-PR change
  (both repos in lockstep).

### Companion repo: `CancerDAO/n1arxiv` v0.1.0

Brand-new public repo. Static Hugo site with:

- `schemas/n1a_bundle.v0.1.schema.json` (mirror)
- `content/papers/2026-05-28-riaz-reference.md` (seed Riaz stub)
- `static/bundles/2026-05-28-riaz-reference.n1a.zip` (seed bundle —
  banner `[REFERENCE CASE — PUBLIC DATA, NOT THIS PATIENT]`)
- `scripts/validate_bundle.py` (schema + SHA + G29-G33 + consent
  attestation; called by CI)
- `.github/workflows/validate_submission.yml` (PR gate)
- `.github/workflows/build_site.yml` (Hugo → `gh-pages`)
- `tests/test_schema_v0_1.py`, `tests/test_ci_rejects_bad_bundle.py`,
  `tests/test_hugo_build.py` (Hugo test gated on `which hugo`)
- `docs/submission_guide.md`, `docs/n1_ethics.md`,
  `docs/ai_authorship_policy.md`, `docs/faq.md`
- `LICENSE` documenting the dual CC-BY-4.0 + MIT split
- `.gitignore` includes `docs/superpowers/` from day one

### Added — tests (opl-cancer side)

- `tests/test_delivery/test_n1arxiv_submitter.py` — 6 unit +
  integration tests: content-stub generation, deterministic paper_id,
  byte-exact zip copy, PR-body real_patient consent reminder,
  no-shell-out invariant, zip integrity round-trip.
- `tests/test_cli/test_opl_submit_to_n1arxiv.py` — 4 CLI tests:
  --help wiring, end-to-end with local clone, instructions-only
  without clone, draft+submit refusal.

### Modified

- `pyproject.toml`: 2.3.0 → 2.4.0
- `SKILL.md`: 2.3.0 → 2.4.0; triggers extended with `n1arxiv`,
  `submission`, `preprint platform`, `submit my paper`
- `README.md`: v2.4.0 line in Recent changes; `## N1Arxiv` section
  linking to `CancerDAO/n1arxiv`
- `src/opl_cancer/cli.py`: `wave6` gains `--submit-to-n1arxiv` +
  `--n1arxiv-repo`; refuses `--submit-to-n1arxiv --draft`

### Deferred to N1Arxiv v0.2

- DOI registration (CrossRef / DataCite)
- Patient one-click submission UI wrapping `gh`
- Domain registration (`n1arxiv.org` — placeholder in README +
  `config.toml`; v0.1 ships on `n1arxiv.cancerdao.org` via GitHub Pages)
- Backend search beyond Hugo's built-in list page
- Formal AI-authorship CRediT taxonomy beyond ADR-0023's
  `ai_authorship_disclosure.md`

---

## [2.3.0] — 2026-05-28 — Wave 6 Manuscript + `.n1a` Bundle

ADR-0023. Adds a publication-grade Wave 6 sibling to Wave 5: takes a
shipped patient brief and emits a preprint-style manuscript + a
self-contained `.n1a` bundle (schema v0.1). Closes P2 fixes #17, #18,
#20, #21, #22 from the 007-zhiqiang post-mortem. Adds 5 new mechanical
gates (G29-G33) for Wave 6 manuscript invariants. The N1Arxiv platform
(v2.4) will consume `.n1a` bundles via PR-based submission.

### Added — Wave 6 runner + bundle

- **`src/opl_cancer/glue/wave6_runner.py`** — transactional sibling to
  `delivery_runner.py` (v2.2 P1-#16 envelope). Three modes:
  `dry_run` / `draft` / `final`. Refuses if Wave 5 has not shipped
  both briefs. Rolls back on any gate-block failure.
- **`src/opl_cancer/delivery/n1a_bundle_writer.py`** — collects Wave 6
  artifacts from `triggers/<run_id>/`, computes SHA-256 per file,
  writes `manifest.json`, zips to `<id>_<date>.n1a.zip`, validates
  against the schema. Banner injection for non-`real_patient`
  data_sources (P2-#18).
- **`schemas/n1a_bundle.v0.1.schema.json`** — JSON Schema draft-2020-12.
  Required fields: schema_version, opl_version, patient_id_hash,
  generated_at, data_source enum, file_index, sha256s. Optional:
  cost_summary, henry_audit_summary, extends_prior_run, banner.

### Added — mechanical gates G29-G33 (28 → 33)

- **G29 `manuscript_authorship_disclosed`** —
  `ai_authorship_disclosure.md` must list every contributing expert
  (CRediT-style table) + attest "no human author beyond patient &
  supervising clinician."
- **G30 `claim_pmid_anchored`** — every claim sentence in
  `manuscript.md` ends with `[PMID:XXXXX]` or `[integrator:NAME
  run_id:HASH]`; `[BACKGROUND]` exempts framing prose.
- **G31 `figure_reproducible`** — each `figures/fig_N.png` has matching
  `figures/fig_N.py`; stochastic reproducers must declare
  `random_seed = X`.
- **G32 `data_availability_declared`** — `reproducibility.md`
  tier-labels every data source (`public` / `DUA` / `patient-private`).
  Patient-private sources MUST be labelled.
- **G33 `n1_design_transparent`** — methods text must declare
  "single-subject (N=1) design"; cohort/population language without
  a same-sentence caveat is flagged.

### Added — task packages (8) (54 → 62)

- `prompts/tasks/manuscript_introduction.md` — Iain; Wave 6;
  G29+G30. Wave 1 retrieval → intro + related work (cite-anchored).
- `prompts/tasks/manuscript_methods.md` — Aviv; Wave 6;
  G29+G30+G32+G33. N=1 design + integrators + data-source tiers
  + Henry gate inventory + consent framing.
- `prompts/tasks/manuscript_results.md` — Aviv; Wave 6; G29+G30+G31.
  Wave 3 evidence → results with figure/table refs.
- `prompts/tasks/manuscript_discussion.md` — Vince; Wave 6;
  G29+G30+G33. Wave 2 hypotheses + Wave 4 validation synthesis;
  N=1 caveats on every cohort/population claim.
- `prompts/tasks/manuscript_limitations.md` — Henry; Wave 6;
  G29+G30+G33. N=1 limits + AI-authorship + integrator snapshots
  + non-PASS gate enumeration.
- `prompts/tasks/manuscript_abstract.md` — Iain; Wave 6;
  G29+G30+G33. 250-word structured abstract (Background/Methods/
  Results/Conclusions).
- `prompts/tasks/citation_assembly.md` — Henry-adjacent; Wave 6;
  G1+G2+G30. PMIDs → BibTeX via PubMed esummary; G1 existence + G2
  first-author match re-verification.
- `prompts/tasks/figure_caption.md` — Aviv; Wave 6; G30+G31.
  Publication-grade captions with axes/N/test/reproducer.

### Added — P2 fixes

- **P2-#17** `src/opl_cancer/plan/prior_run_ingestion.py` — ingests
  `runs/<prior>/chair_final_report.md`; Wave 6 runner auto-detects
  latest prior run; carried into `manifest.extends_prior_run`;
  manuscript framing notes "extends prior MTB run X".
- **P2-#18** `src/opl_cancer/integrators/figure_render.py` —
  `watermark_png()` + `watermark_directory()` overlay diagonal banner
  text on every fig PNG for non-`real_patient` bundles. `manuscript.md`
  also gets the banner stamped into its header.
- **P2-#20** `src/opl_cancer/memory/cost_tracker.py` — append-only
  `runs/<run_id>/cost_log.jsonl`. `CostTracker.record_call()` +
  `record_subagent()` log per-call cost; `aggregate_cost_log()` builds
  the `manifest.cost_summary` shape (total_usd + tokens_input +
  tokens_output + by_model + by_wave + by_expert).
- **P2-#21** `patient_value_hierarchy_weights()` in
  `prior_run_ingestion.py` — reads `profile.patient_value_hierarchy`
  ordering for Wave 2/3 ranking pre-pending.
- **P2-#22** `src/opl_cancer/plan/task_sync.py` — JSONL TaskCreate /
  TaskUpdate writer. OFF by default; `OPL_TASKCREATE_INTEGRATION=1`
  enables. `emit_plan_tasks_for_waves()` + `mark_wave_completed()`.

### CLI

- **`opl wave6`** — new subcommand wiring the Wave 6 runner.
  Options: `--patient-dir` / `--run-id` / `--patient-code` (required);
  `--draft` / `--final` / `--dry-run` (mode); `--data-source` enum;
  `--extends-prior-run` override; `--json`. Exit codes: 0 ok / 2
  Wave5 prereq missing / 3 Wave6Failure.
- **`opl status`** — now reports `Mechanical gates: 33` (was 28) and
  `Wave runners ready: Wave1 / Wave2 / Wave3 / Wave4 / Wave5 (render) /
  Wave6 (manuscript+.n1a)`.

### Tests

- `tests/test_validators/test_g29..g33_*.py` — 39 unit tests across
  the 5 new gates.
- `tests/test_validators/test_gate_registry.py` — updated to 33 gates.
- `tests/test_integration/test_n1a_bundle_schema.py` — 9 integration
  tests on the bundle writer + 4-bundle schema-valid check.
- `tests/test_memory/test_cost_tracker.py` — 10 unit tests on the
  cost tracker.
- `tests/test_glue/test_wave6_runner.py` — 10 integration tests on
  the runner.
- `tests/test_v23_wave6_prompts.py` — 41 structural tests on the 8
  new task packages.
- `tests/test_plan/test_prior_run_ingestion.py` — 8 unit tests on
  P2-#17 + P2-#21.
- `tests/test_plan/test_task_sync.py` — 7 unit tests on P2-#22.
- `tests/test_integrators/test_figure_render_watermark.py` — 4 unit
  tests on P2-#18.
- `tests/test_cli.py` — 3 new CLI tests + status string update.
- `tests/test_e2e/test_wave6_riaz_manuscript.py` — Riaz reference
  E2E (data-presence-gated).
- `tests/test_e2e/test_wave6_007_manuscript.py` — real-patient E2E
  (gated on `OPL_REAL_PATIENT_OK`).

### Attribution

- Leey21/awesome-ai-research-writing prompts adapted (4 borrows:
  Zh→En translation, polish, chart-type recommendation, figure
  caption rules). All paraphrased + oncology-framed; not verbatim.
  License pending upstream grant (Leey21 issue open); fallback:
  rewrite from scratch if no response by v2.4 ship.

### Docs

- **ADR-0023** `docs/adr/0023-wave6-manuscript-and-n1a-bundle.md` —
  rationale, gate definitions, bundle format, P2 implementation
  surface, hand-off to v2.4 N1Arxiv.
- **SKILL.md** — frontmatter version 2.2.0 → 2.3.0; added `wave6`,
  `manuscript`, `n1a`, `preprint` triggers.
- **README.md** — v2.3.0 line in Recent changes.
- **`pyproject.toml`** version 2.2.0 → 2.3.0.

## [2.2.0] — 2026-05-28 — Equipped Experts

ADR-0022. Vendors 8 bio-skill task packages (7 required + 1 optional CPIC)
from `BioTender-max/awesome-bio-agent-skills` (CC0-1.0) as OPL-native
task-package + integrator pairs. Closes P1 fixes #10-#16 from the
007-zhiqiang real-patient run post-mortem. New mechanical gate G28 closes
the "5 weeks → 5 months" LLM time-confusion failure mode.

### Added — task packages (8)

- **`prompts/tasks/msi_detection.md`** — Bert; Wave 3; G14. MSI status
  call from MSIsensor-pro percent-unstable; KEYNOTE-158 + Lynch hooks.
- **`prompts/tasks/tmb_calculation.md`** — Bert; Wave 3; G21. Vendor-aware
  TMB→mut/Mb harmonisation (TSO500 1.94 / FoundationOne 0.8 /
  MSK-IMPACT-468 1.22 / WES 30 Mb). ≥10/Mb = TMB-H.
- **`prompts/tasks/cosmic_signature_extraction.md`** — Bert; Wave 3; G14.
  COSMIC v3.x SBS signature interpretation (HRD / MMR / POLE / APOBEC /
  UV / tobacco / TMZ).
- **`prompts/tasks/acmg_germline_classification.md`** — Bert; Wave 1; G2.
  ACMG 2015 5-tier classification + ClinVar conflict policy.
- **`prompts/tasks/opentargets_evidence.md`** — Maya; Wave 1+2; G1+G2.
  Per-datasource evidence breakdown (chembl / genetics / literature /
  reactome) for orthogonal-source evidence tier scoring.
- **`prompts/tasks/biostats_survival.md`** — Aviv; Wave 3; G15. KM + log-rank
  with explicit subset-filter rule (P1-#12 cBioPortal L3+, P1-#13 KRAS-G12C
  subset).
- **`prompts/tasks/biostats_subgroup.md`** — Aviv; Wave 3; G15+G17. Forest
  plot + interaction-p + multiple-testing correction.
- **`prompts/tasks/pharmacogenomics_cpic.md`** — Mary; Wave 3; G3.
  CPIC reference table for DPYD / TPMT / NUDT15 / UGT1A1 / CYP2D6 / CYP2C19.

### Added — integrators (8)

- **`integrators/msi_sensor.py`** — MSIsensor-pro wrapper + threshold helper.
- **`integrators/tmb_harmonization.py`** — vendor-aware TMB harmoniser
  with `PANEL_FOOTPRINTS_MB` map + `classify_tmb_status()`.
- **`integrators/cosmic_sigprofiler.py`** — SigProfilerAssignment wrapper
  (lazy-import; heavy ~1.5 GB ref) + curated `SBS_INTERPRETATION` table.
- **`integrators/varsome_acmg.py`** — pure-Python ACMG 2015 decision-table
  classifier with conflict-flag policy.
- **`integrators/lifelines_km.py`** — KM + log-rank + `apply_subgroup_filter()`
  helper with `min_n_per_arm` enforcement (G15/G17 prereq).
- **`integrators/cpic.py`** — curated CPIC v2.2 reference table.
- **`integrators/figure_render.py`** — matplotlib renderer for KM curve /
  forest plot / Monte Carlo trajectory PNG (P1-#14).
- **`integrators/paperqa_full_text.py`** — PMC OA full-text fetch shim +
  `CalibrationProvenance` enum (P1-#10).

### Added — P1 fixes

- **P1-#10** `glue/wave3_runner.py:record_monte_carlo_calibration()` —
  every Monte Carlo / model-fit site now emits `parameter_calibration:
  paper_derived | informed_estimate | literature_default` with PMID anchor.
- **P1-#11** `prompts/auditor/quote_verify_numerics.md` + reviewer_hook
  chain — per-PMID `n_resp`/`n_total` verifier auto-runs after Iain
  meta-analysis. Mismatches with `block_downstream:true` halt downstream wave.
- **P1-#12** subset-filter auto rule in `biostats_survival.md` —
  cBioPortal L3+ cohort KM narrows via `apply_subgroup_filter({"line":[3,4,5]})`
  before fit.
- **P1-#13** TROP2 KRAS-G12C subset filter — same `apply_subgroup_filter`
  mechanism (`{"kras":"G12C"}`) before KM.
- **P1-#14** matplotlib forest / KM / Monte Carlo PNG render via
  `figure_render` integrator — required Wave 3 output.
- **P1-#15** **`validators/gates/g28_absolute_date.py`** — relative date
  language (`X mo/week/day ago`, `约 N 月前`) must carry from_date+to_date
  anchor or `[BACKGROUND]` tag. Mechanical closure of the v2.1 LLM
  "5 weeks confused for 5 months" failure mode.
- **P1-#16** **`glue/delivery_runner.py`** + `opl deliver` command —
  Henry audit + patient_plain_brief + patient_pi_brief run as ONE
  atomic transaction; partial failure rolls back all three files.

### Added — extensions

- **`integrators/open_targets.py`** gains `evidence:<sym>:<efo>` key form
  returning per-datasource evidence breakdown.
- **`experts/roster.py`** — `task_package_portfolio` + `preferred_integrator_families`
  populated for Bert / Aviv / Mary / Maya (v2.0 stubs become real).
- **`ATTRIBUTIONS.md`** (top level) — credits BioTender-max/awesome-bio-agent-skills
  + every upstream tool dependency.
- **ADR-0022** Bio-skills vendoring as task packages with scope boundary.
- `pyproject.toml` adds `[bio]` extras group (`lifelines`, `matplotlib`;
  SigProfilerAssignment opt-in via comment).
- `goal_router.yaml` already added MSI / TMB / HRD / germline / DPYD /
  ctDNA keyword rows in v2.1 — v2.2 confirms the rows are still wired.

### Changed

- `pyproject.toml` version 2.1.0 → 2.2.0.
- `SKILL.md` frontmatter `version` 2.1.0 → 2.2.0; tags add
  `equipped-experts bio-skills msi tmb hrd acmg cpic survival-analysis`.
- `cli.py:status` — mechanical gates 27 → 28; integrators 29 → 36.
- `validators/mechanical_gates.py:all_gate_classes()` — registers G28
  AbsoluteDateGate (27 → 28).
- `experts/roster.py` — task_package_portfolio stubs become real for the
  4 v2.2 owning experts (Bert, Aviv, Mary, Maya).

### Tests

- `tests/test_validators/test_g28_absolute_date.py` (9 tests)
- `tests/test_validators/test_gate_registry.py` — bumped EXPECTED_GATE_COUNT 27 → 28
- `tests/test_integrators/test_msi_sensor.py` (10)
- `tests/test_integrators/test_tmb_harmonization.py` (12)
- `tests/test_integrators/test_cosmic_sigprofiler.py` (7)
- `tests/test_integrators/test_varsome_acmg.py` (11)
- `tests/test_integrators/test_open_targets_extended.py` (4)
- `tests/test_integrators/test_lifelines_km.py` (7)
- `tests/test_integrators/test_cpic.py` (9)
- `tests/test_integrators/test_figure_render.py` (6)
- `tests/test_integrators/test_paperqa_full_text.py` (7)
- `tests/test_glue/test_wave3_calibration.py` (4)
- `tests/test_glue/test_delivery_runner.py` (6)
- `tests/test_orchestrator/test_quote_verify_numerics.py` (6)
- `tests/test_experts/test_roster_v22_portfolios.py` (7)
- `tests/test_integration/test_subset_filter.py` (3) — P1-#12/#13 verification
- `tests/test_e2e/test_bio_skills_riaz.py` — Riaz reference, all 7 packages
- `tests/test_e2e/test_bio_skills_real_007.py` — 007-zhiqiang (gated)

---

## [2.1.0] — 2026-05-28 — Truthful Execution

ADR-0021. Closes the eight P0-class design / execution gaps identified in
session 4b177138, plus the fakery class (P1-#9, P2-#19).

### Added

- **`opl run --wave N`** real executor command (P0-#1, #2). Wave 3
  supports `--mode {docker,native,dry-run}` and auto-selects native when
  Docker is absent. `wave1`/`wave2`/`wave3`/`wave4` stay as state-checks
  with explicit help text now marking them so.
- **`src/opl_cancer/plan/goal_router.py`** + `goal_router.yaml` keyword
  routing (P0-#4). Vaccine / irAE / cross-border / MSI-H / TMB / HRD /
  germline / DPYD / ctDNA patterns route to specific expert subsets.
- **`src/opl_cancer/plan/schema_validator.py`** profile↔trigger field
  alignment hard-fail at plan emit (P0-#5). Did-you-mean suggestions.
- **`src/opl_cancer/plan/task_validator.py`** task_package fail-fast
  (P0-#6). 46 task packages glob-loaded at runtime; typos rejected with
  Levenshtein Did-you-mean top-3.
- **`agents/opl-experts.yml`** — 21 OPL-specific subagent types
  (20 experts + Henry) with `Write` scoped to
  `patients/*/triggers/*/tasks/**` (audit/** for Henry) (P0-#3).
- **`docs/SUBAGENT_CONTRACT.md`** explaining Path 1 vs Path 2.
- **`opl preflight --install-agents`** installs the opl-* subagent types.
- **`src/opl_cancer/orchestrator/reviewer_hook.py`** distinct-model +
  distinct-expert reviewer dispatch after every expert write (P0-#7).
  Persisted as `review.json` next to each `report.md`.
- **`src/opl_cancer/integrators/clinicaltrials.verify_site_open()`** +
  `site_verification_map.yaml` — cross-verify CT.gov RECRUITING status
  against the hospital's own page (P0-#8).
- **`src/opl_cancer/validators/fakery_sniffer.py`** cross-cutting
  safety net (P1-#9). Scans every artifact for placeholder language;
  hits halt the wave + emit `SNIFFER_HALT.md`. `[BACKGROUND]` lines are
  exempt.
- **`src/opl_cancer/orchestrator/pushback_router.py`** keyword + sniffer
  auto-trigger (P2-#19). Appends rows to `pushback_trigger_log.jsonl`.
- **ADR-0021** Truthful Execution Invariants — three orthogonal
  invariants that every future release must preserve.
- **`schemas/profile.schema.json`** v0.1 — JSON Schema with required
  `patient_id_hash` + optional triggers; `additionalProperties: true`.
- **`KNOWN_EXPERTS`** in `plan/schemas.py` extended 18 → 20 (adds
  maya + julius) to align with the v2.0 roster declared in SKILL.md.

### Changed

- `wave1`/`wave2`/`wave3`/`wave4` help text now begins with "state-check
  only — does NOT execute. Use `opl run --wave N` for the executor."
- `pyproject.toml` version 1.5.7 → 2.1.0.
- `pyproject.toml` adds `jsonschema>=4.21` dependency.
- `SKILL.md` frontmatter version 2.0.0 → 2.1.0.

### Tests

- `tests/cli/test_opl_run_wave3_native.py` — opl run --wave 3 wires
  NativeAnalysisRunner.
- `tests/cli/test_wave_status_aliases.py` — wave1-4 help marks them
  state-check.
- `tests/cli/test_preflight_refuses_no_executor.py`.
- `tests/plan/test_goal_router.py` + `test_comorbid_planner_with_goal_router.py`.
- `tests/plan/test_profile_schema.py` + `test_schema_validator.py`.
- `tests/plan/test_task_validator.py`.
- `tests/agents/test_opl_experts_yml.py`.
- `tests/test_orchestrator/test_reviewer_hook.py`.
- `tests/test_orchestrator/test_pushback_router.py`.
- `tests/test_validators/test_fakery_sniffer.py`.
- `tests/test_glue/test_sniffer_halt.py`.
- `tests/test_integrators/test_ct_gov_site_verify.py`.
- `tests/test_e2e/test_v2_1_riaz.py` + `test_v2_1_007.py` (skipped when
  patient data not present locally — see file headers).

### Deviations from the original v2.1 plan

* `opl run --wave 3` directly drives `NativeAnalysisRunner.run_notebook`
  on a smoke notebook rather than instantiating the full `Wave3Runner`
  class (which requires populated LLM client + experts). This proves the
  compute path while remaining honest about LLM responsibility staying
  with the SKILL main thread (per ADR-2026-04-22).
* `Wave1Runner.run` now writes per-task `tasks/w1_<task_id>/report.md`
  sidecars; in v2.0 these were aggregated into the final brief without
  per-task persistence. The sidecars are the surface the reviewer hook +
  fakery sniffer attach to.
* `Wave2Runner` / `Wave3Runner` / `Wave4Runner` retain their existing
  signatures unchanged; the reviewer pairing + sniffer hooks are wired
  only in Wave 1 for this release. Extending to Waves 2-4 is tracked for
  v2.1.1 (the hooks are reusable; the wiring is mechanical).
* `goal_router.yaml` lives under `src/opl_cancer/plan/` (Python package
  data) rather than at the repo top-level — this keeps the yaml inside
  the installed wheel and reachable from `Path(__file__).parent`.

## [2.1.0-rc1] — 2026-05-26 — Trace-Digest Evolution (borrowed from EvoMaster, NOT policy)

Branch: `iter/v2-followup-evolution` (off `iter/v2-paradigm`). Implements
ADR-0020 — a post-mortem proposal generator inspired by
`sjtu-sai-agents/EvoMaster`'s `--evolve` architecture, with 3 medical red
lines explicitly enforced. Never auto-applies to baseline.

### Added

- **`src/opl_cancer/evolution/`** package (7 new modules):
  - `models.py` — TraceDigest (bounded ~100KB), EvolutionProposal,
    InvariantImpact, EvolutionCandidates
  - `collector.py` — reads run dir → TraceDigest (read-only)
  - `scrubber.py` — PII/PHI strip BEFORE any LLM call (Chinese names + DOB
    + MRN + email + hospital + PT-code; preserves gene/drug/PMID/NCT)
  - `invariant_gate.py` — static analysis flags patches touching Henry
    L3/L4, G7, G13, persona_prefix, claim_layer, RetractionDB → auto-sets
    `requires_double_signoff: true`
  - `analyzer.py` — red-team system prompt (distinct from main medical
    agents), LLM call OR deterministic heuristic fallback (loud, marked
    `used_heuristic_fallback: true`)
  - `proposal_writer.py` — writes ONLY under `proposals/iter_<N>/`,
    refuses baseline paths at the filesystem level
  - `__init__.py` — package surface
- **`opl-cancer evolve <run_dir>`** CLI subcommand. No `--auto-apply` flag.
- **`scripts/verify_evolution_e2e.py`** — 7-check verifier mapped to
  ADR-0020 success criteria
- **ADR-0020** + `docs/superpowers/plans/2026-05-26-trace-digest-evolution.md`
- **56 new tests** under `tests/test_evolution/`
- ROADMAP updated with ADR-0020 entry

### 3 medical red lines enforced (NOT copied from EvoMaster)

1. **No `_write_prompt_overlays` auto-append.** Patches → unified diff in
   `proposals/iter_<N>/prompt_patches.diff`. Never to `*.evolved.txt`.
2. **No auto-respawn.** Evolution is post-mortem only. Next patient run
   uses baseline unchanged. After human review + Sid+Henry signoff,
   approved patches land via normal PR; future patients benefit.
3. **No skill `extra_roots` auto-extension.** Proposed skills sit in
   `proposals/iter_<N>/skill_additions/<slug>/SKILL.md.proposed` with
   mandatory `clinical_anchor` field. Skill registry merge will be the
   ADR-0014 follow-up branch.

### Beyond EvoMaster

- PII/PHI scrubber (closes EvoMaster's documented `runs/` privacy gap)
- Red-team analyzer prompt (distinct from medical agents)
- InvariantGate static analysis flagging safety surfaces
- ProposalWriter filesystem-level refusal of baseline paths
- Clinical-anchor mandatory for skill proposals (auto-reject otherwise)

### Compatibility

- All v2.0.0-rc1 tests pass (1221 + 56 new = **1277 passed**, 0 failures)
- No production flow touches evolution unless `opl-cancer evolve` invoked
- Output entirely under `<run_dir>/proposals/` (gitignored at project level)

---

## [2.0.0-rc1] — 2026-05-26 — Paradigm Shift: Surface World-Unknown Candidates

Branch: `iter/v2-paradigm`. Driven by the PT-EE62321353 run review which
revealed that Wave 2 produced 17 hypothesis cards but ALL were
recombinations of already-published regimens. The system was a polished
MTB, not an AI scientist team. ADR-0010 documents the forensic.

This release ships the 5-seam paradigm shift. Larger surface changes
(Wave 3 hard gate, Wave 3→Wave 2 feedback loop, live PrimeKG client,
skill registry, K-Dense bridge, Julius live wiring, cross-run memory) are
tracked as independent follow-up branches in `references/v2-roadmap.md`.

### Added

- **2 new generation strategies**: `target_synergy_emergent` +
  `undrugged_target_design`. Extends STRATEGIES tuple (4 → 6) +
  GenerationStrategy Literal + _STRATEGY_GUIDANCE dict.
- **2 new experts in roster (18 → 20)**:
  - **Maya** — Knowledge-Graph Synergy Reasoner. Owns
    `target_synergy_emergent` + `synthetic_lethal_partner_query` +
    `drug_drug_synergy_kg_query` + `pathway_crosstalk_reasoning`.
    Composite archetype: Marinka Zitnik (PrimeKG/Harvard) + Tijana
    Milenković (network medicine).
  - **Julius** — Medicinal Chemist (in silico). Owns
    `undrugged_target_design` + `structure_source_acquisition` +
    `virtual_screen_design` + `chemical_filter_application`. Composite
    archetype: ESMFold + DiffDock + RDKit + medchem filter lineage.
- **PrimeKG integrator stub** at `src/opl_cancer/integrators/primekg.py`.
  Live HTTP/SPARQL client deferred to `iter/v2-followup-primekg`. Stub
  raises `NotImplementedError` on live query (no silent fallback per
  `memory:feedback_no_offline_only`).
- **Patient brief "⚡ World-Unknown / Speculative Candidates" section** in
  both `prompts/delivery/patient_brief.html.j2` + `.md.j2`. Renders [S]
  hypotheses with strategy + Elo + `testability_path` + KG-edge anchors.
  Explicit 中英双语 framing: "研究方向，未发表 / 未验证 — research
  direction, not a treatment recommendation".
- **`testability_path` field mandatory** on all `[S]` hypotheses produced
  by strategies 5+6.
- **ADR-0010** + `references/v2-paradigm.md` + `references/v2-roadmap.md`.

### Changed

- **`prompts/pi/proactive_push.md`** flipped from v1.2.0: speculative
  claims ARE pushed when `testability_path` non-empty +
  `surface_section == world_unknown_candidates`. The v1.2.0 hard ban
  ("Never push speculative claims proactively") was the direct mechanism
  by which Sid hid world-unknown candidates from the patient.
- **`prompts/tasks/hypothesis_generation.md`** v1.2.0 "Do NOT synthesize
  from training data" rule LIFTED for strategies 5+6 (the strategies'
  whole purpose is to propose what training data cannot have seen). Rule
  retained for strategies 1-4.
- README: 18 → 20 experts; new v2 paradigm pointer section.
- 6 existing roster-cardinality tests updated 18 → 20 (with ADR-0010
  cross-reference inline).

### Unchanged

- Wave 1 / 3 / 4 / 5 runners.
- Henry validator (high-Level risk-card behavior intact).
- Tournament Elo math, debate.py judge prompt.
- All existing 18 experts.
- Existing 64 renderer tests pass — World-Unknown section absent when
  `world_unknown_candidates` undefined / empty.

### Tests

- New: tests/test_v2_generation_strategies.py (4 tests).
- New: tests/test_v2_prompts.py (6 tests).
- New: tests/test_v2_roster_maya_julius.py (6 tests).
- New: tests/test_v2_primekg_integrator.py (4 tests).
- New: tests/test_v2_renderer_world_unknown.py (5 tests).

### Verification

- `scripts/verify_v2_e2e.py` checks ADR-0010 success criteria on a run dir.
- E2E validation matrix at `references/v2-e2e-validation-matrix.md`
  (≥2 patients ≥2 cancer types per the multi-case validation rule in `CONTRIBUTING.md`).

### Known follow-ups (see `references/v2-roadmap.md`)

- ADR-0011 Wave 3 hard gate (`iter/v2-followup-wave3-gate`).
- ADR-0012 Wave 3 → Wave 2 feedback loop (`iter/v2-followup-feedback-loop`).
- ADR-0013 live PrimeKG client (`iter/v2-followup-primekg`).
- ADR-0014 skill registry (`iter/v2-followup-skill-registry`).
- ADR-0015 K-Dense-AI bridge (`iter/v2-followup-kdense-bridge`).
- ADR-0016 Julius live wiring (`iter/v2-followup-julius-live`).
- ADR-0017 cross-run memory (`iter/v2-followup-cross-run-memory`).

---

## Earlier releases (pre-v2.0)

All releases before `[2.0.0-rc1]` — the v0.x scaffold series (`v0.0.1-p0` …
`v0.5.0-p5`) and the entire v1.x line (`1.0.0` … `1.5.7`) — are archived in
[`docs/CHANGELOG-archive.md`](docs/CHANGELOG-archive.md).
