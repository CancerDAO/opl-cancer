# ADR-0005: PI as Single Conversational Surface

## Status
Accepted (P0, 2026-05-24)

## Context
With 18 named Expert archetypes (see ADR-0004), the obvious wiring is to let
each Expert speak directly to the patient. That wiring fails on three fronts:

1. **Cognitive overload.** A patient who just learned their cancer recurred
   does not have the bandwidth to read 18 separate expert opinions, even when
   each opinion is short. Multi-channel input from named experts feels less
   like a research team and more like a crowd of people shouting in the
   waiting room.
2. **Visible contradictions without resolution.** Experts will disagree. If
   each speaks to the patient directly, the patient sees raw contradictions
   ("the pathologist says A, the geneticist says B, the oncologist says C")
   with no synthesis layer. This is *worse* than HITL paternalism — it offloads
   the synthesis burden onto the patient at the moment they are least equipped
   to do it.
3. **Trust is identity-bound.** Trust is not built with a flat collective; it
   is built with one consistent identity that has a track record. Splitting
   the conversational surface across 18 identities means no single identity
   accumulates the trust history.

The spec resolves all three by funneling all patient-facing communication
through a **single Principal Investigator (PI)** named **Sid**. The 18 Experts
remain real and remain named in provenance — but they speak through Sid, not
to the patient directly.

## Decision
**Sid is the sole conversational interface.** Concretely:

- Patient natural-language input is received only by Sid. The Experts do not
  have a direct patient channel.
- Sid receives input → consults `experts/roster.yaml` → decides which Experts
  to engage for this turn → dispatches them (main-thread, per ADR-0002) →
  collects their outputs → synthesizes a single conversational response.
- The synthesized response uses three-tier labels (Strong / Moderate / Weak
  evidence) and surfaces inter-expert disagreement explicitly. Drill-down is
  available on demand: the patient can ask "what did the radiologist
  actually say?" and Sid will surface that expert's raw output with
  provenance.
- Trust accumulates against Sid as an identity. Sid carries the founder-mode
  promise from ADR-0003: full transparency, no hidden synthesis, the patient
  is the responsible party.

To prevent Sid from becoming a single point of LLM failure, Sid's outputs are
routed through a **Reviewer** (a different model than Sid's executor — see
spec §7 G13 and `models.yaml`) and then through **Auditor Henry** (the
mechanical 4-layer transparency stack from ADR-0003) before delivery to the
patient.

## Consequences
**Positive**: patient sees a coherent, identity-consistent conversation; trust
accumulates against Sid; synthesis (including disagreement disclosure) happens
before the patient sees output, not in the patient's head; drill-down still
provides full transparency because the Expert outputs remain in provenance.

**Negative**: Sid becomes a high-leverage component. A regression in Sid's
synthesis logic affects every interaction. Mitigation: the
executor-vs-reviewer split forces cross-model agreement on Sid's output, and
the Auditor's 4-layer stack enforces structural transparency regardless of
synthesis quality.

A secondary risk is *over-summarization* — Sid may flatten nuance from the
Expert outputs in pursuit of conversational coherence. Mitigation: the
Auditor's disagreement-surfacing rule (ADR-0003 layer 2) blocks delivery if
Sid silently drops an Expert's dissent.

**Followups**: P1 must instrument Sid's synthesis with a "nuance preservation"
audit — sampling a small fraction of turns to verify that Expert dissent
visible in provenance is also visible in the patient-facing output.

## References
- Spec §2.2 (Expert architecture)
- Spec §2.3 (PI Sid)
- Spec §6.1 (Conversational surface)
- Spec §17.6 R1 (synthesis risk register)
- ADR-0003 (Founder-mode + transparency stack)
- ADR-0004 (Two-layer fractal)
