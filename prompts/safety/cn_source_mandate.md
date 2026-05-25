# CN-Source Mandate (v1.5 P1-6)

When the patient is in mainland China (`profile.country == "CN"` or
`profile.city` resolves to a mainland city), every expert persona that
produces clinical recommendations MUST cross-reference at least the
following CN-domestic sources before finalizing a report. v1.4 retro
(F15 / AP-7): Iain (literature) explicitly flagged
`evidence_gap_1/2/3` for raltitrexed+sintilimab Chinese-language
literature (CNKI / 万方 not searched), and no persona prompt mandated
CN-source coverage.

## Required CN sources (by domain)

| Domain | Source | What to extract |
|---|---|---|
| Drug approvals | 国家药监局 (NMPA) at https://www.nmpa.gov.cn/ | NMPA approval date, indication scope, dosage label, accelerated approval flag |
| Reimbursement | 国家医保局 NRDL + 商保白名单 | listing status, copay tier, regional adjustments (Beijing 普惠 / Shanghai 沪惠保 / Guangdong 粤医保 / Hangzhou 西湖益联) |
| Treatment guidelines | CSCO 临床指南 + 中华医学会 expert consensus | Cat 1A/II/III tier, divergence from NCCN |
| Clinical trials | ChiCTR (via mcp__chictr) + CT.gov CN sites + 国家临床试验数据库 | NCT or ChiCTR ID, recruiting status, mainland CN site count |
| Cross-border | 海南博鳌乐城 (Boao) special-import + 港澳药械通 (GBA cross-border) + 北京天竺综保 | actual operationalized pathway (general/named-patient/IIT) |
| Drug repository | 三医联动 / 国家医保医药管理 (HIIS) | drug retail price tier, hospital procurement status |
| Real-world evidence | RWE 中国队列 (e.g. China KRAS Cohort, ATTRACTION-2 sub-cohort) | mainland CN patient outcome data, ethnicity-adjusted if available |

## Required behavior

1. When `profile.country == "CN"`, the persona's `Retrieval summary`
   footer (v1.5 P1-7) MUST include a `cn_sources` subsection listing
   which CN sources were consulted and which were skipped + why.
2. If a regimen is recommended that is NOT NMPA-approved for the
   indication, the persona MUST surface the off-label status + the
   3 access channels (Boao / EAP / HK), in the regimen card.
3. If a CT.gov trial is suggested but the trial has no mainland CN
   site, the persona MUST flag `[NO_CN_SITE]` and Frances / Dennis
   MUST cover the cross-border path.
4. If a CSCO consensus contradicts NCCN, the persona MUST surface both
   tiers explicitly. Default rendering shows CSCO first for mainland
   CN patients, with the NCCN comparison side-by-side.

## What this is NOT

- It is NOT a CN-only restriction — Western evidence (FDA / EMA / NCCN
  / PubMed) remains the spine. CN sources are the patient-applicability
  + operational-feasibility layer.
- It is NOT a translation requirement — sources can be in English if
  they are about CN regulation (FDA approval, NMPA WhatsThis pages).
- It is NOT a substitute for Patient Translator (`patient_plain_brief_rendering`)
  — that handles language. This handles source coverage.

## Failure modes the auditor checks

| Failure | What Henry catches |
|---|---|
| CN patient + no CN source cited | retrieval footer's `cn_sources` is empty → flag |
| Off-label regimen recommended w/o access path | regimen card missing 3-channel disclosure → block via G8 (L3/L4 disclosure gate) |
| Trial without CN site recommended w/o Frances/Dennis lens | planner heuristic should fire those experts (P0-6); if they're absent, flag the planner output |
| CSCO/NCCN divergence hidden | cross_source_consistency gate flags |

## References

- `references/clinical_stop_rules.json` (v1.5) — stop rules pinned to
  all clinical personas.
- `prompts/safety/subagent_file_write_contract.md` (v1.5) — output
  contract every subagent obeys.
- `prompts/experts/_shared/persona_prefix.md` §4 (v1.5) — traceability
  footer schema.
- ADR-0008 D9 — original v1.3.2 deferred backlog item that this
  document closes for v1.5.
