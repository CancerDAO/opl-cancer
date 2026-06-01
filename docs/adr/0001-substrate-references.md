# ADR-0001: Substrate References

## Status
Accepted (P0, 2026-05-24)

## Context
OPL for Cancer is not built from scratch. The design lifts patterns from a small
set of prior systems, both open-source AI-scientist substrates and CancerDAO
internal predecessors. Recording which substrates are referenced — and to what
extent — keeps attribution honest, lets reviewers find the original prior art,
and prevents "reinvent the wheel" creep when the spec already names a substrate
as canonical for a given primitive.

The substrate inventory the spec relies on:

- **open-coscientist** (Google DeepMind / external) — source of three patterns
  that v0 lifts directly: (a) Elo-based hypothesis ranking and tournament
  evaluation, (b) meta-critique loops between executor and reviewer, and (c)
  generation × evolution × ranking lift for iterative hypothesis refinement.
- **robin** (FutureHouse) — source of the PaperQA2-style evidence-grounded QA
  pattern, the EXPERIMENTAL_INSIGHTS extraction prompt family, and the Finch
  bioinformatics agent pattern referenced for the Bioinformatician archetype.
- **era** (Tencent) — referenced conceptually as a prior researcher-agent
  framework, but v0 does *not* lift code or prompts; the dependency is read-only
  inspiration for the multi-expert architecture.
- **ai-scientist-os-proto** (internal predecessor) — five conceptual archetypes
  (PI, Domain Expert, Reviewer, Critic, Integrator) that predate the named
  roster. The OS-proto archetypes survive as roles inside the 6-primitive
  grammar (planner / executor / reviewer / auditor / integrator / feedback).
- **A CancerDAO internal molecular-tumor-board predecessor branch** — the most
  direct predecessor. Roughly 60-70 % of v0's expert + tournament code derives
  from that branch, including the wave-based dispatch pattern (main-thread only,
  see ADR-0002) and the SQLite-backed integrator cache.
- **A CancerDAO internal engine repo** (separate from the plugin) — used as a
  reference for organize-side schemas (`profile.json`, `readiness.json`,
  `timeline.md`) but *not* taken as a runtime dependency; the upstream engine
  and the downstream plugin diverged into separate repos.

## Decision
The P0 README, SKILL.md, and CHANGELOG explicitly cite each substrate at the
point where it is lifted. No "silent borrowing" is permitted: if a class,
prompt, or schema field originated in one of the named substrates, the source
must be named in a comment header or commit message. The two open-source
substrates lifted in v0 (open-coscientist, robin) are subject to upstream
license compatibility review before P1 ship.

`era` and the internal engine repo are reference-only for v0. Any future code
lift from those two requires a follow-up ADR.

## Consequences
**Positive**: attribution is mechanical, contributors can find prior art
without spelunking through git history, and the project avoids accidental
license violations because the substrate list is short and curated up front.

**Negative**: the curated list is biased toward what the founder has read. Other
relevant substrates (autogen, langgraph-multiagent, etc.) are *not* enumerated
and may be silently reinvented. P1 backlog includes a substrate audit pass.

**Followups**: when P1 starts, run a license-compatibility check against
open-coscientist and robin upstream licenses; add any new substrate lift to
this ADR's inventory rather than starting a new ADR per substrate.

## References
- Spec §18.1-18.4 (substrate inventory and lift policy)
- See `CONTRIBUTING.md` for the substrate-attribution and provenance discipline.
