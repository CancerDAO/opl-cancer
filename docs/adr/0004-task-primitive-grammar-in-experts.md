# ADR-0004: Task-Primitive Grammar Inside Each Expert

## Status
Accepted (P0, 2026-05-24)

## Context
The spec brainstorm iterated through two unsatisfying decompositions before
arriving at the current two-layer fractal:

1. **Flat human-role list.** A first pass modeled the system as 18 named
   experts (pathologist, geneticist, radiologist, …) talking to the patient.
   That works for patient UX but devolves into "一事一议" engineering: each
   expert is a bespoke script with no shared methodology, no shared retry
   strategy, no shared auditor hooks. Adding the 19th expert means writing
   another bespoke script. Reviewers cannot easily reuse code across experts.
2. **Pure task-primitive list.** A second pass modeled the system as a flat
   set of task primitives (search, summarize, rank, audit, integrate, …) with
   no expert identities. That works for engineering but breaks patient UX: the
   patient sees a stream of anonymous tasks rather than identifiable experts,
   loses any sense of "who said this and why I should trust them," and
   provenance becomes a faceless audit log instead of "Dr. Liu the pathologist
   said X based on slide Y."

Both decompositions are individually correct *for one audience* and broken for
the other. The patient mental model needs identities; the engineer mental
model needs primitives.

## Decision
Use a **two-layer fractal** that satisfies both audiences simultaneously:

- **OUTER layer (patient-facing).** 18 named Expert archetypes + PI Sid +
  Auditor Henry. The patient sees a coherent virtual research team with
  identities, domains, and personas. Provenance attributes each claim to a
  named expert. UX language is "Dr. X, the radiologist, examined your scan
  and noted Y."
- **INNER layer (engineer-facing).** Every Expert — regardless of which name
  it carries on the outside — internally runs the *same* 6-primitive grammar:
  **planner → executor → reviewer → auditor → integrator → feedback**. Adding
  a new Expert means instantiating the grammar with a new domain prompt set,
  not writing a new script.

The grammar is the contract. The names are the UX. Both are stable. Adding
the 19th Expert is an act of configuration (new prompt files + roster entry),
not engineering.

## Consequences
**Positive**: patient UX gains an identifiable, persona-driven research team
that supports trust and drill-down. Engineering gains a single reusable
methodology — retry logic, auditor hooks, reviewer pairing, and provenance
schema are all written once and shared across the 18 archetypes. Adding the
19th, 20th, 21st expert is cheap. Code review surface area is bounded.

**Negative**: the two layers can drift if not enforced. An Expert author may
be tempted to bypass the grammar ("my pathologist doesn't need a planner step,
it's obvious"). The Expert abstract base in `src/opl_cancer/experts/` enforces
the grammar with abstract methods, so bypass requires explicit override and
will be caught in code review. A second risk is "persona inflation" — 18
archetypes is already a lot; adding more must clear a roster review.

**Followups**: P1 will lock the 18-name roster in `experts/roster.yaml` and
require an ADR for any new addition. The 6-primitive grammar is locked in the
Expert ABC in `src/opl_cancer/experts/base.py` and is not negotiable per-expert.

## References
- Spec §2.2 (Expert archetypes)
- Spec §17.2 (Two-layer fractal decision record)
- ADR-0002 (Main-thread dispatch — constrains how the grammar fans out)
