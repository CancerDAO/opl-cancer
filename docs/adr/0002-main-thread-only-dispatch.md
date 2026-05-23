# ADR-0002: Main-Thread Only Dispatch (No Subagent Forking)

## Status
Accepted (P0, 2026-05-24)

## Context
Claude Code, OpenCode, Codex, and Cursor share a common runtime constraint that
many multi-agent system designs ignore: **a forked subagent cannot itself fork
further subagents**. This is enforced by the harness, not the model — recursive
fan-out is rejected before the LLM ever sees the prompt. Every multi-agent
design that treats experts as "agents that talk to each other and can spawn
sub-tasks" therefore breaks when ported onto Claude Code as a skill plugin.

OPL for Cancer's natural decomposition has 18 named Expert archetypes and a PI
(Sid), where each Expert internally runs a 6-primitive grammar (planner →
executor → reviewer → auditor → integrator → feedback). A naive port would
model each Expert as a subagent that further forks its six primitives as
sub-subagents. On Claude Code that design simply does not run.

This is not a theoretical concern: `CancerDAO/vmtb-skill` already hit the same
wall on 2026-04-22 and resolved it with the "main-thread orchestrator" pattern
recorded in that repo's ADR-2026-04-22. OPL for Cancer reuses that resolution
verbatim rather than rediscovering it.

## Decision
All subagent dispatch happens in the **main thread only**. The main thread is
the only place a subagent may be forked. Experts are *not* subagents; they are
**logical orchestration units** implemented as Python state machines that issue
LLM calls (and, when needed, request the main thread to dispatch a subagent for
heavy parallel work).

Concretely:
- The `Expert` abstract base in `src/opl_cancer/experts/` is a Python class,
  not a subagent prompt. Its `run()` method executes synchronously in the
  calling thread and may issue ordinary LLM API calls.
- The `Orchestrator` (Sid's coordination layer) runs in the main thread. When
  multiple Experts must run in parallel within a wave, the orchestrator
  dispatches **one** wave of subagents from the main thread — not nested.
- Wave boundaries are explicit. Inside a wave, Experts run concurrently (one
  subagent each, dispatched by the main thread). Between waves, control
  returns to the main thread for integration before the next dispatch.

## Consequences
**Positive**: the architecture is portable across all four harnesses
(Claude Code, Codex, OpenCode, Cursor); failures are predictable because the
dispatch topology is a flat tree, not a recursive one; debugging is simpler
because all subagent traffic is visible to the main thread.

**Negative**: the design cannot exploit "agents that recursively decompose
themselves." Decomposition must be planned by the orchestrator before
dispatch. Patterns from the multi-agent research literature that assume
recursive fan-out require translation.

**Followups**: the wave planner in `src/opl_cancer/orchestrator/` must
explicitly enumerate sub-tasks before dispatch; runtime asserts in
`src/opl_cancer/orchestrator/dispatch.py` should refuse to recurse beyond
depth 1.

## References
- Spec §6 (Dispatch model)
- `CancerDAO/vmtb-skill` ADR-2026-04-22 (origin of the pattern)
- `memory:project_vmtb_architecture`
