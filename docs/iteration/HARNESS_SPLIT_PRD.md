# PRD: opl-cancer dual-brain decoupling migration (prompt-only harness split)

**Status**: approved, in execution · **Target branch**: `feat/harness-split` (forked from `origin/main` @ v2.7.2 / a7897c2) · **Date**: 2026-06-01

## §0 Telos

Move all *patient reasoning* out of Python-internal LLM calls (path B) into the
host agent's prompts, leaving Python as a **deterministic harness only**
(gates / provenance / integrators / attestation). Goals: (1) eliminate the
dual-brain double safety-surface; (2) deliver true agent-agnosticism; (3) close
the audited P0 safety gaps in the same window. **Red line: the gates' "violation
⇒ exit≠0" decision authority stays in Python.**

## §1 Problem (grounded on origin/main)

main is a **dual-brain hybrid** — reasoning happens in two places:

| Path | Entry | Evidence (origin/main) |
|---|---|---|
| A | Claude main thread dispatches expert subagents | SKILL.md:272 "all run via the main-thread orchestrator" |
| B | Python internally calls minimax/anthropic | `experts/_common.py:40 LLMBackedExpert`; `wave1_runner.py` (10 hits); `wave1_live.py`; `renderer.py`; `henry.py:200 await llm_client.complete` |
| C (correct) | pure deterministic code | 42 gates (0 LLM); provenance; integrators; attestation |

Paths A and B are two implementations of the same function. Consequences:
double "never-fabricate" surface; g13 is a patch for path B's existence; hard
`pip install -e` + provider keys undermine the agent-agnostic claim.

## §2 Target architecture

```
  patient input → HOST AGENT (Claude main thread) — the ONLY reasoning brain
                    reads prompts/**: experts / waves / planner / henry audit / debate
                    dispatches subagents
                        │ invoke (JSON args) + write-back artifacts
                        ▼
                  PYTHON HARNESS (no LLM client)
                    gates G1-G43 (exit≠0 authority) · provenance · live integrators
                    (PubMed/CT.gov/ChiCTR) · schema validation · attestation · scaffolds

  DELETE: src/opl_cancer/llm/  +  experts/_common.LLMBackedExpert LLM path
```

**Invariant**: harness never calls an LLM; host agent never makes a
"violation ⇒ hard fail" ruling (that is the gates' job).

## §3 Scope

| In | Out (handled separately) |
|---|---|
| Remove `src/opl_cancer/llm/` | `orchestrator/*` + `evolution/*` self-improvement engine → decouple from patient CLI, prepare for extraction to standalone `opl-cancer-evolution` |
| `experts/_common.py` LLMBackedExpert → prompt | the 42 gate algorithms (only the 3 P0 fixes touched) |
| `wave1_runner` internal LLM → main-thread subagent | live integrators / provenance / attestation (kept) |
| `glue/renderer.py` LLM render → deterministic template | docs (synced in BUMP phase) |
| `henry.py` optional L2 LLM → main-thread prompt | |

## §4 Migration ledger (per module)

| Module (origin/main) | Action | Lands as |
|---|---|---|
| `src/opl_cancer/llm/{router,minimax_client,anthropic_client,base,prompts,errors}.py` | **Delete** | reasoning moves to host agent |
| `experts/_common.py` `LLMBackedExpert` | Delete LLM part; keep Expert ABC/contract | 6-primitive grammar → `prompts/experts/*.md` run by main-thread subagents |
| `glue/wave1_runner.py` / `wave1_live.py` | Make pure scaffold (match wave2-4's 0-LLM shape) | wave1 reasoning → main thread |
| `glue/renderer.py` | Remove LLM render → deterministic template | `prompts/render/*` or Jinja |
| `validators/henry.py` | Drop L2 LLM branch | Henry judgement → main-thread prompt; Python keeps deterministic consistency checks |
| `validators/gates/*` (42) | Keep; apply P0-1/2/3 | see §5 |
| `g13_reviewer_model_distinct.py` | Redefine (path B gone): check the two subagent reports declare distinct models, or fold into G37 | adjust models.yaml `reviewer_pairings` semantics |
| `orchestrator/* + evolution/*` | Decouple from patient CLI; isolate for extraction | standalone engine (repo creation = manual follow-up) |

## §5 Fold in the audited P0 safety trio (this window is the right time)

- **P0-1**: implement G38 (or auto-derive `claim['entities']`) + make missing entities a **BLOCK**, so G36 fires by default instead of voluntary SKIP.
- **P0-2**: in `delivery_gate_runner.py`, when `pubmed is None` AND pending PMID-claims exist ⇒ add to `blocked` (hard fail, no silent pass). Aligns with `feedback_no_offline_only`.
- **P0-3**: upgrade `g35._anchor_targets_exist` to value-in-source: use the parsed `#Lnn` locator to open the sidecar and confirm the asserted value actually appears.

## §6 Branch strategy

```
origin/main (v2.7.2)
  └─ feat/harness-split   ← this PRD's branch (forked from main, NOT feat-prompt-only-migration)
       ├─ P0: safety trio + gate-retention verification (pure Python)
       ├─ P1: remove src/opl_cancer/llm/ + experts LLM + wave1/renderer/henry rewire
       └─ P2: decouple orchestrator/evolution from patient CLI
```
feat-prompt-only-migration's P0a prompt authoring (WIP 98aaa51) is source
material — cherry-pick prompts into this branch, never merge wholesale, and
always keep gate decision authority in Python.

## §7 Risks

| Risk | Consequence | Mitigation |
|---|---|---|
| Prompt-ifying a gate | loses non-bypassable guarantee | Red line: gate algorithms unchanged in Python; prompts may *invoke* gates, never *replace* the ruling |
| Deleting llm/ leaves wave1 reasoning unowned | broken patient path ("computed but disconnected") | top-down E2E required post-migration (§8), not unit-green |
| g13 semantics dangling | same-model echo chamber returns | redefine g13 in the same batch |
| evolution extraction breaks imports | CLI fails to start | patient CLI must not import orchestrator/evolution; grep-verify |

## §8 Acceptance criteria

- **E2E definition**: patient raw records → full delivery package (not stop at chair).
- **Multi-case**: ≥2 patients × 2 cancer types (reuse 007 / Riaz corpora) + validation matrix.
  Note: post-migration the reasoning brain is the host agent, so the full
  records→brief E2E is validated by a live agent session, not a Python-only test.
- **Safety regression**: `test_pipeline_non_bypassable.py` stays green; +1 reproduction test each for P0-1/2/3 (must BLOCK).
- **Zero LLM-in-Python (patient path)**: `git grep 'llm.router|LLMClient' src/` on the patient path returns empty.
- **Self-evidence**: artifact paths + wall-time + ≥3 samples; all roadmap items run before claiming done.

## §9 Resolved decisions

1. orchestrator/evolution → decouple now, extract to standalone repo as a manual follow-up (no autonomous GitHub repo creation).
2. g13 → redefine as dual-subagent model-declaration check.
3. Patient path no longer needs a provider key after path B removal (evolution engine keeps its own if retained).
4. PRD at `docs/iteration/HARNESS_SPLIT_PRD.md`, branch `feat/harness-split`.
