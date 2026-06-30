# ADR-0046: Task Capability Registry

Date: 2026-06-30

## Status

Accepted.

## Context

OPL has two overlapping concepts:

- expert personas: the patient-facing mental model and dispatch identity;
- task packages: the deterministic engineering capability contracts under
  `prompts/tasks/*.md`.

The codebase already had both concepts, but ownership was split across static
expert class `portfolio` tuples, the runtime `ROSTER` profile portfolios, and
the prompt files themselves. That made drift easy: a class could advertise a
capability that had no prompt contract, while a prompt could exist without a
visible owner.

This is especially risky for the v2.0 Maya/Julius capabilities because their
value is not their persona text; it is the reproducible capability chain:
knowledge-graph synergy, synthetic-lethal partner query, structure acquisition,
virtual screening, chemical filtering, and test design.

## Decision

Add `opl_cancer.plan.task_capabilities` as the machine-readable registry for
task capabilities. It indexes:

- every prompt file under `prompts/tasks/`;
- every class-level expert `portfolio`;
- every runtime `ROSTER[*].task_package_portfolio`.

The registry exposes:

- `build_task_capability_registry()`;
- `owners_for_task()`;
- `validate_task_capability_registry()`;
- `registry_as_list()`.

Add `opl-cancer task-capabilities --json` and the optional MCP
`task_capabilities` tool so hosts can inspect the capability surface without
parsing expert modules or prompt directories by hand.

As part of the registry introduction, add the missing prompt contracts for the
class-level Maya/Julius/Tyler capability names:

- `target_synergy_emergent`;
- `synthetic_lethal_partner_query`;
- `drug_drug_synergy_kg_query`;
- `pathway_crosstalk_reasoning`;
- `undrugged_target_design`;
- `structure_source_acquisition`;
- `virtual_screen_design`;
- `chemical_filter_application`;
- `in_silico_experiment_design`.

## Consequences

Positive:

- Expert persona and capability contracts are now separately inspectable.
- A host can ask "what can OPL do?" through CLI or MCP without relying on
  prose documentation.
- Static class portfolios and runtime roster portfolios are checked against the
  same prompt inventory.
- Future capability additions now have one regression target: no owned
  capability may lack a prompt contract.

Tradeoffs:

- The task prompt count snapshot increases from 69 to 78.
- The registry still reports unowned prompt files. That is intentional: some
  prompts are PI, auditor, reviewer, or delivery tasks rather than named-expert
  portfolio entries.

