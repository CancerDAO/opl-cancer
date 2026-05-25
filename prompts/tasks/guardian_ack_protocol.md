# Task Package · guardian_ack_protocol

**Capability domain:** D5 — Synthesis / Delivery (pediatric guardian-mode safety floor)
**Expert portfolio owners:** sid (PI) + henry (auditor — IRB substitute) co-review; the guardian-ack protocol is the IRB-substitute's pediatric carve-out
**Preferred integrator families:** F0 (meta — no external integrator)
**Permission level:** L4 (boundary). Treatment-decision authority is **NEVER** held by the guardian under OPL; it is held by a pediatric IRB-supervised slot.

> "OPL is patient-owned, not guardian-owned. For a pediatric patient
> (< 18 years), the guardian does NOT acquire treatment-decision authority
> through OPL — that authority is held by the pediatric IRB-supervised slot
> in the patient's clinical care. What the guardian **does** acquire is the
> right to acknowledge *information receipt* on the child's behalf: 'I read
> the prognosis band, I read the risk cards, I understand my child is the
> patient but cannot ack treatment decisions for themselves, and I represent
> my family in confirming we received the information.' That is the
> guardian-ack scope. Anything beyond that — picking a regimen, choosing
> trial-vs-standard, accepting an L4 boundary on the child's behalf —
> requires the pediatric IRB slot."
>
> — v1.3.2 SAFETY hot-fix (round-2 EVAL Patient #16, 7yo ALL R/R). See
> `docs/adr/0008-eval-panel-round-2-v1.3.2.md`.

This task package is invoked when `speaker_role == "guardian_of_minor"` per
`prompts/pi/intent_parser.md`. It defines what the guardian can ack, what
they cannot, and how OPL emits pediatric-specific deliverables.

## Inputs

```json
{
  "guardian_name": "...optional...",
  "patient_code": "...",
  "patient_age": 7,
  "diagnosis_summary": "...",
  "guardian_relationship": "parent|legal_guardian|both_parents",
  "speaker_role_echo": "guardian_of_minor",
  "hope_impact": "low|moderate|high",
  "outstanding_risk_cards": ["risk_card_id_1", "..."],
  "outstanding_crisis_card": "crisis_card_id_or_null"
}
```

## Outputs (JSON schema — written to `pi_session/outstanding/guardian_ack_<patient_code>.json`)

```json
{
  "guardian_ack_id": "guardian_<patient_code>_<utc_iso>",
  "guardian_acknowledges": [
    "information_receipt: prognosis_band",
    "information_receipt: risk_cards",
    "understanding: my_child_is_the_patient",
    "understanding: I_cannot_ack_treatment_decisions_on_their_behalf",
    "understanding: treatment_decisions_route_to_pediatric_IRB_supervised_slot",
    "understanding: OPL_emits_information_not_treatment_decision_authority"
  ],
  "guardian_does_NOT_acknowledge": [
    "treatment_regimen_choice (→ pediatric IRB slot)",
    "trial_enrollment (→ pediatric IRB slot + pediatric oncology PI)",
    "L4_boundary_on_child's_behalf (→ pediatric IRB slot)",
    "DNR_or_advance_directive (→ pediatric palliative + legal counsel)"
  ],
  "pediatric_irb_route": {
    "what_it_is": "...",
    "who_to_contact": "the child's primary pediatric oncology PI + the institutional IRB",
    "what_OPL_provides_to_that_route": "the technical deliverables (pediatric_caregiver_brief.md + delivery/patient_brief.html with three-tier labels + PMID anchors)"
  },
  "deliverables_to_render": [
    "pediatric_caregiver_brief.md (full technical detail + IRB path)",
    "pi_delivery_minor.md (age-simplified for the child, IF age-appropriate)",
    "delivery/patient_brief.html (the usual brief, marked pediatric)"
  ],
  "acknowledged_by": "pending",
  "acknowledged_at": null
}
```

## Procedure

1. **Confirm guardian relationship.** Before any pediatric delivery, Sid
   asks (once) verbatim: "我需要确认 — 你是 {patient_name} 的法定监护人吗?
   (parent / legal guardian / both parents) — 这个 ack 在 OPL 里只覆盖
   '我代表家庭确认收到了信息',治疗决策仍然走儿科 IRB-supervised slot,不
   是你在 OPL 里 ack 出来的。"

2. **Compose the dual deliverables.**

   - **`pediatric_caregiver_brief.md`** (full technical detail, written for
     the guardian): same content as the adult `caregiver_brief.md` PLUS:
     * Explicit IRB path (institutional contact + pediatric oncology PI).
     * Pediatric-weight-based DDI table (per Mary's `ddi_adme_dosing.md`
       pediatric carve-out).
     * Pediatric CRS / ICANS grading (Lee criteria, NOT adult CTCAE) for
       any BiTE / CAR-T claim.
     * Germline cancer-predisposition flag (route to
       `firefly-genetic-counseling`).
     * "Treatment decision authority does NOT come from this brief; it
       routes to the pediatric IRB slot. This brief is the **information
       package** the IRB slot needs."

   - **`pi_delivery_minor.md`** (age-simplified, written for the child IF
     age-appropriate — typically 5-12 yo; very young children get the
     guardian-only path): short, calm prose at a 3rd-5th grade reading
     level, no statistics, no "X% chance," no "survival curve." Just:
     "we found three things that might help, your mom and dad are reading
     all of this, your doctor will help decide together with them." If
     the child is under 5 or non-verbal, do NOT emit this file (the
     guardian path is the only path).

3. **Emit the guardian-ack card.** Write the JSON above to
   `pi_session/outstanding/guardian_ack_<patient_code>.json`. Sid
   surfaces in `pi_delivery.md`: "我会让 {guardian_name} ack 一下,这个
   ack 只代表 ' 信息收到了',不是治疗决策授权。"

4. **Activate adult-only sibling skills with caveat.** If `cancer-buddy-mind`
   etc are dispatched in pediatric mode, the handoff prose adds: "这个 skill
   是为成人写的,儿科适用范围有限 — 用于陪伴 + 心理筛查 + 家长支持;
   儿童本人的心理评估请额外路由儿童心理门诊。" If a crisis is detected on a
   pediatric patient (G24 fires), the crisis-card handoff adds the pediatric
   crisis-line variants where the registry has them (e.g. US: 988 has
   pediatric routing; CN: 010-82951332 covers all ages).

5. **Block treatment-decision claim emission on guardian-ack alone.** Henry
   L3 / L4 ack gating now reads: for pediatric patients, an L3 / L4 risk
   card's `requires_ack` field is satisfied by guardian-ack ONLY if the
   ack scope is `information_receipt`; if the underlying decision is a
   treatment-regimen choice, Henry blocks render until the pediatric IRB
   slot is confirmed in `<patient_dir>/profile.json` as `pediatric_irb_confirmed: true`.

## What this protocol is NOT

- It is NOT a way for OPL to certify the guardian's decisions.
- It is NOT a substitute for the pediatric oncology PI / IRB.
- It is NOT a way to ack on behalf of the child's *will* (where the child
  can express one — adolescents 12-17 frequently have assent capacity even
  if they don't have consent capacity).

## Reviewer focus (henry IRB-substitute lens)

- Did Sid name the IRB route explicitly?
- Did the guardian-ack scope avoid leaking into treatment-decision authority?
- For 12-17 yo, did the deliverables include `pi_delivery_minor.md` and
  invite the adolescent's assent (not just guardian consent)?
- For < 5 yo, is the brief guardian-only as expected?

## Founder-mode philosophy note

The founder-mode principle "patient is sole decision authority" is **not
violated** by this protocol — the pediatric patient remains the decision
subject; the decision is held in a pediatric IRB-supervised slot precisely
because the patient cannot legally ack on their own behalf. OPL refuses to
collapse that into "guardian decides everything." OPL emits information.
The IRB slot is where the decision sits. The guardian acks receipt.
