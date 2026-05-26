# ADR-0020 — Trace-Digest Evolution (borrowed architecture, NOT policy, from EvoMaster)

**Status:** Accepted, 2026-05-26
**Branch:** `iter/v2-followup-evolution`
**Depends on:** `iter/v2-paradigm` merged (ADR-0010)
**Related:** ADR-0017 cross-run-memory (will share storage), ADR-0014 skill-registry (will accept evolution skill proposals)

## Context

We surveyed `sjtu-sai-agents/EvoMaster` (Apache-2.0, 2026-05-18) which introduced a `--evolve` flag for closed-loop agent self-evolution. The framework's value pitch: (1) post-run trajectory retrospection, (2) skills/prompt sedimentation, (3) auto re-run with updated baseline. The architecture is genuinely useful; the policy choices are dangerous in medicine.

Read source files:
- `evomaster/evolution/manager.py` — auto-respawn loop, no regression gate
- `evomaster/evolution/analyzer.py` — single LLM call, same medical model, generic system prompt
- `evomaster/evolution/applier.py` — blind `*.evolved.txt` append, no diff review
- `evomaster/evolution/collector.py` — TraceDigest schema (good)
- `evomaster/evolution/models.py` — clean Pydantic
- `evomaster/evolution/proposal.py` — tool proposals JSONL (good)

No published ablation showing the loop improves quality vs cost/latency. Skills + prompts auto-apply; tools require human gate (inconsistent; tools are safer than the other two).

## Decision

Build OPL's own evolution layer **borrowing the architecture, dropping the auto-apply policy**.

### What we copy (architecture)

1. **TraceDigest** schema — compact JSON summary of a run: per-Wave artifacts, evidence-tier distribution, retraction-DB hits, Henry verdict counts, novelty-gate stats, integrator latency. ~100KB cap.
2. **Per-iteration immutable snapshots** under `proposals/iter_<N>/` (never overwriting baseline).
3. **Heuristic fallback** when LLM analyzer unreachable.
4. **Tool proposals as JSONL** (review-only, never auto-enabled).

### What we drop (medical red lines)

5. **No `_write_prompt_overlays` auto-append.** Patches go to `proposals/iter_<N>/prompt_patches.diff` as PR-style unified diffs, never to `*.evolved.txt`. The diff is never applied automatically; only humans (Sid + Henry double signoff) can merge into baseline.
6. **No auto-respawn.** Evolution is post-mortem: run completes → digest → analyze → write proposals → STOP. Next patient run uses current baseline unchanged. After human review (days/weeks), approved patches land in baseline; future patients benefit.
7. **No skill `extra_roots` auto-extension.** Proposed skills go to `proposals/iter_<N>/skill_additions/<slug>/SKILL.md.proposed` with `status: pending_review` + mandatory `clinical_anchor` field (CSCO/NCCN/PMID). Only after expert backing + Henry invariant check does it enter the OPL skill registry (`iter/v2-followup-skill-registry`, ADR-0014).

### What we add beyond EvoMaster

8. **PII/PHI scrubber** runs on TraceDigest BEFORE any LLM call. Patient name, DOB, IDs, addresses, dates, organization names stripped per OPL privacy primitives. Closes EvoMaster's documented `runs/` privacy gap.
9. **Red-team analyzer system prompt** — distinct from main medical agent prompts. Frame: "your job is to detect when OPL might be silently weakening its own safety or grounding". Configurable model pool: `evolution_analyzer_pool` in `models.yaml`; default rules suggest a different model family than the main executor to reduce correlated blindspots.
10. **InvariantGate** — static analysis of proposed patches. Flags any patch touching Henry L3/L4 fields, G7 imperative-free voice, G13 reviewer model split, `prompts/_shared/persona_prefix.md` (canonical persona prefix), or claim_layer enforcement. Hits → `requires_double_signoff: true` automatically; Sid alone cannot approve.
11. **Regression gate (deferred to ADR-0011 Wave 3 hard gate landing first)** — once Wave 3 hard gate provides a real invariant floor, evolution will refuse to mark a patch as `approved` if its application would have caused the test run's Wave 3 gate to fail. Placeholder field `regression_gate_status` written but not enforced in v2.0.0-evolution-rc1.
12. **Clinical anchor mandatory** for skill proposals — `SKILL.md.proposed` lacking a `clinical_anchor` field is auto-rejected by ProposalWriter.

## Compatibility & rollback

- New code lives entirely in `src/opl_cancer/evolution/`.
- New CLI command `opl-cancer evolve` is opt-in. Default off. No existing flow touches evolution.
- All output under `proposals/iter_<N>/` (gitignored by default — opt-in commit per project policy).
- Removing the branch is a no-op for production patients.

## Verification

`scripts/verify_evolution_e2e.py` constructs a synthetic weak run dir, invokes `opl-cancer evolve`, and asserts:

1. `proposals/iter_001/` created.
2. `prompt_patches.diff` is a valid unified diff (no `*.evolved.txt` files written).
3. `status.yaml` has `status: pending` for every proposal.
4. Any proposal touching Henry/G7/G13/persona_prefix has `requires_double_signoff: true`.
5. Any skill proposal without `clinical_anchor` is in `rejected/` not `pending/`.
6. NO file under `src/`, `prompts/` (other than `proposals/`), or `models.yaml` was modified.
7. `tool_proposals.jsonl` exists and is JSONL-valid.
