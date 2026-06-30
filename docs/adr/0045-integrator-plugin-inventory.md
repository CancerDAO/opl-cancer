# ADR-0045 — Integrator Plugin Inventory

## Status

Accepted.

## Context

ADR-0025 introduced `IntegratorABC` and Python entry points under
`opl_cancer.integrators`, but the registry was mostly a declaration surface.
Review notes called this out as decorative: external plugins could be declared,
yet the harness did not expose a stable way for agents, dashboards, or tests to
inspect what was actually available.

## Decision

`IntegratorRegistry` now exposes `describe()`, a machine-readable inventory of
entry-point integrators. The inventory reports:

- entry-point name
- load status and error, if any
- module and class
- declared `id` / `family`
- whether the class implements `IntegratorABC`

The same inventory is exposed through:

- `opl-cancer integrator-plugins --json`
- `opl_cancer.mcp.session_ops.integrator_plugins()`
- optional MCP tool `integrator_plugins`

This consumes the entry-point registry as a real harness surface without forcing
all legacy integrators to migrate at once.

## Consequences

Positive:

- Host agents can discover available live data sources without scraping docs.
- Bad external plugin entry points become visible as inventory rows instead of
  failing the whole discovery pass.
- MCP/dashboard tooling can show integrator availability alongside run state.

Negative:

- This is still an inventory, not dependency injection. Wave runners must be
  wired to instantiate discovered plugins in later iterations.

Follow-up:

- Add a factory method that instantiates entry-point integrators by name with
  cache/TTL configuration.
- Migrate the remaining in-tree integrators to declare entry points.
