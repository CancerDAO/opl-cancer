# OPL for Cancer v1.5 — PRD (iter/v1.5)

**Branch:** `iter/v1.5`
**Drives from:** [`RETROSPECTIVE_v1.4_PT-EXAMPLE-A_run-20260525.md`](RETROSPECTIVE_v1.4_PT-EXAMPLE-A_run-20260525.md) + [`ANTI_PATTERNS_v1.4.md`](ANTI_PATTERNS_v1.4.md)
**Authorization:** user `/goal` 2026-05-25 (autonomous fix + test + commit + sync)

---

## 0. What v1.5 fixes (one paragraph)

v1.4's PT-EXAMPLE-A run produced a real consultation package only after the human caught a silent Wave-3 skip. Four root causes: (1) Wave 3 was declared optional+Docker-gated when it's actually critical-path retrieval not compute, (2) Henry IRB-substitute's format-gates pass "explicit deferral" as compliant, (3) GEPIA3 — the highest-impact tool of the recovery run — is invisible to the planner because the skill doesn't know it exists, (4) `patient_brief` is mislabeled and is in fact clinician-grade. v1.5 closes all four root causes and 4 related P0 items, plus 5 P1 hardenings, with explicit P2 deferrals to v1.6.

---

## 1. Scope (canonical — do not self-cap)

### P0 (must ship in v1.5)
| ID | Title | Touches |
|---|---|---|
| P0-1 | Wave 3 native-Python fallback (cBioPortal REST + scipy + PythonMeta + GEPIA3) | `glue/wave3_runner.py`, `compute/runner.py` |
| P0-2 | GEPIA3 integrator + prompt + planner hint | `integrators/gepia3.py`, `prompts/tasks/gepia3_query.md`, planner |
| P0-3 | G13 reviewer-distinct preflight hard-fail (no key → abort, not warn) | `cli.py:115` |
| P0-4 | Split `patient_plain_brief` (2nd-person zh, ≤2 pp) from `pi_delivery` (clinician) | `prompts/delivery/`, planner |
| P0-5 | Henry epistemic gates G19 (deferred-evidence BLOCK) + G20 (evidence-strength→Elo demotion + self-verify own G17 render) | `prompts/experts/henry/`, `validators/gates/` |
| P0-6 | Planner multi-comorbid L4+ default auto-include Mark/Mary/Frances/Riad/Dennis/Heddy | `prompts/pi/planner.md`, plan code |
| P0-7 | Subagent file-write fallback template (Write tool → Bash heredoc backup) | Wave-1 prompt template |
| P0-8 | Wave 3 non-skippable: remove silent skip; preflight aborts loud or auto-fallbacks | `glue/wave3_runner.py`, preflight |

### P1 (should ship in v1.5)
| ID | Title | Touches |
|---|---|---|
| P1-1 | G7 imperative-voice enforcement upstream (persona prompt PREFIX + forbidden-word list + 3-5 paired rewrites) | `prompts/experts/*/persona.md` (canonical wrapper) |
| P1-2 | Persona min-N retrieval contract (≥5 PMIDs per Tier-A claim or `[BACKGROUND-UNSOURCED]`) | persona prompts |
| P1-3 | Patient-anchor checklist (5 boxes; ≥4 must pass) | persona prompts |
| P1-4 | Shared stop-rule table (eGFR/LVEF/ALB/active-irAE thresholds) pinned to clinical personas | persona prompts |
| P1-5 | Privacy-scrub gate (regex CN phone / email / national ID / hospital MRN → REDACT) | report writer |
| P1-6 | CN-source mandate when patient is in 中国大陆 (CNKI/万方/中华医学会 consensus docs) | persona prompts |
| P1-7 | Source-traceability footer (PMIDs cited / verified-date / institutional sources / estimate-confidence) | persona prompts |
| P1-8 | W3-born hypothesis → W2.5 mini-Elo (≥2 rounds) before delivery placement | `glue/wave3_runner.py` → wave2 hook |
| P1-9 | Beijing-specific centers data (协和/301/北肿/朝阳/中日友好 + cardio-onc names) | `references/centers/` |

### P2 (best-effort in v1.5; document deferrals)
| ID | Title | Status |
|---|---|---|
| P2-1 | CHANGELOG / README auto-sync hook | implement basic; full CI hook in v1.6 |
| P2-2 | SKILL.md ↔ code reconciliation CI step | implement spec; CI in v1.6 |
| P2-3 | Plan-narration enforcement (assistant must narrate planner overrides) | implement as SKILL.md rule; runtime enforcement v1.6 |
| P2-4 | Robin reflector → live feedback loop (re-pair Elo when reflection surfaces new info) | defer to v1.6 (design risk) |
| P2-5 | Cost-currency stamp + sample-N disclosure for Frances/Dennis | persona prompt addition |
| P2-6 | Frances/Dennis explicit "verify access pathway currently operational" task | task prompt addition |

---

## 2. Branch + commit strategy

- All work on `iter/v1.5` branch in 坚果云 git repo
- One logical commit per task group (P0-A=PRD/docs, P0-1+P0-8, P0-2, P0-3, P0-4, P0-5, P0-6, P0-7, P1-A, P1-B, P2-quick, final)
- Conventional commit message format: `feat(v1.5): [task ID] - one-line summary`
- No `--amend`, no `--no-verify`. New commits for each fix per user CLAUDE.md.
- Do NOT push to GitHub (`origin`) unless user explicitly requests; user said "同步到本地" not "push to remote".

## 3. Testing requirements

- Every P0/P1 implementation must include either: (a) a new pytest in `tests/` or (b) extension of existing `test_p*_acceptance.py`.
- Test harness: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/<file>` (workaround for global dash conflict).
- Smoke test gate before final commit: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/ -x --tb=short` must pass.
- Live LLM tests (`tests/test_integration/test_minimax_live*`) are not required but should not regress.

## 4. Sync strategy (the "同步到本地" step)

- After all commits land on `iter/v1.5`, rsync `坚果云 repo → ~/.claude/skills/opl-cancer/`
- rsync excludes: `.git/`, `__pycache__/`, `*.pyc`, `.DS_Store`, `.pytest_cache/`
- Verify with `diff -r` post-rsync.

## 5. Out of scope for v1.5

- Multi-patient batch mode
- Patient-data-vault integration (`firefly-vault` / `cancer-buddy-vault`)
- Full agentic re-plan flow with user confirmation
- Quarterly retro template scaffolding
- Refactor of `LLMBackedExpert` to deprecate the Anthropic-only path

## 6. Acceptance criteria (must all pass before user takes over)

1. `iter/v1.5` branch exists with ≥10 commits matching the scope table
2. All P0 items have code + test in repo (verified by `git log iter/v1.5 --oneline | grep -E 'P0-[1-8]'`)
3. Full pytest under `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` returns green
4. `~/.claude/skills/opl-cancer/` byte-matches 坚果云 repo content post-rsync (`diff -r` empty modulo `.git/__pycache__`)
5. SKILL.md mentions: Wave 3 native fallback, GEPIA3, G13 hard-fail, patient_plain_brief, Henry G19/G20, planner multi-comorbid default, subagent file-write fallback
6. CHANGELOG.md has a complete v1.5 entry with P0/P1 done + P2 deferred
7. No emoji introduced (per user style preference)
8. No `docs/superpowers/` introduced (per `feedback_docs_superpowers_private`)

## 7. Risk register

| Risk | Mitigation |
|---|---|
| GEPIA3 endpoint changes / blocks scraper | Add retry + 12s rate-limit + html-parser fallback; document expected failure mode |
| Hard-fail G13 disrupts users without MiniMax key | Provide clear remediation message + `.env.example` with key acquisition link |
| Persona prompt prefix changes regress G7 detector | Run G7 detector on pre/post sample reports to verify backwards compat |
| W3→W2.5 mini-Elo adds latency | Cap at 2 rounds × max 4 matches; reuse cached Elo from W2 where possible |
| Beijing centers data may be stale | Stamp `as_of_date` per record; design for periodic refresh in v1.6 |
| Test infra dash conflict on user's machine | Document `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` in README test section |

---

## 8. Sign-off

This PRD is the contract for v1.5. Any item moved out of v1.5 must be explicitly relisted in CHANGELOG's "deferred" section with a one-line reason. Items not in this PRD are not part of v1.5 scope.

— End of PRD —
