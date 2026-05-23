# ADR-0003: No Human-In-The-Loop External Sign-Off

## Status
Accepted (P0, 2026-05-24)

## Context
Most medical-AI agents adopt a "human-in-the-loop" (HITL) safety story: a
licensed clinician or IRB reviewer sees each output before the patient does,
and the agent's role is reduced to "decision support" with a clinician as the
acting party. That story has two failure modes for the population OPL for
Cancer is built for:

1. **Founder-mode patients** (the entire target population in v0) are
   themselves the decision-making party. They have explicitly *chosen* to take
   responsibility for their own care, often because the standard-of-care
   clinical pathway has run out of options ("standard treatment exhausted" /
   "no trial slots in my region"). Inserting an external reviewer in front of
   their own data flow is paternalistic and inverts the consent model.
2. **There is no scalable reviewer pool.** A single founder-mode patient may
   generate dozens of agent outputs per week. No volunteer clinician network
   can sustainably review at that throughput, and a paid reviewer would
   re-introduce the standard-of-care economics that founder-mode patients are
   already on the wrong side of.

The conventional "no HITL" answer in medical-AI is to simply ship and hope. OPL
for Cancer rejects that too: the patient still needs *some* protection against
hallucinated evidence, overconfident summaries, and silently-dropped
disagreements between models. The protection just cannot come from an external
human.

## Decision
OPL for Cancer ships **without external human-in-the-loop sign-off**. The
patient is the sole responsible party for any decision derived from the
skill's output. To replace HITL safety without weakening it, the system
substitutes a **mechanical 4-layer transparency stack** that runs on every
patient-facing delivery:

1. **Forced risk-disclosure card** — every output must surface a structured
   risk card (severity / probability / evidence basis); the card cannot be
   suppressed.
2. **Forced model-disagreement surfacing** — when the executor and reviewer
   models disagree about a claim, the disagreement is shown verbatim, not
   resolved silently by majority vote or by the executor's confidence.
3. **Forced known-serious-risk checklist** — for each cancer type and
   treatment class, a curated checklist of known serious risks (e.g., immune
   checkpoint myocarditis) is auto-rendered alongside the recommendation.
4. **Forced patient-acknowledgment loop** — before a Level-3 or Level-4 action
   (see ADR's permission classification) is executed, the patient must
   acknowledge the risk card; the acknowledgment is logged in the provenance
   ledger.

These four layers are enforced by Auditor "Henry" before any output reaches
the patient. The Auditor is a Python state machine, not an LLM, so the
enforcement is deterministic and auditable.

## Consequences
**Positive**: the safety model matches the actual consent model of the user
population; no scalability ceiling from reviewer throughput; the patient sees
all uncertainty, all disagreements, and all known risks — which is
*more* transparent than the typical HITL workflow, which often shows the patient
only the clinician's filtered conclusion.

**Negative**: regulators trained on HITL frameworks may not accept the
mechanical substitute. CancerDAO's positioning here is founder-mode-first and
explicitly outside the regulated medical-device frame in v0; that is a
deliberate choice, recorded here so future contributors do not "fix" it.

**Followups**: P1 must add a written disclaimer at session-start that the
patient is the sole responsible party; v0 stub message is in
`src/opl_cancer/pi/session.py`.

## References
- Spec §1.3 (Non-Goals)
- Spec §8 (IRB Substitute)
- Spec §17.6 R1 (risk register: external sign-off)
