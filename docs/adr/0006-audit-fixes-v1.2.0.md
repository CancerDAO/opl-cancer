# ADR 0006 — Audit fixes for v1.2.0

Date: 2026-05-24

## Status

Accepted. Follow-up to ADRs 0001-0005 + v1.1.0 release.

## Context

Post-v1.1.0 audit surfaced CRITICAL (patient-safety + legal) and IMPORTANT (legal-attribution + completeness) findings. This ADR documents the findings + the resolution decisions taken in v1.2.0.

## Decision

Address every CRITICAL (C1-C7) and IMPORTANT (I1-I9) finding in a single v1.2.0 audit-fix release before tagging. CRITICAL findings ship fully resolved; I5/I6 prompt scaffolding ships as framework stubs to be deepened in v1.3+. Detailed per-finding decisions follow.

## CRITICAL findings (all fixed in this release)

### C1 — Mark inspiration cited a real person who cannot be found

**Finding.** `README.md`, `roster.py`, `CHANGELOG.md` cited "Mark Stelfox" as the ICI endocrine irAE inspiration. No published top-1-3 figure with this name in the ICI irAE endocrine subspecialty could be confirmed. Naming a real person who is not actually the methodological lineage is both an attribution error and a legal exposure.

**Decision.** Replace with `Composite archetype (ASCO + ESMO ICI irAE consensus methodology)` — no single named figure. Mark's persona explicitly carries the "Not a real-person impersonation" disclaimer.

### C2 — Steve cited wrong real-person name

**Finding.** `README.md` + `roster.py` + `steve/persona.md` cited "Stephen Heber" — the correct name of the UCLA Center for Human Nutrition founder is **David Heber**.

**Decision.** Replace with `David Heber (UCLA Center for Human Nutrition founder)` across all surfaces (README, roster, persona, CHANGELOG, source docstring).

### C3 — SKILL.md + CLI status self-contradicted shipped state

**Finding.** `SKILL.md` still said "Status: P0 Skeleton. No experts/task packages/integrators implemented yet." `cli.py status` echoed "P0 Skeleton" and pointed to `docs/superpowers/plans/` (a path that must never be exposed per global memory rule). Yet README claimed v1.1.0 with 781 tests + 18/18 experts + Wave 1-4 runners — direct contradiction.

**Decision.**
- Rewrite `SKILL.md` to list shipped v1.2.0 capabilities (Sid, Henry, 18 experts, Wave 1-4 runners, 20+ integrators, provenance ledger, cross-patient isolation, per-task model routing).
- Tighten the `description:` for trigger-match accuracy (per audit finding I7).
- Rewrite `cli.py status` command to print real v1.x capability snapshot; drop `docs/superpowers/plans/` reference.

### C4 — Mark persona pinned to ASCO 2021 / ESMO 2022 (stale-dated)

**Finding.** Pinning to a specific edition that may be superseded by 2026 is unsafe — patient may receive outdated guidance.

**Decision.** Replace edition pins with runtime-verified consensus language: "the latest ASCO + ESMO ICI irAE consensus — Mark MUST verify edition at runtime via the PubMed integrator; PMIDs pinned from live retrieval, not training data." Applied in `prompts/experts/mark/persona.md` + `prompts/tasks/ici_endocrine_irae.md`.

### C5 — Kieren persona pinned to IDSA 2018 (stale-dated)

**Finding.** Same problem class as C4 — IDSA neutropenic-fever guideline edition changes; pinning is unsafe.

**Decision.** Replace with runtime-verified consensus language. Applied in `prompts/experts/kieren/persona.md` + `prompts/tasks/neutropenic_fever_management.md`.

### C6 — Task packages did not specify behaviour when live integrator returned empty

**Finding.** Tasks like `treatment_line_recommendation.md` instructed the model to use `pubmed_results` and `nccn_excerpts`, but provided no rule for what to do if those came back empty. Risk: LLM fabricates regimens from training data.

**Decision.** Append explicit empty-integrator rule to ALL 15 task packages that consume integrator outputs. If all relevant inputs are empty, the only legal output is `options: []` + `summary: "Live integrator returned no evidence … Refer to treating oncologist; do not fabricate."` + `claim_layer: "speculative"`.

### C7 — DISCLAIMER URLs pointed to wrong repo

**Finding.** `DISCLAIMER.md` referenced `github.com/CancerDAO/opl-for-cancer/issues` — the real repo is `opl-cancer-skill`.

**Decision.** Replace URLs.

## IMPORTANT findings (all fixed in this release)

### I1 — Identity attribution for 18 personas needed sharper framing

**Decision.** Append explicit `## Identity attribution (v1.2.0)` section to each persona — "You are modeled on the methodology of **<Real Person>** … You inherit the following distinctive methodological commitments … Legal: this is an archetype, not impersonation." Real-person mappings reviewed for 2026 accuracy (Vince now routes to Charles Sawyers as the active-2026 combination-and-resistance methodology lineage from DeVita; Ted now Anthony Zietman as the active 2026 lineage; Vincent DeVita †2024 noted; Mark + Frances are composite / lineage rather than living-person impersonation).

### I2 — Task package version pins (NCCN v6.2025, NSCL-15 etc.) replaced with runtime-verified language

**Decision.** Stripped hard-coded NCCN edition refs from all task packages.

### I3 — 10 personas missing founder-mode discipline section

**Decision.** Appended `## Founder-mode discipline (v1.2.0)` to dennis / frances / jen / kieren / mark / mary / riad / steve / ted / tyler.

### I4 — High-risk experts missing Mandatory disclosure (L4 boundary) section

**Decision.** Appended `## Mandatory disclosure (high-risk / L4 boundary)` to frances / dennis / vince / mary / ted / riad / jen / mark.

### I5 — PI (Sid) prompts missing

**Decision.** Created `prompts/pi/persona.md`, `prompts/pi/delivery.md`, `prompts/pi/drilldown.md`, `prompts/pi/proactive_push.md` as framework stubs (~30-50 lines each). Subsequent iterations will deepen.

### I6 — Auditor (Henry) prompts missing

**Decision.** Created `prompts/auditor/l1_mechanical_gates.md`, `l2_disagreement_summariser.md`, `l3_permission_gate.md`, `l4_rollback.md` as framework stubs. v1.3 will migrate the LLM-disagreement-summariser prompt from inline (in `validators/henry.py`) to file-loaded.

### I7 — SKILL.md description optimised for trigger-match accuracy

**Decision.** Already addressed in C3 (single SKILL.md rewrite).

### I8 — Skill-form (npx skills add) needs shell wrappers

**Decision.** Created `scripts/list_experts.sh`, `status.sh`, `init_patient.sh`, `acknowledge.sh`, `run_wave1.sh` — thin `python -m opl_cancer.cli ...` wrappers, executable.

### I9 — Rick trial_matching has ISRCTN delivery gap

**Decision.** Added `isrctn_results` to the input list with explicit gap note: "ISRCTN integrator not yet wired in v1.x — empty list means UK/EU trials not searched yet."

## Deferred to subsequent iterations

- I5/I6 prompts are framework stubs (per budget) — content depth, dialogue patterns, locale tuning to follow.
- Full migration of inline L2 prompt from `validators/henry.py` to file-load (planned v1.3).
- ISRCTN integrator wiring (planned v1.3+).

## Verification

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/ -q` — run during release.
- Manual smoke: `opl-cancer status` no longer says "P0 Skeleton"; `opl-cancer list-experts` shows updated inspirations.
- `grep -r "Mark Stelfox\|Stephen Heber"` returns no hits in source tree.
- `grep -r "opl-for-cancer/issues"` returns no hits.

## Consequences

- v1.2.0 closes legal-attribution + patient-safety gaps without changing public API.
- Skill-form invocation now works via shell wrappers.
- All claim-generating task packages are guarded against empty-integrator fabrication.
