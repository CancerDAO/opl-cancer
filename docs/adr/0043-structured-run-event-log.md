# ADR-0043 — Structured Run Event Log

## Status

Accepted.

## Context

OPL runs are long, multi-wave, and host-agent driven. Before this ADR, durable
state was split across `plan.json`, wave artifacts, provenance, memory ledger,
delivery outputs, and plain progress messages. That was enough to validate a
finished run, but weak for live dashboards, checkpoint/resume, MCP tooling, and
failure recovery because tools had to infer phase transitions from stdout or
from loosely related artifacts.

Arbor's evented runtime is the right pattern to borrow, but OPL cannot make an
event bus the source of clinical truth. Clinical truth remains the artifacts,
provenance hashes, source anchors, and gates. The event layer must be a
machine-readable control log: helpful for orchestration, never a substitute for
evidence.

## Decision

Each trigger run now has an append-only `triggers/<run_id>/run_events.jsonl`.
Events use schema `opl.run_event.v1` and include:

- `event_type`, `phase`, `severity`, `source`, `at`
- an arbitrary JSON-object `payload`
- `event_hash` and short `event_id` derived from canonical JSON

The deterministic implementation lives in `src/opl_cancer/glue/run_events.py`.
`opl-cancer plan` writes `plan.manifest_written` after the run manifest is
minted. `opl-cancer events` can append or read events in JSON. `opl-cancer
observe` includes a compact event summary so the host re-grounds on the same
machine log it will later use for dashboards and MCP tools.

Each run also has one latest checkpoint at `triggers/<run_id>/run_checkpoint.json`
with schema `opl.run_checkpoint.v1`. A checkpoint records the orchestration
resume position (`phase`, `reason`, payload, and the event id that wrote it).
`opl-cancer checkpoint --write` updates that file and appends a
`checkpoint.saved` event; `opl-cancer checkpoint` reads it.

Boundary:

- `run_events.jsonl` records orchestration facts.
- `run_checkpoint.json` records the latest host-agent resume position.
- `provenance.jsonl` records evidence and claim traceability.
- Project Memory records cross-run learning.
- Delivery gates decide whether patient-facing artifacts can ship.

An event may say a phase started or a manifest was written; it never proves that
a claim is true or that a wave completed. Existing gates must continue to inspect
the underlying artifacts.

## Consequences

Positive:

- Long runs gain a stable machine-readable spine for dashboards, resume, and
  future MCP tools without parsing prose.
- Interrupted runs can persist a latest resume point without pretending that a
  wave or delivery artifact is complete.
- `observe` can show recent run activity even when no wave artifact has been
  completed yet.
- The event schema is small enough for external host agents to append their own
  operator notes or dispatch milestones.

Negative:

- There is one more per-run artifact to keep out of patient-facing evidence
  logic.
- Event completeness is initially incremental: older commands may not emit
  events until they are wired in later iterations.
- A checkpoint can become stale if the host writes it and then continues work;
  resume code must still call `observe` and inspect real artifacts before
  dispatching.

Follow-up:

- Emit events from wave state checks, delivery, attestation, gate failures, and
  integrator calls.
- Expose the same event operations through the future OPL MCP tool surface.
