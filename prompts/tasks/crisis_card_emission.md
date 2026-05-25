# Task Package · crisis_card_emission

**Capability domain:** D5 — Synthesis / Delivery (safety floor — pre-empts every other Wave output)
**Expert portfolio owners:** sid (PI) only — Sid is the single voice who hands the patient the crisis-card
**Preferred integrator families:** F0 (meta — no external integrator; reads the jurisdiction phone-line registry below)
**Permission level:** L4 (boundary). Card must be patient-acknowledged before any Wave run resumes.

> "Patient (or caregiver) just gave us a crisis-grade signal. The job is not
> to dispatch experts, not to dump trials, not to refuse silently. The job
> is to acknowledge, surface a phone number that actually rings in this
> patient's jurisdiction, hand off to `cancer-buddy-mind` (and, if the
> speaker is a caregiver / guardian_of_minor, also `cancer-buddy-caregiver`),
> and stop the Wave runners until the patient (or guardian) acknowledges
> the crisis-card was received. Founder-mode: no paternalism, no dismissal,
> no concealment, no fix-it-yourself. Hand the patient another human."
>
> — v1.3.2 SAFETY hot-fix (round-2 EVAL Patient #17). See
> `docs/adr/0008-eval-panel-round-2-v1.3.2.md`.

This task package is invoked by the orchestrator the moment **either** the
upstream `prompts/safety/crisis_detection.md` returns `crisis_detected: true`
**or** the no-LLM `G24CrisisDetectionGate` fires. It writes
`pi_session/outstanding/crisis_card.json` (parallel structure to `risk_card`)
and is the **first** thing Sid renders — before `patient_brief.html`, before
`pi_delivery.md`, before any expert claim.

## Inputs

```json
{
  "crisis_grade": "passive_SI|active_SI|active_plan",
  "trigger_phrase": "<verbatim substring from patient_text or caregiver_text>",
  "jurisdiction_inferred": "CN|US|UK|EU|DE|JP|other|unknown",
  "speaker_role": "patient|caregiver|guardian_of_minor|unknown",
  "patient_code": "...",
  "run_id": "..."
}
```

## Outputs (JSON schema — written to `pi_session/outstanding/crisis_card.json`)

```json
{
  "crisis_card_id": "crisis_<patient_code>_<run_id>_<utc_iso>",
  "crisis_grade": "active_SI",
  "trigger_phrase": "我想死",
  "jurisdiction_inferred": "CN",
  "speaker_role": "patient",
  "phone_lines": [
    {
      "name": "北京心理危机研究与干预中心 24h 热线",
      "number": "010-82951332",
      "hours": "24/7",
      "language": "zh"
    },
    {
      "name": "希望24热线 (全国心理危机干预)",
      "number": "400-161-9995",
      "hours": "24/7",
      "language": "zh"
    }
  ],
  "text_lines": [],
  "crisis_skill_handoff": "cancer-buddy-mind",
  "caregiver_skill_handoff": null,
  "guardian_skill_handoff": null,
  "wave_lock": true,
  "acknowledged_by": "pending",
  "acknowledged_at": null,
  "render_position": "TOP_OF_DELIVERY_BEFORE_ANYTHING",
  "pi_prose_zh": "我听到了 — 你说...{trigger_phrase}... 在我们继续看你的病案之前,我想先把这个放在你面前: ... ",
  "pi_prose_en": "I heard you — you said ... {trigger_phrase} ... Before we go any further with your case, I want to put this in front of you: ..."
}
```

## Phone-line registry (jurisdictional, officially-documented numbers)

> All numbers below are taken from the operator's official public-facing
> page. Do NOT invent. If a number cannot be confirmed at run time, fall
> back to the **international** Befrienders Worldwide line + ask the
> patient to confirm jurisdiction.

| Jurisdiction | Name | Number | Hours | Language |
|---|---|---|---|---|
| CN | 北京心理危机研究与干预中心 | `010-82951332` | 24/7 | zh |
| CN | 希望24热线 (全国心理援助热线) | `400-161-9995` | 24/7 | zh |
| CN | 全国心理援助热线 | `400-161-9995` | 24/7 | zh |
| US | 988 Suicide & Crisis Lifeline | `988` | 24/7 | en, es |
| US | Crisis Text Line (text "HOME" to ...) | `741741` (SMS) | 24/7 | en |
| UK | Samaritans | `116 123` | 24/7 | en |
| UK | SHOUT (text) | `85258` (SMS) | 24/7 | en |
| EU | International Befrienders / EU emergency | `116 123` | 24/7 | local |
| DE | Telefonseelsorge | `0800 111 0 111` | 24/7 | de |
| DE | Telefonseelsorge (second line) | `0800 111 0 222` | 24/7 | de |
| JP | TELL Lifeline (English) | `03-5774-0992` | varies | en |
| JP | よりそいホットライン | `0120-279-338` | 24/7 | ja |
| JP | いのちの電話 | `0120-783-556` | varies | ja |
| other / unknown | Befrienders Worldwide international directory | https://www.befrienders.org/ | 24/7 | local |

## Procedure

1. **Compose the prose.** Sid writes a short paragraph (zh-CN + en-US) that
   does these four things, in this order:
   1. **Acknowledge** the trigger_phrase verbatim. ("我听到了 — 你说 '想结束这一切'。")
   2. **Name** the moment as serious. Not "this happens sometimes." Not
      "it's understandable given your diagnosis." Just: "这是一件大事 / This is serious."
   3. **Offer the phone-line(s)** for the inferred jurisdiction, with the
      hours and language explicitly stated. If `jurisdiction_inferred ==
      "unknown"`, surface the international Befrienders line + ask the
      patient to confirm their location so a local line can be added.
   4. **Hand off** explicitly to `cancer-buddy-mind`. If `speaker_role ==
      "caregiver"`, ALSO hand off to `cancer-buddy-caregiver`. If
      `speaker_role == "guardian_of_minor"`, ALSO add the guardian-of-minor
      route (see `prompts/tasks/guardian_ack_protocol.md`).

2. **DO NOT.**
   - DO NOT minimise. ("Many patients feel this way.")
   - DO NOT redirect into oncology trial dump.
   - DO NOT promise outcomes ("we'll get you better").
   - DO NOT replace the phone number with a chat handoff alone.
   - DO NOT mark the card acknowledged on the patient's behalf. Pending
     stays pending until `cli.py acknowledge <crisis_card_id>` is called.

3. **Wave lock.** Set `wave_lock: true`. The orchestrator
   (`wave1_runner` / `wave2_runner` / ...) must check
   `pi_session/outstanding/crisis_card.json` at the top of `.run()` and
   abort the wave (with a distinct `status: "crisis_locked"` return) if any
   crisis-card is `acknowledged_by: pending`. Aborting does NOT silently —
   it emits the crisis-card to the user explicitly.

4. **Multi-channel emit.** Per `prompts/tasks/scope_handoff_routing.md`,
   normally only one sibling skill is handed off per question. Crisis
   overrides this: `cancer-buddy-mind` AND the jurisdiction phone line are
   BOTH emitted. If `speaker_role == "caregiver"` or `"guardian_of_minor"`,
   add `cancer-buddy-caregiver`. This is the **only** sanctioned
   multi-sibling handoff in OPL.

5. **Persist.** Write `crisis_card.json` to
   `<patient_dir>/pi_session/outstanding/`. Append a provenance entry
   `{type: "crisis_card_emitted", crisis_grade, trigger_phrase, hashed_text,
   timestamp, run_id}` to `memory/provenance/index.jsonl`.

6. **Render.** The crisis-card renders **above** any other content in
   `delivery/patient_brief.html` (CSS class `crisis-card top-pinned`) and is
   the first paragraph in `delivery/pi_delivery.md`. Do NOT bury inside
   "Risk disclosures." It is its own top-pinned section.

## Founder-mode philosophy notes

- This is the **one** place OPL says: "stop, this needs another human."
  OPL does not have a clinician-in-the-loop by design — but it does have a
  crisis-line-in-the-loop. The two are not the same.
- "Patient is sole decision authority" still holds. The patient can
  acknowledge the crisis-card and choose to continue or to stop. We do not
  refuse to ever run a Wave for someone who acknowledged a passive_SI card.
  We require the acknowledgement itself to happen — that the patient has
  *seen* the phone number.
- For `guardian_of_minor` mode: the guardian acknowledges receipt of the
  crisis-card on the child's behalf (this is the only place guardian-ack
  on a behavioural-health item is appropriate; treatment-decision authority
  remains with the pediatric IRB-supervised slot per
  `prompts/tasks/guardian_ack_protocol.md`).

## Reviewer focus (henry + sid co-review)

- Is the prose acknowledging the verbatim trigger phrase (not paraphrasing)?
- Are all phone numbers in the jurisdiction registry above (no invented)?
- Is the handoff to `cancer-buddy-mind` explicit and copy-pasteable?
- For caregiver / guardian, is the second handoff present?
- Is `wave_lock: true` set and `acknowledged_by: pending` not pre-filled?

## Mechanical-gate coupling

- **G24** fires upstream and creates the trigger. This task package fires
  in response.
- **G8** L3/L4 disclosure gate sees this card as L4 (boundary) → acks
  enforced via standard ack flow.
- **G19** PI-imperative detector must NOT block "please call this line" —
  G19's imperative-detection rule has a carve-out for safety-card lines
  (see `g19_pi_imperative_detector.py` allowed-imperatives whitelist).
  If G19 false-positives on a phone-line CTA, surface as a Henry-audit
  issue not a gate block — the crisis-card must render.
