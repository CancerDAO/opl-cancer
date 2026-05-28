# ADR-0025: Compositional Paradigm (v2.5 — Foundations Only)

**Status**: Accepted (v2.5.0 ships the foundation; M1-M6 follow)
**Date**: 2026-05-28
**Supersedes**: none
**Superseded by**: none yet
**Authors**: zwbao (鲍志炜, CancerDAO founder)
**Spec / RFC**: `docs/rfc/0001-compositional-paradigm.md`
**Origin session**: `c3195b66-929f-4721-b56b-ddc0169c8a74` (AutoML-on-N=1
intake → flat refusal; surfaced the underlying paradigm limit)

---

## Context

Through v2.4, OPL operated as an **enumeration system** at five layers:

| Layer | v2.4 form |
|---|---|
| Expert | 20 named personas (`experts/roster.py`) |
| Task package | 63 hand-written `prompts/tasks/*.md` |
| Cancer type | 11 hardcoded planner rows + `(default)` |
| Integrator | 44 hand-written API clients |
| Gate | 33 hardcoded validators `G1-G33` |

The session-c3195b66 incident made the cost visible: a legitimate patient
question that wasn't pre-enumerated could only be refused or jammed into a
near-match. Adding one more task package per failure is the same trap one
row larger. RFC 0001 proposes a **compositional** paradigm where the five
layers expose ABCs + registries that the planner can compose at run time,
with v1.x assets serving as **fast-path caches**.

## Decision

Adopt the compositional paradigm over six milestones:

| Milestone | Deliverable | ETA |
|---|---|---|
| **v2.5 (this ADR)** | Foundation: 4 module ABCs + 8 method primitives + 1 gate family migrated + role taxonomy schema + cancer-context CLI + universal-adapter sandbox + compositional unknown-task intake (c3195b66 bug fix) + Sakana journal pattern + ADR-0025 + RFC 0001 committed | T+1w |
| **M1 / v2.6** | Migrate all 33 gates to families; deprecate hardcoded gate registry; EVAL benchmark corpus | T+4w |
| **M2 / v2.7** | Migrate 20 expert personas to role taxonomy; `experts/roster.py` becomes `FAST_PATH_ROLES` lookup; real LLM `compose_role()` | T+8w |
| **M3 / v2.8** | Migrate 44 integrators to entry-point plugin protocol; ship live universal_adapter (with sanity probe gate) | T+12w |
| **M4 / v2.9** | Expand method primitive library to ~50 primitives across all 4 domains | T+16w |
| **M5 / v3.0-rc1** | TaskComposer LLM upgrade — DAG composition for real; replaces `comorbid_planner` as primary planner | T+20w |
| **M6 / v3.0** | KG cancer-context generator live (PrimeKG + OncoKB + NCCN); seed cache for top-50 cancers; deprecate `(default)` planner row | T+24w |

v2.5 strictly ships the **foundation**. Full migration of any of the five
layers is M1-M6 work.

## Backward compatibility (hard invariants)

v2.5 maintains:
- All 33 v2.4 gates keep registering + checking (`mechanical_gates.all_gate_classes()`)
- All 63 v2.4 task packages still resolve via `task_validator` (now 64 with `unknown_task_intake.md`)
- All 44 v2.4 integrators still importable + their tests pass
- 20 named personas still in `roster.py` (FAST_PATH_ROLES wraps them)
- All v2.4 CLI commands unchanged
- Existing patient runs in `patients/<id>/triggers/<run>/` remain replayable

## Anchors shipped in v2.5

| Asset | Path |
|---|---|
| MethodPrimitive + MethodRegistry | `src/opl_cancer/methods/` |
| 8 seed method primitives | `prompts/methods/*.yaml` |
| GateFamily ABC + 6 families | `src/opl_cancer/validators/gate_families.py` |
| Gate-family registry tagging G1-G33 | `src/opl_cancer/validators/gates_registry.yaml` |
| Provenance family migration of G1/G2/G30 | `validators/gates/g{1,2,30}_*.py` (class attr `family_id`) |
| ExpertRole + FAST_PATH_ROLES + compose_role stub | `src/opl_cancer/experts/role_taxonomy.py` |
| Role taxonomy YAML | `references/role_taxonomy.yaml` |
| Parametric persona template | `prompts/experts/_template.md` |
| CancerContextGenerator + 2 seed JSONs + CLI | `src/opl_cancer/cancer_context/` |
| IntegratorABC + entry-point registry | `src/opl_cancer/integrators/_abc.py` |
| pyproject `opl_cancer.integrators` entry-points (5 of 44) | `pyproject.toml` |
| UniversalAdapter sandbox | `src/opl_cancer/integrators/universal_adapter.py` |
| intake_router + unknown_task_intake.md | `src/opl_cancer/plan/intake_router.py` + `prompts/tasks/unknown_task_intake.md` |
| best-first journal (Sakana borrow) | `src/opl_cancer/orchestrator/best_first_journal.py` |
| RFC 0001 in-repo | `docs/rfc/0001-compositional-paradigm.md` |

## Risk + mitigation

Composition raises hallucination surface area. Mitigation:

1. **Gate families ship FIRST** — v2.5 provenance family migrated as proof
   before any TaskComposer LLM is wired (M5 follows M1, never inverts).
2. **OPL stays closed-world for facts** — composition is over *methods*, not
   *over drugs / trials / doses*. RFC 0001 §6 invariant.
3. **Universal adapter ships sandbox-only** — live LLM-generated requests
   blocked behind `OPL_UNIVERSAL_ADAPTER_LIVE=1` opt-in until M3 adds the
   sanity-probe gate.
4. **Three-tier label preserved** — unknown_task_intake outputs are
   always Level-4 speculative.

## Deferred to subsequent milestones

Out of v2.5 scope (kept here so they don't slip):
- Full TaskComposer LLM (M5)
- Live universal API adapter (M3)
- Migration of remaining 5 gate families (M1)
- Migration of 20 personas to taxonomy entries (M2)
- Migration of 39 integrators to entry points (M3)
- Live KG cancer-context queries (M6)
- EVAL benchmark corpus (M1)
- N1Arxiv-side composition support (deferred)

## Verification (v2.5 release-gating)

- **c3195b66 regression test green**: feeding the literal session question
  to `route_intake()` returns `unknown_task_intake` route with
  `conformal_prediction` + `kaplan_meier` in the DAG and an L4 disclosure
  card — NOT a refusal.
- **Full pytest passes** with strictly increased test count vs v2.4.
- **All 33 v2.4 gates still register**; all 44 v2.4 integrators still
  importable; all v2.4 CLI commands unchanged.

## References

- RFC: `docs/rfc/0001-compositional-paradigm.md`
- Prior ADRs: 0021 (truthful execution), 0022 (bio-skills vendoring),
  0023 (Wave 6 manuscript), 0024 (N1Arxiv skeleton)
- Inspiration: SakanaAI/AI-Scientist-v2 (Cong Lu et al., ICLR 2025
  workshop) — journal pattern adopted; LLM code-gen sandbox NOT adopted.
