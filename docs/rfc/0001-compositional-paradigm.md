# OPL v2 Vision RFC: From Enumerated Catalog to Compositional Engine

**Date**: 2026-05-28
**Author**: CancerDAO Contributors
**Status**: RFC v0.1 — to be committed to repo as `docs/rfc/0001-compositional-paradigm.md`
**Origin**: A user asked whether OPL would auto-download public databases + ML-model their prognosis; OPL responded "no, we don't do AutoML on N=1 because…" — correct on the merits but a symptom of a deeper limit: any method/cancer-type/data-source outside the hardcoded catalog can only be refused or jammed into a near-match. v2 paradigm fixes this at five layers.
**Borrows from**: SakanaAI/AI-Scientist-v2 (best-first tree search, FunctionSpec typed contracts, distributed validation after execution — adapted with closed-world medical guardrails).

---

## §1. Why the current paradigm fails

OPL today is **enumeration-based** at five layers:

| Layer | Today (v2.4) | Failure mode |
|---|---|---|
| Expert | 20 named personas in `references/expert-roster.md` + `experts/roster.py` | New subspecialty (neuro-oncology × pharmacometrics × Bayesian adaptive × NMPA) → hard-jam into Vince, accuracy degrades |
| Task package | 63 hand-written `prompts/tasks/*.md` | Method not in the 63 → refused or mis-routed |
| Cancer type | 11 hardcoded planner rows + (default) for everything else | Rare cancer → default treatment, low resolution |
| Integrator | 44 hand-written API clients | New DB (ChinaMAP, WCH-Cohort, JP NCC-Oncopanel) → requires PR before useable |
| Gate | 33 hardcoded validators G1-G33 | New method → new gate hand-written, or no validation at all |

The AutoML-on-N=1 incident is the canonical symptom: a legitimate question ("AutoML on my profile") hits a refusal because there's no compositional path through the planner. The fix is not adding an `automl_prognostic_modeling.md` task package — that's the same enumeration trap, one row larger. The fix is **composition**.

---

## §2. The 5-layer shift

### 2.1 Expert: 20 fixed → open role taxonomy

**Today**: 20 names with persona prompts; `roster.py` declares them; `agents/opl-experts.yml` grants tools.

**v2**: An *expert role* is a tuple `(discipline, subspecialty, method_specialty, bridging_role)`. The 20 named personas become high-frequency *fast-path* shortcuts pointing at specific tuples. New roles materialize at plan time via a *role-composition* LLM call against a curated taxonomy + the patient's compose-needs.

**Anchor files**:
- `references/role_taxonomy.yaml` — discipline / subspecialty / method-specialty / bridging-role enumerations
- `prompts/experts/_template.md` — parametric persona prompt; render takes role params
- `src/opl_cancer/experts/role_composer.py` — `compose_role(constraints) → ExpertRole` + `to_persona_prompt(role) → str`
- `src/opl_cancer/experts/roster.py` — existing 20 personas become `FAST_PATH_ROLES: dict[name, ExpertRole]`

### 2.2 Task package: static `.md` list → method primitive registry + composition DAG

**Today**: 63 `.md` files, each a hand-written recipe.

**v2**: Method primitives in `prompts/methods/<method_id>.yaml`. Each entry:
```yaml
id: cox_proportional_hazards
domain: statistical
inputs: {event_time: float, event_status: bool, covariates: dataframe}
outputs: {hazard_ratios: dict, ci95: dict, ph_test_p: float}
assumptions: [proportional_hazards, no_competing_risks, ...]
applicable_gate_families: [statistical-validity, reproducibility, provenance]
implementation_ref: integrators.lifelines_km:cox_fit
literature_refs: [PMID:7144749, ...]
```

The planner emits a **DAG of method primitives** in plan.json; the wave runners walk the DAG. Existing 63 task packages become reference recipes — useful examples for the composer, not the only legal vocabulary.

**Anchor files**:
- `src/opl_cancer/methods/registry.py` — `MethodRegistry`, `MethodPrimitive` dataclass, `load_all()`, `find_by_domain()`, `find_by_capability()`
- `prompts/methods/` directory — initial seed of ~8 primitives across 4 domains (statistical / bioinformatics / clinical / pharmacology)
- `src/opl_cancer/plan/task_composer.py` — replaces hardcoded `comorbid_planner`'s task-list emission with DAG composition

### 2.3 Cancer type: 11 hardcoded → KG-derived context generator

**Today**: `planner` has 11 named rows.

**v2**: Any cancer code (ICD-O-3 / SNOMED / NCI Thesaurus) yields a `cancer_context.json` auto-built from:
- PrimeKG (drug-disease-gene graph)
- OncoKB (actionable variants)
- NCCN PageIndex (current SoC chain)
- cBioPortal (real-world frequency)
- ClinicalTrials.gov (trial landscape)

Cached per-cancer at `references/cancer_contexts/<icdo3>.json` with TTL.

**Anchor files**:
- `src/opl_cancer/cancer_context/generator.py` — `CancerContextGenerator(icdo3_or_snomed, force_refresh)` → JSON
- `cli.py generate-cancer-context --icdo3 <code> [--output ...]`
- `src/opl_cancer/plan/task_composer.py` reads the JSON to compose expert + method DAG

### 2.4 Integrator: 44 named → plugin protocol + auto-discovery

**Today**: each integrator hand-written; `integrators/` directory hardcoded.

**v2**: `IntegratorABC` defines protocol. Python *entry points* register integrators (in-tree or external packages). New source = drop-in plugin. **Universal API adapter**: given OpenAPI/GraphQL schema URL, an LLM-generated temporary client + sanity probe enables long-tail DBs without a PR.

**Anchor files**:
- `src/opl_cancer/integrators/_abc.py` — `IntegratorABC` (sources, query, normalize, provenance) + `IntegratorRegistry.discover()` walks `opl_cancer.integrators` entry points
- `pyproject.toml` — `[project.entry-points."opl_cancer.integrators"]` table populated with existing 44
- `src/opl_cancer/integrators/universal_adapter.py` — `from_openapi(schema_url) → AdHocIntegrator` (v2.5 ships with sandbox + sanity probe; live LLM-gen in M3)

### 2.5 Gate: G1-G33 hardcoded → gate families + principled framework

**Today**: 33 gate classes in `validators/gates/`.

**v2**: Six gate families:
1. **provenance** — every claim has evidence anchor (PMID / NCT / KG node / SMILES / notebook SHA)
2. **statistical-validity** — every inference declares assumptions + test + multiple-comparison correction
3. **temporal-recency** — guideline / drug / trial citation ≤ 18 months stale
4. **scope-isolation** — speculative / exploratory / established three-tier non-leakage
5. **safety-disclosure** — L3/L4 claim has risk-card
6. **reproducibility** — any analysis bit-exact rerun

Each method primitive declares `applicable_gate_families: [...]`; gates auto-bind. Existing G1-G33 become *instances* under families.

**Anchor files**:
- `src/opl_cancer/validators/gate_families.py` — `GateFamily` ABC, six concrete families, `bind_gates(method, claim) → list[Gate]`
- `src/opl_cancer/validators/gates_registry.yaml` — each existing G1-G33 mapped to its family + applicability predicate
- Existing `validators/gates/g*.py` classes refactor to inherit from one of the six families

---

## §3. Backward compatibility — v1.x assets as fast-path caches

| v1.x asset | v2 role |
|---|---|
| 20 named experts | `FAST_PATH_ROLES` — high-frequency role-composition shortcuts |
| 11 cancer-type rows | seed entries in `references/cancer_contexts/` cache |
| 63 `prompts/tasks/*.md` | reference recipes for method composer + few-shot in-context examples |
| 33 gates G1-G33 | concrete instances inside the six gate families |
| 44 integrators | initial entry-point registrations against `IntegratorABC` |

Existing patient runs in `patients/<id>/triggers/<run>/` MUST keep working without modification.

---

## §4. Migration path — 6 milestones over ~3-6 months

| Milestone | Deliverable | ETA |
|---|---|---|
| **v2.5.0** (this RFC ships) | Foundation: 4 module ABCs + 8 method primitives + 1 gate family migrated + role taxonomy schema + `cancer_context generate` CLI + universal_adapter sandbox + bug fix (compositional unknown-task intake) | T+1w |
| **M1 / v2.6** | Migrate all 33 gates to families; deprecate hardcoded gate registry | T+4w |
| **M2 / v2.7** | Migrate 20 expert personas to role taxonomy; `experts/roster.py` becomes `FAST_PATH_ROLES` lookup | T+8w |
| **M3 / v2.8** | Migrate 44 integrators to entry-point plugin protocol; ship live universal_adapter | T+12w |
| **M4 / v2.9** | Expand method primitive library to ~50 primitives across all 4 domains | T+16w |
| **M5 / v3.0-rc1** | TaskComposer LLM upgrade — DAG composition for real, replaces `comorbid_planner` as primary planner | T+20w |
| **M6 / v3.0** | KG cancer-context generator live (PrimeKG + OncoKB + NCCN); seed cache for top-50 cancers; deprecate `(default)` planner row | T+24w |

---

## §5. EVAL strategy — testing an open-world system

The hardest design problem. Sketch (refined in v2.6):

1. **Closed-world regression**: every prior patient run must reproduce bit-exact (provenance + reproducibility gate families do double duty)
2. **Composition coverage**: for a curated benchmark of 100 prompt-types crossing (cancer × method × data-source), measure planner success rate (DAG validates against gate families) without human PR
3. **Hallucination audit**: for every novel composition the planner emits, gate-family bind-rate must be 100% before run; failed binds halt with `BindFailureHalt`
4. **Safety regression**: synthetic adversarial prompts (e.g., "predict my prognosis via AutoML on N=1") must route to risk-card emission + L4-disclosure, not silent execution
5. **Borrowed from SakanaAI**: best-first tree search at hypothesis stage with metric pruning; rejected branches log to journal for audit
6. **Patient delivery sanity**: random sample of N=20 generated reports reviewed by clinician panel; report includes `provenance_completeness_pct` and `unbound_gate_count` headers

---

## §6. Risk — composition raises hallucination surface; gate framework must stabilize FIRST

- Composition trades structural correctness (enumeration ensures every output type is pre-validated) for breadth (any method composable).
- Without solid gate families, broader composition = broader fabrication.
- **Therefore**: v2.5 ships **gate family framework first** + 1 family fully migrated as proof. M1 (full gate migration) precedes M5 (TaskComposer LLM upgrade) — never invert.
- **SakanaAI lesson**: their unguarded LLM code generation is fine for ML research where patients aren't downstream. OPL stays closed-world for drug/trial/dose IDs; composition is *over methods*, not *over facts*.

---

## §7. Decision points for maintainers

Below items require founder decision before milestone close:

1. **v2.5 scope confirmation** — is "foundation + 1 family + RFC committed" enough for the next session test? *Default yes; see §4.*
2. **Naming**: `MethodRegistry` vs `MethodLibrary` vs `MethodPrimitiveStore` *(default: MethodRegistry)*
3. **Role taxonomy custodian** — auto-curated by LLM vs human-vetted YAML? *Default: human-vetted YAML in v2.5/2.6; LLM-augmented in M3*
4. **Universal API adapter risk** — auto-generated clients running against live medical DBs without human review = NO. Sanity-probe + dry-run only in v2.5; live mode gated behind `OPL_UNIVERSAL_ADAPTER_LIVE=1` opt-in
5. **Gate family numbering** — keep G1-G33 as instance IDs OR renumber under families (e.g., P1 / S1 / T1 etc.)? *Default: keep G1-G33 as instance IDs; add `family:` tag*
6. **EVAL benchmark corpus** — needs to be authored separately (~100 patient-prompts); deferred to v2.6 M1

---

## §8. v2.5.0 ship list (this release)

1. **This RFC** — committed to repo at `docs/rfc/0001-compositional-paradigm.md` (NEW directory)
2. **MethodRegistry** — ABC + dataclass + loader; **8 seed method primitives** across 4 domains:
   - statistical: `cox_proportional_hazards`, `kaplan_meier`, `conformal_prediction`
   - bioinformatics: `deseq2_differential_expression`, `gsea_enrichment`
   - clinical-research: `recist_response_assessment`, `acmg_germline_classification`
   - pharmacology: `popPK_NONMEM_proxy`
3. **GateFramework** — `GateFamily` ABC + 6 concrete families + auto-bind; **provenance family fully migrated** (G1 PMID-existence + G2 PMID-quote-match + G30 claim-anchored as concrete instances under it); remaining 30 gates carry an `applicable_family` tag for M1 migration
4. **RoleTaxonomy** — YAML schema; existing 20 personas declared as `FAST_PATH_ROLES`; `compose_role()` API stub (returns FAST_PATH match in v2.5; real composition in M2)
5. **CancerContextGenerator** — CLI `opl generate-cancer-context --icdo3 <code>` writes stub `cancer_context.json` (real KG queries in M6; v2.5 ships scaffold + 2 seed cancers HCC + NSCLC)
6. **IntegratorABC + entry-point discovery** — ABC + 5 existing integrators (pubmed, opentargets, clinicaltrials, cbioportal, oncokb) declared as entry points; 39 others tagged for M3
7. **UniversalAdapter sandbox** — `from_openapi(schema_url, dry_run=True)` only; live mode raises until M3
8. **Compositional unknown-task intake (the AutoML-on-N=1 bug fix)** — new `prompts/tasks/unknown_task_intake.md` + `src/opl_cancer/plan/intake_router.py`. Any patient question that doesn't match an existing task package no longer refuses — routes to TaskComposer (stubbed in v2.5; real in M5) which emits a method DAG plus an explicit L4-disclosure card explaining what's being composed
9. **ADR-0025** — Architecture decision record memorializing the v2 paradigm
10. **README + SKILL.md** — bump to v2.5.0; "Recent changes" section explains the compositional shift; trigger tags add `compositional`, `method primitive`, `role taxonomy`
11. **Tests** — at least 1 test per new module; backward-compat test that every v2.4 task package still resolves; the AutoML-on-N=1 regression test (AutoML question routes via intake_router instead of refusing)
12. **Borrow from SakanaAI**: best-first ranking helper at `src/opl_cancer/orchestrator/best_first_journal.py` (used by Wave 2 hypothesis tournament). Pattern adapted: rank by `evidence_strength` + `citation_count`; log pruned branches to `journal.jsonl` for audit. **Not the runtime: we keep closed-world; the journal pattern is what we adopt.**

Backward compat strictly maintained: all 33 v2.4 gates keep running; all 63 task packages still resolve; all 44 integrators still callable; 20 experts still in roster.py. The new compositional layer SITS ABOVE them.

---

## §9. Out of scope for v2.5

- Full TaskComposer LLM (M5)
- Live universal API adapter (M3)
- Migration of remaining 5 gate families (M1)
- Migration of 20 personas to taxonomy entries (M2)
- Migration of 39 integrators to entry points (M3)
- Live KG cancer-context queries (M6)
- N1Arxiv-side composition support (deferred)
- EVAL benchmark corpus (M1 deliverable)

---

## §10. Acknowledgements

- SakanaAI/AI-Scientist-v2 (Cong Lu et al., ICLR 2025 workshop) — best-first journal pattern + typed-output FunctionSpec inspiration
- The AutoML-on-N=1 case for surfacing the failure mode in concrete form
