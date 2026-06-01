# PRD: opl-cancer v2.9 audit-polish — close all remaining audit findings

**Status**: approved, in execution · **Branch**: `feat/v2.9-audit-polish` (forked from `feat/harness-split` @ 7f28f17) · **Date**: 2026-06-01

## §0 Scope

Close **every** finding from the 4-lens audit (skill-craft / engineering / medical
evidence-integrity / packaging) that the harness-split round did NOT already fix.
Already done (NOT repeated here): P0 safety trio (G36/offline/G35), G13 redefine,
evolution decouple, SKILL.md execution-model section, conftest/pytest-green.

**Canonical counts (code = source of truth, reconcile ALL docs to these):**
- **20 experts** — `src/opl_cancer/experts/roster.py` `ROSTER` = 20 entries. (Docs saying "18" are stale.)
- **42 registered gates** — `mechanical_gates.all_gate_classes()` = 42; numbering G1–G43 with **G38 reserved**. (Docs saying "20 gates" are stale.)
- **Integrators** — reconcile to the integrator registry truth (not the raw `.py` file count); SKILL says 29, references say 22 — one number, derived from the registry, everywhere.

**Hard constraints (public repo):**
- **No private/local skill names** in SKILL.md / README / PRD (no cancer-buddy / vmtb / beacon / firefly …). The description's `Do NOT` clause is generic ("not for one-shot record organization / a single report / emotional support — OPL is the full multi-wave research run").
- **No `memory:*` anchors** in any public file — replace with the public ADR/CONTRIBUTING anchor or drop.
- **No outward actions executed autonomously** — git tags / GitHub releases / repo rename / mirror creation / the evolution repo split are listed as MANUAL follow-ups, not done by the workflow.

## §1 P0 — correctness / discoverability-blocking

| ID | Finding | Fix | Files |
|---|---|---|---|
| P0-A | References a full major version behind body: "18 experts / 20 gates" vs canonical 20/42 → drill-down contradicts itself (worst for a medical tool) | Reconcile every count to canonical; add a "superseded/extended by v2 — see references/v2-paradigm.md" banner atop v1-era refs | `references/architecture.md`, `expert-roster.md`, `mechanical-gates.md`, `agent-portability.md`, `DISCLAIMER.md` |
| P0-B | No multi-platform plugin manifests → not installable via marketplace | Add `.claude-plugin/plugin.json` + `marketplace.json`, `.codex-plugin/`, `.cursor-plugin/` | new dirs |
| P0-C | Install slug inconsistent (`opl-cancer-skill` vs canonical remote `opl-cancer`; works only via GitHub rename-redirect) | Standardize all 6 doc refs to `CancerDAO/opl-cancer` | `README.md`, `README.zh-CN.md`, `SKILL.md`, `pyproject.toml` |
| P0-D | Evidence Contract scattered (SKILL.md:33/94/469), no single declarable block — the most safety-critical section for a medical skill | Add one `## Evidence Contract` (sources-of-record / never-fabricate / fallback) | `SKILL.md` |

## §2 P1 — should fix

| ID | Finding | Fix |
|---|---|---|
| P1-A | **SKILL.md should be a router** (505 lines, 8 distinct intents, 11-step script inlined over the CLI it says to prefer) | Convert to thin router (~120 lines: frontmatter + execution-model + operating-contract + when-to-use + workflow index); move the 11-step conversation script + interrupt protocol into `workflows/*.md` |
| P1-B | Description leaks *how* ("PI Sid + 20 expert archetypes + Henry") + no `Do NOT` clause | Trim to deliverable + triggers; add generic `Do NOT` (no private skill names) |
| P1-C | `references/v2/*` + `references/adr/*` nested two levels (REF_NESTED) | Flatten to `references/v2-*.md`; move the two stray ADRs into `docs/adr/` with the rest |
| P1-D | 6 reference docs >100 lines, no TOC (REF_NO_TOC) | Add a `## Contents` TOC to each |
| P1-E | DISCLAIMER.md contradicts core positioning ("physician must co-sign" vs "no physician sign-off") + stale "v1.x / 18 experts" | Resolve the contradiction in favour of the SKILL.md/README stance (patient = sole decision authority, no external sign-off); update scope to v2.x / 20 experts |
| P1-F | Reasoning gates G41/G43 are warn-only + G39–G43 SKIP on missing field, but SKILL.md:368 lists them as "enforced" without flagging | Annotate advisory vs blocking in the gate list |
| P1-G | `delivery_runner.py` vs `delivery_gate_runner.py` naming collision (maintenance trap) | Add a one-line module docstring to each stating which the CLI invokes; (rename deferred — low value, high churn) |
| P1-H | `gates_registry.yaml` header stale ("33 gates"), G34–G43 lack family/`migrated` | Update header + assign family/flags |
| P1-I | README EN/ZH drift: BibTeX `2.6.0`; ZH test count 1734 vs 1828; ZH missing Citation/Example sections | Sync BibTeX→current, ZH counts→current, bring ZH to structural parity |
| P1-J | CoC contact dangling (MAINTAINERS.md has no email); MAINTAINERS `TBD` rows | Point CoC at `opl-security@cancerdao.org` (or add a CoC contact); fill/clarify TBD rows |

## §3 P2 — polish

| ID | Finding | Fix |
|---|---|---|
| P2-A | `memory:*` private anchors leak in `models.yaml`, `.gitignore`, `CONTRIBUTING.md`, `SKILL.md`, several references | Replace with public ADR/CONTRIBUTING anchors or drop |
| P2-B | CHANGELOG 168KB, not Keep-a-Changelog | Add KaC + SemVer header; archive pre-v2 entries to `docs/CHANGELOG-archive.md`, keep recent majors inline |
| P2-C | Integrator count drift (29 vs 22) | Reconcile to registry truth everywhere |
| P2-D | SKILL.md numbering: two principles "6"; wrong ADR range ("0001-0006" → 0001-0026); deprecated `render` referenced in Step 10b; double `---` rule; 3 numbering systems (Step/Wave/stage) | Fix all in the router rewrite |
| P2-E | G34 forge-resistance / G37 regex author-detection are floors, not proofs | One-line honesty note in the gate list |

## §4 Out of scope (MANUAL follow-ups — not executed)

- Tag a clean `v2.9.0` GitHub release (outward).
- Rename repo or publish `opl-cancer-skill` mirror (outward) — handled here by standardizing docs to the canonical `opl-cancer` instead.
- Physically extract `orchestrator/* + evolution/*` to `opl-cancer-evolution` (outward; tracked in `EVOLUTION_EXTRACTION_TODO.md`).

## §5 Acceptance

- `python scripts/lint_skill.py` (skill-creator-pro): 0 errors; REF_NESTED + REF_NO_TOC + FM_DESC warnings cleared.
- Bare `PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q` stays green (no regressions).
- Counts identical across SKILL.md + all references + DISCLAIMER (20 experts / 42 gates / one integrator number).
- `grep -rn 'memory:' SKILL.md README* references/ models.yaml .gitignore CONTRIBUTING.md` → empty (public files).
- No private skill name in SKILL.md / README / this PRD.
- Router SKILL.md ≤ ~150 lines; every `workflows/*.md` link resolves; operating contract + Evidence Contract present in the router.
- Self-evidence: artifact paths + line counts + wall-time + ≥3 samples; honest pass/partial/deferred per item.
