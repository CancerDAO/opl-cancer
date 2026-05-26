# Changelog

## [2.1.0-rc1] — 2026-05-26 — Trace-Digest Evolution (borrowed from EvoMaster, NOT policy)

Branch: `iter/v2-followup-evolution` (off `iter/v2-paradigm`). Implements
ADR-0020 — a post-mortem proposal generator inspired by
`sjtu-sai-agents/EvoMaster`'s `--evolve` architecture, with 3 medical red
lines explicitly enforced. Never auto-applies to baseline.

### Added

- **`src/opl_cancer/evolution/`** package (7 new modules):
  - `models.py` — TraceDigest (bounded ~100KB), EvolutionProposal,
    InvariantImpact, EvolutionCandidates
  - `collector.py` — reads run dir → TraceDigest (read-only)
  - `scrubber.py` — PII/PHI strip BEFORE any LLM call (Chinese names + DOB
    + MRN + email + hospital + PT-code; preserves gene/drug/PMID/NCT)
  - `invariant_gate.py` — static analysis flags patches touching Henry
    L3/L4, G7, G13, persona_prefix, claim_layer, RetractionDB → auto-sets
    `requires_double_signoff: true`
  - `analyzer.py` — red-team system prompt (distinct from main medical
    agents), LLM call OR deterministic heuristic fallback (loud, marked
    `used_heuristic_fallback: true`)
  - `proposal_writer.py` — writes ONLY under `proposals/iter_<N>/`,
    refuses baseline paths at the filesystem level
  - `__init__.py` — package surface
- **`opl-cancer evolve <run_dir>`** CLI subcommand. No `--auto-apply` flag.
- **`scripts/verify_evolution_e2e.py`** — 7-check verifier mapped to
  ADR-0020 success criteria
- **ADR-0020** + `docs/superpowers/plans/2026-05-26-trace-digest-evolution.md`
- **56 new tests** under `tests/test_evolution/`
- ROADMAP updated with ADR-0020 entry

### 3 medical red lines enforced (NOT copied from EvoMaster)

1. **No `_write_prompt_overlays` auto-append.** Patches → unified diff in
   `proposals/iter_<N>/prompt_patches.diff`. Never to `*.evolved.txt`.
2. **No auto-respawn.** Evolution is post-mortem only. Next patient run
   uses baseline unchanged. After human review + Sid+Henry signoff,
   approved patches land via normal PR; future patients benefit.
3. **No skill `extra_roots` auto-extension.** Proposed skills sit in
   `proposals/iter_<N>/skill_additions/<slug>/SKILL.md.proposed` with
   mandatory `clinical_anchor` field. Skill registry merge will be the
   ADR-0014 follow-up branch.

### Beyond EvoMaster

- PII/PHI scrubber (closes EvoMaster's documented `runs/` privacy gap)
- Red-team analyzer prompt (distinct from medical agents)
- InvariantGate static analysis flagging safety surfaces
- ProposalWriter filesystem-level refusal of baseline paths
- Clinical-anchor mandatory for skill proposals (auto-reject otherwise)

### Compatibility

- All v2.0.0-rc1 tests pass (1221 + 56 new = **1277 passed**, 0 failures)
- No production flow touches evolution unless `opl-cancer evolve` invoked
- Output entirely under `<run_dir>/proposals/` (gitignored at project level)

---

## [2.0.0-rc1] — 2026-05-26 — Paradigm Shift: Surface World-Unknown Candidates

Branch: `iter/v2-paradigm`. Driven by the PT-EE62321353 run review which
revealed that Wave 2 produced 17 hypothesis cards but ALL were
recombinations of already-published regimens. The system was a polished
MTB, not an AI scientist team. ADR-0010 documents the forensic.

This release ships the 5-seam paradigm shift. Larger surface changes
(Wave 3 hard gate, Wave 3→Wave 2 feedback loop, live PrimeKG client,
skill registry, K-Dense bridge, Julius live wiring, cross-run memory) are
tracked as independent follow-up branches in `references/v2/ROADMAP.md`.

### Added

- **2 new generation strategies**: `target_synergy_emergent` +
  `undrugged_target_design`. Extends STRATEGIES tuple (4 → 6) +
  GenerationStrategy Literal + _STRATEGY_GUIDANCE dict.
- **2 new experts in roster (18 → 20)**:
  - **Maya** — Knowledge-Graph Synergy Reasoner. Owns
    `target_synergy_emergent` + `synthetic_lethal_partner_query` +
    `drug_drug_synergy_kg_query` + `pathway_crosstalk_reasoning`.
    Composite archetype: Marinka Zitnik (PrimeKG/Harvard) + Tijana
    Milenković (network medicine).
  - **Julius** — Medicinal Chemist (in silico). Owns
    `undrugged_target_design` + `structure_source_acquisition` +
    `virtual_screen_design` + `chemical_filter_application`. Composite
    archetype: ESMFold + DiffDock + RDKit + medchem filter lineage.
- **PrimeKG integrator stub** at `src/opl_cancer/integrators/primekg.py`.
  Live HTTP/SPARQL client deferred to `iter/v2-followup-primekg`. Stub
  raises `NotImplementedError` on live query (no silent fallback per
  `memory:feedback_no_offline_only`).
- **Patient brief "⚡ World-Unknown / Speculative Candidates" section** in
  both `prompts/delivery/patient_brief.html.j2` + `.md.j2`. Renders [S]
  hypotheses with strategy + Elo + `testability_path` + KG-edge anchors.
  Explicit 中英双语 framing: "研究方向，未发表 / 未验证 — research
  direction, not a treatment recommendation".
- **`testability_path` field mandatory** on all `[S]` hypotheses produced
  by strategies 5+6.
- **ADR-0010** + `references/v2/PARADIGM.md` + `references/v2/ROADMAP.md`.

### Changed

- **`prompts/pi/proactive_push.md`** flipped from v1.2.0: speculative
  claims ARE pushed when `testability_path` non-empty +
  `surface_section == world_unknown_candidates`. The v1.2.0 hard ban
  ("Never push speculative claims proactively") was the direct mechanism
  by which Sid hid world-unknown candidates from the patient.
- **`prompts/tasks/hypothesis_generation.md`** v1.2.0 "Do NOT synthesize
  from training data" rule LIFTED for strategies 5+6 (the strategies'
  whole purpose is to propose what training data cannot have seen). Rule
  retained for strategies 1-4.
- README: 18 → 20 experts; new v2 paradigm pointer section.
- 6 existing roster-cardinality tests updated 18 → 20 (with ADR-0010
  cross-reference inline).

### Unchanged

- Wave 1 / 3 / 4 / 5 runners.
- Henry validator (high-Level risk-card behavior intact).
- Tournament Elo math, debate.py judge prompt.
- All existing 18 experts.
- Existing 64 renderer tests pass — World-Unknown section absent when
  `world_unknown_candidates` undefined / empty.

### Tests

- New: tests/test_v2_generation_strategies.py (4 tests).
- New: tests/test_v2_prompts.py (6 tests).
- New: tests/test_v2_roster_maya_julius.py (6 tests).
- New: tests/test_v2_primekg_integrator.py (4 tests).
- New: tests/test_v2_renderer_world_unknown.py (5 tests).

### Verification

- `scripts/verify_v2_e2e.py` checks ADR-0010 success criteria on a run dir.
- E2E validation matrix at `references/v2/E2E-VALIDATION-MATRIX.md`
  (≥2 patients ≥2 cancer types per `memory:feedback_multi_case_validation`).

### Known follow-ups (see `references/v2/ROADMAP.md`)

- ADR-0011 Wave 3 hard gate (`iter/v2-followup-wave3-gate`).
- ADR-0012 Wave 3 → Wave 2 feedback loop (`iter/v2-followup-feedback-loop`).
- ADR-0013 live PrimeKG client (`iter/v2-followup-primekg`).
- ADR-0014 skill registry (`iter/v2-followup-skill-registry`).
- ADR-0015 K-Dense-AI bridge (`iter/v2-followup-kdense-bridge`).
- ADR-0016 Julius live wiring (`iter/v2-followup-julius-live`).
- ADR-0017 cross-run memory (`iter/v2-followup-cross-run-memory`).

---

## [1.5.7] — 2026-05-26 — Runtime honesty + prompt-first generalisation

Driven by the PT-EE62321353 run retrospective (2026-05-25) which surfaced a
class of issues my v1.5.6 code-review hardening didn't touch: **the v1.4
false-completion vector wasn't a code-quality bug, it was a CLI honesty
bug** — `wave1/wave2/wave3/wave4` returned `{"ok": true}` after `mkdir`,
so the orchestrator could declare "complete" while no expert / data /
validation had actually happened.

First-principles fix: **the CLI is a state reader, not a pretend-runner.**
A wave is `ok` only when the artifacts real execution leaves on disk are
actually present. Empty → exit non-zero + `requires_main_thread_dispatch:
true` + LLM-readable action so the orchestrator dispatches the real path.

Per `memory:feedback_default_prompt_over_script`, the planner / Henry /
patient-brief fixes are prompt-layer, not Python keyword tables — LLM
generalisation across patient varieties beats hardcoded if-elif trees.

**Runtime honesty (P0-CRIT)**

- `cli.py wave1/wave2/wave3/wave4` rewritten as artifact state-readers.
  Probes `triggers/<run_id>/tasks/w{1,4}_*/report.md`, `tournament/*.json`,
  and `data/**/*.{csv,json,ipynb,png}`. Empty run-root → exit 2 +
  `ok: false` + `requires_main_thread_dispatch: true` + an
  LLM-readable `action` field telling the orchestrator what to do.
- New `_WAVE_ARTIFACT_PROBES` table per wave: `out_dir_segment`,
  `expected_glob`, `min_count`, plain-language `story`.
- Closes run-retrospective issues #2 (CLI false-positive stubs) and #5
  (Wave 3 skip-able default).

**Prompt-first planner expansion (P0-C)**

- `SKILL.md` `Cancer-type-aware planner hints` adds two missing rows:
  - **mCRC KRAS G12C MSS, line 4+** — fills the v1.4 retrospective gap.
    Frances + Tyler (TROP2 GEPIA3) + Mark (MSS immune-cold) + Mary (CKD
    × cumulative tox) + Heddy (Q6-8wk imaging) + Hong (CN herb × EGFR-ab
    DDI) + Dennis (CodeBreaK / KRYSTAL / ACROBAT). Calls out the
    mandatory Wave 3 data: cBioPortal KRAS G12C+MSS cohort, TCGA +
    MSK-IMPACT survival projection, ctDNA Monte Carlo from baseline VAF.
  - **Late-line (≥ 4 prior lines) resistance — generic disease-agnostic
    row** — when a patient has exhausted ≥ 3 SoC lines, planner MUST add
    Frances + Heddy + Mary + Tyler + Mark + Riad on top of the
    disease-specific base. Founder-mode: line 4+ patients have weeks-to-
    months horizons.
- Prompt-layer expansion, not Python row table — generalises across the
  long tail of resistance scenarios via LLM judgment.

**Safety stack (P1)**

- `G7ImperativeDetectorGate(strict_imperative_isolation=True)` is now
  the **default**. Closes the v1.4 single-sentence spoof
  (`"You must take drug X PMID:12345 — risk of bleeding."`) at the gate
  layer rather than relying on Henry's review. Legacy permissive
  behaviour available via `strict_imperative_isolation=False`.
- `prompts/auditor/l1_mechanical_gates.md` — Henry now has explicit
  Rule 5: G7 violations are non-negotiable blocking; v1.4 case had 8 G7
  flags but delivery proceeded because Henry only flagged. Rule 5 also
  prescribes the rewrite contract: "必须" / "should" → options-language
  ("可以考虑" / "您可以").

**Patient delivery (P1)**

- `prompts/tasks/patient_plain_brief_rendering.md` — Section 0 (一句话
  答案) prepended, MANDATORY. Three sentences: top recommendation +
  rough effect size + rough risk + ONE next step, all in plain
  language. Reader who reads only Section 0 walks away with the answer.
- Section 0 includes an honest-failure clause: if Wave 3 did not
  produce data anchors, the brief says so plainly ("这次分析没有跑到底,
  所以我们没法给您一个有把握的答案") and jumps to Section 4 (questions
  for the doctor) instead of pretending Sections 2/3 carry weight they
  don't.

**Documentation**

- README.md — ASCII architecture diagram added (no Mermaid, per user
  preference for plain-text portability).
- New TECHNICAL_REPORT.md — full technical overview: first-principles
  design contract, 5-Wave lifecycle in detail, 27-gate safety stack
  breakdown, 30 integrators by F1-F10 family, provenance &
  reproducibility, honest state matrix (what's real vs P1 stub).

**Tests added**

- `tests/test_cli_honest_failure.py` — 5 cases pinning the wave
  state-reader contract: empty run-root → exit non-zero, real artifact
  → ok=true.
- `tests/test_validators/test_g7_imperative_detector.py` — strict-mode
  default test + explicit opt-out test.
- `tests/test_patient_plain_brief.py` — Section 0 conclusion-first
  contract + honest-failure clause checks.
- Adjusted `tests/test_cli.py::test_cli_status_runs` for version + gate
  count bump.

Full suite: 1134 passed, 0 failed (3 live MiniMax deselected — quota wall).

## [1.5.6] — 2026-05-25 — P0/P1 hardening from independent code-review verification

Fixes 7 issues surfaced by independent parallel-subagent verification of the
prior code review. Several review claims were validated (gates 24/27 registered,
NCBI calls missing identity, models.yaml silent fallback, expert stubs); several
were corrected against ground truth (rollback.py, trigger.py, IntegratorCache
SQLite, Wave-3 Docker, meta-critique structured injection — all already exist
and work as spec'd).

**P0 (compliance + prod-reliability)**

1. **`integrators/base.py`** — `models.yaml` parse/IO failure now raises
   `IntegratorError` instead of silently returning `{}` and falling back to
   class-default TTLs. Violates G11 / `memory:feedback_no_offline_only`.
2. **NCBI integrators (`pubmed`, `clinvar`, `geo`, `sra`)** — every call to
   `eutils.ncbi.nlm.nih.gov` now sends `tool=opl-cancer` + `email=` (overridable
   via `OPL_NCBI_EMAIL` / `OPL_NCBI_TOOL` env; `NCBI_API_KEY` raises the rate
   limit from 3 to 10 req/s). Without these, NCBI rate-limits and may IP-ban
   bursts. New shared helper: `integrators/_ncbi.py::with_ncbi_identity()`.
3. **`mechanical_gates.all_gate_classes()`** — registry now returns 27 gates
   (was 23). G21 (`quantitative_anchor`), G25 (`deferred_evidence_block`),
   G26 (`evidence_strength_ranking`), G27 (`privacy_scrub`) were defined and
   re-exported but never picked up by the orchestrator loop. README/SKILL.md
   advertised "27+ gates"; runtime ran 23. Now matches spec §7.
4. **Retry + exponential backoff** — new `integrators/_http.py::request_with_retry()`
   implements tenacity-based retry (4 attempts, 0.5→8s exp backoff) on transient
   failures: `httpx.TransportError`, `TimeoutException`, HTTP 429, HTTP 5xx.
   Respects `Retry-After` header on 429. Migrated to the 4 NCBI integrators
   (highest 429 risk under wave-concurrent dispatch); other 26 integrators
   can opt in via the same helper in a follow-up.

**P1 (spec-honesty + correctness)**

5. **`experts/_common.py`** — `plan()`, `audit()`, `feedback()` now emit
   `StubMethodWarning` so callers can detect they're P1 stubs (per spec §2.2
   the 6 task-primitive grammar is incomplete — these 3 return constants
   without LLM calls). Callers can `simplefilter("error", StubMethodWarning)`
   to fail-fast in tests that need real behaviour.
6. **G7 imperative-detector — `strict_imperative_isolation` mode** — closes
   the known single-sentence bypass ("You must take drug X PMID:12345 — risk
   of bleeding."). Strict mode (opt-in, default off for backwards-compat)
   requires the imperative clause itself to NOT carry a bare PMID/NCT/URL —
   evidence must live in a separate clause (split on commas, semicolons,
   em-dashes, parens) or be parenthesised. v1.6 will flip strict on by default.
7. **Robin lit-loop wired** — `experimental_insights_chain` written by each
   tournament round was previously never consumed. `tournament_loop.py` now
   passes round-N insights into round-N+1 `DebateJudge.judge_pair()` prompt
   (new `experimental_insights=...` arg). Tested via prompt capture.

**Test additions**: `test_integrators/test_base.py::test_malformed_models_yaml_hard_fails`,
`test_integrators/test_ncbi_identity.py` (5 cases), `test_integrators/test_http_retry.py`
(5 cases), `test_validators/test_gate_registry.py` (3 cases),
`test_experts/test_common.py::test_stub_methods_emit_warnings`,
`test_validators/test_g7_imperative_detector.py` (+4 strict-mode cases),
`test_orchestrator/test_tournament_loop.py::test_insights_injected_into_next_round_judge_prompt`.

Full suite: 1127 passed, 0 failed (3 live MiniMax tests deselected — quota wall).

## [1.5.5] — 2026-05-25 — Remove wrong safety email + fix post-rename DISCLAIMER URLs

`safety@cancerdao.org` was not a real intake — removed from `DISCLAIMER.md`, `CHANGELOG.md` (historical mention redacted to "GitHub Issues"), `docs/landing/founder_mode_against_cancer.md`, and the `test_p6_acceptance.py` assertion (which had an OR fallback to "issues", so coverage is preserved). The two `opl-cancer-skill` URLs in `DISCLAIMER.md` (still pointing to the pre-rename repo) are also updated to `opl-cancer`. Other `opl-cancer-skill` references across README/CONTRIBUTING/install.sh/etc. are left for a separate rename-sweep commit.

## [1.5.4] — 2026-05-25 — Inline delivery contract (Sid must speak conclusions in chat, not just point to files)

User feedback after testing v1.5.3: "执行完任务后, Sid 只让用户去看本地报告, 不在对话里总结结论。" The render step was writing files correctly, but the assistant was then closing the run with "报告已生成, 请查看 `delivery/patient_brief.html`" — file-handoff with zero substantive content surfaced inline. This is delivery theater, not delivery.

Fix:

1. **SKILL.md Step 10b (new)** — explicit 8-element inline-delivery contract: L3/L4 acks → goal echo → run metadata → top-3 conclusions **with content + provenance, not just titles** → disagreements → trade-offs → options → file pointers (LAST, not first). Documents the 4 forbidden patterns (file-handoff, titles-only, "see the .md", empty-stage-end + file list).
2. **prompts/pi/delivery.md Rule 5 (new)** — chat surface is the primary delivery medium; saved files are persistence + drill-down evidence; "报告已生成, 请查看 …" pattern → BLOCK.

No code changes — pure prompt contract update. The render pipeline already produces the right content in `pi_delivery.md`; the gap was that the orchestrator was not surfacing it inline.

## [1.5.3] — 2026-05-25 — Public-release prep (PII redaction + README rewrite + internal/public docs split)

Three changes preparing the repository for public flip on GitHub:

1. **PII redaction** — every canonical leak token from the v1.4 case
   study (real patient name, family phone, patient code, location)
   replaced with placeholders across tracked files. Git history rewritten
   via `git-filter-repo` so the leak tokens are unreachable in any
   commit diff or commit message. Verified zero hits across all files
   and full history.
2. **README rewrite** — old 211-line internal-feeling README replaced
   with cancer-buddy-skill-style public-facing README: centered header
   + badges, pain-point opening, 8-row problem/solution table, 5-step
   lifecycle (using plain-language stage labels from v1.5.1), 3 dialog
   scenarios, design philosophy with explicit "won't do" list,
   founder-mode framing, technical-implementation overview for
   developers, contribution vectors, visible emergency routing.
3. **docs/internal/ + tests/internal/ split** — the v1.5 iteration
   scaffolding (retrospective / anti-patterns / PRD / P2 deferrals)
   plus their contract test moved to gitignored `docs/internal/` and
   `tests/internal/`. Lessons from these docs are already encoded in
   the v1.5 code (G25/G26/G27 gates, persona_prefix auto-prepend,
   progress_reporter, interrupt_handling). Public surface retains:
   ADRs (9 files, OSS standard), landing page, governance docs,
   technical report, vmtb-skill diff.

1126/1126 public-tracked tests + 4/4 internal tests green.

---

## [1.5.2] — 2026-05-25 — UX patch round 2 (reporter wired + auto-prefix + interrupt protocol)

User follow-up after v1.5.1: three explicit "didn't finish" items needed to land before user testing. v1.5.2 closes all three on the same `iter/v1.5` branch.

### v1.5.2-1: ProgressReporter wired into Python long-runners

- `Wave1Runner.__init__` + `Wave3Runner.__init__` now accept a keyword-only `reporter: ProgressReporter | None = None` (back-compat: None default = v1.5 behavior).
- Wave1Runner.run() emits `start_stage(1)` at entry, 4 forced heartbeats at natural seams (after case-load, after intent, after plan, after expert dispatch), `end_stage(1)` with lay summary + "下一步: 想办法" preview. Early-exit on non-NEW_GOAL intent emits a tailored end_stage.
- Wave3Runner.run() emits `start_stage(3)` ("查数据 / Cross-checking"), forced heartbeat after dataset_acquisition, per-hypothesis heartbeats during bioinformatics_data_analysis (cadence-respecting, not forced — protects against spammy chat), `end_stage(3)` with "下一步: 审核" preview.
- New `tests/test_e2e/test_runners_with_reporter.py` (6 cases) — start/end emission, next-stage preview wording, no-jargon-leak trip-wire on default messages, signature back-compat.

### v1.5.2-2: persona_prefix auto-prepended in LLMBackedExpert

- `LLMBackedExpert._compose_system_prompt()` (new) loads + class-level-caches the canonical persona prefix (`prompts/experts/_shared/persona_prefix.md`, v1.5 P1-A) and prepends it to every expert's `persona.md` before passing as `system=` to the LLM. All 18 personas inherit G7 voice + 3-tier rubric + patient-anchor checklist + traceability footer + privacy hygiene WITHOUT manual backfill of 18 .md files.
- New keyword-only `skip_persona_prefix=True` escape hatch for unit tests in isolation.
- Missing prefix file raises `FileNotFoundError` (loud — no silent degradation per `memory:feedback_no_offline_only`).
- `tests/test_persona_prefix_auto.py` (7 cases) — prefix present, compose includes prefix for bert, escape hatch, missing-prefix raises, prefix inlined for all roster experts with persona.md, cache avoids repeated disk reads.
- `tests/test_experts/test_common.py` fixture updated to stub a minimal `_shared/persona_prefix.md` and reset the class-level cache per test.

### v1.5.2-3: SKILL.md interrupt protocol

- New SKILL.md section ("Interrupt protocol") with 7 canonical actions (SKIP-STAGE / SIMPLIFY-STAGE / PAUSE-AND-SHOW-PARTIAL / PARTIAL-DELIVERY / CANCEL / REPLAN / STATUS+ETA), pattern table (zh + en), hard rules (acknowledge ≤5s, never silent scope-change, gate-aware skip, cancel preserves artifacts, replan re-runs comorbid expansion), 3 worked dialog examples, wiring notes.
- New `prompts/tasks/interrupt_handling.md` (task contract) — JSON envelope schema (`parsed_intent` / `safety_warnings` / `plan_modification` / `needs_user_confirm`), procedure, hard-rules mirror, failure modes (intent ambiguous / safety-override demanded / cancel mid-write / partial-delivery with no claims). G25 safety surface and `ProgressReporter.block(...)` integration documented.
- `tests/test_interrupt_handling.py` (12 cases) — SKILL.md interrupt section present, 7 canonical actions enumerated consistently between SKILL.md and the task prompt, zh + en pattern coverage, hard-rules mirrored, G25 safety surface, cancel.json preservation, reporter.block integration, ≥3 worked examples.

### Test count

v1.5.1: 1101 → v1.5.2: 1126. All green under `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`.

### Migration

- ProgressReporter wiring is opt-in (default None for v1.4 / v1.5 callers); pass `Wave1Runner(reporter=ProgressReporter(on_emit=chat.send))` to drive heartbeats from Python.
- LLMBackedExpert subclasses get the prefix automatically. To opt out (tests only): `Expert(profile=..., skip_persona_prefix=True)`.
- Mid-run user input handling: any chat input arriving during Steps 4-10 is routed through `prompts/tasks/interrupt_handling.md` to parse intent and produce a structured plan modification with safety surface.

## [1.5.1] — 2026-05-25 — Long-run UX hotfix (plain-language progress)

User feedback after v1.5 ship: *"opl-cancer 太久了, 用户一直在等好几个小时, 普通人体验较差; 输出内容太专业 — 存档可以专业, 但输出给用户要通俗。"* v1.5 fixed the final deliverable (`patient_plain_brief_rendering.md` + `patient_jargon_glossary.json`) but left the **intermediate run** of 30-90 minutes silent + jargon-heavy. v1.5.1 closes both gaps in one patch on the same `iter/v1.5` branch.

### Changes

1. **`prompts/tasks/progress_message_rendering.md`** (new) — canonical contract for plain-language progress messages. 5 stage labels (准备 / 想办法 / 查数据 / 审核 / 写报告) replace internal "Wave 1..5". 5 message templates (start / heartbeat / end / delay / block) with worked examples. Hard rules: no internal jargon (Wave / hypothesis / Elo / I² / ctDNA / log2FC / G-codes / RC-xxx / H-xxx), ETA always a range, never silent past 60s, no outcome promises, no apology-for-tech.

2. **`src/opl_cancer/glue/progress_reporter.py`** (new) — `ProgressReporter` class with `start_stage` / `heartbeat` / `end_stage` / `delay` / `block` methods. Heartbeat respects 60s default cadence (configurable). Jargon-scrub trip-wire flags leaks with `[jargon-leak:X]`. JSONL audit trail. `on_emit` callback wires user-facing string to the chat. Language switchable zh / en / bilingual (default).

3. **SKILL.md surface rewrites** — every Step 4-10 user-facing example switched to plain-language 5-stage format. Internal Wave/Elo/Henry/G-codes stay in the archive (`triggers/<run_id>/tasks/...`) and the clinician brief, never in the live chat. Explicit instruction to emit a stage-start, heartbeats (≥60s), and stage-end at every Wave boundary. The `comorbid_expansion_triggers_fired` payload (v1.5 P0-6) is now narrated in lay terms too.

4. **`references/patient_jargon_glossary.json` 38 → 73 terms** — adds Wave 1..5, hypothesis, Elo, Henry, Sid, PMID, NCT, ChiCTR, CT.gov, NMPA, TCGA, GEPIA3, GTEx, cBioPortal, meta-analysis, pooled-ORR, subgroup, I², heterogeneity, audit, verdict, risk-card, ack, L3/L4, rate-limit, retrieval, integrator, provenance, preflight, hypothesis-tournament, gate. Schema bumped to v1.5.1.

5. **`tests/test_progress_reporter.py`** — 20 new tests for stage labels (bilingual + monolingual), ETA range presence, heartbeat cadence, force override, delay invite-skip phrasing, block letter options, jargon-scrub trip-wire on v1.5 internal codes, JSONL persistence, on_emit callback, unknown-stage error.

### Test count

1081 (v1.5) → 1101 (v1.5.1). All green under `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`.

### Migration

- No breaking API change. ProgressReporter is opt-in (Wave runners accept it as an optional kwarg; v1.5 default behavior is unchanged when `reporter=None`).
- Skill prompt-layer assistants MUST start using the 5-stage labels at every stage transition. The Python helper is a convenience; the orchestrator can also emit strings directly per `prompts/tasks/progress_message_rendering.md`.

## [1.5.0] — 2026-05-25 — Retrospective-driven hardening (iter/v1.5)

Driven by `docs/RETROSPECTIVE_v1.4_PT-EXAMPLE-A_run-20260525.md` (compiled from 6 parallel Explore-subagent audits of the v1.4 PT-EXAMPLE-A run) and the 16 anti-patterns it surfaced (`docs/ANTI_PATTERNS_v1.4.md`). PRD lives at `docs/PRD_v1.5.md`. Closes 8 P0 + 9 P1 items; 3 of 6 P2 deferred to v1.6 with explicit rationale in `docs/P2_DEFERRALS_v1.5.md`.

### P0 — must ship

1. **P0-1+P0-8 Wave 3 native-Python path + non-skippable critical path** — `src/opl_cancer/compute/native_runner.py` provides `NativeAnalysisRunner` with the same `run_notebook` interface as `BixbenchRunner`. `compute/__init__.py` exports `select_compute_runner()` selector that prefers native (jupyter on PATH) and falls back to bixbench (docker on PATH); raises when both are absent. `src/opl_cancer/compute/kernel_requirements.txt` created — fixes the broken `bixbench.Dockerfile:85 COPY kernel_requirements.txt` build (AP-1, AP-14). `glue/wave3_runner.py` widened to `ComputeRunner = BixbenchRunner | NativeAnalysisRunner` (back-compat preserved). Preflight refuses to start when neither runner is available.

2. **P0-2 GEPIA3 first-class integrator** — `src/opl_cancer/integrators/gepia3.py` (`GEPIA3Integrator`, family F12). Key `gepia3:exp:<GENE>:<TCGA_TYPE>` returns log2fc + q-value + tumor/normal counts. Default 12-second rate-limit pacing matches empirical PT-EXAMPLE-A recovery threshold. `batch()` collects per-query status. `prompts/tasks/gepia3_query.md` is the Aviv task contract (no fabrication, G7 voice, cohort-vs-patient caveat, CN-source supplement for mainland). Tests `tests/test_integrators/test_gepia3.py` (12 cases, respx-mocked). Closes AP-5: GEPIA3 was the highest-impact recovery tool of v1.4 and was invisible to the planner.

3. **P0-3+P0-10 G13 reviewer-distinct preflight hard-fail + Wave 3 gating** — `cli.py preflight` now blocks (exit 1) when no `MINIMAX_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` is set (previously `[warn]` only). New `--allow-single-model` flag bypasses for dev/test with `[warn]`. New `wave3_compute` check field with `native_runner_ready` + `bixbench_runner_ready` + `default_runner` + 3-line remediation message. AP-10 closed.

4. **P0-4 patient-plain-brief delivery split** — `prompts/tasks/patient_plain_brief_rendering.md` ships a separate audience target: 2nd-person zh / en, ≤ 2 pages at 12-pt, 4 mandatory sections (病情一页纸 / 下一步 / 不同选择 / 问医生 5 个问题), no PMIDs / Elo / I² stats in body, no outcome promises ("您会响应" → block). `references/patient_jargon_glossary.json` (38 bilingual terms covering the high-frequency v1.4 offenders) is read by the renderer for the new G-jargon gate. AP-6 closed.

5. **P0-5 Henry epistemic gates G25 + G26 + self-verify** — `validators/gates/g25_deferred_evidence_block.py` blocks delivery when an evidence-critical claim carries `deferred=True` or `[SKIPPED]` / `[NOT RUN]` / "wave 3 skipped" markers, unless the patient explicitly opted out. `g26_evidence_strength_ranking.py` caps Elo boost at 15 when `subgroup_match_fraction < 0.5` OR `i_squared > 60%`, and requires a `demotion_disclosed` marker in narrative or flags. `prompts/auditor/l1_mechanical_gates.md` adds a self-verify section: Henry checks its own G17 rendering mandate against the actual artifact. Tests `tests/test_validators/test_g25_g26.py` (17 cases including the canonical PT-EXAMPLE-A failure modes). AP-1, AP-2, AP-3 closed.

6. **P0-6 Deterministic multi-comorbid planner expansion** — `src/opl_cancer/plan/comorbid_planner.py` reads `profile.json` and fires trigger-tasks when the patient phenotype matches: active irAE (→ Mark), ≥3 prior lines (→ Frances), ≥3 co-meds OR cardiac OR CKD (→ Mary), mainland-CN (→ Riad + Dennis), imaging gap OR age ≥70 (→ Heddy). `cli.py plan` surfaces `comorbid_expansion_triggers_fired` in JSON output — silent override of the baseline plan is now visible (AP-9, AP-11). Tests `tests/test_comorbid_planner.py` (20 cases including the canonical PT-EXAMPLE-A phenotype).

7. **P0-7 Subagent file-write contract** — `prompts/safety/subagent_file_write_contract.md` canonicalizes the output procedure for every dispatched expert subagent: PRIMARY Write tool → FALLBACK Bash heredoc with `OPL_REPORT_EOF` sentinel → CONFIRMATION JSON envelope (`report_path` + `report_bytes` + `report_sha256_short` + `status`). Orchestrator validates filesystem matches envelope; 1 retry on mismatch. `write_failed` is loud, never silent (AP-12 / F12).

### P1 — should ship

8. **P1-A Canonical persona prefix + G27 privacy scrub** — `prompts/experts/_shared/persona_prefix.md` is the required first section of every expert persona prompt: G7 forbidden-word list + 3 paired imperative→informational rewrites + 3 escape hatches, 3-tier evidence rubric, 5-box patient-anchor checklist (≥4 required), source-traceability footer schema, privacy hygiene. `validators/gates/g27_privacy_scrub.py` blocks reports containing CN mobile phones, emails, CN national IDs (18-digit), MRN-labeled identifiers (en + zh), insurance-card identifiers — caught the canonical `[FAMILY-CONTACT] 13800138000` Dennis leak from v1.4 (AP-7, AP-8). `redact_text()` + `scan_text()` helpers exported. Gate count 25 → 26.

9. **P1-B Shared clinical stop-rules + CN-source mandate** — `references/clinical_stop_rules.json` documents 7 canonical stop-rules (STOP-RENAL-1, STOP-CARDIAC-1, STOP-HEPATIC-1, STOP-ACTIVE-IRAE-1, STOP-MARROW-1, STOP-BLEED-1, STOP-QTC-1), each with PMID-backed evidence. `prompts/safety/cn_source_mandate.md` requires NMPA / 国家医保局 / CSCO / 中华医学会 / ChiCTR / Boao / 港澳药械通 coverage when `profile.country == "CN"`. Closes AP-7 (cross-cutting persona-prompt failures #5 + #7).

### P2 — deferred to v1.6 with rationale

`docs/P2_DEFERRALS_v1.5.md` is the single source of truth. Shipped in v1.5: P2-1 partial (this CHANGELOG entry), P2-3 plan-narration (via `comorbid_expansion_triggers_fired`), P2-5 cost-currency stamp (via persona-prefix §4). Deferred to v1.6: P2-2 SKILL.md ↔ code CI hook, P2-4 Robin reflector live feedback loop, P2-6 Frances / Dennis access-pathway live probe.

### Gate registry

- 23 → 26: +G25 deferred-evidence-block, +G26 evidence-strength-ranking, +G27 privacy-scrub.

### Test results

- 1081/1081 test cases under `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` green. Includes pre-existing ADR-0009 heading fix.

### Migration

- New `MINIMAX_API_KEY` requirement: get a free key at https://platform.minimaxi.com/ — see `.env.example`. For dev / smoke runs only, use `opl-cancer preflight --allow-single-model`.
- New optional `OPL_NATIVE_LIVE=1` env var to enable real jupyter `nbconvert --execute` in `NativeAnalysisRunner` (defaults to native-dry-run). `OPL_BIXBENCH_LIVE=1` continues to gate Docker bixbench.
- `profile.json` is now consulted by `plan()`; missing / malformed profile = empty-dict fallback (no expansion fires, no crash).

### Provenance

- Branch: `iter/v1.5` on git@github.com:CancerDAO/opl-cancer-skill.git
- Authority: `docs/PRD_v1.5.md` §1 P0/P1/P2 scope
- Retrospective: `docs/RETROSPECTIVE_v1.4_PT-EXAMPLE-A_run-20260525.md`
- Anti-patterns: `docs/ANTI_PATTERNS_v1.4.md`

## [1.4.0] — 2026-05-25 — Round-2/3 deferred backlog (priority A + B)

After v1.3.3 ship-ready, ADR-0008's Deferred-to-v1.4 backlog (13 items with trigger conditions + effort estimates) is worked through in one batch fix. 11 of the 13 items close (5 priority A + 6 priority B); 2 items (D11 Bilingual delivery, D12 Expert-mode delivery channel) remain deferred to v1.5 as they belong to a delivery-layer rewrite that would over-scope v1.4. Three new task packages, two substantive task-package extensions, one new integrator, one CLI UX expansion, one intent_parser field, one planner row.

### Priority A — round-2 P0-equivalent fixes (5 items)

1. **A1 `prompts/tasks/surveillance_schedule.md` (new, ~265 lines)** — D1 domain; Heddy + Bert + Vince three-way; closes round-2 EVAL Patient #12 MEN1 post-resection pancreatic NET + parathyroid + pituitary surveillance gap. Inputs: `cancer_type` + `treatment_status` (curative_intent_completed / resected_with_residual_risk / maintenance / adjuvant_completed / watchful_waiting / post_definitive_RT) + `genetic_syndrome` (MEN1 / Lynch / LFS / HBOC_BRCA1/2 / VHL / NF1/2 / FAP / Peutz-Jeghers / Cowden / none) + `prior_recurrences[]`. Outputs: `surveillance_schedule[]` per modality (imaging / biomarker / clinical_exam / genetic_cascade) with cadence + integrator-anchored guideline + claim_layer. Mandatory: G14 cohort match for `recurrence_risk_projection`; G21 quantitative anchor for 5yr DFS / OS estimate + CI; cascade hand-off to `firefly-genetic-counseling` when syndrome+. Integrator anchors: NCCN Survivorship + cancer-specific NCCN follow-up + ASCO Survivorship + syndrome consensus (Thakker 2012 MEN1, Villani 2016 LFS, NCCN Lynch, NCCN HBOC). Surveillance is structurally NOT recurrence response (`recist_progression.md`) NOT next-line (`treatment_line_recommendation.md`) NOT acute workup (`staging_workup.md` restaging).

2. **A2 `prompts/tasks/irae_rechallenge.md` schema extension (modify)** — Closes round-2 EVAL Patient #14 G2 myocarditis + G3 pneumonitis concurrent multi-organ gap. Schema changes:
   - `prior_irae_record` changed from **singleton → list** (each entry `{organ, ctcae_grade, resolution_status, time_since_resolution_days}`); legacy singleton wrapped to length-1 list (no break).
   - New `cumulative_organ_load_index` field with severity-weighted formula `Σ_i (grade_i^2 × organ_severity_weight_i × resolution_penalty_i)` + canonical weight table (myocarditis 2.5 / encephalitis 2.5 / pneumonitis 1.8 / hepatitis 1.3 / colitis 1.2 / nephritis 1.4 / GBS 2.2 / endocrine 0.6-1.0 / dermatitis 0.4 / arthritis 0.6) + resolution penalty (complete 1.0 / partial 1.4 / chronic 2.0 / not_resolved 3.0) + bands (low <2 / moderate 2-5 / high 5-10 / very_high >10).
   - New contraindication escalation rules: `myocarditis_g2+` → STRONG RELATIVE (escalated from g3+, anchored to Salem ESC 2022 + Mahmood JACC 2018 PMID 29567210); `pneumonitis_g3+ AND any other_organ_irAE_g2+` → STRONG RELATIVE (v1.4.0 multi-organ rule); `2+ G3+ events in different organs` → NEAR-ABSOLUTE (~50% pooled rebound mortality); `cumulative_organ_load_index band ∈ {high, very_high}` → STRONG RELATIVE.
   - L3 risk-card escalates to L4 when any escalation rule fires; `organ_specific_warning` becomes verbatim concatenation of all matching rules; `rebound_specific_text` includes the cumulative_organ_load_index value + band.

3. **A3 `prompts/tasks/boundary_unregulated_channel_disclosure.md` retrospective mode (modify)** — Closes round-2 EVAL Patient #15 already-administered grey-market Lu-177 gap. Schema changes:
   - New `disclosure_mode: prospective | retrospective | mixed` mandatory field.
   - New `forensic_evaluation_request: bool` + `retrospective_records: {dosimetry_log_present, batch_records_present, packaging_photos_present, post_exposure_lab_panel_present, imaging_response_present, adverse_event_log_present}`.
   - `procurement_refusal_text` split into `_prospective` + `_retrospective` variants; retrospective text reads: *"OPL cannot validate the source post-hoc — the exposure already happened. What OPL can do is help you quantitatively check what your dosimetry log / batch records / packaging photos / post-exposure labs / imaging response / AE log can tell us about activity match / radiochemical purity flags / response window / cross-contaminant signature. FUTURE doses through this channel remain refused — the prospective boundary holds."*
   - New `retrospective_forensic_evaluation` block with 5 record-type rows + what_we_cannot_check_post_hoc + next_step_monitoring (renal q4w × 6mo / parotid + lacrimal q3mo × 12mo / marrow recovery q2w × 6mo / PSA + PSMA-PET 8w / 16w / 24w).
   - Boundary on future-procurement remains permanent regardless of mode.

4. **A4 `prompts/tasks/n1_cohort_projection.md` fallback chain (modify)** — Closes round-2 EVAL Patient #11 Hartwig DUA-raise + Patient #14 BRCA-NSCLC fallback miss. Schema changes:
   - Inputs now declare `candidate_cohorts[]` ordered array (per-cancer planner hints: HCC → [Hartwig-HCC, ICGC-LIRI-JP, cBioPortal-LIHC, GEO-HCC-TACE-refractory pooled]; mCRPC → [Hartwig-PCa, ICGC-PROFILE, MSK-IMPACT, SU2C-PCF]; BRCA-NSCLC → [Hartwig-NSCLC-BRCA-subset, MSK-IMPACT-NSCLC, MSK-IMPACT-pan-cancer-BRCA, AACR-GENIE-BRCA]; AML R/R → [BeatAML 2.0, Hartwig-AML, TARGET-AML, OHSU-AML]).
   - Procedure step 1 rewritten as ordered fallback loop: per candidate try retrieval → apply filter → compute match_score → decision (DUA-gated / empty / small_n / low_match → CONTINUE; pass → SELECT + STOP). Record every attempt to `cohort_alternatives_attempted[]` with `{dataset_id, ordinal, selected, n_after_filter, match_score, reason}` — surfaces the full attempt trail to the patient brief.
   - If all candidates exhaust without selection → emit `projection: null` + speculative claim_layer + summary names every reason.

5. **A5 `prompts/tasks/caregiver_filter_protocol.md` (new, ~205 lines)** — D5 domain; Sid + Henry L4; closes round-2 EVAL Patient #11 老公 "let me consume first" caregiver-as-filter gap. Adult-patient caveat (the pediatric guardian path is handled by `guardian_ack_protocol.md`). Inputs: `speaker_role: caregiver` + `patient_currently_competent` + `patient_consent_to_relay_decision: explicit | inferred | unknown`. Output: `caregiver_preview_mode: true` → emits `caregiver_brief.md` BUT **keeps `patient_brief.html` intact in delivery folder** (OPL does NOT suppress / hide / move / encrypt / rename — the boundary is structural). Mandatory explicit disclosure to caregiver: *"OPL cannot withhold from the patient — the patient brief will materialize the moment your wife / husband / family member opens the patient_root folder. Honest options: (a) talk to patient now with this material; (b) hand off to cancer-buddy-disclosure sibling skill to script the conversation; (c) accept that withholding is YOUR decision, not OPL's — OPL keeps patient brief intact"*. Sid explicitly **declines** to make the disclosure decision on the patient's behalf — preserves patient-sole-decision-authority invariant. Caregiver acks `preview_receipt` only; cannot ack L3/L4 cards on patient's behalf.

### Priority B — round-2/3 P1 batch (6 items)

6. **B1 `prompts/tasks/patient_pushback_handling.md` (new, ~195 lines)** — D5 domain; Sid + Henry L2; closes round-2 EVAL Patient #18 sister-physician zolbetuximab dissent + Patient #14 老婆 rechallenge disagreement gap. Inputs: `original_claim_id` + `pushback_text` (verbatim) + `pushback_role: patient | family_member | physician_audit` + `pushback_axis_hint`. Output: NEITHER concede (echo violates `memory/feedback_third_party_lens`) NOR paternalism (don't restate same number louder). Surfaces `alternative_read` honestly, `integrator_anchored_dissent[]` (SPOTLIGHT critics on absolute PFS Δ vs OS HR; NCCN Cat 1 vs 2A; ESMO MCBS dissent), `value_lattice_reframe` (maps original framing vs alternative framing to patient's stated value), `your_choices_optionful` (accept alternative / accept original / re-rank value lattice / ask Wave re-run as NEW_GOAL). NOT a Wave re-run (that's a new trigger); a re-frame + re-anchor of existing claim. Logged to `memory/feedback_log/` regardless of patient choice.

7. **B2 `src/opl_cancer/integrators/hkctr.py` (new, ~165 lines)** — F3 family; closes round-2 EVAL Patient #20 NPC EBV CN/DE/HK three-jurisdiction registry gap. Real HTTP scrape of `https://www.hkclinicaltrials.com/` with fallback to Department of Health Drug Office `https://www.drugoffice.gov.hk/eps/`. Two layout regex patterns (linked-anchor cards + drug-office tabular rows) + de-duplication by hkctr_id. Schema-drift detection raises `IntegratorError` on markers-present-but-zero-rows. Both endpoints unreachable raises. Genuine empty (no markers) returns empty list. Registered in `integrators/__init__.py` + `cli.py preflight integrator_modules` (28 → 29) + status banner ("Integrators wired: 29 / + HKCTR"). 8 unit tests covering primary / fallback / drift / unreachable / genuine-empty / malformed-key / empty-term / family-classification.

8. **B3 SKILL.md Step 4 — TNBC + LM planner row** — Closes round-2 EVAL Patient #13 TNBC + LM gap. Added row: *"TNBC + LM (leptomeningeal mets): Bert + Vince + Heddy + Aviv + Iain + Rick + Ted (HA-WBRT — NRG-CC003 backbone for TNBC LM) + Jen (LM palliative — TNBC LM median survival 2-4 months) + Frances (sacituzumab + IT-nivolumab compassionate — IT-trastuzumab N/A for TNBC, IT-MTX is canonical) + Tyler (wet-lab biomarker)."* Explicit chemistry note: TNBC LM-route chemistry differs from breast-HER2 LM (IT-trastuzumab N/A; IT-MTX canonical; IT-pembrolizumab emerging; HA-WBRT radiation backbone).

9. **B4 `prompts/pi/intent_parser.md` — delivery_tone_hint extraction** — Closes round-2 EVAL Patient #13 "我不想被 sugar-coated" + Patient #16 parents "more padding" gap. New JSON output field `delivery_tone_hint: blunt | warm | clinical | unspecified`. Extraction rules:
   - **blunt** triggers: ZH `直接告诉我 / 别 sugar coat / 别软话 / 实话实说 / 直说 / 不要绕弯子 / 坦白 / 别藏着掖着` + EN `give it to me straight / no sugar coating / blunt / honest / cut to the chase / unvarnished / no padding`.
   - **warm** triggers: ZH `温柔点 / 委婉 / 不要直接说 / 轻一点 / 慢慢说 / 不要太冲击` + EN `gently / soft / careful / pace it / take it slow / easy on me`.
   - **clinical** triggers: ZH `用医生的话说 / 给我临床版 / 我是医生 / 给我学术版` + EN `clinical voice / peer-physician / I'm a physician / expert mode`.
   - **unspecified** = default, downstream `pi_delivery.md` heuristics-pick.
   Persists to `pi_session/preferences.json.delivery_tone` with source-tracking (`user_explicit_set` wins over `intent_parser_extracted`; later parses overwrite earlier parses).

10. **B5 Ack-batch UX — `cli.py acknowledge --batch <pattern>` + `pi_delivery.md ack_consolidation_card`** — Closes round-2 EVAL Patient #14 stacked 3+ acks repeatedly triggered. CLI:
    - `opl-cancer acknowledge --batch L3-all` — ack all L3 cards.
    - `opl-cancer acknowledge --batch L4-all` — ack all L4 cards.
    - `opl-cancer acknowledge --batch Lall` — ack all L3+L4 pending.
    - `opl-cancer acknowledge --batch by-drug:<inn>` — ack all cards mentioning the INN (case-insensitive substring scan of claim_text + known_serious_risks).
    - `opl-cancer acknowledge --batch by-claim:<id_prefix>` — ack all cards with claim_id starting with prefix.
    - `opl-cancer acknowledge --batch by-card-prefix:<prefix>` — ack all cards with card_id starting with prefix.
    Each individual card is still acked atomically and audit-trail-recorded; the batch flag only reduces UX friction. `pi_delivery.md` adds an `ack_consolidation_card` section at the top (above the per-card risk-card render) when 3+ unacked cards exist — lists only baseline safety disclosure (irAE risks / EAP-is-not-approval / cross-border-is-not-continuity / off-label-is-off-label / L4-boundary), provides the batch CLI hint, but explicitly preserves drug-specific acks as individual cards (no consolidation of patient-conscious drug-specific risks into a single ack).

11. **B6 `prompts/tasks/n1_cohort_projection.md` lab_trajectory feature (modify)** — Closes round-2 EVAL Patient #11 HCC AFP 240→8400 over 5mo (35x rise — strongest prognostic signal but v1.3.x modeled static labs only). Schema:
    - Inputs `patient_features_extracted.lab_trajectory: {biomarker → {slope_per_month, doubling_time_mo, fold_change_x, baseline_value, latest_value, trajectory_span_months, trajectory_class}}`.
    - Trajectory-eligible biomarker per cancer: HCC → AFP / AFP-L3 / DCP-PIVKA-II; PCa → PSA; TNBC + ER+/HER2- → CA15-3; HGSOC → CA-125; CRC → CEA; pancreatic → CA19-9; gastric → CA72-4 / CEA; AML → WBC / blast %; MM → M-protein / light chains / β2-microglobulin; DLBCL → LDH trajectory + sIL-2R; pancreatic NET → chromogranin A.
    - Procedure step 2 updated: ≥2 serial measurements spanning ≥30 days REQUIRED to compute trajectory; single-measurement biomarkers emit `lab_trajectory.<biomarker>: null` + extrapolation_warning ("single measurement; trajectory not computable"). The LLM may NOT fabricate a trajectory from a single value (`memory/feedback_no_offline_only.md`).
    - `patient_features_used[]` now includes `lab_trajectory:<biomarker>:slope_per_month` + `lab_trajectory:<biomarker>:doubling_time_mo` as Cox covariates.

### Version bumps

12. `pyproject.toml` — `version = "1.3.3"` → `"1.4.0"`.
13. `SKILL.md` — `metadata.version: "1.3.3"` → `"1.4.0"` + v1.4.0 anchor narrative (lists A1-A5 + B1-B6 + integrator count 28 → 29).
14. `src/opl_cancer/cli.py` — `VERSION = "1.3.3"` → `"1.4.0"`; `status` reports `Integrators wired: 29 ( … + HKCTR + …)`; preflight `integrator_modules` list grows by `"hkctr"`.
15. `tests/test_cli.py` — asserts `v1.4.0` + `Integrators wired: 29` + retains `Mechanical gates: 23`.

### ADR — Deferred table updated

16. `docs/adr/0008-eval-panel-round-2-v1.3.2.md` — Deferred-to-v1.4+ table updated: D1 / D2 / D3 / D4 / D5 / D6 / D7 / D8 / D9 / D10 / D13 ✓ marked fixed in v1.4.0 with file refs; D11 (Bilingual delivery) + D12 (Expert-mode delivery channel) remain deferred to v1.5 (delivery-layer rewrite scope) with re-stated trigger conditions.

### Test count delta

- HKCTR: 8 new unit tests in `tests/test_integrators/test_hkctr.py`.
- CLI: existing tests + status banner update validated.
- Task-package count: 38 → 41 (surveillance_schedule + caregiver_filter_protocol + patient_pushback_handling).
- Mechanical gates unchanged at 23 (G1-G20 + G22 + G23 + G24).
- Integrators: 28 → 29.

## [1.3.3] — 2026-05-25 — Round-3 verification follow-up (catalogue + recency completeness)

After v1.3.2 SAFETY hot-fix, round-3 focused verification (3 patients: #21 SI, #22 pediatric guardian, #23 sister-physician audit) confirmed the 3 SAFETY P0 fixes (G24 crisis detection / guardian_ack_protocol / drilldown 4 classes) all PASS. Found 2 one-line gaps:

- **`knowledge/serious_risks_per_drug.json`** — added 4 entries: **revumenib** (Revuforj / SNDX-5613, menin inhibitor; Differentiation syndrome BOXED + QTc + hepatotox + cytopenias), **ziftomenib** (KO-539 investigational, menin-i; class-effect DS), **bleximenib** (JNJ-75276617 Phase 2, menin-i; class-effect DS), **ceralasertib** (AZD6738 investigational Phase 3, ATR inhibitor; severe myelosuppression + transaminitis + IO-combo pneumonitis HUDSON/CAPRI). Closes Patient #22 FAIL: v1.3.2 added "Pediatric AML R/R" planner row pointing to revumenib EAP but the L3 known-serious-risk JSON lacked the entry → Henry would emit `[unknown drug]` for menin-i pediatric AML cases.
- **`g23_recency_band.py FAST_MOVING_TOPICS`** — added ~30 DDR-targeting tokens (ATR-i: atr / atr-i / ceralasertib / azd6738 / berzosertib / m6620 / vx-970 / elimusertib / bay1895344 / camonsertib / rp-3500 / atrn-119 + CHK1-i: chk1 / chk1-i / prexasertib / ly2606368 + WEE1-i: adavosertib / azd1775 / wee1 / wee1-i + Polθ-i: novobiocin / polq / polθ inhibitor / art4215 / art-4215). Closes Patient #23 PARTIAL: G23 now fires recency-band WARN on stale ATR-i citations alongside the existing brca-reversion trigger.

Both are one-line knowledge-file / regex-list additions. No architectural change. 977 tests still pass; ruff clean.

**Verification verdict on v1.3.2 SAFETY paradigm**: round-3 confirms the 3 round-2 P0 drivers are mechanically closed (G24 fires on "想结束这一切" passive_SI · guardian_ack_protocol blocks treatment-decision authority for guardian-of-minor speaker · drilldown.md 4-class envelope handles compound sister-physician audits). v1.3.3 is the residual one-line catalogue / recency completeness pass; ship-ready.

## [1.3.2] — 2026-05-25 — SAFETY hot-fix (round-2 EVAL response)

Round-2 EVAL panel (seed 11-20) exposed 2 SAFETY P0 + 1 carry-over P0 + 3 critical P1 that cannot be deferred to v1.4. Ships as a same-day hot-fix.

### Safety P0 — Suicidal-ideation crisis detection (round-2 Patient #17)

v1.3.1 had no SI / self-harm keyword detection — phrases like "想结束这一切 / end it all / can't go on" fell through to EMOTION intent then trial-dumped to an ECOG-3 bedbound suicidal patient.

1. `prompts/safety/crisis_detection.md` — new bilingual (ZH + EN) crisis-detection prompt. Three grades (`passive_SI` / `active_SI` / `active_plan`) over keyword banks A/B/C. Keyword-scan FIRST (no LLM-only path), LLM grades after. Outputs `{crisis_detected, crisis_grade, trigger_phrase, jurisdiction_inferred, speaker_role_echo, rationale}`.
2. `src/opl_cancer/validators/gates/g24_crisis_detection.py` — new G24 gate. No-LLM keyword-scan over patient_text + caregiver_text. On hit → `GateStatus.FAIL + block=True` with payload `{crisis_grade, trigger_phrase, jurisdiction_inferred, recommended_handoff: [cancer-buddy-mind, jurisdiction-crisis-line:XX], wave_lock: true}`. Registered in `validators/gates/__init__.py` + `mechanical_gates.all_gate_classes()` (22 → 23 gates).
3. `prompts/tasks/crisis_card_emission.md` — new owner-sid task package. Emits `pi_session/outstanding/crisis_card.json` with jurisdictional phone lines (CN 010-82951332 + 400-161-9995; US 988; UK Samaritans 116-123; DE Telefonseelsorge 0800-111-0-111; EU 116-123 international; JP TELL 03-5774-0992 + 0120-783-556; international Befrienders fallback). Founder-mode prose: acknowledge + name the moment + offer phone + hand off to `cancer-buddy-mind` (+ `cancer-buddy-caregiver` if speaker is caregiver / guardian). Wave runners must check + lock on `acknowledged_by: pending`.
4. `SKILL.md` — "When NOT to invoke" adds **Acute psychiatric crisis** row with G24 auto-fire + Wave-lock description.
5. `prompts/pi/intent_parser.md` — adds `crisis_grade: none|passive_SI|active_SI|active_plan` to output JSON; EMOTION intent gets a CRISIS subclass branch that forks to `crisis_card_emission` instead of soft handoff.
6. `prompts/tasks/scope_handoff_routing.md` — adds "Crisis multi-handoff exception" overriding the single-sibling rule on `crisis_grade != none`.
7. `tests/test_validators/test_g24_crisis_detection.py` — 12 cases: passive_SI ZH/EN, active_SI ZH/EN, active_plan ZH/EN, false-positive avoidance (advance directive / DNR / hospice), false-negative caregiver_text scan, grade-picks-highest, jurisdiction inference (explicit hint + UK location token).

### Safety P0 — Pediatric guardian mode (round-2 Patient #16)

v1.3.1 told a 7yo ALL R/R guardian to "wait for v1.4" — excludes pediatric patients from the "every patient" promise.

8. `prompts/pi/intent_parser.md` — adds `guardian_of_minor` speaker_role (caregiver + patient_age<18 + first-degree relative + age-from-text inference rules).
9. `prompts/tasks/guardian_ack_protocol.md` — new task package, sid + henry co-review. Guardian acks **information receipt only** (NOT treatment-decision authority — that routes to pediatric IRB-supervised slot). Emits `pediatric_caregiver_brief.md` + `pi_delivery_minor.md` (age-simplified for 5-12 yo if appropriate). Adult-only sibling skills activated with caveat.
10. `SKILL.md` Step 4 — adds 4 pediatric planner rows: Pediatric ALL R/R (revumenib/menin-i + Lee CRS), Pediatric AML R/R, Pediatric DIPG / brain tumor (H3K27M + ONC201 + pediatric proton), Pediatric solid (Ewing / RMS / neuroblastoma).
11. `SKILL.md` "When NOT to invoke" — replaces "wait for v1.4" with the guardian + child unit model + IRB-slot routing.

### Safety P0 — drilldown.md depth (round-2 Patient #18 sister-physician audit)

12. `prompts/pi/drilldown.md` — full rewrite from v1.2.0 stub. Four canonical drill-down classes: **claim_provenance** (PMID + quote + hash + notebook + reproduce_command), **reasoning** (expert's step-by-step chain + premise set + alternatives rejected), **statistical** (method + dataset + assumptions + sensitivity + interpretation), **disagreement** (round + experts + axis + Henry L2 verdict + tie-break). Output schema `drilldown_card.json` with `drilldown_type`, `original_claim_id`, `expanded_evidence`, `expanded_reasoning`, `expanded_statistics`, `expanded_disagreement`. Refuses to invent new claims; cross-routes to `intent_parser` for new territory.

### Critical P1 (3 fixes)

13. `src/opl_cancer/validators/gates/g22_ddr_zygosity.py` — adds `_NON_DDR_LINEAGE_CONTEXTS` (pediatric ALL / AML / lymphoma / NPC / thyroid / DIPG) + `_DDR_THERAPY_TOKENS` (PARPi class + ATR-i + platinum + DDR-trial names). If DDR gene mentioned but no therapy-token AND cancer-context is in non-DDR lineage list → SKIP (carve-out) instead of FAIL. BLOCK hint message now disease-context-aware (NSCLC → HUDSON/MEDIOLA-LUNG; ovarian → SOLO1/SOLO2/PRIMA; breast → OlympiA; pancreas → POLO) — no longer defaults to PROfound for non-prostate. 5 new test cases.
14. `src/opl_cancer/validators/gates/g23_recency_band.py` — extends `FAST_MOVING_TOPICS` with menin / revumenib / ziftomenib / bleximenib / KMT2A-r / NPM1-mut AML / EBV / EBV-CTL / tab-cel / tabelecleucel / LMP1 / LMP2 / EBNA / NPC / HA-WBRT / NRG-CC003 / IT-nivolumab / IT-pembrolizumab / craniospinal proton / LM proton / Dato-DXd / datopotamab deruxtecan / tarlatamab / BiTE / KRAS G12D / G12V / MRTX1133 / BTK degrader / pirtobrutinib / nemtabrutinib. 4 new test cases.
15. `SKILL.md` description — adds 14 cancer types (NPC/鼻咽癌, MEN1/多发性内分泌肿瘤, pancreatic NET/胰腺神经内分泌瘤, pituitary adenoma/垂体腺瘤, GIST/胃肠间质瘤, sarcoma/软组织肉瘤, thyroid/甲状腺, cholangiocarcinoma/胆管癌, mesothelioma/间皮瘤, head and neck/头颈, esophageal/食管, RCC/肾细胞癌, bladder/膀胱, glioma/胶质瘤, pediatric ALL/AML/DIPG/Ewing/RMS/neuroblastoma).

### New ADR

16. `docs/adr/0008-eval-panel-round-2-v1.3.2.md` — documents the round-2 panel (seed 11-20), the 2 P0 SAFETY + 1 P0 carry-over + 3 critical P1 fixed in v1.3.2, and the ~13 P1+P2 deferred to v1.4 with trigger conditions + effort estimates.

### Bumps

17. `pyproject.toml` — version 1.3.1 → 1.3.2.
18. `SKILL.md` — `metadata.version` 1.3.1 → 1.3.2 + v1.3.2 anchor narrative.
19. `src/opl_cancer/cli.py` — `VERSION = "1.3.2"` + `status` reports `Mechanical gates: 23 (G1-G20 + G22 + G23 + G24)`.
20. `tests/test_cli.py` — asserts `v1.3.2` + `Mechanical gates: 23`.

## [1.3.1] — 2026-05-25 — Post-EVAL hot-fix release

Closes the v1.3.0.post1 "deferred to v1.3.1" batch from the 10-patient EVAL panel — 5 new task packages + 2 new gates + 7 new integrator stubs + ADR-0007 follow-up. See `docs/adr/0007-eval-panel-v1.3.0-followup.md` for the panel narrative + the deferred-to-v1.4 backlog.

### New task packages (5)

1. `prompts/tasks/boundary_unregulated_channel_disclosure.md` — D5, Sid + Dennis + Frances co-review. Mandatory `acknowledgement_of_existence: true` + `procurement_refusal: true` + L4 ack + permanent broker / clinic / price / procurement-logistics block flags (Patient #9).
2. `prompts/tasks/n1_cohort_projection.md` — D3, Aviv + Iain. Cox fit + KM stratification + projected OS-12mo / PFS-XX with CI + extrapolation_warnings; G14 + G21 enforced. Consumed by `irae_rechallenge` + `intrathecal_therapy_navigation` (Patient #10).
3. `prompts/tasks/intrathecal_therapy_navigation.md` — D1, Ted + Vince + Jen three-way. Chamberlain stratification + IT-MTX / IT-cytarabine / IT-trastuzumab (HER2-only) / IT-nivolumab (melanoma) / Ommaya + HA-WBRT + craniospinal-proton + mandatory `prognosis_band` with CI (Patient #10).
4. `prompts/tasks/irae_rechallenge.md` — D1, Mark + Vince + Iain. Dolladille / Simonaggio / Pollack pooled HR + n1-projected rebound probability with CI + organ-specific absolute contraindications (myocarditis g3+ / encephalitis g3+) + L3 ack (Patient #4).
5. `prompts/tasks/family_cascade_routing.md` — D5, Sid + Bert. Cancer-syndrome-cascade specialisation of `scope_handoff_routing`; variant-fidelity payload + at-risk-relative graph + handoff to `firefly-genetic-counseling` without auto-invocation (Patient #8).

Task-package total: 31 → 36.

### New mechanical gates (2)

6. `src/opl_cancer/validators/gates/g22_ddr_zygosity.py` — Failure mode F7. BLOCK on any DDR/HRR/PARPi claim missing `ddr_gene + ddr_zygosity ∈ {biallelic, monoallelic, unknown, not_applicable} + trial_subgroup + pmid`. Hint message names canonical PROfound / PROpel / MAGNITUDE pairings (Patient #9 E3).
7. `src/opl_cancer/validators/gates/g23_recency_band.py` — Failure mode F8. WARN (not BLOCK) when fast-moving-topic claim (PSMA-RLT / Lu-177 / AR-V7 / CAR-T / BTK-degrader / KRAS-G12C / MET-amp / BRCA-reversion / ADC / BiTE) cites PMID older than 18 months. Carries caveat into patient brief (Patient #9 E4).

Both gates registered in `src/opl_cancer/validators/gates/__init__.py` and `mechanical_gates.all_gate_classes()`. Gate count: 20 → 22.

### New integrator stubs (7)

Per `memory/feedback_no_offline_only.md` — no training-data fabrication. Controlled-access integrators raise `IntegratorError` with the canonical access path; public-API integrators perform real HTML scrape / GraphQL fetch.

8. `src/opl_cancer/integrators/hartwig.py` — F5, Hartwig Medical Foundation (DUA-gated). Raises with application URL + Priestley *Nature* 2019 descriptor PMID 31645765. TTL 30 days.
9. `src/opl_cancer/integrators/beataml.py` — F5, BeatAML 2.0 (Vizome portal, DAR-gated for patient-level). Raises with Vizome URL + Bottomly *Cancer Cell* 2022 PMID 36055236 + Tyner *Nature* 2018 PMID 30333627. TTL 30 days.
10. `src/opl_cancer/integrators/icgc.py` — F5/F6 hybrid, ICGC data portal (DCC public-aggregate + EGA controlled-access for patient-level). Raises with DCC + ARGO + EGA-DAC URLs + PCAWG *Nature* 2020 PMID 32025007. TTL 30 days.
11. `src/opl_cancer/integrators/isrctn.py` — F3, ISRCTN UK trial registry. Real HTML scrape (no auth), 1-day TTL, schema-drift detection raises on parse-zero with non-empty page.
12. `src/opl_cancer/integrators/eu_ctr.py` — F3, EU Clinical Trials Register. Real HTML scrape (no auth), 1-day TTL, schema-drift detection.
13. `src/opl_cancer/integrators/ema_eap.py` — F8, EMA compassionate-use (Regulation 726/2004 Article 83). Real HTML scrape (no auth), 7-day TTL, Member-State-overlay note (AIFA / BfArM / ANSM / AEMPS).
14. `src/opl_cancer/integrators/open_targets.py` — F9, Open Targets Platform GraphQL (no auth). 3 query shapes (target / disease / target_disease), 7-day TTL (Patient #2 E2).

Integrator total: 21 → 28. Family coverage F1/F2/F3/F4/F5/F6/F7/F8/F9 complete. Re-exported from `src/opl_cancer/integrators/__init__.py`; CLI preflight `integrator_modules` list updated.

### New ADR

15. `docs/adr/0007-eval-panel-v1.3.0-followup.md` — documents the 10-patient EVAL panel, the 5 cross-cutting findings, the v1.3.1 fix mapping, and the v1.4 deferred backlog (LM expert / multi-language drilldown / IPD-meta task / hope-impact delivery modality / ack-batch UX / triplet-DDI schema / BRCA-reversion examples in Bert persona / AR-V7 splice-variant assay-source schema in Bert) with trigger conditions + effort estimates per item.

### Bumps

16. `CHANGELOG.md` — this `[1.3.1]` entry.
17. `pyproject.toml` — version 1.3.0 → 1.3.1.
18. `SKILL.md` — `metadata.version` 1.3.0 → 1.3.1 + `version 1.3.1` anchor in H1 paragraph + integrator-count narrative updated 22 → 28.
19. `src/opl_cancer/cli.py` — `VERSION = "1.3.1"` + `status` command reports `Integrators wired: 28` + `Mechanical gates: 22 (G1-G20 + G22 + G23)`.
20. `tests/test_cli.py` — asserts `v1.3.1` + `Mechanical gates: 22`.

## [1.3.0.post1] — 2026-05-25 — Post-10-patient-EVAL hot-fix (main thread)

This entry covers fixes applied **after** the v1.3.0 skill-form re-architecture, in response to a 10-patient EVAL panel run (seed 1-10) covering HCC TACE-refractory, NSCLC EGFR + LM, BRCA1+ TNBC + reversion, MSI-H CRC + irAE hepatitis, HER2+ gastric post-T-DXd, AML R/R IDH1 + triplet, pancreatic KRAS G12C, ovarian HRD+ post-niraparib + BRCA reversion, mCRPC AR-V7 + Lu-177 boundary, melanoma BRAF post-MAPKi + CNS+LM.

### Cross-cutting EVAL findings (consolidated)

1. **Trigger description vernacular gap** — real patients say "TACE 失败 / osimertinib 耐药 / BRCA reversion / 我等不了" not "我有 HCC 想要 AI 分析". Description now expanded with ~40 vernacular trigger phrases.
2. **Cancer-type-aware planner hints** — Step 4 now lists which experts are starting brackets for 10 common scenarios (HCC TACE-refractory → +Riad +Hong; NSCLC LM → +Ted +Jen; ICI irAE rechallenge → Mark lead; HRD+ ovarian → +firefly-genetic-counseling handoff; etc).
3. **G14 dataset-patient-match expanded** — added conditional axes `metastatic_site / cns_involvement / ethnicity / sex / age_bracket` with `_CONDITIONAL_FLOOR=0.4`. Cohort-ethnicity mismatch (e.g. MSK-IMPACT 70%-white projected to Chinese patient) now WARN-surfaces honestly.
4. **G21 quantitative-anchor gate (new)** — Wave-3-evidenced claims must surface HR/OR/RR-with-CI / Cox-β / percentile-projection / median-OS / IC50 / log-rank-χ² etc; founder-mode "real prediction, not labels" promise now mechanically enforced, not aspirational.
5. **intent_parser deepened** — added `PROGNOSIS_QUERY` intent + `speaker_role` (patient / caregiver / unknown) + `hope_impact` (low / moderate / high). High-hope-impact prognostic claims now force L3 ack regardless of base permission level + emit dual-track delivery (patient-paced `pi_delivery.md` + caregiver-detail `caregiver_brief.md`).
6. **models.yaml reviewer-pairing comments fixed** — prior comment "iain: heddy — irAE reviewed by hepatology" was mislabel (Iain = Cochrane meta archetype, Heddy = radiology); now reads "meta-pooled effect sizes reviewed against imaging-response definitions" reflecting actual scope. NEW pairing `vince: iain` added for treatment-line ↔ pooled-evidence cross-review (Patient #4 irAE rechallenge surfaced the need).
7. **knowledge/serious_risks_per_drug.json expanded** — 5 drugs → 25 drugs covering panel scenarios (T-DXd, sacituzumab govitecan, zolbetuximab, cabozantinib, regorafenib, lenvatinib, olaparib, niraparib, amivantamab, tepotinib, sotorasib, adagrasib, venetoclax, gilteritinib, ivosidenib, azacitidine, Lu-177-PSMA-617, encorafenib, binimetinib, ceralasertib, berzosertib, adavosertib, cabazitaxel, abiraterone, enzalutamide). Henry L3 known-serious-risk checklist now fires correctly across the panel — no more `[unknown drug]` UX hole.
8. **scope_handoff_routing task package (new)** — Patient #8 (BRCA2+ mom asks about 36yo daughter cascade testing) showed OPL was silently refusing off-scope asks. New task package emits acknowledgement + in-scope partial anchor + named sibling skill (firefly-genetic-counseling, cancer-buddy-mind, etc) + copy-pasteable invocation phrasing. Founder-mode "I hear you, here's where to go" pattern, not silent refusal.

### Files added / modified

- `SKILL.md` — description expanded (~40 vernacular triggers), Step 4 cancer-type-aware planner hints (10 scenarios with expert brackets + handoff triggers).
- `prompts/pi/intent_parser.md` — full rewrite (PROGNOSIS_QUERY + CAREGIVER + hope_impact + caregiver_brief routing).
- `prompts/tasks/scope_handoff_routing.md` — new D5 task package.
- `models.yaml` — reviewer_pairings comments cleaned; new vince⟂iain pairing.
- `knowledge/serious_risks_per_drug.json` — schema v0.1.0 → v0.2.0 (5 → 25 drugs).
- `src/opl_cancer/validators/gates/g14_dataset_patient_match.py` — conditional axes added.
- `src/opl_cancer/validators/gates/g21_quantitative_anchor.py` — new gate.
- `tests/test_validators/test_g14_dataset_patient_match.py` — 2 new test cases (conditional axis warn + emission-gated pass).

### Deferred to v1.3.1 (batch-fix subagent in flight)

5 new task packages (`boundary_unregulated_channel_disclosure` / `n1_cohort_projection` / `intrathecal_therapy_navigation` / `irae_rechallenge` / `family_cascade_routing`) + 2 new gates (G22 DDR zygosity, G23 PMID recency band for fast-moving topics) + 7 integrator stubs (Hartwig / BeatAML / ICGC / ISRCTN / EU-CTR / EMA-EAP / Open Targets) + ADR-0007 EVAL followup.

## [1.3.0] — 2026-05-25 — Skill-form re-architecture (PRD §0 telos full alignment)

### Headline

OPL is now a true Claude-Code-skill: `npx skills add CancerDAO/opl-cancer-skill` clones into `~/.claude/skills/opl-cancer/`, conversation script in `SKILL.md` drives the patient experience, Python codebase serves as the execution substrate. **No more `pip install + CLI run`** — patient triggers the skill by natural language ("我有 NSCLC,想要 AI team 帮我分析"). All five Waves + Henry audit + Sid delivery rewrite + drill-down are wired through `scripts/cli.py` subcommands the SKILL.md invokes step-by-step.

### Major

- **R1** — `SKILL.md` completely rewritten (~250 lines) as conversational orchestration prompt modelled on `cancerdao-vmtb` blueprint:
  - 11-step dialog (preflight → input → organize → readiness → plan → Wave 1-4 → Henry → render → drill-down)
  - Trigger description optimised for natural-language match (D2/D3 hypothesis + bioinformatics keywords expanded)
  - "When NOT to invoke" section added (emergency, non-patient, undiagnosed → firefly, pediatric → wait for v1.4)
  - `Quick start` removed (no longer command-line driven)
  - Patient data root standardised on `~/CancerDAO/patients/` (env override `OPL_PATIENT_DATA_ROOT`, CLI `--patient-root`)
- **R2** — `scripts/cli.py` shim added so `python ~/.claude/skills/opl-cancer/scripts/cli.py …` works whether the package is pip-installed or only present in the skill directory.
- **R3** — `scripts/install.sh` added — idempotent one-time installer (Python check + editable install + patient root + .env scaffold + preflight verdict).
- **R4** — `.env.example` added covering LLM keys (Anthropic + MiniMax + optional OpenAI tertiary), integrator emails / API keys (NCBI, OncoKB, Unpaywall), compute (`OPL_BIXBENCH_IMAGE`), founder-mode discipline knobs (`OPL_REQUIRE_PMID_ANCHOR=1` etc).
- **R5** — `src/opl_cancer/cli.py` extended with the subcommands SKILL.md invokes per Wave step: `preflight` `readiness` `plan` `wave1`/`wave2`/`wave3`/`wave4` `audit` `render` `withdraw` `reproduce`. Existing `status` `init-patient` `list-experts` `acknowledge` `list-pending-acks` retained. Every command takes `--json` for machine-readable parsing.
- **R6** — `src/opl_cancer/compute/compose.yml` added so Wave 3 can `docker compose run --rm bixbench …` (Dockerfile was already shipped in v0.3.0-p3; compose is the ergonomic wrapper).
- **R7** — `docs/landing/founder_mode_against_cancer.md` rewritten (79 → 177 lines) to fix 10 paradigm-misalignment deviations identified against the PRD:
  D1+D2+D3 three-way Telos restored; PI single-conversational-surface added; Hybrid Lifecycle + Project Memory + 5 Triggers added; real statistical / bioinformatics prediction (HR/OR/RR + CI + Cox + KM + drug ranking with quantified efficacy) clearly stated; PR governance separated from patient-side L3/L4 ack; physicians moved from "service target" to "drill-down audience"; install repointed to `npx skills add`; 11-bucket names corrected; DISCLAIMER / governance paths fixed; archetype-not-impersonation wording softened.
- **R8** — `references/` directory added with 8 offloaded reference docs (architecture / wave-lifecycle / expert-roster / integrator-catalog / mechanical-gates / permission-levels / founder-mode-philosophy / troubleshooting) so `SKILL.md` stays under 500 lines while deep readers can navigate.

### Task packages (D2 + D4 + D5 completion)

- **T1** — `prompts/tasks/drug_repurposing.md` added (D2, Co-Sci Evolution 6 strategies, expert portfolio: Aviv + Iain + Bert; preferred integrators F4 Genomics Knowledge + F1 Literature + F7 Cell/Drug).
- **T2** — `prompts/tasks/literature_synthesis.md` added (D2, PaperQA2 anti-hallucination RAG, expert portfolio: Iain + Aviv; preferred integrators F1).
- **T3** — `prompts/tasks/staging_workup.md` added (D1, TNM/AJCC + restaging recommendations, expert portfolio: Vince + Rosa + Heddy).
- **T4** — `prompts/tasks/china_rwe_adjustment.md` added (D1, China RWE bias correction against NCCN, expert portfolio: Vince + Hong).
- **T5** — `prompts/tasks/source_verification.md` added (D4 reviewer subtask, PMID online verify + quote match).
- **T6** — `prompts/tasks/claim_audit.md` added (D4 reviewer subtask, claim-evidence consistency + numerical-hallucination detection).
- **T7** — `prompts/tasks/cross_source_consistency.md` added (D4 reviewer subtask, NCCN-vs-CSCO-vs-NCI-PDQ + OncoKB-vs-CIViC level disagreements).
- **T8** — `prompts/tasks/patient_brief_rendering.md` added (D5 PI task, three-tier labels + PMID anchor + provenance hash + risk-disclosure-card pin + model-disagreement table + G7 imperative-detector pre-write).
- **T9** — `prompts/tasks/pi_delivery.md` added (D5 PI task, conversational rewrite — "team 跑了 X,发现 Y,Reviewer 在 Z 上分歧").

Total task packages: 22 → 31. (PRD §2.4 v0 estimate ~34; remaining 3 are pure-PI-internal helpers that live in `prompts/pi/`.)

### Mechanical gates (G1-G20 completion)

- **G4** `g4_dose_unit_declared.py` — dose without explicit unit (mg/mcg/mg·kg⁻¹/m²/IU) + frequency (qd/bid/tid/q3w/q21d) → BLOCK. Failure mode A4.
- **G5** `g5_patient_context_isolation.py` — claim.patient_code != run.patient_code → raise `CrossPatientContaminationError`. Failure modes B1, B3.
- **G6** `g6_injection_scan.py` — prompt-injection scanner over raw patient input. Failure mode B2.
- **G8** `g8_level34_disclosure.py` — Level-3/4 claim without risk-disclosure-card → BLOCK pre-render. Failure mode C2.
- **G10** `g10_guideline_version.py` — NCCN/CSCO/ESMO citation without version + date OR > 12 months stale → reviewer flag. Failure mode D2.
- **G12** `g12_memory_overflow.py` — Memory context > 80% window → trigger pruning, never silent truncate. Failure mode A6.
- **G13** `g13_reviewer_model_distinct.py` — Reviewer model == Executor model → BLOCK. Per `models.yaml.reviewer_pairings`. Failure mode E6.
- **G14** `g14_dataset_patient_match.py` — `dataset_acquisition` `match_score` < 0.6 (cancer / stage / platform / N) → reviewer reselect. Failure mode F1.
- **G15** `g15_multiple_testing_correction.py` — bioinformatics notebook missing BH / Bonferroni / FDR cell → BLOCK. Failure mode F2.
- **G16** `g16_batch_effect_declared.py` — bioinformatics task missing batch variable declaration → BLOCK. Failure mode F3.
- **G17** `g17_meta_i2_policy.py` — meta_analysis I² > 50% must use random-effects; I² > 75% must tag "high heterogeneity, pooling suspect". Failure mode F4.
- **G18** `g18_meta_search_strategy.py` — meta_analysis missing search strategy + PRISMA flow → BLOCK. Failure mode F5.
- **G19** `g19_pi_imperative_detector.py` — PI prose with imperatives ("you should") → rewrite as options. Failure mode PI-C1.
- **G20** `g20_pi_disagreement_surfacing.py` — Reviewer disagreement > 0.4 AND PI delivery lacks "team 内部分歧" marker → BLOCK render. Failure mode PI-C3.

Total mechanical gates: 6 → 20 (full PRD §7 coverage).

### Bumps

- `pyproject.toml` 1.2.0 → 1.3.0
- `SKILL.md` `metadata.version` 1.2.0 → 1.3.0
- `README.md` install section repointed to `npx skills add`

### Tests

- 10-patient subagent panel scaffolded under `tests/test_e2e/panel/` (HCC TACE-refractory · NSCLC EGFR post-osimertinib · BRCA TNBC · MSI-H CRC · HER2+ gastric · AML R/R IDH1 · pancreatic KRAS G12C · ovarian HRD+ post-platinum · prostate AR-V7 · melanoma BRAF V600E post-MAPKi). See `tools/run_quad_evaluation.py` for invocation.

### Deferred to v1.4+

- guardian-mode (PRD §15 G4) for pediatric / cognitive impairment / language barrier cases.
- web-wrapper (PRD §17.4) for non-CLI patients.
- multi-language PI persona beyond zh-CN + en (PRD §17.4).
- federated cross-patient learning protocol (PRD §15 G5).
- cloud Jupyter alternative to local Docker for Wave 3 (PRD §15 G1).

## [1.2.0] — 2026-05-24 — Audit-fix release

### CRITICAL (patient-safety / legal)

- **C1**: Mark inspiration corrected — "Mark Stelfox" was not a verifiable real-person archetype → `Composite archetype (ASCO + ESMO ICI irAE consensus methodology)`. Updated README, roster, mark.py docstring, mark/persona.md with "Not a real-person impersonation" disclaimer.
- **C2**: Steve inspiration corrected — `Stephen Heber` → `David Heber (UCLA Center for Human Nutrition founder)`. Updated README, roster, steve.py, steve/persona.md.
- **C3**: `SKILL.md` + `cli.py status` rewritten — drop "P0 Skeleton" fiction; list real v1.x capabilities; SKILL `description:` tightened for trigger-match accuracy; removed `docs/superpowers/plans/` reference per global memory rule.
- **C4**: Mark persona + ici_endocrine_irae task — `ASCO 2021 / ESMO 2022` replaced with runtime-verified consensus language.
- **C5**: Kieren persona + neutropenic_fever_management task — `IDSA 2018` replaced with runtime-verified consensus language.
- **C6**: Empty-integrator rule appended to all 15 task packages that consume integrator outputs.
- **C7**: `DISCLAIMER.md` repo URLs corrected — `opl-for-cancer/issues` → `opl-cancer-skill/issues`.

### IMPORTANT

- **I1**: All 18 personas got explicit `## Identity attribution (v1.2.0)` section with 2026-accurate real-person methodological lineage + legal disclaimer.
- **I2**: Hard-coded NCCN edition refs stripped from task packages — replaced with runtime-verified language.
- **I3**: 10 personas got `## Founder-mode discipline (v1.2.0)` section: dennis, frances, jen, kieren, mark, mary, riad, steve, ted, tyler.
- **I4**: 8 high-risk experts got `## Mandatory disclosure (high-risk / L4 boundary)` section: frances, dennis, vince, mary, ted, riad, jen, mark.
- **I5**: Created PI prompts (`prompts/pi/persona.md` + `delivery.md` + `drilldown.md` + `proactive_push.md`) — framework stubs per budget.
- **I6**: Created Auditor prompts (`prompts/auditor/l1_mechanical_gates.md` + `l2_disagreement_summariser.md` + `l3_permission_gate.md` + `l4_rollback.md`) — framework stubs.
- **I7**: SKILL.md `description:` optimised — addressed in C3.
- **I8**: Skill-form wrappers under `scripts/`: `list_experts.sh`, `status.sh`, `init_patient.sh`, `acknowledge.sh`, `run_wave1.sh`.
- **I9**: `trial_matching.md` — added `isrctn_results` input with gap note.

### Docs

- ADR `docs/adr/0006-audit-fixes-v1.2.0.md` — full audit + decision record.
- `pyproject.toml` 1.1.0 → 1.2.0; `README.md` status block reflects v1.2.0.

### Deferred to v1.3+

- Deepen PI + Auditor prompt content (currently framework stubs).
- Migrate inline L2 prompt from `validators/henry.py` to file-load.
- Wire ISRCTN integrator implementation.

## [1.1.0] — 2026-05-24 — Iter 20 (final v1.x release)

Comprehensive aggregation of the v1.x iteration series. Roster complete
(18/18 experts), **iterations completed: 20**, 781 tests + 3 env-gated live,
mypy --strict on touched files + ruff clean across all 20 iters.

### Highlights across v1.0.1 → v1.1.0

- **Per-task routing (v1.0.5)** — `ModelRouter.client_for_task()` selects
  executor by task package (Opus for deep reasoning / code; MiniMax-M2.7
  for literature synthesis). Driven by `models.yaml.per_task_routing`.
- **Observability (v1.0.6, v1.0.9)** — `tools/observe.py` aggregator;
  `Wave1Runner.run` emits `triggers/<run_id>/run_metadata.json` with the
  required schema (`run_id`, `token_cost`, `wall_time_seconds`,
  `claims_produced`, `claims_withdrawn`, `reviewer_fail_rate`,
  `mechanical_gate_blocks`).
- **Configurable integrator TTL (v1.0.7, v1.0.10)** — instance and class
  overrides + lazy `_load_models_yaml_ttls()` so `Integrator.__init__`
  reads family defaults from `models.yaml.integrator_ttl_seconds`
  (`family_config_key`). NCCN wired to 30-day TTL through this path.
- **Legal / safety surface (v1.0.8)** — `DISCLAIMER.md` v1.x release scope
  + emergency contacts (120 / 911 / 112) + jurisdictional notice
  (FDA/NMPA/EMA/CE/PMDA/MHRA/TGA/Health Canada).
- **Cross-patient isolation red-team (v1.0.11)** — Wave1Runner asserts
  patient_code consistency in expert outputs and raises
  `CrossPatientContaminationError` on any mismatch (top-level or nested
  in a claim record). New `tests/test_safety/` test suite.

### Version bumps

- `pyproject.toml`: `1.0.2` → `1.1.0`
- README status block: `v1.0.8` → `v1.1.0`, iterations completed: 20.

### Stats

- 781 tests + 3 env-gated live (was 774 at start of v1.1.0 series).
- ruff clean; mypy --strict clean on touched files.

## [1.0.11] — 2026-05-24 — Iter 19 (cross-patient isolation red-team)

### Added — `src/opl_cancer/glue/wave1_runner.py`
- New `CrossPatientContaminationError` (RuntimeError subclass).
- `Wave1Runner._collect_claims` now invokes `_assert_patient_isolation`
  per task. If an expert output declares (top-level or per-claim) a
  `patient_code` that differs from the current run's patient, the runner
  raises immediately — no silent context bleed.

### Tests — `tests/test_safety/test_cross_patient_isolation.py` (new)
- `test_runs_on_patient_a_never_contain_patient_b`: 2-patient red-team
  scenario; verifies brief.html/.md + provenance.jsonl never mention the
  other case's `patient_code`.
- `test_mismatched_patient_code_raises`: poisoned top-level patient_code
  in expert output → CrossPatientContaminationError.
- `test_mismatched_patient_code_inside_claim_raises`: poisoned nested
  patient_code → CrossPatientContaminationError.

### Stats
- 781 tests pass (was 778, +3). ruff clean, mypy --strict clean.

## [1.0.10] — 2026-05-24 — Iter 18 (integrator_ttl_seconds from models.yaml)

### Added — `src/opl_cancer/integrators/base.py`
- `Integrator` gained `family_config_key: ClassVar[str | None]` and a lazy
  classmethod `_load_models_yaml_ttls()` that reads the repo-root
  `models.yaml`'s `integrator_ttl_seconds` block once per process.
- `Integrator.__init__` now resolves `self.ttl_seconds` from
  `models.yaml.integrator_ttl_seconds[<family_config_key>]` when the subclass
  declares one. Class-level default is preserved for fallback.

### Added — `src/opl_cancer/integrators/nccn.py`
- `NCCNPageIndexIntegrator.family_config_key = "nccn"` — NCCN now sources its
  30-day TTL from `models.yaml`.

### Tests
- `tests/test_integrators/test_ttl_config.py::test_nccn_integrator_reads_ttl_from_models_yaml`
  (new): asserts NCCN integrator reads 30-day TTL from models.yaml.

### Stats
- 778 tests pass (was 777, +1). ruff clean, mypy --strict clean.

## [1.0.9] — 2026-05-24 — Iter 17 (run_metadata.json emission)

### Added — `src/opl_cancer/glue/wave1_runner.py`
- `Wave1Runner.run` now emits `triggers/<run_id>/run_metadata.json` with the
  required schema: `run_id`, `token_cost` (placeholder 0), `wall_time_seconds`,
  `claims_produced`, `claims_withdrawn` (placeholder 0), `reviewer_fail_rate`
  (placeholder 0.0), `mechanical_gate_blocks`.
- `mechanical_gate_blocks` counted by scanning rendered claims for the
  `[BLOCKED by ...]` prefix produced by failed mechanical gates.

### Tests
- `tests/test_glue/test_wave1_runner.py::test_wave1_runner_emits_run_metadata`
  (new): asserts the file exists with all 7 keys and consistent run_id.

### Stats
- 777 tests pass (was 776, +1). ruff clean, mypy --strict clean.

## [1.0.8] — 2026-05-24 — Iter 16 (DISCLAIMER + README polish)

### Changed — DISCLAIMER.md
- Added explicit **v1.x release scope** notice: `WITHOUT WARRANTY OF ANY KIND`,
  not validated for clinical decision-making, not for oncologic emergencies.
- Added **emergency-contact** paragraph: 120 (CN), 911 (US/CA), 999 (UK),
  112 (EU). Software cannot triage emergencies and must never substitute.
- Added **jurisdictional notice** enumerating all unregistered regulators
  (FDA / NMPA / EMA / CE / PMDA / MHRA / TGA / Health Canada / IRBs) and
  declaring no doctor-patient relationship.

### Changed — README.md
- Refreshed `## Status` block to v1.0.8 (was stale at v1.0.2); 774 tests.
- Added `## Roadmap` section listing v1.1+ themes: full BioLinkX
  integration, additional cancer types, web UI, multi-language briefs,
  ongoing integrator breadth.

### Tests
- **`tests/test_readme.py`** — added `test_readme_has_roadmap_section`
  (asserts the 4 themes are present) and
  `test_disclaimer_has_v1_release_and_emergency_notice` (asserts v1.x,
  120, 911, WITHOUT WARRANTY, Jurisdictional notice).

### Stats
- 776 tests pass (was 774, +2). ruff clean, mypy --strict clean.

## [1.0.7] — 2026-05-24 — Iter 15 (Configurable integrator TTL)

### Added
- **`Integrator.default_ttl_seconds_overrides: ClassVar[dict[str, int]]`**
  — class-level per-key TTL override map.
- **`Integrator(ttl_seconds_overrides=...)`** ctor arg — instance-level
  per-key TTL override map.
- **`Integrator.resolve_ttl(key)`** — instance > class > default precedence.
- **`models.yaml.integrator_ttl_seconds`** — declared family TTL defaults:
  `nccn=30d`, `pubmed=7d`, `clinicaltrials=1d`, `civic=7d`, `oncokb=7d`,
  `fda_eap=7d`.
- `cached_fetch` now calls `resolve_ttl(key)` instead of using static
  `self.ttl_seconds` directly.

### Tests
- **`tests/test_integrators/test_ttl_config.py`** — 3 tests (precedence,
  models.yaml carrying family defaults, cached_fetch using resolved TTL).

### Stats
- 774 tests pass (was 771, +3). ruff clean, mypy --strict clean.

## [1.0.6] — 2026-05-24 — Iter 14 (tools/observe.py)

### Added
- **`tools/observe.py`** — trigger-run observability aggregator per spec §10.
  Scans `--root` recursively for `run_metadata.json` files; emits JSON
  aggregate + Markdown report (stdout or `--out-json` / `--out-md`).
- Metrics tracked: `token_cost`, `wall_time_seconds`, `claims_produced`,
  `claims_withdrawn`, `reviewer_fail_rate`, `mechanical_gate_blocks`.
- Runs with missing keys surface in `skipped[]` with reason
  (memory:feedback_no_false_completion — transparent accounting).

### Tests
- **`tests/test_tools/test_observe.py`** — 3 tests (sum+mean aggregation,
  skip on missing keys, Markdown rendering) using fake trigger dirs in
  `tmp_path`.

### Stats
- 771 tests pass (was 768, +3). ruff clean, mypy --strict clean.

## [1.0.5] — 2026-05-24 — Iter 13 (Per-task model routing)

### Added
- **`ModelRouter.client_for_task(task_package)`** — spec §17.5 P2 per-task
  routing. Falls back to default executor model when task is unmapped.
- **`models.yaml.per_task_routing`** — 4 task packages declared:
  - `bioinformatics_data_analysis` → `claude-opus-4-7` (code reasoning)
  - `literature_synthesis` → `minimax-m2-7` (cheaper, sufficient)
  - `hypothesis_generation` → `claude-opus-4-7` (deep reasoning)
  - `meta_analysis` → `claude-opus-4-7`
- **`ModelRouter.model_id_for_task(task_package)`** — pure-lookup helper.

### Tests
- **`tests/test_llm/test_router_per_task.py`** — 4 tests: literature →
  MiniMax, hypothesis → Opus, unknown → executor fallback, unknown target
  raises.

### Stats
- 768 tests pass (was 764, +4). ruff clean, mypy --strict clean.

## [1.0.4] — 2026-05-24 — Iter 12 (4 new synthetic patients + edge cases)

### Added — golden_set/synthetic_patients
- **`anon_pancreatic_001`** — BRCA2 5946delT germline mPDAC post-FOLFIRINOX/Gem-nabP
  PD; KRAS G12D somatic; HRD-high. Profile + readiness + case_text + timeline
  + NGS + pathology.
- **`anon_gbm_001`** — IDH-wildtype, MGMT-methylated, TERT C228T newly-diagnosed
  GBM, gross-total resection, Stupp planning. Full canonical set.
- **`anon_ped_all_001`** — 8yo F Philadelphia+ B-ALL, induction failure Day33
  MRD 8%, T315I emergence. Declares guardian_consent + pediatric depth
  preferences (memory:feedback_no_false_completion — pediatric safeguards).
- **`anon_myeloma_001`** — 64yo M high-risk MM, t(4;14)+del(17p), R-ISS III,
  early biochemical relapse post-VRd/auto-HSCT/maintenance.

### Edge cases covered
- Pediatric guardian-consent + age-appropriate assent declared.
- Germline BRCA2 placed in `comorbidities` for HRD-aware planning.
- High-risk cytogenetics surfaced in `diagnosis.risk_category` + `molecular`.

### Tests
- **`tests/test_golden_set/test_iter12_new_patients.py`** — 25 tests covering
  directory presence, canonical file presence, profile schema, readiness gate,
  ≥2-bucket requirement (NGS+pathology), pediatric safeguards, BRCA germline
  documentation, high-risk cytogenetics, real-name pattern scan, SYNTHETIC
  marker.
- **`tests/test_e2e/test_wave1_e2e.py`** — extended parametrize to all
  **8 patients** (HCC/NSCLC/CRC/BRCA + pancreatic/GBM/ped-ALL/myeloma) with
  canned LLM responses. memory:feedback_multi_case_validation satisfied:
  ≥2 cancer types, ≥2 patients per axis, 4 new histologies.

### Tests total
- 764 passed, 3 skipped. +41 over v1.0.3.

## [1.0.3] — 2026-05-24 — Iter 11 (Quad Independent Evaluator tool)

### Added
- **`tools/run_quad_evaluation.py`** — generates 4 evaluator prompts
  (architecture / safety / code_quality / ux) + JSON result schema for parallel
  third-party subagent dispatch (memory:feedback_review_via_parallel_subagents,
  memory:feedback_third_party_lens). CLI: `--out evaluator_workspace/`
  optionally `--dimension <one>`.
- **`tools/aggregate_evaluator_verdicts.py`** — validates 4 JSON verdicts,
  computes overall verdict (any-fail-dominates, missing-counts-as-conditional)
  + mean score, writes `evaluator_report.html`.
- **`tests/test_tools/test_quad_evaluator.py`** — 13 tests: dimension parity,
  prompt rejection of paternalistic language, schema shape, aggregation rules
  (all-pass / any-fail / conditional / missing), HTML render, end-to-end run,
  bad-verdict rejection, missing-dir handling.

### Notes
- Tool does NOT itself dispatch subagents — operator (or main-thread Claude)
  hands each prompt to an independent evaluator. Keeps CI deterministic.
- mypy --strict + ruff clean on both tools.

### Tests
- 723 passed, 3 skipped (live, env-gated). +13 over v1.0.2.

## [1.0.2] — 2026-05-24 — Iter 10 patch (MiniMax live integration)

### Added
- **`tests/test_integration/test_minimax_live.py`** — live integration tests
  for MiniMax-M2.7 (api.minimaxi.com/v1/chat/completions). Marked `live`,
  skipped by default; runs when `MINIMAX_API_KEY` env var is set. Validates:
  - Endpoint reachable + 200 status
  - LLMResponse parses cleanly (Pydantic)
  - `response_format={"type": "json_object"}` honoured
  - errcode 2056 surfaces as typed `LLMQuotaError`
  - max_tokens=96000 ceiling accepted (per memory:reference_minimax_llm)
- **`tests/test_integration/test_minimax_live_meta.py`** — meta-tests (run
  unconditionally) verifying live test module imports, `live` marker
  registered in pyproject, verify script syntactically valid, skipif
  scaffolding correct.
- **`scripts/verify_minimax_setup.py`** — manual CLI checks: env present,
  endpoint reachable, json_object completion + parse. Exit codes
  (0/1/2/3/4) for env/transport/parse/quota outcomes.
- **`pyproject.toml`** — declared `live` pytest marker.

### Deferred
- **E2E live variant** (`tests/test_e2e/test_wave1_minimax_live.py`) running
  full Wave1Runner with MiniMax as Reviewer — deferred. Requires real
  MiniMax key + paid budget; not safe to enable by default. Manual operator
  run via `scripts/verify_minimax_setup.py` covers the per-call validation.

### Tests
- 710 passed, 3 skipped (live, env-gated). Full suite green.

## [1.0.1] — 2026-05-24 — Iter 9 patch

### Added — P6 deferred items closed
- **Routing-matrix golden test** (`tests/test_experts/test_routing_matrix.py`):
  26 tests covering 18-expert × task_package portfolio + 4-cancer candidate
  coverage (HCC/NSCLC/CRC/BRCA). Documents intentional `hypothesis_validation`
  overlap (aviv in-silico vs tyler wet-lab) via `SHARED_PACKAGES` registry.
- **Henry L2 LLM disagreement summariser** (`HenryAuditor.summarise_disagreement_axes`):
  async, env-gated, accepts any `LLMClient`; returns
  `{"axes": [...], "summary": "..."}`. Defensive against malformed LLM output
  (non-list axes coerced to `[]`). `response_format={"type": "json_object"}`
  honoured per memory:reference_minimax_llm. memory:feedback_no_offline_only —
  raises on network failure, no silent rule-based fallback when caller invokes
  LLM path.
- **`ProjectMemoryStore.acknowledge_insight()`** —
  propagates `patient_acknowledged_at` into `InsightCard` (schema already had
  field). Raises `KeyError` on missing card; preserves all other fields.

### Tests
- 706 total (was 674) → **+32 new tests**
- All `mypy --strict` + `ruff` clean on touched files
- Full suite `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/ -q` green

### Deferred to a later iter (honest scope)
- **Wave1Runner per-claim L3/L4 card emission rewire** — current runner only
  emits L3 placeholder cards via gate-block path; full Henry-driven per-claim
  card emission inside `_collect_claims` remains. (Iter 9 task #1)
- Iter 10 (MiniMax live integration), Iter 11 (quad-evaluator dispatch tool),
  Iter 12 (4 additional cancer patients + edge cases) — deferred to next
  session per context-budget.

## [1.0.0-p6] — 2026-05-24 — v1.0.0 Release

### Added — Multi-case E2E + Legal + Open-Source Polish

- **Multi-case Wave1 E2E** (`tests/test_e2e/test_wave1_e2e.py`):
  - Parametrise list expanded from 2 → **4 cancer types** —
    HCC (CTNNB1 S37F), NSCLC (EGFR C797S in cis L858R), CRC (KRAS G12D
    post-anti-EGFR), BRCA (HER2+ post-T-DM1)
  - All LLM + integrator calls mocked; each patient produces
    `patient_brief.html` + `provenance.jsonl` with sha256 hashes + three-tier
    label + no command-form leakage
  - Satisfies `memory:feedback_multi_case_validation` — ≥2 cancer types
    cross-sample validation matrix
- **`NOTICE`** (root) — Apache-2.0 attribution + third-party model card
  acknowledgements (Claude/Anthropic, MiniMax) + public data source citations
  (PubMed, ClinicalTrials.gov, ChiCTR, NCCN, OpenFDA, CIViC) per spec §17.6
- **`DISCLAIMER.md`** (root) — explicit "not clinical decision support, not
  doctor substitute, patient sole decision authority" per spec §17.6, with
  safety reporting pathway (GitHub Issues, 72-hour response)
- **`tools/sign_contributor_agreement.py`** — first-time contributor signing
  flow per spec §16; writes `governance/contributors/<handle>.json` with
  SHA-256 of agreement text, ISO-8601 UTC timestamp; supports `--dry-run` and
  `--force`; idempotent (raises `FileExistsError` without `--force`)
- **`docs/landing/founder_mode_against_cancer.md`** — landing copy ready for
  cancerdao-global homepage integration; covers 为什么造这个 / 与你一起做的事 /
  谁能用 / 怎么开始 / 如何贡献 / 安全与边界 / 我们相信什么
- **P6 acceptance suite** (`tests/test_p6_acceptance.py`) — enumerates the
  v1.0.0 release gates: NOTICE + DISCLAIMER content, signing-tool dry-run +
  persistence + idempotency, landing copy, 4-cancer-type parametrisation,
  18-expert roster integrity, golden_set 4-patient coverage, pyproject and
  CHANGELOG version bumps

### Changed — Versioning

- `pyproject.toml` `version` → **`1.0.0`** (was `0.0.1`)
- `README.md` status block → v1.0.0

### Deferred to v1.x patch series (P5 carry-over not blocking v1.0.0)

- Wave1Runner per-claim Henry risk-card emission rewire (basics live; full
  L2 disagreement-summariser Claude-call gated by env)
- 15-expert routing-matrix golden test (canned data per task package needed)
- Henry L2 LLM disagreement summariser (Claude-call gated by env)
- `patient_acknowledged_at` propagation to `InsightCard` schema

## [v0.5.0-p5] — 2026-05-24

### Added — Validation Stack

- **Henry 4-layer IRB-substitute auditor** (`src/opl_cancer/validators/henry.py`):
  - L1 forced risk-disclosure-card emission for any L3/L4 claim (spec §8.L1)
  - L2 model-disagreement surfacing from reviewer challenges (rule-based; LLM
    summariser deferred to P6)
  - L3 forced known-serious-risk checklist reading
    `knowledge/serious_risks_per_drug.json`; unknown drugs surface as explicit
    `[unknown drug: ...]` warnings (fail-closed per spec §7 G11 spirit)
  - L4 patient acknowledgment loop — writes pending acks to
    `outstanding/<card_id>.json` with ISO-timestamp `patient_acknowledged_at`
    field; `HenryAuditor.acknowledge()` + `list_pending()` helpers
- **Risk-disclosure-card model + renderer** (`src/opl_cancer/delivery/risk_card.py`):
  - Pydantic v2 `RiskDisclosureCard` with fail-closed cross-field validator
    (must declare ≥1 `known_serious_risks` OR `epistemic_gaps`)
  - HTML-safe rendering (escapes `<script>`, `&`, etc) + Markdown renderer
  - `content_hash()` for provenance integrity (excludes ack/created timestamps)
- **Serious-risks knowledge catalogue** (`knowledge/serious_risks_per_drug.json`):
  - 5 drugs stubbed (atezolizumab / bevacizumab / osimertinib / pembrolizumab /
    trastuzumab) with INN + class + ≥2 known serious risks each
- **CLI ack loop** — two new subcommands in `opl-cancer`:
  - `opl-cancer acknowledge <card_id>` — patient marks a pending card
    acknowledged with UTC-ISO timestamp
  - `opl-cancer list-pending-acks` — lists awaiting cards (level + claim preview)

### Added — Reviewer pairings (spec §2.2 rotation)

- `models.yaml.reviewer_pairings` populated for all 18 roster experts:
  - Genomics ↔ Pharmacology: bert↔aviv
  - Bioinformatics ↔ Pharmacology: mary↔tyler
  - Clinical ↔ Trial matching: rosa↔rick
  - Toxicity ↔ Clinical: iain↔heddy
  - Translational ↔ Mechanism: ted→aviv, vince→aviv, hong→bert
  - Supportive ↔ Clinical: jen→rosa, kieren→rosa, mark→iain
  - EAP ↔ Cross-border: frances↔dennis
  - Specialised: riad→ted, steve→tyler
- Acceptance: ≥15 pairings populated; no self-review; all reviewers in roster.

### Added — Operator tools (`tools/`)

- **`tools/reproduce.py`** — given `<patient_dir> <run_id>`, loads the
  per-run provenance.jsonl and verifies recipe is reproducible
  (prompt_versions pinned + claim_hashes present + models recorded). Exits 0 on
  reproducible, 2 on missing artifact / gap.
- **`tools/verify_provenance.py`** — recomputes the sha256 of every entry's
  hashable payload and compares against stored `claim_hash` / `content_hash`.
  Reports `matches`, `mismatches`, `no_hash`. Exits 0 on all-match, 1 on any
  mismatch.

### Added — Golden set expansion (`validators/golden_set/`)

- **+2 synthetic patients** (now 4 distinct cancer types):
  - `anon_crc_001` — colorectal MSS KRAS-G12D, post-FOLFIRI+cetuximab PD
  - `anon_brca_001` — breast HER2+ post-T-DM1 recurrence
- **+5 failure-mode inputs** (now 8 total, ≥6 distinct gates exercised):
  - `drug_name_confusion_input.json` (G3)
  - `dose_unit_input.json` (G4)
  - `batch_effect_input.json` (G15)
  - `cherry_pick_input.json` (G16)
  - `retraction_cascade_input.json` (G9 cascade)
- **New `regression_anchors/`** (≥2 anchors):
  - `cf_pici_co_sci.json` — Co-Sci tournament anchor
  - `ripasudil_robin.json` — Robin drug-repurposing anchor
- **New `boundary_cases/`** (≥3 cases):
  - `empty_ngs.json`, `fifty_plus_files.json`, `contradicting_reports.json`

### Closed — P4.5 deferred items

- **RxNorm → Mary** integrator-dict wiring verified via constructor contract
- **NMPA + FDA EAP → Frances** wiring verified
- **CT.gov + ChiCTR → Dennis + Rick** wiring verified
- All four contract tests in `tests/test_p5_integrator_wiring.py`

### Tests

- **+160 tests** in 4 new files (501 → 661):
  - `tests/test_p5_acceptance.py` (33 — top-level acceptance)
  - `tests/test_p5_golden_set_per_file.py` (49 — per-fixture parametrised)
  - `tests/test_p5_henry_deep.py` (71 — per-drug + per-pairing parametrised)
  - `tests/test_p5_integrator_wiring.py` (7 — async integrator routing)

### Deferred (honest)

- **LLM-backed Henry L2 disagreement summariser** — currently rule-based
  pass-through of reviewer challenges. P6 will add a Claude-summarised
  disagreement-axis renderer.
- **Wave1Runner.run integration of risk_card emission** — Henry can be called
  per-claim, but Wave1Runner does not yet auto-emit risk cards into the brief
  HTML output. P6.
- **15-expert routing-matrix golden test across HCC + NSCLC** — partial; only
  smoke-imports validated. Full routing matrix deferred to P6 wave-runner
  integration work.
- **`patient_acknowledged_at` propagation to memory store schemas** — currently
  written only to `outstanding/` JSON. Memory-store schema field deferred to P6.

### Acceptance criteria met

- 661 tests passing (target ≥600 exceeded by 61).
- `ruff check src tests tools` clean.
- All 4 P5 task buckets (T1-T9) shipped to production-grade.
- memory:feedback_no_offline_only — Henry refuses to construct without serious-
  risks catalogue (fail-loud on missing knowledge).
- memory:feedback_no_false_completion — deferred items above explicitly listed.

## [v0.4.5-p4.5] — 2026-05-24

### Added

- **Expert Batch E — 3 deferred experts shipped** (Kieren / Mark / Dennis):
  - `KierenExpert` (Infectious Disease, Kieren Marr archetype) — portfolio `neutropenic_fever_management`; families F1/F8. Demands MASCC score + IDSA empiric regimen + pseudomonal-coverage invariant + fungal escalation trigger.
  - `MarkExpert` (Endocrinologist irAE) — portfolio `ici_endocrine_irae`; family F1. Demands CTCAE grade + adrenal-axis safety check before T4 replacement + ASCO 2021 / ESMO 2022 anchored steroid algorithm.
  - `DennisExpert` (Cross-Border Coordinator, Dennis Lo 卢煜明 archetype) — portfolio `cross_border_navigation`; families F3/F8. Mandatory L4 boundary disclosure (founder-mode discipline) + cost_model + visa_pathway_url; refuses "guaranteed" framing.

- **3 new persona files** under `prompts/experts/{kieren,mark,dennis}/persona.md` — each with three-tier discipline + Anti-patterns + non-imperative output rules.

- **3 new task prompt files** under `prompts/tasks/`:
  - `neutropenic_fever_management.md` — MASCC + IDSA + pseudomonal + fungal escalation invariants
  - `ici_endocrine_irae.md` — CTCAE grade + adrenal_axis_checked + ici_hold_decision
  - `cross_border_navigation.md` — jurisdiction + cost_model + visa_pathway + L4 disclosure mandatory non-empty

- **`Wave4Runner` hypothesis-validation orchestrator** (`src/opl_cancer/glue/wave4_runner.py`):
  - Mirrors Wave3Runner pattern: Aviv leads data-anchored verdict, Iain meta-validates (Cochrane lens)
  - Classifies each top-K hypothesis as `validated` / `falsified` / `inconclusive`
  - Writes `triggers/<run_id>/wave4_validation.json` + provenance.jsonl (≥2 stages per hypothesis)
  - Main-thread sequential awaits per ADR-2026-04-22

- **`G7ImperativeDetectorGate`** (`src/opl_cancer/validators/gates/g7_imperative_detector.py`):
  - failure_mode_code `C1` — scans recursive walk of all string fields for imperative patterns
  - Detects EN ("you should/must", "must give/start/take/stop", "start immediately") + ZH ("应该", "必须", "建议立即", "立即停用", "立即开始")
  - PASS only if sentence has both PMID/NCT/URL evidence AND a risk caveat keyword ("may"/"risk"/"side effect"/"可能"/"副作用"/"风险"); otherwise FAIL+block=True
  - Catches nested fields like `symptom_plan[].intervention`

- **36 new tests** (501 total, up from 465):
  - `tests/test_experts/test_batch_e.py` — 18 tests (portfolio + persona + L4 boundary on Dennis + adrenal-axis on Mark + MASCC on Kieren + 18-expert roster completeness)
  - `tests/test_validators/test_g7_imperative_detector.py` — 8 tests (clean pass / EN imperative fail / ZH imperative fail / imperative+evidence+risk pass / imperative+evidence-no-risk fail / nested symptom_plan / NCT pass / failure_mode_code = C1)
  - `tests/test_e2e/test_wave4_runner.py` — 4 tests (validated / falsified / inconclusive / artifacts written)
  - `tests/test_p4_5_acceptance.py` — 6 tests (roster=18 / modules importable / G7 wired / Wave4Runner wired / 3 task prompts present / 3 personas present)

### Roster status
- v0 roster now complete: **18/18 experts** wired with portfolios + personas + task templates.

### Deferred to P5 (explicit)
- F10 RxNorm wiring to Mary integrator dict (currently a fake integrator in tests).
- Frances→NMPA+FDA EAP integrator wire (currently fake).
- 15-expert routing matrix golden test across HCC + NSCLC patients (P5 router benchmark).
- BixbenchRunner live-mode (P3 shipped dry-run + env-gated live).

### Acceptance
- 501 pytest passing (PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, ~2.2s wall-time, all LLM + HTTP mocked).
- `mypy --strict src/opl_cancer` — clean (95 source files).
- `ruff check src/ tests/` — clean.
- Tag `v0.4.5-p4.5`.

## [v0.4.0-p4] — 2026-05-24

### Added

- **Expert Batch D — 6 of 9 shipped** (Mary / Ted / Riad / Jen / Frances / Steve):
  - `MaryExpert` (Pharmacologist, Mary Relling archetype) — portfolio `ddi_adme_dosing`; families F1/F10. Demands RxNorm `rxcui` + TPMT/DPYD/UGT1A1 phenotype surfacing.
  - `TedExpert` (Radiation Oncologist, Theodore Lawrence archetype) — portfolio `radiation_planning`; families F1/F2. Demands BED10 + OAR constraint table + QUANTEC/TG-101 anchoring.
  - `RiadExpert` (Interventional Oncologist, Riad Salem archetype) — portfolio `interventional_oncology`; families F1/F2. Demands Child-Pugh + BCLC + thermoprotection flag.
  - `JenExpert` (Palliative Specialist, Jennifer Temel archetype) — portfolio `palliative_symptom_qol`; family F1. Demands ESAS + morphine equivalents + mandatory bowel-regimen flag on opioid plans.
  - `FrancesExpert` (Expanded Access Navigator, Frances Kelsey archetype) — portfolio `expanded_access_navigation`; families F3/F8. Mandatory L4 boundary disclosure on every option; refuses "guaranteed" framing.
  - `SteveExpert` (Nutritionist, David Heber archetype) — portfolio `oncology_nutrition`; families F1/F2. Demands PG-SGA score + cachexia stage + ROS-window caveat for concurrent antioxidants.

- **6 new persona files** under `prompts/experts/{mary,ted,riad,jen,frances,steve}/persona.md` — each ≥30 lines, three-tier discipline, Anti-patterns section, founder-mode no-paternalism stance.

- **6 new task prompt files** under `prompts/tasks/`:
  - `ddi_adme_dosing.md` — RxNorm-anchored DDI screen, severity, pgx implications, renal/hepatic adjustments
  - `radiation_planning.md` — dose / fractions / BED10 / OAR table / re-irradiation flag
  - `interventional_oncology.md` — modality / Child-Pugh / BCLC / intent
  - `palliative_symptom_qol.md` — ESAS scores / opioid mg + MED / mandatory bowel regimen
  - `expanded_access_navigation.md` — L4 boundary mandatory non-empty; jurisdiction explicit
  - `oncology_nutrition.md` — PG-SGA / kcal-protein target / supplement-DDI cross-ref / ROS window caveat

- **PI intent_parser LLM upgrade** (`PISession.classify_intent_llm`):
  - Replaces P0 `classify_intent_stub` for live deployments (memory:feedback_default_prompt_over_script)
  - Loads `prompts/pi/intent_parser.md` via `PromptTemplate`
  - Raises `LLMResponseParseError` on bad JSON / unknown intent / missing key (G11 contract — no silent degradation)
  - `IntentClass` enum extended with `HYPOTHESIS_REQUEST` (routes to Wave 2 tournament per intent_parser.md)
  - Stub retained for offline CI fallback; updated to also detect `HYPOTHESIS_REQUEST` keywords

- **34 new tests** (465 total, up from 431):
  - `tests/test_experts/test_batch_d.py` — 21 tests (portfolio + persona discipline + task template invariants + per-expert anchors)
  - `tests/test_orchestrator/test_pi_session_llm.py` — 8 tests (LLM happy paths for 3 intents + 3 failure modes + enum extension + stub fallback)

### Deferred to P4.5 (honest scope limit per memory:feedback_no_false_completion)

- KierenExpert (Infectious Disease — neutropenic fever)
- MarkExpert (Endocrinologist — ICI irAE endocrine)
- DennisExpert (Cross-Border Coordinator — US/JP/EU)
- Wave 4 `hypothesis_validation` runner (P2 hypotheses ↔ P3 data; Aviv + Iain integration)
- Patient brief polish + imperative-detector strict gate + three-tier strict gate
- F10 RxNorm integrator wiring (persona references it; integrator already exists from P1 — Mary instance not yet auto-wired)

### Plan

- `docs/superpowers/plans/2026-05-24-opl-cancer-p4-pi-integration.md` (~96 lines)

## [v0.3.0-p3] — 2026-05-24

### Added

- **Expert Batch C extensions:**
  - `TylerExpert` (Wet-Lab Designer, Tyler Jacks archetype) — portfolio `hypothesis_validation`, `in_silico_experiment_design`; preferred F6/F7
  - `prompts/experts/tyler/persona.md` (KP/KPC mouse model archetype, falsifiable-experiment-first methodology)
  - `AvivExpert` portfolio extended with `dataset_acquisition`, `bioinformatics_data_analysis`, `hypothesis_validation`; preferred families now F1/F4/F6/**F7**

- **5 new omics integrators:**
  - `GEOIntegrator` (F6) — NCBI GEO via eutils `db=gds` (GSE/GDS/GPL/GSM + `search:` prefix; 7-day TTL)
  - `ArrayExpressIntegrator` (F6) — EBI BioStudies API for E-MTAB / E-GEOD accessions
  - `SRAIntegrator` (F6) — NCBI SRA runinfo via eutils for SRR/SRP/SRX/SRS
  - `DepMapIntegrator` (F7) — Broad DepMap portal CRISPR gene effect + dependency probability (30-day TTL)
  - `CCLEIntegrator` (F7) — DepMap portal CCLE expression (TPM) by gene × DepMap_ID
  - All raise `IntegratorError` on transport / HTTP / empty result (memory:feedback_no_offline_only)

- **bixbench Docker compute runtime (`compute/`):**
  - `compute/bixbench.Dockerfile` — lifted from `robin/finch/src/fhda/Dockerfile.pinned` (miniconda3 + R 4.3.3 + bioconda DESeq2 / EnhancedVolcano / clusterProfiler / gseapy / FastQC / scanpy stack)
  - `compute/runner.py` — `BixbenchRunner` env-gated wrapper (`OPL_BIXBENCH_LIVE=1` for live docker invocation; dry-run otherwise). Returns `BixbenchRunResult` dataclass with mode + image + docker_cmd + workdir + timeout
  - Image tag: `opl-cancer/bixbench:v0.3.0-p3`. CI does NOT build the image — smoke tests only verify Dockerfile presence + runner protocol shape

- **5 new task prompt files** (`prompts/tasks/`):
  - `dataset_acquisition.md` — G14 dataset-patient match scoring (cancer-type / stage / platform / size / control)
  - `bioinformatics_data_analysis.md` — required steps + falsification rule + compute estimate
  - `single_cell_reanalysis.md` — QC + integration + clustering + DA + pathway
  - `pathway_enrichment.md` — ORA + GSEA with BH correction (G15)
  - `hypothesis_validation.md` — support_score / verdict / claim-layer transition + smallest wet-lab experiment

- **Wave 3 data-evidence runner (`Wave3Runner`):**
  - `glue/wave3_runner.py` — sequential `dataset_acquisition` (Aviv) → per-top-hyp `bioinformatics_data_analysis` (Aviv + dry-run BixbenchRunner) → `hypothesis_validation` (Tyler if present, else Aviv)
  - Writes `triggers/<run_id>/wave3_data_evidence.json` + `provenance.jsonl`
  - Per ADR-2026-04-22 main-thread sequential awaits (no asyncio.gather spawning)

- **59 new tests** (431 total, up from 372):
  - `tests/test_integrators/test_geo.py` — 6 tests
  - `tests/test_integrators/test_arrayexpress.py` — 4 tests
  - `tests/test_integrators/test_sra.py` — 4 tests
  - `tests/test_integrators/test_depmap.py` — 4 tests
  - `tests/test_integrators/test_ccle.py` — 4 tests
  - `tests/test_experts/test_tyler.py` — 5 tests (incl. Aviv extension assertion)
  - `tests/test_experts/test_p3_task_prompts.py` — 2 tests
  - `tests/test_compute/test_runner.py` — 7 tests (image tag / dry-run / command shape / live-mode missing-docker / env gate / round-trip / Dockerfile present)
  - `tests/test_e2e/test_wave3_runner.py` — 4 tests
  - `tests/test_p3_acceptance.py` — 19 parametrised tests

### Deferred to P4+

- Live bixbench image build in CI (Dockerfile committed but not built — gated)
- DepMap/CCLE schema-drift adapter (quarterly release tracking)
- meta_analysis Wave-3 data integration extension (Iain) — added in P2 task list but not yet bridged to Wave3 output

## [v0.2.0-p2] — 2026-05-24

### Added

- **Expert Batch B (assumption/repurposing族):**
  - `IainExpert` (Meta-Analyst) — portfolio `meta_analysis`, `cross_source_consistency`; preferred F1/F2/F4
  - `AvivExpert` (Bioinformatician) — portfolio `hypothesis_generation`, `pathway_enrichment`, `single_cell_reanalysis`; preferred F1/F4/F6
  - `prompts/experts/iain/persona.md` + `prompts/experts/aviv/persona.md` (Cochrane / Regev archetypes)
  - New task prompts: `prompts/tasks/meta_analysis.md` + `prompts/tasks/hypothesis_generation.md`

- **Co-Sci-style hypothesis tournament machinery (`orchestrator/`):**
  - `EloTournament` — extends P0 `EloRater` (alias preserved). `pair_rotation`, `apply_round`, `top_k`, `convergence_check` (spec §17.5 P2 early-stop)
  - `DebateJudge` — LLM-driven pairwise comparator (G13 reviewer model); JSON-parse-safe (lift from `open-coscientist/agents/ranking.py`)
  - `MetaCritiqueAggregator` — round-N → round-N+1 critique propagation (lift from `open-coscientist/agents/meta_review.py`)
  - `HypothesisGenerator` — 4 strategies (`literature_gap` / `cross_domain` / `novel_mechanism` / `feasibility_first`); meta-critique + EXPERIMENTAL_INSIGHTS injection points (lift from `open-coscientist/agents/generation.py`)
  - `EvolutionStrategist` — 6 strategies (`combination` / `simplification` / `extension` / `analogy` / `resilience` / `outside_box`); parent_chain preserved (lift from `open-coscientist/agents/evolution.py`)
  - `Reflector` — 6 modes (`basic` / `simulation` / `observation` / `deep_verification` / `full_review` / `falsification`) returning verdict `passes`/`weakened`/`falsified` (lift from `open-coscientist/agents/reflection.py`)
  - `tournament_loop.run_tournament` — multi-round loop with convergence early-stop; mutates Hypothesis Elo + meta_critique_inherited in place

- **Robin lit-loop integration:**
  - `ExperimentalInsightsFeedback` — Robin `EXPERIMENTAL_INSIGHTS_APPENDAGE` adapter (lift from `robin/robin/robin/prompts.py`). Injects round results into next-round Generation prompts
  - `PaperQA2Integrator._paperqa_query` — full PaperQA2 wrapper (replaces P1 LiteRAG-only fallback). Wraps `paperqa.Docs.aadd` + `paperqa.Docs.aquery`. LiteRAG fallback retained when `paper-qa` not installed

- **Wave 2 hypothesis-generation end-to-end orchestrator (`Wave2Runner`):**
  - 4-strategy generation → 2-evolution → tournament loop → top-3 reflection (basic + falsification)
  - Writes `triggers/<run_id>/wave2_hypotheses.json` + provenance.jsonl
  - Per ADR-2026-04-22 main-thread only

- **PI intent extension:** `HYPOTHESIS_REQUEST` added to `prompts/pi/intent_parser.md` — triggers Wave 2 dispatch when patient asks "what novel directions exist?"

- **Memory schema additions (`memory/schemas.py`):**
  - `Hypothesis` (id/text/elo_rating/status/parent_chain/generation_strategy/evidence_refs/meta_critique_inherited/rationale) — defaults to `claim_layer=speculative` per founder-mode philosophy
  - `TournamentRound` (round_id/wave_index/participants/pairings/outcomes/elo_deltas/meta_critique)
  - `TournamentOutcome` (a/b/winner/reason)

- **82 new tests** (372 total, up from 290):
  - `tests/test_memory/test_hypothesis_schema.py` — 6 tests
  - `tests/test_orchestrator/test_elo_tournament.py` — 9 tests
  - `tests/test_orchestrator/test_debate_judge.py` — 5 tests
  - `tests/test_orchestrator/test_meta_critique.py` — 4 tests
  - `tests/test_orchestrator/test_generation.py` — 6 tests
  - `tests/test_orchestrator/test_evolution.py` — 7 tests
  - `tests/test_orchestrator/test_reflection.py` — 7 tests
  - `tests/test_orchestrator/test_experimental_insights.py` — 4 tests
  - `tests/test_orchestrator/test_tournament_loop.py` — 5 tests
  - `tests/test_experts/test_iain_aviv.py` — 8 tests
  - `tests/test_glue/test_wave2_runner.py` — 4 tests
  - `tests/test_integrators/test_paperqa.py` (+2 new for PaperQA2 wrapper)
  - `tests/test_e2e/test_p2_hypothesis_e2e.py` — 1 test
  - `tests/test_p2_acceptance.py` — 14 tests

### Validation

- 372 tests pass (`pytest tests/`)
- `ruff check src/ tests/` green
- `mypy --strict src/` green (75 files)
- All LLM calls mocked (no real network); PaperQA2 paperqa module monkey-patched in tests

### Tag

`v0.2.0-p2`

---

## [v0.1.0-p1] — 2026-05-24

### Added

- **6 Expert Batch A (clinical interpretation D1):** Rosa / Bert / Vince / Rick / Heddy / Hong
  - Each with persona prompt + task-package prompt + LLMBackedExpert wrapper
  - Roster `portfolio` + `preferred_families` declared per expert
- **15 Integrator concrete clients (F1-F5 + F8 partial + F10 backbone):**
  - **F1 Literature:** PubMed / Unpaywall / PaperQA2 (LiteRAG fallback) / RetractionDB
  - **F2 Guidelines:** NCCN PageIndex (HCC + NSCLC 2025 excerpts)
  - **F3 Trials:** ClinicalTrials.gov v2 / ChiCTR
  - **F4 Genomics Knowledge:** OncoKB / CIViC / ClinVar / gnomAD
  - **F5 Cohorts:** cBioPortal / GDC
  - **F8 Drug Access:** NMPA EAP / FDA EAP
  - **F10 Drug Safety (backbone):** RxNorm
- **5 mechanical gates (P1-relevant subset of spec section 7):**
  - G1 PMID-existence (PubMed-resolved)
  - G2 PMID-quote-match (PaperQA2 retrieval-backed)
  - G3 Drug-normalization (RxNorm-backed)
  - G9 Retraction-check (RetractionDB-backed)
  - G11 No-silent-fallback (integrator contract)
- **LLM client infrastructure:**
  - `AnthropicClaudeClient` + `MiniMaxClient`
  - `ModelRouter` enforcing G13 (executor != reviewer model family)
  - `PromptTemplate` (Jinja2 + StrictUndefined) + `find_prompts_root`
- **Wave 1 end-to-end orchestrator (`Wave1Runner`):**
  - intent -> planner -> fanout (parallel experts) -> reviewer audit -> render
  - Writes `delivery/patient_brief.{html,md}` + `provenance.jsonl`
  - Depth <= 1 RuntimeError enforced (closes P0 loop-back)
- **Patient brief renderer (`PatientBriefRenderer`):**
  - HTML + Markdown variants
  - Three-tier labels (established / exploratory / speculative)
  - PMID links -> pubmed.ncbi.nlm.nih.gov/{id}
  - Risk-card-at-top + reviewer-challenges section
  - Provenance hash per claim (sha256: prefix)
- **Patient case loader (`PatientCaseLoader`):**
  - profile.json + readiness.json + 11 buckets -> typed dict
- **2 synthetic golden-set patients (clinically plausible, no real PHI):**
  - `anon_hcc_001` — HCC HBV+ TACE-refractory + Atezo+Bev PD (3L decision)
  - `anon_nsclc_001` — NSCLC EGFR L858R + emergent C797S in cis (post-osimertinib)
- **3 failure-mode golden inputs:**
  - `fake_pmid_input.json` (blocked by G1)
  - `retracted_pmid_input.json` (blocked by G9)
  - `imperative_command_input.json` (G7 deferred to P5, documented)
- **Independent third-party evaluator dispatcher (`scripts/dispatch_e2e_evaluator.py`):**
  - 6-dimension prompt + verdict JSON schema
  - Operator dispatches via `/superpowers:dispatching-parallel-agents`
- **Parametrised E2E test:** Wave1Runner on both synthetic patients (mocked LLM + integrators)

### Changed

- **`dispatch_wave` is now async** with real concurrency via `asyncio.gather` + semaphore
  - Depth <= 1 RuntimeError assert closes P0 loop-back
- **Integrator base class is async** (`async def fetch`) with `cached_fetch` TTL helper
- **CHANGELOG policy:** enumerated per-PR entries (no more empty `[Unreleased]` blocks)
- Acceptance test file renamed: `test_p0_acceptance.py` -> `test_p1_acceptance.py`

### Fixed (P0 loop-back items)

- `test_acceptance_pytest_runs` tautology -> renamed/expanded with real assertions
- `test_dispatch_wave_respects_concurrency_limit` -> augmented with real-concurrency speedup test
- `classify_intent_stub` removed from P0 path: Wave1Runner uses LLM-backed intent parser

### Deferred

- G4-G8 + G10 + G12 / G14-G20 mechanical gates -> P5
- Co-Sci tournament loop (open-coscientist lift) -> P2
- Wave 2-5 hypothesis / data analysis / validation -> P2-P4
- Compute runtime bixbench Docker -> P3
- 12 remaining experts (Mary/Aviv/Tyler/Iain/Ted/Riad/Jen/Kieren/Mark/Frances/Dennis/Steve) -> P2-P4
- TBD MAINTAINERS.md slots -> P6
- Substrate license-compatibility audit (ADR-0001 follow-up) -> P6

### Acceptance criteria met

- >= 150 tests passing (target enforced by `test_acceptance_total_test_count_threshold`)
- All 6 experts importable + portfolio declared
- All 15 integrators importable
- All 5 P1 gates registered + contract-tested
- Wave1Runner end-to-end on 2 patients with 2 distinct cancer types
- Real LLM API integration (Claude executor × MiniMax reviewer) gated on env keys

## [v0.0.1-p0] — 2026-05-23

Initial scaffold (memory + provenance + orchestrator stubs + ADR-0001..0005 + Apache-2.0).
