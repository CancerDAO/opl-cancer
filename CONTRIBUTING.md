# Contributing to OPL for Cancer

This is an Apache-2.0 open-source project. **Patient safety is the highest priority.** PRs that compromise it get bounced even if every test goes green.

---

## Quick start

```bash
git clone https://github.com/CancerDAO/opl-cancer
cd opl-cancer
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev,bio]
pytest tests/ -q -m "not live"          # 1693 passing as of v2.5.1
```

Optional — for the bio integrators (KM survival, COSMIC signatures, etc.):

```bash
pip install -e .[bio]
```

Optional — for live integrator tests (require API keys via `.env`):

```bash
pytest tests/ -q -m "live"              # requires .env populated
```

---

## TDD workflow

OPL is TDD-first. Every behaviour change ships in this order:

1. Write the failing test
2. Run it; confirm it fails for the right reason
3. Implement the minimum code to make it pass
4. Run it; confirm it passes
5. Run the broader surface (`pytest tests/<your_dir>/ -q`)
6. Commit

For each BLOCKER-grade fix include a **before/after repro pair** in the commit message — show the failure mode at HEAD~1 and the passing run at HEAD.

Golden-set tests live under `tests/test_golden_set/` (and `validators/golden_set/` for legacy fixtures). They are part of the broader `pytest tests/ -q -m "not live"` suite — every PR keeps the golden_set green.

---

## Branch + commit conventions

* Branch from `main`. Name as `feat/<short-name>` / `fix/<short-name>` / `release/v<x.y.z>-<short-name>` / `docs/<short-name>`.
* One logical change per commit; one commit per BLOCKER for release branches.
* Commit messages: `<type>(<scope>): <summary>` (e.g. `fix(v2.5.1 B2): wire route_intake into cli.py plan`).
* Never `git commit --no-verify`. Never skip hooks. Never `git push --force` on `main`.
* For release branches: tag after merge (`git tag v<x.y.z>` + `git push origin v<x.y.z>`).

---

## ADR process

Architectural Decision Records live under [`docs/adr/`](docs/adr/). Open one for any decision that:

* Changes a public API
* Adds or removes a wave / expert / integrator
* Changes the founder-mode safety floor (drug-class redaction, banner stamps, refusal contracts)
* Trades off performance vs honesty
* Touches the Henry audit gates (G1-G33)

Template: copy the latest existing ADR (e.g. [`docs/adr/0025-compositional-paradigm.md`](docs/adr/0025-compositional-paradigm.md)) and follow the same structure (Context / Decision / Consequences / References).

Bigger architectural shifts (paradigm-level) get an RFC under [`docs/rfc/`](docs/rfc/) first — see [`docs/rfc/0001-compositional-paradigm.md`](docs/rfc/0001-compositional-paradigm.md) as the canonical example.

---

## Milestone discipline

OPL is organised around the v2.5 RFC's 6-milestone plan (M1-M6). Each milestone:

1. Ships behind a feature flag where the migration is partial
2. Keeps backward-compat strict for at least one minor version
3. Closes with a release tag + a CHANGELOG entry
4. Publishes a milestone retrospective in [`docs/adr/`](docs/adr/) if the design changed during the milestone

If your PR depends on a not-yet-shipped milestone (e.g. M3 universal integrator adapter live wiring), feature-flag it and document the activation env var.

---

## The 4 mandatory discipline rules (from CLAUDE.md)

These are enforced by reviewers; PRs that break them get bounced.

### 1. No false completion

Every "done" claim ships **paths + line counts + wall-time + ≥ 3 sampling verifications**. Don't say "all green" when you ran 5 of 10 planned roadmap items — say "5 done, 5 deferred to <branch>". Don't say "tests pass" without giving the pytest line count + duration. Don't claim a fix without showing the before/after repro pair.

### 2. TDD — failing test first, always

Failing test → confirm fail → implement → confirm pass → commit. No retrofitting tests around implementation. No "tested manually". Every BLOCKER fix gets a NEW test that would have failed before the fix and now passes.

### 3. No mock-only paths to production

Medical integrators query **live APIs** (`memory:feedback_no_offline_only`). When the network is unavailable, integrators raise; they do not silently fall back to canned snapshots. LLM synthesis is never a substitute for evidence retrieval. New integrators must include both a live-mode test (marked `@pytest.mark.live`) and a transport-error test.

### 4. No model downgrade

Opus 4.7 stays the executor for any LLM work the runner spawns (`memory:feedback_no_model_downgrade`). Don't drop to Sonnet / Haiku for medical synthesis tasks to save cost — the trade-off is unacceptable for a patient-facing tool.

---

## Code style

* Python 3.11+
* `pydantic` v2 for all schemas
* `ruff` for linting; `mypy --strict` for typing
* File responsibility ≤ ~300 lines (split when growing)
* Docstrings: explicit pre/post-conditions for any function the wave runners call; cite the relevant ADR / RFC / `memory:*` rule

Run before committing:

```bash
ruff check src/ tests/
mypy --strict src/opl_cancer/
pytest tests/<your_dir>/ -q
```

---

## What NOT to commit

* Real patient data (`patients/` is gitignored; never paste real records into tests or docs)
* LLM API keys / secrets (`.env`, `secrets/` are gitignored)
* Brainstorm artifacts (`docs/superpowers/` is gitignored)
* `tmp_live_v2_e2e/` outputs from non-reference patients
* Large binary diffs (>500 KB; use Git LFS if you genuinely need it)

---

## Filing issues

Bugs / feature requests / docs improvements all welcome via GitHub issues. Use the templates under [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/):

* **Bug report** — for code defects
* **Feature request** — for new task packages / integrators / waves
* **Patient question** — for "how do I do X with OPL" — we route these to user docs improvements

Security-sensitive issues: see [SECURITY.md](SECURITY.md) — do not file these in public issues.

---

## Code of conduct

Be kind. We follow the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Full text: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
