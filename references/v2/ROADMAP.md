# OPL v2 Roadmap — Follow-Up Branches (post `iter/v2-paradigm`)

`iter/v2-paradigm` ships the 5-seam paradigm shift (ADR-0010). It
deliberately does not include the larger surface changes below; each is
tracked as its own branch + ADR + E2E validation.

## P0 — paradigm-completing follow-ups

| Branch | ADR | Title | Why |
|---|---|---|---|
| `iter/v2-followup-wave3-gate` | 0011 | Wave 3 hard gate via Henry L1 | Without this, Wave 3 can still be skipped and Wave 2 `[S]` never gets validated against real omics. |
| `iter/v2-followup-feedback-loop` | 0012 | Wave 3 → Wave 2 feedback loop | New hypotheses from data → re-tournament. Closes the loop so `[S]` gets disproven OR upgraded based on real data. |
| `iter/v2-followup-primekg` | 0013 | Live PrimeKG client (replaces stub) | Maya currently stubbed; needs real Harvard PrimeKG HTTP/SPARQL client + 2024.1 graph data + license attribution. |

## P1 — capability expansion

| Branch | ADR | Title |
|---|---|---|
| `iter/v2-followup-skill-registry` | 0014 | `registry/skills.yaml` + agent adapter spec — open expert pool |
| `iter/v2-followup-kdense-bridge` | 0015 | K-Dense-AI/scientific-agent-skills bridge (138 skills lazy-load) |
| `iter/v2-followup-julius-live` | 0016 | Julius live wiring (ESMFold + DiffDock + RDKit + medchem filters via Modal GPU dispatch) |
| `iter/v2-followup-cross-run-memory` | 0017 | Sid cross-run episodic log + wishlist closure tracker |

## P2 — system-level intelligence

| Branch | ADR | Title |
|---|---|---|
| `iter/v2-followup-cross-patient` | 0018 | Cross-patient twin matching + federated meta |
| `iter/v2-followup-novelty-benchmark` | 0019 | Novelty dim in SBT_Benchmark adapter |
| `iter/v2-followup-streaming-pi` | 0020 | Streaming Sid delivery (PRD §17.5 P0 — partially shipped v1.5) |
| `iter/v2-followup-multi-channel-output` | 0021 | Patient / clinician / regulator outputs + CN/EN bilingual |
| `iter/v2-followup-pipeline-auto-deploy` | 0022 | Aviv autonomous pipeline picker (Snakemake/Nextflow/Modal) |

Each branch lands in its own PR with its own ADR + E2E validation matrix
(≥2 patients ≥2 cancer types per `memory:feedback_multi_case_validation`).

## Triage policy

Follow-ups are NOT bundled into a single v2.0.0 release. Per
`memory:feedback_branch_purpose_separation`, each branch ships independently
with its own E2E validation. v2 as a paradigm is "complete" when P0 follow-
ups merge; v2.x continues to expand P1 + P2.
