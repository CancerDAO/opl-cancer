---
name: opl-cancer
description: OPL for Cancer (智愈 AI 科研团队) — patient gets their own 18-expert AI scientist team for cancer research. Use when patient describes any cancer case + wants research-grade analysis (treatment options / clinical trial matching / NGS interpretation / hypothesis generation / second opinion / bioinformatics). Triggers on - 我有 NSCLC / HCC / 胰腺癌 / 乳腺癌 / 等任何癌症的咨询; review my NGS; find me a clinical trial; 找临床试验; second opinion on treatment plan; expanded access for [drug]; 同情用药; cross-border treatment; 海外就医; 假设生成; hypothesis tournament; opl, opl-cancer, AI scientist team, founder mode against cancer.
---

# OPL for Cancer — AI Scientist Team Skill (v1.2.0)

A patient gets a private 18-expert AI scientist team. The team gathers world-known evidence (PubMed / NCCN / CSCO / ESMO / ClinicalTrials.gov / ChiCTR / FDA-EAP / NMPA-EAP / RxNorm / CIViC / cBioPortal / OncoKB / DepMap / CCLE / GEO / ArrayExpress / SRA) AND generates world-unknown hypotheses. Patient is sole decision authority.

## Capabilities (v1.x — shipped)

- **Sid (PI)** — single conversational surface; routes intent across `INFO_REQUEST | HYPOTHESIS_REQUEST | DATA_VALIDATION | DELIVERY | DRILLDOWN | ACK`
- **Henry (Auditor)** — 4-layer IRB substitute (L1 mechanical gates / L2 LLM disagreement summariser / L3 Level-0-4 permission gate + risk card / L4 rollback registry)
- **18 named Experts active** — Rosa pathology · Bert genetics · Vince oncology · Rick trials · Heddy radiology · Mary pharmacology · Aviv bioinformatics · Tyler wet-lab · Iain meta-analysis · Ted radiation · Riad interventional · Jen palliative · Kieren ID · Mark irAE · Hong TCM · Frances expanded access · Dennis cross-border · Steve nutrition
- **Wave 1 retrieval pipeline** — intent → planner → parallel experts → reviewer pairing → mechanical gates → patient_brief.html with three-tier labels + PMID links + provenance hashes
- **Wave 2 hypothesis pipeline** — generator (4 strategies) → evolution (6 strategies) → Co-Sci-style Elo tournament → Robin feedback → Reflector (6 modes) → ranked hypothesis pack
- **Wave 3 data-evidence pipeline** — dataset acquisition (GEO / ArrayExpress / SRA / DepMap / CCLE) → bioinformatics analysis (BixbenchRunner Docker, env-gated) → hypothesis validation
- **Wave 4 hypothesis validation runner** — Wave-2 hyp ↔ Wave-3 omics evidence
- **20+ live integrators** wired with configurable TTL via `models.yaml.integrator_ttl_seconds`
- **Provenance ledger** — every claim carries `sha256:<hash>` over its source quote + canonical source ID + three-tier label
- **Cross-patient isolation** — `CrossPatientContaminationError` raised on foreign `patient_code`
- **Per-task model routing** — `ModelRouter.client_for_task()` (Opus 4.7 for code/hypothesis reasoning, MiniMax-M2.7 for literature synthesis)
- **Apache-2.0**, NOTICE attribution, DISCLAIMER.md jurisdictional notice + emergency contacts

## Quick start

```bash
pip install -e .
opl-cancer status
opl-cancer list-experts
opl-cancer init-patient anon_001 --root ~/opl_patients
opl-cancer acknowledge <card_id>
opl-cancer list-pending-acks
```

Shell wrappers under `scripts/` mirror the CLI for skill-form invocation.

## Read this first

`DISCLAIMER.md` — not clinical decision support; not for emergencies (call 120 / 911 / 112). Apache-2.0; no warranty.

## License

Apache-2.0. See [LICENSE](LICENSE).
