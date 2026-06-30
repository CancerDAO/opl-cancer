# ADR-0047: Release Golden Evaluation Harness

Date: 2026-06-30

## Status

Accepted.

## Context

OPL already carries a `validators/golden_set/` with synthetic patients, failure
mode fixtures, regression anchors, and boundary cases. Tests checked pieces of
this tree, but release automation lacked one stable command that answers:

- is the golden set present and parseable?
- does it still cover enough cancer types, failure modes, gates, anchors, and
  boundary cases?
- what exactly failed, in machine-readable form?

That gap matters because prompt, model, and architecture changes can pass unit
tests while silently narrowing the release regression surface.

## Decision

Add `opl_cancer.evaluation.release_golden` as a deterministic, no-network,
no-LLM release harness. It returns a JSON report with schema
`opl.release_golden_eval.v1` and per-check status records:

- `category`;
- `name`;
- `ok`;
- `severity`;
- `message`;
- `evidence`.

Expose the harness through:

- `opl-cancer release-eval --json`;
- optional `--out <path>` report writing;
- MCP `release_eval`.

The first version checks the current golden-set shape:

- at least four synthetic patients across at least four primary sites;
- each synthetic profile has matching `anon_` code, diagnosis, demographics,
  and non-empty treatment history;
- at least eight failure-mode fixtures across at least five gate codes;
- at least two regression anchors;
- at least three boundary cases.

## Consequences

Positive:

- Release automation gets one fail-closed command instead of scraping many
  tests or prose files.
- Hosts can inspect failures through JSON or MCP without parsing stdout.
- The golden-set coverage contract becomes explicit and versionable.

Tradeoffs:

- This harness validates fixture coverage and shape. It does not run LLM
  outputs or live integrators; those remain separate, opt-in evaluation layers.
- As new golden-set categories appear, this module needs corresponding checks.

