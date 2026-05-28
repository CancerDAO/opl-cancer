## Summary

(1-3 sentences. What does this PR do and *why*.)

## Type of change

- [ ] Bug fix
- [ ] New feature (task package / integrator / method primitive / gate / role)
- [ ] Refactor (no behaviour change)
- [ ] Docs
- [ ] Release / version bump

## Test plan

- [ ] Added a failing test FIRST, confirmed it failed for the right reason, then implemented
- [ ] Full `pytest tests/ -q -m "not live"` passes
- [ ] For BLOCKER-grade fixes: included before/after repro pair in commit message
- [ ] For new integrators: live-mode test (`@pytest.mark.live`) + transport-error test
- [ ] CHANGELOG.md updated with entry under `## [Unreleased]`

## CLAUDE.md discipline self-check

The 4 mandatory rules — please confirm each:

- [ ] **No false completion.** Every "done" claim in the PR description ships paths + line counts + wall-time + ≥ 3 sampling verifications.
- [ ] **TDD.** Test-first, not retrofit.
- [ ] **No mock-only path to production.** Medical integrators query live APIs; LLM synthesis is not a substitute for evidence retrieval.
- [ ] **No model downgrade.** Opus 4.7 stays the executor for LLM work the runner spawns.

## ADR / RFC

- [ ] This PR does NOT need an ADR
- [ ] This PR includes / references an ADR: `docs/adr/<NNNN>-<name>.md`
- [ ] This PR is part of an RFC: `docs/rfc/<NNNN>-<name>.md`

## Patient-safety self-check

- [ ] No real patient data added (tests use Riaz reference / synthetic fixtures)
- [ ] No keys / secrets committed
- [ ] If touching the founder-mode safety floor (drug-class redaction, banner stamps, refusal contracts), reviewers from @CancerDAO-maintainers requested

## Linked issues

Closes #
Relates to #
