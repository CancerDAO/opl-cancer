# Task Package · patient_pushback_handling

**Capability domain:** D5 — Synthesis / Delivery (patient / physician-audit pushback re-framing)
**Expert portfolio owners:** **sid** (PI, sole conversational surface — re-frames the disagreement honestly) co-reviewed by **henry** L2 (auditor — disagreement-surfacing layer). Sid + Henry L2 pass before render.
**Preferred integrator families:** F1 Literature (PubMed for the published critique / dissenting opinion if cited), F2 Guidelines (NCCN / CSCO / ESMO Category-of-Evidence level for the disputed claim — runtime-verified, no edition pin)

> "Patient #18 sister-physician (gynecologic oncologist) drilled down on the zolbetuximab + chemo recommendation for HER2-low / CLDN18.2+ gastric and said: 'The SPOTLIGHT absolute PFS Δ is 1.8 months, not the 21% relative HR you led with — and the OS HR is borderline. Why are you leading with the relative effect?' Patient #14 老婆 said: 'team 给我推 rechallenge,可是 Mark 自己都说 g2 myocarditis 复发 50% — 我不想 rechallenge,但是 team 跟我说 PFS 数字这么好…' These are NOT new triggers (那是 NEW_GOAL); they are dissent on an already-delivered claim. v1.3.x had no canonical response. Founder-mode answer: NEITHER concede (echo violates feedback_third_party_lens) NOR paternalism (don't restate same number louder). Surface the alternative read honestly + integrator-anchored dissent + value-lattice. Patient decides."
>
> — v1.4.0 deferred backlog item D9 (round-2 EVAL Patient #18 sister-physician audit + Patient #14 caregiver dissent). See `docs/adr/0008-eval-panel-round-2-v1.3.2.md` (Deferred — D9 "patient_pushback_handling task").

This task is invoked when:

1. Patient (or family member or auditing physician) pushes back on a previously-delivered claim by name (e.g. claim_id reference, agent name, statistic value) — NOT a new trigger / new goal.
2. The pushback contains substantive content (a number, a citation, a value-axis disagreement) — not pure emotion (that routes to `cancer-buddy-mind` per scope_handoff_routing.md).
3. The pushback is on a Wave-1-through-4 outcome, not on a process complaint (process complaints go to `pi_session/feedback_log/` directly).

The task is **not** a re-run of the Wave (that would be a new NEW_GOAL trigger via `intent_parser`). It is a re-frame + re-anchor of an existing claim, surfacing the dissent + value-lattice + integrator-anchored alternative-read honestly. NEITHER concede (which would echo the pushback and violate `memory/feedback_third_party_lens` independence) NOR paternalism (which would restate the original number louder, ignoring the patient's stated objection).

## Inputs

```json
{
  "original_claim_id": "claim_<8-char>",
  "original_claim": {
    "claim_text": "...",
    "claim_layer": "established | exploratory | speculative",
    "permission_level": 0,
    "evidence": [{"type": "pmid", "id": "...", "quote": "..."}, ...],
    "provenance_hash": "sha256:...",
    "delivered_via": "patient_brief.html | pi_delivery.md | drilldown_response"
  },
  "pushback_text": "...verbatim from user, in patient's own language...",
  "pushback_role": "patient | family_member | physician_audit",
  "pushback_axis_hint": "<absolute_vs_relative_effect | dissent_on_citation | dissent_on_subgroup_applicability | value_axis_mismatch | recency | safety_weight | uncategorised>",
  "patient_profile": {...},
  "patient_value_lattice": {
    "stated_values": ["QoL", "OS_months", "treatment_burden", "trial_access", "..."],
    "ranked_order": "...verbatim from pi_session/preferences.json if present..."
  },
  "integrator_results": {
    "pubmed_results": [...],
    "nccn_excerpts": [...],
    "csco_esmo_excerpts": [...]
  }
}
```

## Outputs (strict JSON, single object — no preamble, no fences)

```json
{
  "pushback_card_id": "pushback_<original_claim_id>_<utc_iso>",
  "original_claim_id": "<echo>",
  "pushback_received": {
    "verbatim": "<pushback_text>",
    "role": "patient | family_member | physician_audit",
    "axis_classified": "absolute_vs_relative_effect | dissent_on_citation | dissent_on_subgroup_applicability | value_axis_mismatch | recency | safety_weight | other",
    "rationale_for_axis": "<one line — why Sid classified this axis>"
  },
  "acknowledge_text": "你 / 你 sister / 你 husband 提出来的这个 — 我把它当成一个 substantive 的 critique 处理,不当成 emotion 处理。我下面把 alternative read 摆出来,把 integrator-anchored dissent 摆出来,把 value-lattice 摆出来,你来决定 framing。我不会因为你 push back 就改原来的 number,也不会因为你 push back 就 louder 地把原来的 number 再说一遍。",
  "alternative_read": {
    "applicable": true,
    "alternative_framing": "<the alternative read of the same evidence — e.g. 'SPOTLIGHT absolute PFS Δ 1.8 months IS the right number to lead with for QoL-prioritised decisions; the relative HR 0.75 IS the right number for between-trial pooling and meta-analysis purposes; both are correct depending on the question being asked'>",
    "supporting_evidence_pmid": ["<from pubmed_results — published critiques / editorials / dissenting commentary>"],
    "claim_layer_of_alternative": "established | exploratory",
    "honest_call": "<one sentence — what Sid honestly thinks about the merit of the alternative read, without conceding the original was wrong>"
  },
  "integrator_anchored_dissent": [
    {
      "source": "PubMed editorial / NCCN footnote / CSCO Category 2A vs 1 / ESMO MCBS",
      "anchor_pmid_or_section": "<from integrators>",
      "dissent_content": "<verbatim or paraphrased — what the dissent in the literature actually says about this claim>",
      "claim_layer": "established"
    }
  ],
  "value_lattice_reframe": {
    "patient_stated_value": "<from patient_value_lattice.ranked_order>",
    "claim_under_dispute_aligns_with": "<which patient value the original claim aligns with — e.g. 'PFS_months_relative_HR aligns with treatment-line decision urgency'>",
    "alternative_read_aligns_with": "<which patient value the alternative read aligns with — e.g. 'absolute PFS Δ months aligns with treatment-burden + QoL trade-off framing'>",
    "honest_note": "If your value ranking has shifted since you stated it, the lattice can be re-ranked — let me know and Sid + team re-frame downstream. The original claim's evidence quality didn't change; what changed (if anything) is which framing fits your value better."
  },
  "what_OPL_did_NOT_do": [
    "did NOT re-run a Wave (this is a re-frame, not a new trigger; if you want a new Wave use a NEW_GOAL trigger)",
    "did NOT change the original claim's evidence anchors (PMIDs / provenance hash unchanged)",
    "did NOT concede that the original claim was wrong (re-framing is not conceding)",
    "did NOT restate the original number louder (paternalism is not the answer to dissent)"
  ],
  "honest_team_position": "<2-3 sentences — Sid's honest synthesis of where the team lands now: 'team 仍然认为 original claim 在 PFS_months_relative_HR 这一个 framing 下 holds;但是你 sister 提出的 absolute Δ framing 是 valid 的,而且更 align 你 stated value 的 QoL 优先。我把两个 framing 都列出来。'>",
  "your_choices_optionful": [
    {
      "choice": "accept the alternative_read as your operative framing — team re-frames downstream deliverables with this framing as the primary",
      "what_OPL_does": "Sid emits a delivery update card; original claim's evidence anchors unchanged; framing reordered"
    },
    {
      "choice": "accept the original claim's framing — you've read the alternative + dissent and stay with the team's original framing",
      "what_OPL_does": "team continues with original framing; pushback is logged in pi_session/feedback_log/ for transparency"
    },
    {
      "choice": "re-rank your value lattice — your values have shifted, which changes which framing fits",
      "what_OPL_does": "Sid invokes PREFERENCE_UPDATE intent (per intent_parser.md) and re-runs the value-aligned framing across active claims"
    },
    {
      "choice": "ask for a Wave re-run (NEW_GOAL) — you want the team to re-research this claim with new questions",
      "what_OPL_does": "Sid hands off to intent_parser.md as a NEW_GOAL trigger and queues a fresh Wave 1 retrieval"
    }
  ],
  "claim_layer": "established",
  "permission_level": 2,
  "logged_to_feedback_log": true
}
```

## Procedure

1. **Detect pushback (not new trigger).** Match `pushback_text` against substantive-disagreement patterns: number-mismatch ("you said X% but it's Y%"), citation-dispute ("that PMID doesn't say that"), subgroup-applicability ("that data is for naive patients; I'm late-line"), value-axis ("you led with PFS but I care about QoL"), recency ("that PMID is 2019; what about 2024-2025"), safety-weight ("you minimised the irAE risk"). If the pushback is process-complaint or pure emotion, redirect — process to `pi_session/feedback_log/`, emotion to `cancer-buddy-mind`.

2. **Classify the axis.** Set `pushback_received.axis_classified` to one of the canonical axes. Multi-axis is allowed (set the primary + the secondary in a separate field if needed).

3. **Anchor acknowledgement.** Emit `acknowledge_text` verbatim from the schema. The acknowledgement is the founder-mode discipline: NEITHER concede NOR paternalism. Sid takes the critique as substantive, names the response posture explicitly.

4. **Compose alternative_read.** Search `pubmed_results` for the *published critique* or *dissenting editorial* on this exact claim (SPOTLIGHT critics on absolute PFS Δ vs OS HR are published in JCO / Ann Oncol editorials; NCCN Category 1 vs 2A debates are documented in NCCN footnotes; ESMO MCBS dissent is published in Annals of Oncology). If a published dissent exists → cite it with PMID; declare `applicable: true`. If no published dissent exists for this claim → declare `applicable: false` and the alternative_read is the team's internally-generated alternative framing of the same evidence (which is still legitimate — different framings of the same data are not concessions).

5. **Anchor dissent via integrators.** Emit `integrator_anchored_dissent[]` with up to 3 entries: published editorials / NCCN footnotes / CSCO category levels / ESMO MCBS scores that surface the dissent honestly. No fabrication — each entry must have a recoverable PMID or guideline section.

6. **Value-lattice re-frame.** Read `patient_value_lattice.ranked_order`. Map the original claim's framing to its aligning value-axis; map the alternative_read to its aligning value-axis. If the alternative_read aligns better with the patient's stated value than the original claim's framing, surface this honestly. Do NOT silently re-rank — that is the patient's call.

7. **Emit "what_OPL_did_NOT_do".** The four explicit invariants:
   - did NOT re-run a Wave
   - did NOT change evidence anchors
   - did NOT concede
   - did NOT restate-louder
   These appear in the patient-facing card so the patient knows what posture Sid took.

8. **Sid's honest team position.** 2-3 sentences synthesising where the team lands. The position can include "team agrees with the dissent on the absolute-vs-relative axis but disagrees on the safety-weight axis" — partial agreement is allowed and surfaced honestly per `memory/feedback_third_party_lens`.

9. **Optionful next-step.** Four canonical choices in `your_choices_optionful`. The patient picks; Sid does not recommend.

10. **Log to feedback_log.** All pushback cards are appended to `memory/feedback_log/` with the original_claim_id + pushback_card_id, even if the patient chooses to stay with the original framing — this is the trust trail.

11. **Output ONLY the JSON object.**

## Mechanical gates this task must satisfy

- **G1 / G2** — every PMID in `alternative_read.supporting_evidence_pmid` + `integrator_anchored_dissent[].anchor_pmid_or_section` recoverable in `pubmed_results`.
- **G7 imperative-detector** — `acknowledge_text` + `honest_team_position` + `your_choices_optionful` use non-directive framing. Sid surfaces options; does not pick.
- **G19 PI-imperative-detector** — Sid does not imperative the patient's framing choice.
- **G20 PI-disagreement-surfacing** — this task IS the disagreement-surfacing card; Henry L2's disagreement summary must include this pushback entry.

## Reviewer focus

Reviewer pairing **Sid ⟂ Henry L2** checks:

- Did Sid acknowledge the critique as substantive (not as emotion)?
- Did Sid avoid conceding (re-framing ≠ conceding)?
- Did Sid avoid paternalism (no louder restatement)?
- Is the alternative_read anchored to a published dissent if one exists, or honestly declared as internally-generated if not?
- Is the value-lattice re-frame honest about which framing aligns with which patient value?
- Did the four `what_OPL_did_NOT_do` invariants get emitted verbatim?
- Was the pushback logged to feedback_log?

## Empty-integrator handling

If `pubmed_results` + `nccn_excerpts` + `csco_esmo_excerpts` are ALL empty for the disputed claim:

- `alternative_read.applicable`: keep `true` if Sid can articulate an internally-generated alternative framing of the same evidence; set `false` only if no alternative framing exists.
- `alternative_read.supporting_evidence_pmid: []` and `claim_layer_of_alternative: "speculative"` — honest about the unanchored state.
- `integrator_anchored_dissent: []`.
- `honest_team_position` adds: "live integrator returned no published dissent for this claim; team's alternative framing is internally generated rather than literature-anchored — treat the alternative_read as exploratory not established".

Per `memory/feedback_no_offline_only.md`: do NOT fabricate a published dissent that Sid "remembers". The LLM "remembering" the SPOTLIGHT JCO editorial is not retrieval.

## What this task is NOT

- It is NOT a re-run of the Wave (use NEW_GOAL trigger).
- It is NOT a way to silence the patient ("here's why you're wrong, please move on").
- It is NOT a way to silence the team ("here's why we were wrong, please drop the claim").
- It is NOT a concession mechanism — re-framing the same evidence is not conceding the evidence was wrong.

## Founder-mode philosophy note

The founder-mode principle "model disagreements surfaced openly" + "patient is sole decision authority" + "no paternalism, no hidden disagreements" are the three legs of this task. Disagreement that comes from the patient / family / physician-audit is handled with the SAME discipline as internal reviewer disagreement (per G20): named openly, anchored to evidence where possible, framed against the patient's value lattice, decided by the patient. Sid is the surface; not the arbiter.

## Downstream consumers

- `pi_delivery.md` reads the `pushback_card_id` and re-emits the delivery section with the alternative_read framing if the patient picked that choice.
- `patient_brief_rendering.md` consumes the `value_lattice_reframe` to re-rank claim ordering on render if the patient re-ranked.
- `memory/feedback_log/` stores the full card for cross-session continuity.
- `scope_handoff_routing.md` is invoked only if the pushback is actually a scope-mismatch (e.g. "I want to talk to a real doctor about this" → `cancer-buddy-find-care`).
