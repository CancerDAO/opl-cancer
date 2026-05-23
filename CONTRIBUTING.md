# Contributing to OPL for Cancer

This is an Apache-2.0 open-source project. Patient safety is the highest priority.

## Quick start

```bash
git clone https://github.com/CancerDAO/opl-cancer-skill
cd opl-cancer-skill
pip install -e .[dev]
pytest tests/
```

## Before submitting a PR

1. **Golden set must pass.** `pytest validators/golden_set/` — every test green.
2. **Add CHANGELOG.md entry.** Brief note in `## [Unreleased]` section.
3. **For prompt / rule / model changes:** include a `historical-impact-statement` in the PR description (does this affect reproducibility of past patient briefs?).
4. **Tests required.** TDD style: failing test → minimal code → green → commit.
5. **Sign CONTRIBUTOR_AGREEMENT** on first PR (see `docs/governance/`).

## Code style

- Python 3.11+
- Pydantic v2 for all schemas
- `ruff` for linting; `mypy --strict` for typing
- File responsibility ≤ ~300 lines (split when growing)

## What NOT to commit

- Real patient data (`patients/` is gitignored)
- LLM API keys / secrets (`.env`, `secrets/`)
- Brainstorm artifacts (`docs/superpowers/` is gitignored)

## Filing issues

Bugs / feature requests / docs improvements all welcome via GitHub issues.

Patient feedback channels are separate — see `docs/governance/`.
