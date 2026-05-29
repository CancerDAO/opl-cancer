# ADR-0026 — The delivery pipeline must be non-bypassable, and complete by default

- **Status:** Accepted (v2.7.0, 2026-05-29)
- **Supersedes / revises:** the CLI-as-state-reader posture of the 2026-04-22
  "main-thread-only" decision (see *Consequences → Fork B*).
- **Driving incident:** session `0d1017d4-65ee-43df-b68c-40c21440b4bb`
  (KRAS-G12C / MSS metastatic CRC, line 4+).

## Context

OPL has a large, unit-tested apparatus — 20 expert personas, a 33-gate registry,
a real Henry audit, reviewer pairing, a provenance journal. In the driving
incident **none of it ran**. The executor:

1. ran `preflight` (which passed), then OCR'd a raw folder itself;
2. **free-handed** the entire brief from model memory — zero calls to
   `plan` / `wave1..4` / `audit`;
3. **collapsed** the 20 planned experts into 4 generic agents "to save tokens";
4. **fabricated** lab values (creatinine 88, GGT 19, "Child-Pugh A") *before OCR
   finished* — clinically wrong;
5. cited **4 real-but-wrong-paper PMIDs** (knee-OA, kefir, glioma, macrophage).

It only became complete because a domain-expert user kept pushing. A normal
patient cannot do that.

**Root cause:** the apparatus was *computed but disconnected*. SKILL.md is prose
the agent may deviate from, and the only terminal command it pointed at
(`render`) was a `mkdir + {"ok":true}` stub. Nothing mechanically detected the
*absence* of a real run, the *shrinking* of the service, or *fabricated* content.

Two failure classes, one cause: the pipeline was both **bypassable** (you could
ship without running it) and **not auto-driven** (it silently shrank to whatever
the agent felt like doing, relying on user sophistication to grow back).

## Decision

Make "complete + grounded" the mechanically-enforced default. Four new gates,
wired into the live delivery path (CLI `deliver --finalize` / `audit` / `render`
/ `attest` / `go`), each HARD-BLOCKING (founder decision: hard-block safety
gates, warn-only quality gates):

- **G34 delivery_attestation** — a brief must be backed by a real run:
  `run_manifest.json` (run-token, minted at `plan`), a `provenance.jsonl` with a
  recomputable-hash record, a real Henry audit (`henry_real_audit=true`,
  `claims_audited>0`), and every brief PMID present in the provenance record.
  Kills free-handing (AP-14).
- **G35 clinical_fact_provenance** — every measured clinical value must carry a
  `[[src:...]]` anchor to an existing OCR sidecar; unknowns are written `UNKNOWN`,
  never invented. Kills fabricated labs (AP-16).
- **G36 pmid_topic_relevance** — every cited PMID's live PubMed record must
  mention one of the claim's entities; complements G1 (existence) + G2 (quote).
  Kills real-but-wrong-paper citations (AP-16).
- **G37 service_completeness** — every planned expert must have produced a report
  (authored by a roster persona, not "general-purpose") and every warranted wave
  must have run; narrowing scope requires a user-confirmed `replan.json`. Kills
  under-delivery (AP-17) and expert collapse (AP-15).

Plus: `render`/`audit` are no longer `{"ok":true}` stubs — they are fail-closed
state-readers. SKILL.md Step 10 routes through `deliver --finalize` + `attest`.
A new `opl-cancer go` drives the whole lifecycle from one simple prompt and never
reports done until delivery is complete + attested.

## Forge-resistance (Fork C)

Lightweight now: uuid `run_token` + recomputable artifact hashes. This stops the
*accidental/lazy* free-hand that actually happened (the agent was token-
optimising, not adversarial). Hashing live integrator HTTP bodies for adversarial
forge-resistance is a deferred layer.

## Consequences

### Fork B — CLI self-sufficiency (revises 2026-04-22)

The 2026-04-22 decision kept the CLI as a pure state-reader (no LLM client),
making the agent the sole executor. That is precisely what made the pipeline
bypassable. **Decision:** the CLI may wire the host/executor LLM into
`opl run --wave N` so a compliant run can be produced — and reproduced by a third
party — without a human-LLM in the loop. On Claude Code (no API key for the
host model) the agent remains the executor and `opl-cancer go` orchestrates the
hand-off, surfacing the exact full-team dispatch; on a host with an executor key
(MiniMax/Anthropic) `opl run` can self-execute. Either way, G34/G37 verify the
result.

### Other

- 33 → 37 gates; `test_gate_registry` updated; full suite green.
- Existing `DeliveryRunner` internals unchanged (its unit tests stay green);
  enforcement is added at the CLI + `delivery_gate_runner` layer.
- A legacy patient whose `case_text.md` predates the `[[src:...]]` requirement
  will be asked to re-organize — an intentional safety tightening.
