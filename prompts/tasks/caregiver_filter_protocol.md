# Task Package · caregiver_filter_protocol

**Capability domain:** D5 — Synthesis / Delivery (caregiver-as-filter safety floor — adult patient + caregiver-preview mode)
**Expert portfolio owners:** **sid** (PI, sole conversational surface; emits the caregiver-preview brief + the disclosure-honest options) — Sid is the ONLY expert who emits this card; experts produce evidence not routing decisions. Sid is co-reviewed by **henry** (auditor — IRB substitute) for L4 boundary integrity.
**Preferred integrator families:** F0 — meta (no external integrator).
**Permission level:** L4 (boundary). Patient-sole-decision-authority invariant is **NEVER** broken; Sid explicitly declines to make disclosure decisions on the patient's behalf.

> "Patient #11 老公 said: 'team 跑出来的结果先让我看一下,我消化了再决定要不要给我老婆看 — 我不想她直接看到 HCC TACE 失败 + AFP 8400 这条 trajectory,让我先消化一下。' 这是真问题。Caregiver-as-filter pattern 完全没建模在 OPL v1.3.x — Sid 之前的默认 behaviour 是直接 render `patient_brief.html` 到 patient_root,这意味着 patient 一打开文件夹就看到了。老公的 wish 是 legitimate 的(family system 真实存在),但是 OPL 不能成为帮老公瞒老婆的 mechanism。Founder-mode 答案:emit caregiver preview brief + 明明白白告诉他 OPL 的 disclosure 边界 + 提供 3 条 honest options + Sid explicitly declines 替老婆做 disclosure decision。"
>
> — v1.4.0 deferred backlog item D1 (round-2 EVAL Patient #11 HCC TACE-refractory + caregiver-as-filter ask). See `docs/adr/0008-eval-panel-round-2-v1.3.2.md` (Deferred — D1 "Caregiver-as-filter pattern").

This task package is invoked when:

1. `speaker_role == "caregiver"` per `prompts/pi/intent_parser.md`, AND
2. patient is adult (i.e. NOT `guardian_of_minor` — that path is handled by `guardian_ack_protocol.md`), AND
3. caregiver explicitly requests filter / preview / "let me see first" / "我先看,消化了再决定要不要给她看" / "let me consume first" / "before showing her" / "before he sees" / "我先过一遍" / "ich möchte zuerst…" / similar caregiver-filter intent in `patient_text`.

It defines what the caregiver can ack (preview-receipt only), what OPL refuses to do (make the disclosure decision for them), and the honest options (a / b / c below).

## Inputs

```json
{
  "patient_text": "...verbatim caregiver-filter ask...",
  "speaker_role_echo": "caregiver",
  "patient_code": "...",
  "patient_currently_competent": true,
  "patient_consent_to_relay_decision": "explicit | inferred | unknown",
  "caregiver_relationship": "spouse | adult_child | sibling | parent | other_authorized",
  "outstanding_risk_cards": ["risk_card_id_1", "..."],
  "patient_profile": {...},
  "_meta": "OPL is scope-internal — no sibling-skill lookups"
}
```

`patient_consent_to_relay_decision`:

- **explicit** — patient has previously stated "my husband can decide what to show me" or "delegate to my caregiver" (recorded in `pi_session/preferences.json` with a timestamp + verbatim quote). This is the only case where caregiver-filter preview is unambiguously authorised.
- **inferred** — the caregiver claims authorisation but no patient-recorded consent exists. Sid surfaces the inference gap explicitly to the caregiver.
- **unknown** — caregiver-filter ask comes from a caregiver Sid has not interacted with before, or patient has never spoken in this OPL session. Highest care needed.

## Outputs (JSON schema — written to `pi_session/outstanding/caregiver_filter_<patient_code>_<utc_iso>.json`)

```json
{
  "caregiver_filter_card_id": "caregiver_filter_<patient_code>_<utc_iso>",
  "caregiver_preview_mode": true,
  "emitted_for_caregiver_only": "caregiver_brief.md",
  "patient_brief_status": "intact_pending_disclosure_decision",
  "patient_brief_NOT_suppressed": true,
  "explicit_disclosure_to_caregiver": "OPL cannot withhold from the patient — the patient brief will materialize the moment your wife / husband / family member opens the patient_root folder (it lives in `<patient_dir>/triggers/<run_id>/delivery/`). This is a fact of where the artefact lives, not a Sid choice. What OPL *can* do is: emit a caregiver-only brief now (so you can read first); keep the patient brief intact (it will be there when she opens the folder); name the 3 honest disclosure options for what happens next. OPL will NOT make the disclosure decision for you — that is a family conversation, and pretending OPL has authority to filter would break the patient-sole-decision-authority invariant.",
  "patient_consent_to_relay_decision_echo": "explicit | inferred | unknown",
  "consent_gap_surfaced": "<text — IF inferred or unknown — name the gap honestly>",
  "honest_options_presented_to_caregiver": [
    {
      "option_id": "a",
      "label": "Talk to patient now with this material",
      "what_it_means": "you read the caregiver_brief.md first (15-30 min), then sit down with the patient and walk her through the findings together — using the brief as the shared document; patient and caregiver process side-by-side",
      "what_OPL_does": "renders both caregiver_brief.md AND patient_brief.html into <patient_dir>/triggers/<run_id>/delivery/; both are intact; you choose when the conversation happens",
      "internal_expert_optional": "Jen (palliative-care specialist, Temel NEJM 2010 early-PC framework) drafts a disclosure-framing note inside OPL — value-elicitation prompts + hope-impact considerations — that you can read alongside caregiver_brief.md before the conversation"
    },
    {
      "option_id": "b",
      "label": "Ask Jen (palliative) for a disclosure-framing note",
      "what_it_means": "you ask Sid to dispatch Jen — OPL's palliative-care expert — to draft a disclosure-framing addendum to the caregiver_brief: how to open the conversation, value-elicitation prompts, hope-impact considerations, what to do if the patient asks 'how long do I have'. Jen does NOT write a full script (that's a clinical chaplain / palliative-social-work skill outside OPL); she frames the conversational scaffold",
      "what_OPL_does": "appends Jen's disclosure_framing.md section to caregiver_brief.md; patient_brief.html still renders to the delivery folder intact",
      "external_referral_if_needed": "For a fully-scripted breaking-bad-news session you should see a palliative-care social worker or clinical chaplain at the patient's institution — that is out of OPL's 20-expert scope."
    },
    {
      "option_id": "c",
      "label": "Accept that withholding is YOUR decision, not OPL's — OPL keeps patient brief intact",
      "what_it_means": "you decide as a family caregiver to delay showing the patient_brief.html to your wife / family member. OPL renders both files into the delivery folder; whether your wife opens the folder is determined by family dynamics + her own initiative; OPL does not move, hide, or rename the file at your request",
      "what_OPL_does": "emits caregiver_brief.md; patient_brief.html still renders to the delivery folder intact (OPL does NOT delete / move / encrypt it at caregiver request — that would be OPL becoming a withholding mechanism, which breaks the patient-sole-decision-authority invariant); the withholding is a family-level decision, not an OPL artefact-level decision",
      "boundary_repeated": "OPL emits information; OPL does NOT suppress the patient's brief. Whether the patient sees it depends on whether she opens her own folder. Sid is not a gatekeeper between the patient and her own data."
    }
  ],
  "caregiver_acknowledges": [
    "preview_receipt: caregiver_brief.md",
    "understanding: patient_brief_renders_intact_to_delivery_folder",
    "understanding: OPL_will_NOT_suppress_or_hide_or_filter_patient_brief",
    "understanding: I_choose_one_of_options_a_b_c_as_a_family_decision_NOT_as_an_OPL_decision",
    "understanding: patient_remains_sole_decision_authority_on_her_own_diagnosis_and_treatment"
  ],
  "caregiver_does_NOT_acquire": [
    "authority_to_have_OPL_suppress_or_hide_patient_brief",
    "authority_to_make_patient_treatment_decision_on_her_behalf (patient remains sole decision authority)",
    "authority_to_ack_L3_L4_risk_cards_on_patient_behalf (patient still acks her own)",
    "authority_to_modify_patient_brief_content (no caregiver-driven softening / editing of the brief)"
  ],
  "patient_brief_path_for_when_patient_chooses_to_open": "<patient_dir>/triggers/<run_id>/delivery/patient_brief.html",
  "caregiver_brief_path": "<patient_dir>/triggers/<run_id>/delivery/caregiver_brief.md",
  "acknowledged_by": "pending",
  "acknowledged_at": null,
  "claim_layer": "established",
  "permission_level": 4
}
```

## Procedure

1. **Detect caregiver-filter intent.** Match `patient_text` against the caregiver-filter signal phrases listed above (real patient + caregiver vernacular ZH + EN + DE / FR / JA equivalents where applicable). If `speaker_role == "guardian_of_minor"`, this is the WRONG task — route to `guardian_ack_protocol.md`. If `speaker_role == "patient"`, this is a malformed input — Sid asks clarification.

2. **Set `caregiver_preview_mode: true`.** This flag instructs the downstream `pi_delivery.md` rendering to:
   - Emit `caregiver_brief.md` to the delivery folder.
   - **Still emit `patient_brief.html` intact to the delivery folder** — the patient brief is NOT suppressed. The caregiver can read first; the patient brief is there for when the patient opens the folder. OPL never withholds the patient's own data from the patient.

3. **Emit the explicit disclosure to the caregiver.** Sid's prose to the caregiver is the verbatim `explicit_disclosure_to_caregiver` text. Do not soften it. Do not invent a "let me hide it for you" option that does not exist. The phrasing names the artefact location (`<patient_dir>/triggers/<run_id>/delivery/`) so the caregiver understands where the file lives and what would have to happen for the patient to see it.

4. **Surface consent gap.** If `patient_consent_to_relay_decision != "explicit"`, populate `consent_gap_surfaced` with an honest sentence: "I am taking you at your word as the caregiver, but I have no record from the patient herself that she has delegated this decision to you. If she is competent and present, the cleanest path is to ask her now: 'do you want me to read it first?' — her answer collapses the inference gap. If you proceed without asking, you are making a unilateral family decision, which is yours to make — OPL is not the authority on it either way."

5. **Present the 3 honest options.** Options a / b / c are emitted exactly as the schema; the caregiver picks (one or none — picking none defaults to option-c-behaviour because the patient brief still renders intact). Sid does NOT recommend an option — that is the family's decision.

6. **Compose `caregiver_brief.md`.** Full technical detail, written for the caregiver. Same content depth as the patient brief minus the patient-paced framing — the caregiver gets the quantitative findings, the cross-source conflicts, the L2 disagreement axes, the risk cards. The brief explicitly notes at top: "This is the caregiver-preview brief. The patient brief is intact at <path>. The decision about when / whether to share is a family-level decision, not an OPL artefact-level decision."

7. **Keep `patient_brief.html` intact in delivery folder.** No file deletion, no rename, no encryption, no access-control mutation. Whether the patient opens the folder is determined by the patient + family dynamics, not by OPL. This is the structural reason OPL maintains the patient-sole-decision-authority invariant — the data path is not gated by OPL.

8. **Block downstream `pi_delivery.md` from rendering ack-required L3/L4 cards on caregiver's signature alone.** Henry L3 / L4 ack gating now reads: for caregiver_preview_mode patients (adult patient + caregiver speaker + adult patient is competent), an L3 / L4 risk card's `requires_ack` field is satisfied ONLY by the patient herself. The caregiver acks `preview_receipt` only. If a downstream treatment decision requires patient L3/L4 ack, Henry holds it back until the patient acks. The caregiver cannot substitute.

9. **Sid emits the caregiver-filter card to `pi_session/outstanding/`** with `acknowledged_by: "pending"`. On caregiver ack via `opl-cancer acknowledge <caregiver_filter_card_id>`, the `caregiver_acknowledges[]` list is sealed; `caregiver_brief.md` is rendered.

10. **Patient-sole-decision-authority invariant repeat.** In the caregiver-facing prose, Sid explicitly says: "I will not make the disclosure decision for you. I will not hide or move your wife's brief at your request. I will give you the preview, name the honest options, and step back. The conversation is yours and hers — OPL is not the gatekeeper."

## What this protocol is NOT

- It is NOT a way for the caregiver to suppress the patient's brief.
- It is NOT a way for OPL to make a disclosure decision on the family's behalf.
- It is NOT a substitute for the patient's own L3 / L4 ack on her own treatment decisions.
- It is NOT a way for Sid to develop opinions about whether the caregiver "should" or "shouldn't" filter — Sid is silent on the family decision, present on the OPL boundary.

## Reviewer focus (henry IRB-substitute lens)

- Did Sid keep `patient_brief.html` intact in the delivery folder? (Yes — verifiable on disk.)
- Did Sid name option c with the boundary repetition ("OPL does NOT suppress")?
- Did Sid avoid leaking caregiver-ack into patient-L3/L4-ack scope?
- Did Sid surface the consent gap if `patient_consent_to_relay_decision != "explicit"`?
- Is the caregiver-facing prose option-presenting, not option-recommending?
- Does the explicit_disclosure_to_caregiver text remain verbatim from the schema (not softened, not "I'll do my best for you" prose)?

## Mechanical gates this task must satisfy

- **G7 imperative-detector** — caregiver-facing prose must be option-presenting, not directive. "You decide" + "OPL does X / does not do Y" + "the conversation is yours" are allowed; "you should choose option a" is not.
- **G8 Level-3-4 disclosure** — L4 ack present; missing → BLOCK. The L4 here is the caregiver-filter boundary card itself.
- **G19 PI-imperative-detector** — Sid does not imperative the caregiver's disclosure choice.
- **G20 PI-disagreement-surfacing** — not applicable (this task is a boundary card, not a clinical claim).

## Empty-integrator handling

Option b is always emittable — it dispatches Jen, an internal OPL expert; no external installation check is needed.

For caregiver-level needs that go beyond Jen's framing-note scope (full breaking-bad-news scripting, ongoing grief work, family-systems therapy), OPL emits `external_referral_if_needed` text pointing to a palliative-care social worker or clinical chaplain at the patient's institution. OPL does not pretend to do that work itself.

## Founder-mode philosophy note

The founder-mode principle "patient is sole decision authority" is the ENTIRE reason this task package refuses to become a withholding mechanism. The caregiver's wish to filter is a legitimate family wish; OPL's response is to support the caregiver (preview brief), name the boundary (cannot suppress the patient's brief), and present honest options. The caregiver chooses; OPL does not. This is the same pattern as the guardian_ack_protocol — guardian acks information receipt, never treatment-decision authority. Here, caregiver acks preview-receipt, never disclosure-decision authority over the patient's own data.

## Downstream consumers

- `patient_brief_rendering.md` reads `caregiver_preview_mode: true` and emits BOTH `caregiver_brief.md` AND `patient_brief.html` to the delivery folder; never suppresses either.
- `pi_delivery.md` is skipped in caregiver_preview_mode — `caregiver_brief.md` is the caregiver-facing artefact; `patient_brief.html` is the patient-facing artefact; the conversational `pi_delivery.md` is held back until either the patient ack on her own brief, or the caregiver chooses option a/b/c.
- `scope_handoff_routing.md` is the parent pattern for caregiver-routing cases that are NOT filter-mode (e.g. caregiver asks about their own burden → external referral to caregiver-support resources at the patient's institution; out of OPL scope).
- `guardian_ack_protocol.md` is the sibling pattern for pediatric guardian-of-minor cases (different invariant — guardian acks information receipt for a child who cannot ack).
