# ADR-0010 — v2 Paradigm Shift: Surfacing World-Unknown Candidates

**Status:** Accepted, 2026-05-26
**Branch:** `iter/v2-paradigm`
**Supersedes:** none (ADR-0009 v1.5 backend-rewrite is orthogonal)

## Context

User testing of OPL v1.5.7 on PT-EE62321353 (KRAS G12C MSS mCRC L4+) revealed
that Wave 2 produced 17 hypothesis cards in a full Co-Sci Elo tournament +
Robin 6-mode reflection — methodologically rigorous — but **all 17 were
recombinations of already-published regimens**. None proposed:

- A target-target synergy in this patient's profile that PrimeKG documents
  but no one has tested in this subtype.
- A candidate molecule against an undrugged target (e.g. MTAP-loss → PRMT5
  synthetic-lethal scaffold via DiffDock).
- An auto-deployed bioinformatics pipeline result that pre-dates publication.

The Top-5 was: cardiac workup (procedural) → sotorasib+panitumumab via Boao
(CodeBreaK 300 NEJM 2023) → re-NGS (procedural) → adagrasib+cetuximab
(KRYSTAL-1) → TAS-102+bev (SUNLIGHT NEJM 2023). Polished MTB, not an AI
scientist team.

Forensic of `tasks/w2_aviv/report.md` + the v1.5 code traced this to **four
mechanisms**:

1. `prompts/tasks/hypothesis_generation.md` `Empty-integrator rule (v1.2.0)`
   contains a hard ban: `"Do NOT synthesize from training data"` —
   mathematical forbid on novel synthesis.
2. `STRATEGIES` tuple in `src/opl_cancer/orchestrator/generation.py:24-29`
   lists only 4 strategies — none pointed at synergy / undrugged-target /
   pipeline-emergent.
3. `prompts/pi/proactive_push.md:32` (v1.2.0) says `"Never push speculative
   claims proactively"` — Sid is **forbidden** from surfacing `[S]`
   hypotheses to the patient.
4. `prompts/delivery/patient_brief.{html,md}.j2` has no dedicated section
   for `[S]` candidates — even if surfaced, they get buried alongside `[E]`
   options.

Plus roster gaps: no medicinal chemist (drug design for undrugged targets),
no KG-synergy reasoner. PrimeKG / Open Targets / DepMap synthetic-lethal
data are not consumed by Wave 2.

## Decision

Ship a paradigm shift in **5 seams** (this branch `iter/v2-paradigm`):

1. **Extend `STRATEGIES`** from 4 → 6: add `target_synergy_emergent` +
   `undrugged_target_design`. Pydantic Literal `GenerationStrategy`
   extended in lockstep.
2. **Rewrite `prompts/tasks/hypothesis_generation.md`**: lift `"Do NOT
   synthesize from training data"` rule for strategies 5+6 (where the
   point is to propose what training data cannot have seen); keep rule
   for strategies 1-4; require new `testability_path` field on all `[S]`
   hypotheses produced by strategies 5+6.
3. **Flip `prompts/pi/proactive_push.md`**: speculative claims ARE allowed
   proactive push if `testability_path` non-empty + rendered in dedicated
   `surface_section: world_unknown_candidates`.
4. **Add `world_unknown_candidates` section** to `patient_brief.html.j2` +
   `patient_brief.md.j2` with explicit `未发表 / 未验证 / research
   direction` framing, placed prominently above Summary.
5. **Add 2 new experts**: Maya (KG-synergy reasoner) + Julius (in-silico
   medicinal chemist). Stubs in `src/opl_cancer/experts/` + personas at
   `prompts/experts/{maya,julius}/persona.md` + roster entries. PrimeKG
   integrator stub at `src/opl_cancer/integrators/primekg.py` (live HTTP
   client deferred to follow-up).

## Out of scope (this branch — tracked in `references/v2/ROADMAP.md`)

| Topic | Follow-up branch | Follow-up ADR |
|---|---|---|
| Wave 3 hard gate (Henry L1 BLOCK on skipped Wave 3) | `iter/v2-followup-wave3-gate` | ADR-0011 |
| Wave 3 → Wave 2 feedback loop | `iter/v2-followup-feedback-loop` | ADR-0012 |
| Live PrimeKG client (replaces stub) | `iter/v2-followup-primekg` | ADR-0013 |
| Skill registry + agent adapter | `iter/v2-followup-skill-registry` | ADR-0014 |
| K-Dense-AI bridge adapter (138 skills) | `iter/v2-followup-kdense-bridge` | ADR-0015 |
| Julius live wiring (ESMFold+DiffDock+RDKit on Modal GPU) | `iter/v2-followup-julius-live` | ADR-0016 |
| Sid cross-run episodic log + wishlist tracker | `iter/v2-followup-cross-run-memory` | ADR-0017 |
| Cross-patient twin matching + federated meta | `iter/v2-followup-cross-patient` | ADR-0018 |
| Novelty benchmark dim in SBT_Benchmark | `iter/v2-followup-novelty-benchmark` | ADR-0019 |

Each follow-up branch requires its own ADR + ≥2-patient ≥2-cancer-type E2E
validation per `memory:feedback_multi_case_validation`.

## Consequences

**Positive:**
- Wave 2 will produce `[S]` candidates that ARE the differentiator vs MTB.
- Patient brief explicitly shows what's new vs what's known.
- Sid no longer hides speculative material — it's surfaced in a dedicated
  section with explicit "research direction, not recommendation" framing.
- Roster now has structural capacity for KG-synergy + drug-design questions.

**Negative:**
- Novelty inflation risk — without Wave 3 hard gate (follow-up branch),
  Wave 2 could over-produce `[S]`. Mitigation: `testability_path` is
  mandatory; Henry L3 risk-card unchanged; renderer explicitly frames as
  research direction.
- Maya / Julius are LLM-shell only in this branch (no live KG / docking).
  This is honest — they raise `NotImplementedError` on live integrator
  calls rather than silently returning empty (`memory:feedback_no_offline_only`).

**Compatibility:**
- All existing 18 experts untouched.
- Wave 1 / 3 / 4 / 5 runners untouched.
- Henry, tournament Elo math, dispatch untouched.
- Existing renderer tests pass — new section absent when
  `world_unknown_candidates` undefined / empty.
- 6 existing roster-cardinality tests updated 18 → 20.

## Verification

`scripts/verify_v2_e2e.py` checks ADR-0010 success criteria on a run dir:
- Wave 2 output contains ≥1 hypothesis with
  `generation_strategy: target_synergy_emergent`.
- Wave 2 output contains ≥1 hypothesis with
  `generation_strategy: undrugged_target_design`.
- Wave 2 output contains ≥2 `[S]`-with-testability hypotheses.
- `patient_brief.html` contains `World-Unknown` section with research-
  direction framing.

E2E validation matrix at `references/v2/E2E-VALIDATION-MATRIX.md` covers
≥2 patients ≥2 cancer types.
