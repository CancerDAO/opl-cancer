---
name: Feature request
about: Propose a new task package / integrator / wave / gate / expert role
title: "[feat] <one-line summary>"
labels: enhancement
assignees: ''
---

## What problem does this solve

(Which patient situation is currently under-served?)

## Proposed solution

(One paragraph. What you'd add / change.)

## Type of change

- [ ] New task package (`prompts/tasks/<name>.md`)
- [ ] New integrator (`src/opl_cancer/integrators/<name>.py`)
- [ ] New method primitive (`prompts/methods/<name>.yaml`)
- [ ] New gate / gate family (`src/opl_cancer/validators/gates/`)
- [ ] New expert / role (`src/opl_cancer/experts/`)
- [ ] CLI / surface change
- [ ] Other

## Does this need an ADR?

A new ADR is required if the change touches a public API, adds/removes a
wave/expert/integrator, changes the founder-mode safety floor, or
trades off performance vs honesty. See [CONTRIBUTING.md](../../CONTRIBUTING.md#adr-process).

- [ ] Yes — I'll open an ADR before the PR
- [ ] No — minor scope
- [ ] Not sure (we'll discuss)

## Compatibility

Will this be backward-compatible? If not, what's the deprecation path?

## Test plan

What new tests will land alongside? (TDD-first — see CONTRIBUTING.md.)

## Acknowledgements

If this draws on external work, please credit it now (we'll add to
ATTRIBUTIONS.md on merge).
