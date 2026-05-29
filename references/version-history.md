# OPL for Cancer — pre-v2 inline version notes

Historical per-version notes that previously lived inline at the top of
`SKILL.md`. Moved here in v2.7.2 (skill-creator-pro audit) to keep the
always-loaded skill body under the 500-line budget — these are changelog
content, not operating instructions. The authoritative changelog is
`CHANGELOG.md`; ADRs are under `docs/adr/`.

## version 1.3.2 — SAFETY hot-fix release (round-2 EVAL seed 11-20)

Adds G24 crisis-detection gate + `prompts/safety/crisis_detection.md` +
`prompts/tasks/crisis_card_emission.md` (SI/self-harm Wave-lock + jurisdictional
crisis-line surface); pediatric guardian mode via
`prompts/tasks/guardian_ack_protocol.md` + 4 pediatric planner rows; full
drilldown.md depth (4 drilldown classes); G22 lineage-context SKIP carve-out;
G23 fast-moving list extended to menin-i / EBV-CTL / NPC / HA-WBRT / Dato-DXd /
etc.; cancer-type description list +14 cancer types. See
`docs/adr/0008-eval-panel-round-2-v1.3.2.md`.

## version 1.4.0 — Round-2/3 deferred backlog batch fix (ADR-0008 D1-D13 priority A + B)

Adds: A1 `surveillance_schedule.md` (MEN1 + Lynch + LFS + HBOC syndrome-driven
surveillance lattice + G14 cohort match + G21 5yr DFS/OS anchor); A2
`irae_rechallenge.md` multi-organ schema (prior_irae_record list +
cumulative_organ_load_index + myocarditis G2+ → STRONG RELATIVE + pneumonitis-G3+
× any-G2+ rule + 2+ G3+ different-organs NEAR-ABSOLUTE rule); A3
`boundary_unregulated_channel_disclosure.md` retrospective mode (already-used
unregulated channel + forensic_evaluation_request + post-hoc records check); A4
`n1_cohort_projection.md` candidate_cohorts[] ordered fallback chain +
cohort_alternatives_attempted[] evidence; A5 `caregiver_filter_protocol.md`
(caregiver-preview brief + 3 honest options + patient_brief intact + Sid
explicitly declines disclosure decision on patient's behalf); B1
`patient_pushback_handling.md` (NEITHER concede NOR paternalism re-frame for
patient/sister-physician/caregiver dissent); B2 HKCTR Hong Kong Clinical Trials
Registry integrator (28 → 29); B3 TNBC + LM planner row (HA-WBRT + IT-MTX +
IT-pembrolizumab + Frances sacituzumab + Jen palliative); B4
`delivery_tone_hint: blunt|warm|clinical|unspecified` extraction in
intent_parser; B5 `cli.py acknowledge --batch L3-all | L4-all | Lall |
by-drug:<inn> | by-claim:<id_prefix> | by-card-prefix:<prefix>` + pi_delivery.md
`ack_consolidation_card`; B6 `n1_cohort_projection.md` lab_trajectory feature
(AFP / PSA / CA15-3 / CA-125 / CEA / CA19-9 / LDH trajectory not just static).
See `docs/adr/0008-eval-panel-round-2-v1.3.2.md` (Deferred section, now ✓).
