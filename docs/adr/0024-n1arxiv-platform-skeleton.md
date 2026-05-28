# ADR-0024: N1Arxiv Platform Skeleton — cross-repo submission via PR

**Status**: Accepted (v2.4.0 ships this)
**Date**: 2026-05-28
**Supersedes**: none (extends ADR-0023)
**Superseded by**: none yet
**Authors**: zwbao (鲍志炜, CancerDAO founder)
**Spec**: `/Users/baozhiwei/docs/superpowers/specs/2026-05-28-opl-v2.1-to-v2.4-design.md` §6
**Cross-repo**: `CancerDAO/opl-cancer` + new `CancerDAO/n1arxiv`

---

## Context

v2.3 (ADR-0023) shipped Wave 6: a publication-grade manuscript
generator that emits a self-contained `.n1a` bundle. A bundle on disk
is a scholarly artifact, but it is not yet *published*. The 007-zhiqiang
session ended with a `.n1a.zip` in the patient's local directory and
no public surface to point at.

The original spec named four options for the publication surface:
N1Arxiv, iArxiv, CaseArxiv, PersonalArxiv. The name **N1Arxiv** was
chosen because the "N-of-1" study design has decades of standing in
medicine (single-subject trials, the N=1 trial concept in critical
care, etc.) — anchoring the platform name in that tradition signals
"rigorous single-subject science", not "individual blog".

The question for v2.4 was: how should the platform consume bundles?

Three options were considered:

1. **Backend service** — upload form, database, server-side validation.
   Rejected: requires hosting, auth, takedown workflow, and is opposite
   of the patient-controlled-data philosophy.
2. **Hugo static site + manual file copy** — author copies their bundle
   into the repo and opens a PR by hand. Rejected: too much manual
   ceremony for the patient; high error rate on the content stub.
3. **PR-based submission with a generator on the OPL side** — OPL
   produces the diff, the patient reviews it locally, opens a PR. CI
   validates schema + audit + consent. This is what shipped.

Option 3 keeps the patient as the sole decision authority (founder
mode), gives full transparency (the diff is reviewable before push),
and pushes all validation to the platform CI so the OPL side never has
to know n1arxiv's invariants except through the shared schema.

## Decision

### 1. Two repos, one canonical schema

`schemas/n1a_bundle.v0.1.schema.json` is **canonical in opl-cancer**.
`CancerDAO/n1arxiv` ships a **mirror** of the same file. Both copies
carry a header comment naming the canonical location + mirror
relationship. Drift is detected by `tests/test_integration/...` on the
opl side and by `tests/test_schema_v0_1.py` on the n1arxiv side; both
test files load their local copy and validate fixture bundles, so a
schema bug would surface in both repos' CI within the same release.

### 2. opl-cancer side: `opl wave6 --submit-to-n1arxiv`

A new flag on the existing `wave6` command (requires `--final`; draft
mode cannot submit because G29-G33 are not enforced in drafts). The
flag invokes `src/opl_cancer/delivery/n1arxiv_submitter.py` which:

1. Reads `manifest.json` from the just-built `.n1a.zip`
2. Derives a deterministic `paper_id` (`YYYY-MM-DD-<slug>`)
3. Builds a Hugo content stub from the manifest — never inlines the
   manuscript prose (the stub points to the bundle for the actual paper)
4. Drafts the PR body (Frances persona; sees `prompts/tasks/n1arxiv_pr_assembly.md`)
5. If `--n1arxiv-repo PATH` is provided, byte-copies the bundle into
   `static/bundles/` and writes the stub into `content/papers/`
6. Returns the plan as JSON: `bundle_target`, `content_stub_target`,
   `pr_body`, `suggested_commands`

The submitter **never** calls `git push` or `gh pr create`. Founder-mode
invariant: the patient triggers publication, not the agent. The
`execute=True` path is a hard refusal at the API level (raises
`SubmitterError`), so future callers cannot quietly enable auto-PRs.

### 3. n1arxiv side: PR-based, no backend

The platform is a Hugo static site. Submission contract:

1. Author runs `opl wave6 --final --submit-to-n1arxiv --n1arxiv-repo PATH`
2. Author forks `CancerDAO/n1arxiv`, commits the staged files, opens PR
3. `validate_submission.yml` CI:
   - Unzips the bundle
   - Validates `manifest.json` against the schema
   - Re-computes SHA-256 for every listed file; refuses mismatch
   - Reads `HENRY_AUDIT.json`; refuses if any G29-G33 = FAIL
   - For `data_source: real_patient`: refuses if `ethics_declaration.md`
     lacks the canonical consent attestation string
4. Maintainer reviews + merges (human checkpoint, kept minimal)
5. `build_site.yml` runs Hugo → publishes to `gh-pages`

No DOI registration in v0.1 — deferred to N1Arxiv v0.2 once the
submission cadence and content-quality patterns are clearer.

### 4. Versioning, license, withdrawal

- `n1arxiv` starts at v0.1.0. opl-cancer ships v2.4.0 as the release
  that enables submission. The version numbers are independent.
- Dual license: CC-BY 4.0 for `content/` + `static/` (the papers
  themselves); MIT for `layouts/` + `scripts/` + `tests/` +
  `.github/` (the platform code).
- Withdrawal: the patient may request bundle removal at any time
  (`docs/n1_ethics.md`). The content stub is preserved with the body
  replaced by `[WITHDRAWN_BY_PATIENT]`; the bundle file is deleted.
  This honours the patient-decision-authority invariant without
  rewriting git history.

## Consequences

### Positive

- The patient stays in full control of when (or whether) their session
  becomes public. The OPL agent stops at the diff; the patient opens
  the PR.
- The platform has zero auth surface. There is no account, no login,
  no backend to compromise. The only state is the public git history.
- Schema drift is structurally hard to introduce: both repos' tests
  load the same schema file (canonical in opl-cancer, mirrored in
  n1arxiv) and would fail in lockstep.
- Adding a new field to `manifest.json` is a single PR pair:
  opl-cancer schema + n1arxiv schema, both validated by the same
  fixtures.

### Negative

- A patient who doesn't have a GitHub account cannot submit. This is
  acceptable for v0.1 (the typical OPL user is technical enough to
  run `opl wave6`). A future v0.2 may offer a one-click submission UI
  that wraps `gh` for the patient.
- Withdrawal preserves git history. A truly bit-erasing takedown
  would require `git filter-branch` and a force-push. For v0.1 the
  policy is "content stub kept, bundle deleted, history preserved" —
  this is honest about the limits of git-as-store while still meeting
  the patient's intent.
- Hugo is an extra build dependency for the n1arxiv repo. The
  schema + CI-reject tests do not require Hugo; the Hugo build test
  is gated on `which hugo` and skips when Hugo is not installed, so
  contributors without Hugo can still run unit tests.

### Deferred

- DOI registration (CrossRef / DataCite) — v0.2
- Patient one-click submission UI — v0.2
- Domain registration (`n1arxiv.org`) — staged in README + config.toml
  as a placeholder; v0.1 ships on `n1arxiv.cancerdao.org` via
  GitHub Pages
- Backend search / discovery beyond Hugo's built-in list page — v0.2
- A formal AI-authorship CRediT taxonomy beyond the existing
  `ai_authorship_disclosure.md` template — v0.2

## Three medical red lines (continuing ADR-0020 + ADR-0023 lineage)

1. The submitter never auto-PRs. The patient is the only entity that
   pushes to the public PR surface.
2. The submitter never edits the bundle. Banner, hashes, audit are
   already baked in by Wave 6 (ADR-0023); the submitter only stages
   a byte-exact copy.
3. The platform CI never silently relaxes a gate. Any G29-G33 FAIL
   refuses the PR. A change to G29-G33 itself requires an ADR-supersedes
   of ADR-0023 in the opl-cancer repo before n1arxiv's schema can drift.

## Compliance

| CLAUDE.md rule | How met |
|---|---|
| `feedback_no_false_completion` | Release report includes artifact paths + wall-time + sampling verifications across both repos |
| `feedback_top_down_trace_required` | Patient → `opl wave6 --submit-to-n1arxiv` → `n1arxiv_submitter.assemble_submission` → staged files in clone → reviewed by patient → manual `gh pr create` → CI |
| `feedback_branch_purpose_separation` | opl-cancer release branch `release/v2.4-n1arxiv-platform`; n1arxiv repo independent from day one |
| `feedback_docs_superpowers_private` | Both repos gitignore `docs/superpowers/` from day one |
| `feedback_branch_readme_sync` | README + CHANGELOG + SKILL.md + pyproject all bumped to v2.4.0 in the same commit |
