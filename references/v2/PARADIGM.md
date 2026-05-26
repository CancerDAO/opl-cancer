# OPL v2 Paradigm — What Changed and Why

## The failure that triggered v2

Wave 2 of OPL v1.5.7 produces hypothesis cards using 4 strategies
(`literature_gap` / `cross_domain` / `novel_mechanism` /
`feasibility_first`), runs a Google AI Co-Scientist style Elo tournament +
DeepMind Robin 6-mode reflection, ranks Top-5. The methodology is rigorous.

But on PT-EE62321353 (KRAS G12C MSS mCRC L4+) the Top-5 was:

1. Cardiac workup (procedural).
2. Sotorasib+panitumumab via 博鳌乐城 (CodeBreaK 300 NEJM 2023, published).
3. Re-NGS 500-gene (procedural).
4. Adagrasib+cetuximab (KRYSTAL-1 PMID 36546659, published).
5. TAS-102+bev (SUNLIGHT NEJM 2023 PMID 37133585, published).

**Every** clinical hypothesis cited an existing phase III or phase Ib trial.
None proposed a target-target synergy that PrimeKG had documented but no one
had tested in this patient subtype. None proposed a candidate molecule for an
undrugged target (e.g. MTAP-loss → PRMT5 synthetic-lethal candidate scaffold
via DiffDock + ESMFold). None proposed an auto-deployed bioinformatics
pipeline result that pre-dated publication.

**This is a polished MTB, not an AI scientist team.**

## Why this happened (4 mechanisms)

See `references/adr/0010-v2-paradigm-shift.md` §Context for the detailed
forensic. The four converging mechanisms:

1. The `Empty-integrator rule (v1.2.0)` forbids synthesizing from training
   data — necessary to prevent hallucination on `literature_gap` strategy,
   but it kills the `world-unknown` use case where the whole point is to
   propose what hasn't been written yet.
2. The 4 generation strategies don't include anything pointing at synergy /
   undrugged targets.
3. `proactive_push` policy forbids surfacing `[S]` claims — the patient
   never sees them.
4. The renderer has no place for `[S]` candidates — they get mixed with
   `[E]` and buried.

## What v2 changes (5 seams)

1. **`STRATEGIES` tuple** — +2 entries pointed at synergy + undrugged-target
   design. Source: `src/opl_cancer/orchestrator/generation.py:24-31`.
2. **`hypothesis_generation.md` prompt** — lift the synthesis ban for `[S]`-
   with-`testability_path`; mandate `testability_path` field.
3. **`proactive_push.md`** — speculative claims ARE pushed when
   `testability_path` present + rendered in `world_unknown_candidates`
   section.
4. **Patient brief renderer** — dedicated `world_unknown_candidates` section
   above Summary with `未发表 / 未验证 / research direction` framing.
5. **Roster** — +2 experts: **Maya** (KG-synergy reasoner, archetype:
   Marinka Zitnik + Tijana Milenković) and **Julius** (in-silico
   medicinal chemist, archetype: ESMFold/DiffDock/RDKit/medchem lineage).
   PrimeKG integrator stub at `src/opl_cancer/integrators/primekg.py`.

## What v2 does NOT change (intentionally deferred)

See `references/v2/ROADMAP.md` for the 9 follow-up branches. Most important:

- Wave 3 hard gate (Henry L1 BLOCK if Wave 3 skipped).
- Wave 3 → Wave 2 feedback loop (new hypotheses from real data go back to
  the tournament).
- Live PrimeKG / DiffDock / ESMFold / RDKit wiring (stubs only in this PR).
- Skill registry + K-Dense-AI bridge for 138 scientific skills.

## How to verify v2 worked

Run the same PT-EE62321353 trigger that produced the v1.5.7 failure mode.

v2 success criteria (programmatic check via `scripts/verify_v2_e2e.py`):

- [ ] Wave 2 output JSON contains ≥1 hypothesis with
      `generation_strategy: target_synergy_emergent` AND non-empty
      `testability_path`.
- [ ] Wave 2 output JSON contains ≥1 hypothesis with
      `generation_strategy: undrugged_target_design` AND non-empty
      `testability_path`.
- [ ] Patient brief HTML contains `<section class="world-unknown">` with
      ≥2 entries.
- [ ] Patient brief MD contains `## ⚡ World-Unknown` section with ≥2
      bullets.
- [ ] No regression in existing Wave 1 / 3 / 4 / 5 outputs.

A second patient from a different cancer type (per
`memory:feedback_multi_case_validation`) must also satisfy these. Tracked in
`references/v2/E2E-VALIDATION-MATRIX.md`.
