# ADR-0048: Deterministic Recovery Plan

Date: 2026-06-30

## Status

Accepted.

## Context

Long OPL runs fail in different ways: missing manifests, checkpointed pauses,
executor/report failures, delivery without attestation, or under-delivery. The
project already had structured events, checkpoints, `observe`, and `validate`,
but the operator still had to infer the next recovery step from several
surfaces.

That inference is exactly where drift happens in long sessions: the host may
continue from memory, skip the actual failing invariant, or rerun the wrong
phase.

## Decision

Add `opl_cancer.glue.recovery.build_recovery_plan()` and expose it through:

- `opl-cancer recovery-plan --json`;
- MCP `recovery_plan`.

The recovery plan is read-only. It consumes durable state:

- `observe` projection;
- `validate` problems;
- latest checkpoint;
- structured run events and latest error events.

It emits schema `opl.recovery_plan.v1` with:

- `status`: `blocked`, `needs_repair`, `ready_to_resume`, `needs_triage`,
  `needs_progress`, or `complete`;
- `checkpoint`;
- `event_summary`;
- `latest_error_events`;
- `validation`;
- `blockers`;
- `next_actions[]` with `code`, `label`, `reason`, and optional command.

Priority order is explicit:

1. missing run root blocks;
2. validation errors must be repaired before resume;
3. checkpoint resume comes before generic wave progress;
4. error events trigger triage;
5. delivered + attested runs need no recovery;
6. otherwise continue the next outstanding wave or observe state.

## Consequences

Positive:

- Recovery is now a deterministic artifact rather than chat-memory inference.
- MCP hosts can resume long runs without scraping CLI prose.
- Checkpoint semantics become operational: they feed `next_actions`, not just a
  stored note.

Tradeoffs:

- The plan proposes actions but does not execute them. This is intentional:
  automatic repair could mutate clinical artifacts or hide state corruption.
- The command strings are operator hints. Gates and state-checks remain the
  source of truth.

