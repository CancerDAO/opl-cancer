## Task Package · boundary_unregulated_channel_disclosure

**Capability domain:** D5 — Synthesis / Delivery (boundary disclosure surface)
**Expert portfolio owners:** Sid (PI, holds the conversational surface) — co-reviewed by **Dennis** (cross-border regulatory framing) + **Frances** (compassionate-use / regulator-anchored alternative). Sid emits the card; Dennis + Frances each pass a reviewer block before render.
**Preferred integrator families:** F1 Literature (PubMed for any peer-reviewed evidence on the unregulated channel), F8 EAP registry (FDA/NMPA/EMA — to surface a *regulator-permitted alternative* whenever one exists), F3 Trials (CT.gov / ChiCTR / ISRCTN / EU-CTR — to surface enrollable trials of the same agent under IRB)

> "Patient asked about a Russian / Indian generic Lu-177 (Patient #9 E6). Founder-mode forbids paternalism — we cannot refuse to discuss the existence of the channel. Founder-mode equally forbids brokerage — we cannot name a clinic, a contact, a price, or a procurement path. The honest move is: *acknowledge → disclose the evidence base honestly → enumerate the risks mechanically → refuse procurement → route to the regulator-anchored alternative if one exists*."
>
> — v1.3.0 EVAL panel finding (Patient #9 E6 / unregulated PSMA-RLT channel). See `references/founder-mode-philosophy.md` L60-L74 ("the L4 boundary is *disclosure*, not *recommendation*").

OPL is asked about an **unregulated channel** when ANY of these signals appears in `patient_text`:

- Non-MRA jurisdiction sourcing (Russia / India / Mexico / non-EU-EEA / non-FDA / non-NMPA)
- "Grey-market" / "compassionate import" / "named-patient program" outside FDA/NMPA/EMA EAP
- "Clinic that will infuse X" with no IRB / no trial / no EAP wrap
- "Friend brought back X from Y" with no provenance
- Radionuclide / cell-therapy / gene-therapy product from a non-licensed manufacturing site
- Online pharmacy sourcing of a controlled / prescription oncology agent

For each such ask, OPL must emit a **boundary disclosure card** with the schema below. The card is L4 (mandatory patient acknowledgement) and is permanently locked — Sid cannot soften it via drill-down.

### Inputs

```json
{
  "patient_text": "...verbatim from user...",
  "agent_or_channel": "Lu-177-PSMA-617 (unregulated source) | bevacizumab-biosimilar from non-MRA site | ...",
  "jurisdiction_of_source": "RU | IN | MX | non-MRA-EU | other",
  "disclosure_mode": "prospective | retrospective | mixed",
  "forensic_evaluation_request": false,
  "retrospective_records": {
    "dosimetry_log_present": false,
    "batch_records_present": false,
    "packaging_photos_present": false,
    "post_exposure_lab_panel_present": false,
    "imaging_response_present": false,
    "adverse_event_log_present": false
  },
  "patient_profile": {...},
  "integrator_results": {
    "pubmed_results": [...],
    "eap_results": [...],
    "trials_results": [...]
  }
}
```

**v1.4.0 schema bump.** `disclosure_mode` is a new mandatory field:

- **prospective** (default, original v1.3.1 behaviour) — patient is *considering* the unregulated channel; OPL emits acknowledgement + risk inventory + procurement refusal + regulator-anchored alternative.
- **retrospective** — patient **already used** the unregulated channel (e.g. round-2 EVAL Patient #15 — already-administered grey-market Lu-177 from an Indian compounding pharmacy). OPL cannot un-do the exposure; the prospective `procurement_refusal_text` is the wrong response. Instead, OPL offers a forensic evaluation: what can be quantitatively checked *now* from the retrospective_records.
- **mixed** — patient used the unregulated channel once and is considering using it again. Emits BOTH the retrospective forensic offer AND the prospective refusal-plus-alternative; the two pieces live in the same card.

`forensic_evaluation_request: true` triggers the retrospective forensic block (see schema below). The boundary on procurement of FUTURE doses remains hard-coded.

### Required output (strict JSON, single object — no preamble, no fences)

```json
{
  "boundary_disclosure_card": {
    "acknowledgement_of_existence": true,
    "channel_name_in_patient_language": "<verbatim from patient_text, no euphemism>",
    "published_evidence_status": "no peer-reviewed | case reports only | preclinical only | regulated-product peer-reviewed but THIS source unstudied",
    "published_evidence_citations": [
      {"type": "pmid", "id": "<from pubmed_results>", "quote": "<exact>"}
    ],
    "risk_inventory": [
      "unknown QA / radiochemical purity (no batch certificate; no GMP audit)",
      "dose calibration drift (no on-site dosimetry against patient-specific kidney / parotid dose limits)",
      "no IRB oversight (no informed-consent process, no adverse-event reporting obligation)",
      "supply chain provenance (cold-chain breach undetectable; mislabelled product undetectable)",
      "no liability path (no manufacturer recall, no insurance, no medico-legal recourse on harm)",
      "cross-border legal exposure (importer-of-record liability in patient jurisdiction; customs seizure risk)"
    ],
    "procurement_refusal": true,
    "disclosure_mode": "prospective | retrospective | mixed",
    "procurement_refusal_text_prospective": "OPL does not name clinics, contacts, prices, brokers, or procurement paths for this channel. The team will not assist with importation. This is a hard boundary — not adjustable via drill-down.",
    "procurement_refusal_text_retrospective": "OPL cannot validate the source post-hoc — the exposure already happened and the chain of custody is what it is. What OPL *can* do is help you quantitatively check what your dosimetry log / batch records / packaging photos / post-exposure labs / imaging response / adverse-event log can tell us about: (a) whether the activity received matches a labelled dose; (b) whether radiochemical purity flags are detectable in the post-exposure renal / parotid / marrow signal; (c) whether the imaging response window aligns with the published Pluvicto / VISION cohort; (d) whether any flagged adverse events match the regulated agent's profile vs cross-contaminant signature. This is forensic-evaluation territory, not procurement assistance. OPL still will not name clinics, brokers, or contacts for FUTURE doses — the prospective boundary holds.",
    "procurement_refusal_text": "<picks text based on disclosure_mode>",
    "retrospective_forensic_evaluation": {
      "applicable": false,
      "what_we_can_check_with_available_records": [
        {
          "record_type": "dosimetry_log",
          "what_it_tells_us": "whether activity delivered (GBq) matches the labelled dose for this agent (e.g. Pluvicto 7.4 GBq per cycle); deviation > 15% surfaces a label-vs-actual mismatch flag",
          "claim_layer": "established"
        },
        {
          "record_type": "batch_records / packaging_photos",
          "what_it_tells_us": "manufacturer / lot number / radiochemical purity certificate presence; absence of certificate is itself a flag (regulated product carries lot-traceable QA — unregulated copy typically does not)",
          "claim_layer": "established"
        },
        {
          "record_type": "post_exposure_lab_panel",
          "what_it_tells_us": "renal function trajectory (creatinine + eGFR) over the post-exposure 6 weeks — Pluvicto VISION cohort baseline AE rate vs your trajectory; parotid Hounsfield + xerostomia symptom log; marrow recovery (ANC / Plt / Hgb) trajectory vs VISION baseline",
          "claim_layer": "established"
        },
        {
          "record_type": "imaging_response",
          "what_it_tells_us": "PSMA-PET / PSA / RECIST response curve vs the VISION published median PFS — alignment is partial evidence of an active agent reaching the target; non-response in the expected window is concerning but does NOT prove fraud",
          "claim_layer": "exploratory"
        },
        {
          "record_type": "adverse_event_log",
          "what_it_tells_us": "AE profile match to the regulated agent's known profile (e.g. Pluvicto: xerostomia, fatigue, anaemia, nausea); off-pattern AEs (e.g. neurotoxicity that does not fit beta-emitter profile) raise the cross-contaminant flag",
          "claim_layer": "exploratory"
        }
      ],
      "what_we_cannot_check_post_hoc": [
        "actual radiochemical purity of the administered dose (the sample is gone)",
        "ligand identity (PSMA-617 vs analog) without preserved aliquot",
        "carrier-impurity profile (heavy-metal / endotoxin / chemical-residue) without preserved aliquot",
        "manufacturing-site GMP compliance (independent of patient outcome — that is a regulatory question not a clinical one)"
      ],
      "forensic_summary_for_patient": "<one paragraph — what records you have / what they tell us / what remains uncheckable / what the next-step monitoring would be to detect a delayed adverse signal>",
      "next_step_monitoring": [
        "renal function q4w × 6mo (creatinine + eGFR + cystatin-C)",
        "parotid + lacrimal symptom + Hounsfield-CT q3mo × 12mo",
        "marrow recovery (CBC) q2w × 6mo then q4w",
        "PSA + PSMA-PET response curve at 8w / 16w / 24w post-exposure"
      ],
      "claim_layer": "exploratory",
      "permission_level": 3,
      "boundary_repeat": "Forensic evaluation does NOT validate the source; it only quantitatively checks what the available records say. The source remains unvalidated. FUTURE doses through this channel remain refused."
    },
    "regulator_anchored_alternative": {
      "exists": true,
      "options": [
        {
          "type": "EAP | trial | named-patient via MRA-EU | hospital-exemption",
          "program_or_trial_id": "<from eap_results or trials_results>",
          "regulator": "FDA | NMPA | EMA | MHRA | PMDA",
          "sponsor_contact_url": "<from integrator>",
          "claim_layer": "established | exploratory"
        }
      ],
      "alternative_summary": "<one sentence — what the regulator-permitted path looks like>"
    },
    "risk_disclosure_card": {
      "level": "L4",
      "boundary_disclosure": "EAP / clinical trial / regulator-permitted alternative is an exception path, not approval. Unknown long-term safety; no guarantee of efficacy; sponsor may decline; IRB approval required.",
      "patient_acknowledgement_required": true,
      "ack_text_for_patient": "I have read the unregulated-channel risk inventory above. I understand OPL will not assist with procurement of the unregulated product. I have read the regulator-anchored alternative path. I am the sole decision authority."
    },
    "claim_layer": "speculative",
    "permission_level": 4,
    "permanent_block_flags": {
      "broker_naming": true,
      "clinic_naming": true,
      "price_quoting": true,
      "procurement_logistics": true
    }
  },
  "summary": "<2-3 sentence Sid synthesis — non-directive, names the channel, names the risk class, names the regulator-anchored alternative if any>"
}
```

### Procedure

1. **Detect channel.** Match `patient_text` against the unregulated-channel signals listed above. If no match, this task is not applicable — return SKIP via empty card (see Empty-integrator handling).
2. **Detect disclosure_mode.** Walk `patient_text` for temporal markers: future-tense / "想知道" / "正在考虑" / "thinking about" / "should I" → **prospective**. Past-tense / "已经做了" / "用过了" / "我已经打过 3 cycle" / "got it from" / "received" → **retrospective**. Both signals present → **mixed**. Default if ambiguous → **prospective** (the safer assumption — emits the procurement refusal + alternative). Set `boundary_disclosure_card.disclosure_mode`.
3. **Acknowledge existence.** `acknowledgement_of_existence: true` is **mandatory** — never omit. Founder-mode forbids pretending the channel does not exist or refusing to discuss it. For retrospective mode, acknowledge that the exposure already happened ("I hear you — you've already used it; we cannot validate the source post-hoc, but here is what we can quantitatively check").
4. **Honest evidence status.** Search `pubmed_results` for THIS specific source / lot / channel. If only the regulated counterpart has peer-reviewed evidence, declare `published_evidence_status: "regulated-product peer-reviewed but THIS source unstudied"`. Do not extrapolate from the regulated product's evidence to the unregulated source.
5. **Mechanical risk inventory.** Emit at least the 6 risks listed in the schema. Add jurisdiction-specific risks if known (e.g. customs seizure history, prior contamination reports). Each risk is a class, not a slur on a country — keep language neutral and factual.
6. **Procurement refusal — mode-aware text selection.** `procurement_refusal: true` is mandatory in ALL modes (no mode unlocks future-procurement assistance). `procurement_refusal_text` selection:
   - `prospective` → `procurement_refusal_text_prospective`
   - `retrospective` → `procurement_refusal_text_retrospective` (acknowledges the exposure happened, offers forensic evaluation, holds future-procurement boundary)
   - `mixed` → concatenate both texts in order
   Drill-down requests are still refused with the appropriate text repeated verbatim. This is permanent — G7 + G19 + permanent_block_flags enforce.
7. **Retrospective forensic block.** If `disclosure_mode ∈ {retrospective, mixed}` AND `forensic_evaluation_request: true` (default true in retrospective/mixed modes) → emit `retrospective_forensic_evaluation.applicable: true` + the `what_we_can_check_with_available_records[]` list filtered by which `retrospective_records.*_present` flags are true. If NO records are present, `what_we_can_check_with_available_records: []` and `forensic_summary_for_patient` becomes: "no preserved records remain; only forward monitoring (renal / marrow / parotid surveillance) can detect a delayed adverse signal — no retrospective forensic claim can be anchored". Boundary_repeat is mandatory non-empty in all retrospective/mixed cases.
8. **Regulator-anchored alternative.** Search `eap_results` + `trials_results` for the regulator-permitted version of the same agent / mechanism (e.g. for unregulated Lu-177-PSMA: look up Pluvicto FDA EAP, the VISION post-hoc EAP, ENZA-p / PSMAddition / SPLASH active trials, and any NMPA approval status). Surface up to 3 alternatives, each with a real sponsor URL from integrators — never invent. In retrospective mode the alternative is "if you want to continue treatment, here is the regulator-anchored path forward".
9. **L4 risk-disclosure-card.** `level: "L4"` is mandatory in all modes. `patient_acknowledgement_required: true` is mandatory. The ack text is the literal contract — Sid will not render without an ack signature recorded in `pi_session/outstanding/`.
10. **Single best-fit reviewer pairing.** This task requires Dennis (regulatory) + Frances (EAP / sponsor pathway) to both pass before render. Disagreement between them surfaces via G20 in Sid's prose.
11. **Output ONLY the JSON object.**

### Mechanical gates this task must satisfy

- **G1 / G2** — every PMID + quote recoverable in `pubmed_results`; sponsor URLs recoverable in `eap_results` / `trials_results`.
- **G3** — agent names use generic INN (Lu-177-PSMA-617, not brand "Pluvicto" except when discussing the FDA-approved program by name).
- **G7 imperative-detector** — `procurement_refusal_text` is the only place an imperative is allowed ("OPL does not …"), and it is hard-coded. No imperatives elsewhere.
- **G8 Level-3-4 disclosure** — L4 ack present; if absent → BLOCK before render.
- **G11 NoSilentFallback** — if `pubmed_results` is empty, do not fabricate "case reports exist"; declare `published_evidence_status: "no peer-reviewed"`.
- **G19 PI-imperative-detector** — Sid's downstream prose may not contain action verbs ("you should try", "you should avoid"). Sid frames as inventory + alternative.
- **G7 + G19 + permanent_block_flags** — broker / clinic / price / procurement-logistics naming is permanently blocked. Drill-down requests for these get the canonical refusal text.

### Reviewer focus

Reviewer pairing **Sid ⟂ Dennis ⟂ Frances** (three-way) checks:

- **Sid** — acknowledgement is present, language is non-paternalistic, the patient's question is not dismissed.
- **Dennis** — risk inventory is jurisdictionally accurate (customs path, MRA framing, importer-of-record liability statement correct for patient's jurisdiction).
- **Frances** — regulator-anchored alternative is real (sponsor URL recoverable in integrator), is a *true* alternative (same agent / mechanism / line), not just any open trial.

Sid + Dennis + Frances must all sign before delivery. Disagreement surfaces in the patient brief as a `## Team 内部分歧` block per G20.

### Empty-integrator handling

If the channel-detection step fires but `pubmed_results` + `eap_results` + `trials_results` are ALL empty:

- `boundary_disclosure_card.acknowledgement_of_existence: true` (still mandatory)
- `published_evidence_status: "no peer-reviewed"` (the empty result is the answer — do not fabricate)
- `published_evidence_citations: []`
- `regulator_anchored_alternative.exists: false`
- `regulator_anchored_alternative.alternative_summary: "Live integrator returned no regulator-permitted alternative for this agent. No alternative path can be surfaced from current data; further retrieval is required before a regulator-anchored alternative can be offered. Patient is sole decision authority; OPL still refuses procurement of the unregulated channel."`
- `procurement_refusal: true` (still hard-coded)
- `risk_disclosure_card.level: "L4"` (still mandatory)
- `claim_layer: "speculative"`

Per `memory/feedback_no_offline_only.md`: integrator empty does not relax the procurement refusal and does not relax the L4 acknowledgement. If the patient retries with a more specific channel query, OPL re-runs the integrator search; it does not synthesize the alternative from training data.

### Hard rules (non-negotiable)

- `acknowledgement_of_existence: true` is **never** false.
- `procurement_refusal: true` is **never** false.
- `permanent_block_flags.broker_naming: true` is permanent for the session.
- `permanent_block_flags.clinic_naming: true` is permanent for the session.
- The patient may not unlock procurement assistance via drill-down. Drill-down requests for procurement return the canonical refusal text + an optional second cross-border-navigation hand-off (`prompts/tasks/cross_border_navigation.md`) if they want help with the *regulated* path.
- This card never includes prices, customs codes, broker emails, individual physician names, freight forwarders, or import-permit how-to.
