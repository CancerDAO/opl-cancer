# ADR-0044 — Claim-Level Evidence Graph

## Status

Accepted.

## Context

OPL already requires patient-facing claims to carry evidence anchors, risk-card
disclosure where needed, and mechanical gate verdicts. Those pieces existed as
fields inside structured claims, delivery artifacts, and gate output. That is
enough for blocking bad delivery, but weak for downstream inspection: a host
agent, dashboard, or reviewer has to reconstruct which source supports which
claim and which gate checked it.

The brief should remain a rendering, not the source of truth. The next layer is
a deterministic graph underneath the brief.

## Decision

Add `src/opl_cancer/delivery/claim_graph.py` with schema
`opl.claim_evidence_graph.v1`.

The graph normalizes:

- claim nodes from structured claim objects
- evidence-source nodes from `claim.evidence[]`
- gate verdict nodes from `GateResult` objects or dictionaries
- risk-card nodes from `RiskDisclosureCard` objects or dictionaries
- typed edges: `supported_by`, `checked`, `discloses_risk_for`

`opl-cancer claim-graph --claims-json <file>` builds and validates the graph.
The validation is intentionally mechanical: it checks referential integrity and
flags claims with no evidence-source edge. It does not decide whether a source is
clinically adequate; that remains the job of the existing gates and Henry audit.

## Consequences

Positive:

- Review tools can inspect claim/source/gate/card relationships without parsing
  brief markdown.
- Future renderers can be generated from the graph instead of hand-assembled
  side files.
- Claim graph output gives MCP/dashboard clients a stable target for drill-down.

Negative:

- Initial graph generation is opt-in via CLI and tests; delivery integration is
  still a later wiring step.
- A graph can show that a claim has a source edge, but only gates prove whether
  the source is on-topic, sufficiently deep, current, and quote-matched.

Follow-up:

- Emit `claim_graph.json` during delivery finalization.
- Expose claim-graph build/validate operations through the MCP surface.
- Bind graph nodes to provenance journal record ids once delivery emits all
  claims as structured records.
