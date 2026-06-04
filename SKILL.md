---
name: opl-cancer
description: "OPL for Cancer (CancerDAO) — a cancer patient's own AI scientist team that produces a PMID-anchored, three-tier-labelled research brief (not treatment advice; the patient is sole decision authority). Use when a cancer patient or caregiver has records (PDF/images/folder/zip) and wants research-grade analysis: next-line options, NGS interpretation, clinical-trial matching, expanded-access / cross-border navigation, hypothesis generation, drug repurposing, public-dataset re-analysis, or a second look at a treatment plan. Do NOT use for one-shot record organization alone, a single static report, undiagnosed / triage questions, or emotional support — OPL is the full multi-wave research-team run. Triggers: opl, opl-cancer, OPL for Cancer, AI scientist team, founder mode against cancer, 我的 AI 科研团队, 把我的病例当 N=1 跑研究, 标准治疗用尽, 二线/三线进展, 下一线方案, 靶点协同, world-unknown candidates, 同情用药, cross-border, 海外就医, hypothesis tournament, drug repurposing, NGS 解读, 临床试验匹配."
license: Apache-2.0
metadata:
  author: CancerDAO Contributors
  version: "2.10.0"
  tags: oncology precision-medicine ai-scientist-team founder-mode hypothesis-generation co-scientist robin bixbench meta-analysis clinical-trials evidence-grounded world-unknown-candidates kg-synergy undrugged-target-design trace-digest-evolution equipped-experts bio-skills msi tmb hrd acmg cpic survival-analysis wave6 manuscript n1a preprint n1arxiv submission preprint-platform pr-assembly cross-repo-submission compositional method-primitive role-taxonomy n=1 automl prognosis
---

# OPL for Cancer — your own AI scientist team

> **North Star:** every person gets a complete AI scientist team working for them alone — retrieving the world-known + producing the world-unknown — and the patient is the sole decision-maker of their own case. (full text + per-version history: [`references/version-history.md`](references/version-history.md); changelog in `CHANGELOG.md`.)

OPL for Cancer is the patient's own scientist team, built by **CancerDAO**. **Not** a clinical decision-support tool, **not** a diagnostic device, **not** a doctor-replacement. It is an open-source skill plugin that gives one patient one PI (Sid) coordinating a **20-expert virtual lab** (v1.x 18 + v2.0 Maya KG-synergy reasoner + Julius in-silico medicinal chemist) + an IRB-substitute auditor (Henry) + 29 live data integrators + PrimeKG stub, running a 5-Wave research lifecycle from records-in to patient-brief-out — with every claim PMID-anchored, provenance-hashed, three-tier-labelled, and reproducible.

Patient is sole decision authority. No human-in-the-loop external sign-off. Model disagreements surfaced openly. Level-3/4 high-stakes claims gated by patient-acknowledgement, never by physician sign-off.

## Operating contract (v2.7.0 — read before anything else)

> Root-cause fix for session 0d1017d4: OPL under-delivered (ran 4 generic agents instead of the planned team, skipped Wave 2/3/4, skipped the audit) **and** fabricated content (invented lab values before OCR; cited 4 real-but-wrong-paper PMIDs). It only became complete because a domain-expert user kept pushing. A normal patient cannot do that. See `docs/ANTI_PATTERNS.md` + `docs/adr/0026-delivery-non-bypassable.md`.

These five rules are non-negotiable and **mechanically enforced** (gates G34–G37 + G1/G2/G36) — violating them makes delivery `exit ≠ 0`, not a warning:

1. **One simple prompt → full professional service.** The patient may give a single vague sentence ("帮我看看我爸下一步怎么办"). You MUST NOT ask them to specify which experts, which waves, or how deep. The planner expands a simple goal into the full research agenda; you run it. Default to the comprehensive path, never a minimal one.
2. **Never under-deliver, never wait to be pushed.** Run the FULL planned team and every warranted wave. Do not stop at a partial answer and wait for the user to ask "did you run the experts?". `G37 service_completeness` BLOCKS delivery if any planned expert produced no report or a warranted wave left no artifacts. To narrow scope you need an explicit, user-confirmed `replan.json` — you may never shrink the service silently.
3. **Never collapse experts to save tokens.** Substituting fewer generic ("general-purpose") agents for the named personas is FORBIDDEN and `G37` HARD-BLOCKS it (non-roster authors are detected). Token cost is not a reason to do less analysis (`models.yaml` core principle #5).
4. **Never free-hand a brief.** Every delivered conclusion must originate from a `triggers/<run_id>/` artifact produced by the pipeline and verified by `opl-cancer attest` / `deliver --finalize`. If you have not run `plan` (which mints the `run_token`) and the waves, **you have not run OPL** — say so and run it; do not write a report from memory. `G34 delivery_attestation` refuses any brief with no manifest / no provenance journal / no real Henry audit.
5. **Never fabricate a clinical fact or a citation.** Do not write a lab value, stage, or biomarker you did not read from a source — write `UNKNOWN`. Every clinical value must carry a `[[src:...]]` anchor to an OCR sidecar (`G35`). Every PMID must come from a live PubMed search this session and actually be about the claim — never from model memory (`G1`+`G2`+`G36`; the incident's knee-OA / kefir / glioma / macrophage PMIDs are now blocked).

**The one-command path:** `opl-cancer go --patient <dir> --goal "<the patient's words>"` drives the whole lifecycle and tells you the exact next action (with the full expert list) until the delivery is complete + attested. Prefer it over driving the steps by hand.

## Execution model (v2.8 harness-split — read with rule 4)

OPL is two halves that hand off via artifacts on disk. Do not confuse them:

- **You (the host agent) are the only reasoning brain.** The named experts, the planner's judgment, hypothesis generation, cross-expert review, and Henry's disagreement reasoning are all done by **you dispatching subagents** per `prompts/experts/expert_task_package.md` (+ `prompts/render/`, `prompts/auditor/`). Each subagent writes its report into `triggers/<run_id>/tasks/<task_id>/`. **There is no LLM inside the Python package — it never calls a model.**
- **The `opl-cancer` CLI is a deterministic harness, not an executor.** `plan` / `wave1..4` / `run` / `audit` / `deliver` / `attest` scaffold the run, pre-fetch live integrator data, **validate the artifacts you wrote**, run the 42 gates (verdict = Python, `exit≠0` on violation), hash provenance, and assemble the brief. `opl-cancer wave1` and friends are *state-checks*: they confirm your dispatched reports exist and pass gates — they do **not** produce the reasoning.
- So every wave is a **two-beat loop**: (1) you dispatch the experts as subagents → they write reports; (2) you run the matching CLI command → it validates + gates and tells you the next beat.
- **Install consequence:** `pip install -e <skill_dir>` installs the *harness*. The patient path needs **no LLM provider key** — the reviewer is a second subagent of yours, not a Python API call. (Provider keys only feed the optional self-improvement engine, which is being extracted.)

## Where patient data lives

Patient records, run artefacts, memory ledger all live **outside** the skill repo (so the skill can be reinstalled / version-bumped without touching patient state):

```
~/CancerDAO/patients/<patient_code>/
├── 01_当前状态/ … 11_诊断证明/      # 11-bucket organized records (canonical OPL input layout)
├── case_text.md · profile.json · timeline.md · readiness.json
├── inbox/                           # new file drop → Feedback agent watches
├── pi_session/                      # Sid state: conversation.jsonl + preferences + outstanding/* + push_budget
├── memory/                          # Project Memory (versioned, append-only)
│   ├── version.json · insights/<id>_vN.json · hypotheses/<id>.json
│   ├── citations/<pmid>.json · evidence_graph/snapshot_<v>.json
│   ├── tournaments/<round_id>.json · provenance/index.jsonl
│   └── feedback_log/<id>.json
├── triggers/<run_id>/               # one Wave run = one run_id
│   ├── plan.json · tasks/<task_id>/ · data/ (GEO/ArrayExpress/analysis/)
│   ├── meta_analysis/ · tournament/ · provenance.jsonl
│   └── delivery/patient_brief.html + .md + pi_delivery.md
└── archives/                        # closed triggers archived here
```

Override default location: CLI `--patient-root <path>` (highest) > env `OPL_PATIENT_DATA_ROOT` > default `~/CancerDAO/patients/`.

## Evidence Contract

OPL touches facts that are dangerous to guess. Declared once so no run re-litigates
"can I make this up?" under pressure (enforced by gates G1/G2/G34/G35/G36):

- **Sources of record (live, never memory):** PubMed / Europe PMC (PMIDs),
  ClinicalTrials.gov + ChiCTR (trials), NCCN / CSCO (guidelines), OncoKB / CIViC /
  ClinVar (variants), and the 29 integrators in `references/integrator-catalog.md`.
  Prefer live retrieval over the model's memory every time.
- **Never fabricate** a lab value, stage, biomarker, dose, PMID, or trial ID. A
  clinical value you did not read is written `UNKNOWN` and carries a `[[src:...]]`
  anchor to its OCR sidecar (`G35`). Every PMID comes from a live search this
  session and must be on-topic (`G1`/`G2`/`G36`).
- **Fallback = raise, never substitute.** If a required input or integrator is
  unavailable, name the exact missing item and continue only with retrieved /
  user-provided evidence; the LLM never fills the gap from memory, and an offline
  citation layer blocks delivery rather than silently passing (`G11`).

## Workflow Index

After triggering, load exactly one workflow — the procedure is NOT inlined here.

| Workflow | Load when |
|---|---|
| [`workflows/run-lifecycle.md`](workflows/run-lifecycle.md) | Running a patient case end-to-end — the 11-step dialog (organize → plan → Wave 1-5 → Henry audit → deliver → iterate). Default path; prefer `opl-cancer go`. |
| [`workflows/interrupt-protocol.md`](workflows/interrupt-protocol.md) | The patient interrupts mid-run (skip / simplify / pause / cancel / replan / status). |

**Routing rules:** a new patient request → load `run-lifecycle.md`. A mid-run skip/simplify/pause/cancel/replan/status → load `interrupt-protocol.md`. The five Operating-contract rules + the Evidence Contract above bind every workflow.

## Core principles (founder-mode)

1. **Patient is sole decision authority.** Sid never commands. No physician sign-off is required — physicians may drill-down to verify, but they do not gate delivery. Patient ack on L3/L4 is the only human gate.
2. **No paternalism, no hidden disagreements.** Reviewer disagreement is always surfaced. Three-tier labels never stripped. Uncertainty stated, not papered over.
3. **Provenance-strict.** Every numeric / factual claim carries a `[PMID]` / `[NCT]` / `[NCCN-section]` / `[notebook]` anchor + SHA-256 provenance hash. G2 mechanical gate blocks unanchored claims at write time.
4. **No silent fallback.** Integrators raise on API failure. LLM never substitutes for a missing data point. Clinical values you did not read are written `UNKNOWN`, never invented (`G35`). PMIDs come from a live search and must be on-topic, never from model memory (`G1`/`G2`/`G36`).
5. **No model downgrade for cost.** Per `models.yaml`: Opus 4.7 for code / hypothesis reasoning / chair; MiniMax-M2.7 for lit synthesis / reviewer. Don't trade depth for tokens.
6. **No under-delivery, no expert collapse, no free-handing (v2.7.0).** Run the full planned team and warranted waves from one simple prompt; never shrink the service silently or substitute generic agents (`G37`); never deliver a brief that is not backed by a verifiable run (`G34`). The patient should not have to know what to ask for — see the Operating contract above + `docs/ANTI_PATTERNS.md`.
7. **Real prediction, not just labelling.** Wave 3 outputs are quantitative — pooled HR/OR/RR + 95% CI, patient-projected scores, Cox / KM survival predictions, drug ranking with quantified efficacy scores. The three-tier label annotates evidence strength of the prediction, not its existence.
8. **Apache-2.0 + open-source-reproducible.** Any rendered brief can be re-run by a third party with the same model + prompt versions (`tools/reproduce.py`).

## When NOT to invoke

- **Emergency / oncologic emergency** (spinal cord compression, hypercalcemic crisis, neutropenic sepsis, TLS). → Call 120 / 911 / 112. OPL is not a triage system.
- **Acute psychiatric crisis** — suicidal ideation, self-harm intent, acute distress beyond OPL scope. → Call the jurisdictional crisis line (中国 12320 / 北京心理援助热线 010-82951332 / US 988 / UK Samaritans 116 123) and contact a licensed mental-health professional. OPL is a research tool, not a crisis service. The no-LLM G24 crisis-detection gate **automatically** fires on SI/self-harm keywords (ZH + EN, passive_SI / active_SI / active_plan) and locks Wave runners until the patient (or guardian) acknowledges the crisis-card. See `prompts/safety/crisis_detection.md` + `prompts/tasks/crisis_card_emission.md`.
- **Anyone other than the patient or their primary caregiver acting with the patient's consent**. OPL is patient-owned, not clinician-owned, not pharma-owned, not insurance-owned. See `DISCLAIMER.md`.
- **Diagnostic claim** ("am I terminal?", "do I have cancer?"). OPL works *from* an existing diagnosis, not toward one. For undiagnosed cases: complete tissue biopsy + IHC + NGS through your treating clinician first; OPL accepts the canonical patient layout described in `references/patient-data-layout.md`. (Suspected rare hereditary syndromes — LFS / Lynch / VHL / HBOC — additionally warrant a board-certified medical geneticist consult; this is upstream of OPL.)
- **Pediatric patients** — OPL serves the **guardian + child** as a unit (v1.3.2). Guardian acks information receipt (NOT treatment decision authority); treatment decisions route to a pediatric IRB-supervised slot. Use the `prompts/tasks/guardian_ack_protocol.md` task package + cancer-type planner pediatric rows in Step 4 (Pediatric ALL R/R, Pediatric AML R/R, Pediatric DIPG / brain tumor, Pediatric solid Ewing/RMS/neuroblastoma). For pediatric mental-health / family-support needs, refer to a licensed child psychologist or pediatric palliative-care team (out of OPL's 20-expert scope).

## References (heavy material offloaded)

- [`references/architecture.md`](references/architecture.md) — full 7-task-primitive × 20-expert × 5-domain × 10-integrator-family architecture (PRD §2). v1.x 18 + v2 Maya + Julius.
- [`references/wave-lifecycle.md`](references/wave-lifecycle.md) — single-trigger-run state machine (PRD §4).
- [`references/expert-roster.md`](references/expert-roster.md) — all 20 expert personas + archetype attribution + task-package portfolio (v1.x 18 + v2 Maya + Julius). Persona prompts live in `prompts/experts/<name>/persona.md`.
- [`references/integrator-catalog.md`](references/integrator-catalog.md) — 29 integrators × API + cache TTL + auth requirements.
- [`references/mechanical-gates.md`](references/mechanical-gates.md) — full 42-gate spec (G1–G43, G38 reserved) + failure-mode mapping (PRD §6.5 + §7).
- [`references/permission-levels.md`](references/permission-levels.md) — Level 0-4 boundaries + risk-card schema (PRD §8).
- [`references/founder-mode-philosophy.md`](references/founder-mode-philosophy.md) — why no human-in-the-loop, why patient-as-sole-decider, why archetype-not-impersonation.
- [`references/troubleshooting.md`](references/troubleshooting.md) — common failure modes + recovery.
- `DISCLAIMER.md` — jurisdictional notice, no-warranty, no-clinical-decision-support, emergency contacts.
- `docs/adr/` — Architecture Decision Records 0001–0026 (incl. 0010/0020 relocated here from references/adr/).

## License

Apache-2.0. See `LICENSE` + `NOTICE`. Substrate attribution: Co-Scientist (Nature 2026, `10.1038/s41586-026-10644-y`), Robin (Nature 2026, `10.1038/s41586-026-10652-y`), CancerDAO medical-record intake modules.
