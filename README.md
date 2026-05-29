<div align="center">

# OPL for Cancer

### One Person Lab — your own AI scientist team, for one cancer patient

[![Version](https://img.shields.io/badge/version-2.7.0-blue)](CHANGELOG.md)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-1778%20passing-brightgreen)](#contributing)
[![Status](https://img.shields.io/badge/status-research%20preview-orange)](#what-this-is--what-this-is-not)
[![Not a medical device](https://img.shields.io/badge/medical%20advice-no-red)](DISCLAIMER.md)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)

**English · [中文](README.zh-CN.md)**

**[What is this](#what-is-this) · [What it does / does not do](#what-this-is--what-this-is-not) · [Quickstart](#30-second-quickstart) · [The 5-Wave pipeline](#the-5-wave-pipeline) · [Example output](#example-output) · [Why N=1 is hard](#why-n1-is-hard) · [Architecture](#architecture) · [Contributing](#contributing) · [Ethics](#ethics--safety) · [Cite](#citation)**

</div>

---

OPL for Cancer is an open-source skill plugin that gives one cancer patient a coordinated team of 20 named AI scientists, one project-manager PI, and one IRB-substitute auditor — assembled by **CancerDAO** to run a single research session on that patient's records. Every claim it surfaces carries a PMID anchor, a three-tier evidence label (established / exploratory / speculative), and a SHA-256 provenance hash. The output is not a treatment recommendation. It is a research-grade brief the patient and their treating clinician can use as the basis for the next conversation.

OPL is a **research preview**. It is not a clinical decision-support tool, not a diagnostic device, and not a doctor-replacement. The patient is the sole decision authority for their own case.

> 中文版文档见 **[README.zh-CN.md](README.zh-CN.md)** — the Chinese-language version of this README is maintained in parallel.

---

## What is this

OPL is consumed in two ways: as a **Claude Code skill** (`npx skills add CancerDAO/opl-cancer-skill`), where the Claude Code main thread runs the reasoning, and as a **Python package** (`pip install`), which provides the harness — planning, validation, safety gates, live-data integrators, and honest scaffolds. You point it at a folder of your medical records. It assembles a 20-expert virtual lab around your specific situation — a PI named **Sid** coordinates which 5-12 experts come onto your case — and runs a 5-Wave research lifecycle from records-in to brief-out. About 30-50 minutes per session.

The lifecycle ends with two artifacts:

1. **`patient_plain_brief.md`** — a 2-page lay-language brief the patient and family can read together
2. **`patient_pi_brief.md`** — a clinician-grade brief with PMID anchors, risk-disclosure cards, and reviewer disagreements surfaced verbatim

Both are atomically shipped alongside `HENRY_AUDIT.json`. Delivery has two honest modes (v2.6.0): `opl deliver` emits a **template scaffold** the Claude Code SKILL main thread fills (`status: scaffold_pending_fill`, `henry_real_audit: false`), and `opl deliver --finalize` runs the **real 4-layer `HenryAuditor.audit_claim()`** over the filled briefs — refusing if any placeholder language remains — and only then reports `henry_real_audit: true`. If upstream evidence is missing *or hollow*, delivery refuses to ship.

The 20-expert roster (each is an *archetype* of a real-world clinician/scientist, not an impersonation): **Rosa** (pathology), **Bert** (molecular/NGS), **Vince** (treating oncology), **Rick** (clinical trial matching), **Heddy** (imaging), **Mary** (DDI / pharmacogenomics), **Aviv** (bioinformatics), **Tyler** (wet-lab design), **Iain** (meta-analysis), **Ted** (radiation), **Riad** (interventional), **Jen** (palliative), **Kieren** (infectious disease), **Mark** (irAE / endocrine), **Hong** (TCM), **Frances** (expanded access), **Dennis** (cross-border), **Steve** (nutrition), **Maya** (knowledge-graph synergy reasoner; v2.0+), **Julius** (in-silico medicinal chemist; v2.0+). Coordination layer: **Sid** (PI / chief-of-staff — your only conversation window) + **Henry** (IRB-substitute auditor — internal review). Full archetype credits in [`references/expert-roster.md`](references/expert-roster.md).

> **Why "OPL"?** **OPC (One Person Company)** is the 2024-2025 paradigm of "one founder + AI tool stack = a real company." CancerDAO extends it to a more urgent domain: **OPL (One Person Lab)** = "one patient + AI scientist team = a real private research lab." We chose cancer because cancer decisions are the canonical **real research task every family eventually faces** — once standard-of-care is exhausted, you and your clinician both need a systematic, evidence-graded, provenance-traceable research artifact to ground the next choice. Today that artifact is produced only by top-tier hospital Molecular Tumor Boards. OPL puts a credible version of it on your laptop.

---

## What this is / What this is not

| ✅ What OPL does | ❌ What OPL does NOT do |
|---|---|
| Surfaces **evidence-anchored research directions** the patient can take to their oncologist | Tell you which treatment to choose |
| Anchors every claim to PMIDs + integrator queries + a provenance hash | Replace your clinician, your MTB, or your pathology workup |
| Labels evidence as **established / exploratory / speculative** so nothing speculative is mistaken for standard-of-care | Diagnose, prescribe, or dose |
| Surfaces **reviewer disagreements verbatim** rather than picking a side | Hide uncertainty to look more confident |
| Redacts specific drug names → **drug-class equivalents** in patient-facing speculative sections (fail-closed since v2.6.0) | Recommend specific off-label drugs to the patient |
| Refuses to ship when upstream waves haven't produced real (or non-hollow) evidence (v2.5.1 B5 + v2.6.0) | Run silent fallbacks to canned outputs |
| Is **transparent**: every decision, every provenance hash, every audit gate is in the repo | Operate as a black box |

**OPL is for the patient.** Final decisions belong to the patient and their treating clinician. OPL is the homework that informs that conversation. In medical emergencies, dial your local emergency line first (China: **120**; United States: **911**; EU: **112**) — OPL is for non-emergency research, not crisis response.

---

## 30-second quickstart

**OPL runs as a Claude Code skill — that is how you use it.** Install it once:

```bash
npx skills add CancerDAO/opl-cancer-skill
```

Then, in Claude Code, point **Sid** (your PI) at your records folder and ask your question in plain language — no commands to memorise:

> *"Here are my records: `~/CancerDAO/patients/mine`. I've been on osimertinib for 14 months; my latest CT shows progression. What are my evidence-based next-line options?"*

Sid greets you, organizes the records, decides which 5-12 experts join your case, drives Waves 1-5, and delivers `patient_plain_brief.md` + `patient_pi_brief.md` + `HENRY_AUDIT.json` (about 30-50 minutes). As it runs you see plain-language stage labels (localized to you). Everything below — the `opl` commands — is the harness the skill drives **under the hood**; you do not type them yourself in normal use.

<details>
<summary><b>Under the hood — the harness CLI (advanced / contributors / CI)</b></summary>

The skill's main thread drives a Python harness: planning, validation, safety gates, live-data integrators, and honest delivery scaffolds. You can install and call it directly for debugging, automation, or CI:

```bash
# Install the harness (Python 3.11+)
pip install -e .

# 1. Initialise a patient directory under ~/CancerDAO/patients/
opl init-patient demo-001

# v2.7.0 — one-command autonomous path: a single (even vague) prompt drives the
# whole lifecycle and tells you the exact next action until delivery is complete
# + attested. Never under-delivers, never collapses the team, never free-hands.
opl go --patient ~/CancerDAO/patients/demo-001 \
       --goal "what should my dad do next?" --run-id r1

# …or drive the steps by hand:
# 2. Plan the run (mints the run-token; Sid's intake_router decides the FULL team)
opl plan --patient ~/CancerDAO/patients/demo-001 \
         --goal "I have been on osimertinib for 14 months; CT shows progression — what are my next-line options?" \
         --run-id r1

# 3. Waves 1-4 run on the SKILL.md main thread (the harness verifies state, the
#    Claude Code main thread does the reasoning). See SKILL.md §Step 5-8.

# 4. Delivery — scaffold first, then --finalize once the SKILL fills the prose,
#    then attest (v2.7.0 delivery-integrity gates G34/G35/G37 + G1/G2/G36 —
#    refuses any brief not backed by a real run, with fabricated labs, or with
#    wrong-paper PMIDs).
opl deliver --patient ~/CancerDAO/patients/demo-001 --run-id r1
opl deliver --patient ~/CancerDAO/patients/demo-001 --run-id r1 --finalize
opl attest  --patient ~/CancerDAO/patients/demo-001 --run-id r1

# 5. Optional — Wave 6 manuscript + .n1a bundle
opl wave6 --patient-dir ~/CancerDAO/patients/demo-001 \
          --run-id r1 --patient-code demo-001 --draft
```

</details>

Expected `opl deliver` output (scaffold mode — the SKILL main thread then fills
the prose and re-runs with `--finalize` for the real audit):

```json
{
  "ok": true,
  "status": "scaffold_pending_fill",
  "out_dir": ".../triggers/r1/delivery",
  "written_files": [
    ".../HENRY_AUDIT.json",
    ".../patient_plain_brief.md",
    ".../patient_pi_brief.md"
  ],
  "henry_real_audit": false,
  "brief_complete": false
}
```

> **CLI vs SKILL (read this).** The pip-installable Python package is the
> **harness**: it plans, validates, gates, fetches from live integrators, and
> emits honest scaffolds + state — it does **not** itself write the patient-facing
> prose or run the expert LLMs. The reasoning (Sid + the 20 experts + Henry's
> per-claim audit) runs on the **Claude Code SKILL main thread** (`npx skills add
> CancerDAO/opl-cancer-skill`). `opl deliver` (no flag) is a scaffold; `opl
> deliver --finalize` audits the SKILL-filled briefs.

If upstream Waves 1-5 haven't produced real artifacts, `opl deliver` refuses with a structured error rather than shipping a fabricated brief (v2.5.1 B5):

```json
{
  "ok": false,
  "error": "upstream_artifacts_missing",
  "missing": ["plan: …", "wave1_expert_reports: …", "wave2/3/4 evidence: …"]
}
```

---

## The 5-Wave pipeline

```
Prepare / Find-options / Check-data / Review / Write-up  (plain-language stage labels; localized to the patient)
─────────────────────────────────────────────────────────────────────────────────────
Wave 1  Retrieval        5-12 experts pull from 29+ live integrators
                         (PubMed / OncoKB / CIViC / ClinicalTrials.gov / ChiCTR /
                          NCCN / Open Targets / cBioPortal / GEO / TCGA / GDC / …)

Wave 2  Hypothesis       6 generation strategies + Co-Sci Elo tournament + Reflector
                         falsification (8 hypotheses → top-3)

Wave 3  Data evidence    TCGA / GEO / cBioPortal re-analysis;
                         DESeq2 / scanpy / KM survival; Monte Carlo + conformal

Wave 4  Validation       Aviv (data-anchored verdict) + Iain (Cochrane-lens
                         meta-validation) → validated / falsified / inconclusive

Wave 5  Patient brief    atomic delivery (Henry audit + patient_plain_brief +
                         patient_pi_brief) — partial failure rolls back

Wave 6  Manuscript+.n1a  optional: preprint draft + bundle for N1Arxiv submission,
                         gated by G29-G33
```

Full lifecycle detail: [`references/wave-lifecycle.md`](references/wave-lifecycle.md). RFC for the v2.5 compositional foundation: [`docs/rfc/0001-compositional-paradigm.md`](docs/rfc/0001-compositional-paradigm.md). ADR ledger: [`docs/adr/`](docs/adr/).

---

## Example output

An excerpt from the Riaz-reference patient brief (drug-class redaction + PMID anchoring + three-tier labelling are mandatory in every patient-facing section; specific compounds and untranslated jargon stay in the clinician brief):

```
### Scenario: KRAS-G12C second-line progression — Section 3 · The paths you could take

**Path A** — KRAS-G12C class inhibitor + EGFR-class antibody doublet
  Layer:        ⚪ exploratory (CodeBreaK 300 phase III evidence)
  Effect size:  ORR 30-46% (95% CI per PMID:37870974); mPFS 5-8 mo in matched cohort
  Risk:         skin reactions (≥G2 in 35%) + hepatic transaminitis (≥G3 in 8%)
  Anchors:      [PMID:37870974] [PMID:34233156] [integrator:opentargets t1]

**Path B** — chemo + anti-angiogenic standard-of-care
  Layer:        ✅ established (your hospital's default; see Vince's report)
  Effect size:  ORR 18-25%; mPFS 4-6 mo (CT.gov NCT04793958 secondary endpoint)
  Risk:         neutropenia + proteinuria; well-characterised
  Anchors:      [PMID:32861308] [ctgov:NCT04793958]

**Path C** — single-arm trial (cross-border, expanded access via Frances / Dennis)
  Layer:        🟠 speculative — N=1 projection; world-unknown candidate
  Note:         specific drug names redacted to class — see PI brief for the
                clinician-grade list. Not a recommendation.
```

Reference cases (Riaz, etc.) are methodology demonstrations — they are banner-stamped throughout and are never presented as real patient outputs.

---

## Run scenarios

OPL covers very different real situations. Three concrete dialog flows (every run produces the same artifacts, but the experts on stage shift):

### Scenario 1 — Standard-of-care exhausted, asking about next-line options

> *"I have stage IV mCRC, KRAS G12C, used regorafenib + TAS-102, both progressed. What does the literature suggest is worth trying next?"*

Sid puts **Rosa + Bert + Vince + Rick** on as the spine, adds **Maya** (KG-synergy for G12C combos) + **Julius** (undrugged-target backup designs) + **Frances** (expanded access) + **Iain** (Cochrane lens on CodeBreaK 300). Wave 2 produces 6-8 hypotheses ranked by an Elo tournament. Wave 3 re-analyses TCGA-COAD + matched cBioPortal cohorts. Wave 4 validates against Cochrane lens. Wave 5 ships a brief with three concrete paths, each with effect-size range + honest risk + the PMID it came from.

### Scenario 2 — Immune-related side effect, asking about rechallenge

> *"I developed grade-3 ICI hepatitis on pembrolizumab; the tumour was responding. Can we rechallenge after taper?"*

Sid puts **Mark + Mary + Vince + Iain** on as the core team. Wave 1 pulls per-organ rechallenge evidence from ASCO / ESMO consensus + irAE re-exposure literature. Wave 2 generates rechallenge / dose-adjust / class-switch hypotheses. Wave 4 surfaces explicit reviewer disagreements (Iain vs Mark on whether the G3 transaminitis threshold permits rechallenge). The Wave 5 brief surfaces both positions verbatim — patient + treating oncologist arbitrate.

### Scenario 3 — Cross-border / expanded access question

> *"Standard of care here doesn't include the new BRAF-V600E combo for my pancreas NET. Where could I get it — Boao? Hong Kong? Compassionate use in Germany?"*

Sid puts **Dennis + Frances + Rick + Bert** on. Wave 1 pulls the regulatory + supply chain landscape (NMPA accelerated approval, HKFDA, EMA compassionate use, named-patient access in JP/KR). Wave 4 grounds each route in feasibility (cost / time / clinical infrastructure / interpreter / follow-up logistics). Wave 5 ships a concrete decision-aid table — *not* a "go to Boao" recommendation, but a structured comparison the patient can use to talk to family + clinician.

---

## Why N=1 is hard

You have one patient. One tumour board. One progression trajectory. The standard tools of computational oncology — AutoML on TCGA, prognostic models with 80/20 train-test splits, deep-learning survival forests — silently overfit when you point them at N=1. There is no IID assumption to invoke. There is no held-out cohort. There is no replicate.

OPL was built around this constraint, not against it.

* We **don't train models on your data**. We retrieve evidence, compose it, and project it onto your situation honestly.
* We **always show effect-size ranges**, not point estimates — and we surface the cohort the range came from.
* For unknown-task questions (the "auto-build me a prognostic model" case), OPL **routes to a compositional intake** that declines the naive shortcut, explains why, and proposes a safer alternative (external-cohort baseline + distribution-free uncertainty bounds via conformal prediction).
* Wave 3 Monte Carlo runs carry **parameter-calibration provenance** (paper-derived / informed-estimate / literature-default) so the brief never anchors a forecast to a number whose source is "the model made it up".

The trade-off: OPL surfaces fewer, more honest answers — not more, more confident ones.

---

## Architecture

```
                    ┌──────────────────────────────────────────┐
                    │  SKILL.md (main-thread orchestrator)     │
                    └────────────────────┬─────────────────────┘
                                         │
            ┌────────────────────────────┼────────────────────────────┐
            │                            │                            │
   ┌────────▼─────────┐         ┌────────▼─────────┐         ┌────────▼─────────┐
   │  Sid (PI)        │         │  20 experts      │         │  Henry (audit)   │
   │  intake_router   │         │  Wave 1-4        │         │  L1-L4 gates     │
   └────────┬─────────┘         └────────┬─────────┘         └────────┬─────────┘
            │                            │                            │
            │           ┌────────────────▼────────────────┐           │
            │           │  29+ live integrators           │           │
            │           │  PubMed / CIViC / OncoKB /      │           │
            │           │  CT.gov / ChiCTR / NCCN /       │           │
            │           │  Open Targets / cBioPortal /    │           │
            │           │  GEO / TCGA / GDC / …           │           │
            │           └────────────────┬────────────────┘           │
            │                            │                            │
            └────────────────────────────┼────────────────────────────┘
                                         │
                                ┌────────▼─────────┐
                                │  Wave 5 delivery │
                                │  (atomic)        │
                                │  plain brief +   │
                                │  PI brief +      │
                                │  HENRY_AUDIT.json│
                                └────────┬─────────┘
                                         │
                                ┌────────▼─────────┐
                                │  Wave 6 (opt)    │
                                │  manuscript +    │
                                │  .n1a bundle →   │
                                │  N1Arxiv         │
                                └──────────────────┘
```

Compositional layers (v2.5 RFC):

* **Method primitives** (`src/opl_cancer/methods/`) — 8 seed primitives across statistical / bioinformatics / clinical-research / pharmacology; M4 grows to ~50.
* **Gate families** (`src/opl_cancer/validators/gate_families.py`) — 6 families (provenance / statistical-validity / temporal-recency / scope-isolation / safety-disclosure / reproducibility). Provenance family fully migrated; the rest tagged for M1.
* **Role taxonomy** (`src/opl_cancer/experts/role_taxonomy.py`) — `ExpertRole` 4-axis dataclass + 20-persona `FAST_PATH_ROLES`. `compose_role()` LLM stub raises for novel constraints until M2.
* **Integrator ABC** (`src/opl_cancer/integrators/_abc.py`) — entry-point discovery; 5 of 44 registered, the rest deferred to M3.

Full RFC: [`docs/rfc/0001-compositional-paradigm.md`](docs/rfc/0001-compositional-paradigm.md). Architecture map: [`references/architecture.md`](references/architecture.md). All ADRs: [`docs/adr/`](docs/adr/). Latest product audit + iteration roadmap: [`docs/iteration/REVIEW_v2.6.0.md`](docs/iteration/REVIEW_v2.6.0.md).

---

## Contributing

We welcome contributions — bug reports, new task packages, new integrators, new method primitives, prompt improvements, reproducer notebooks. See [CONTRIBUTING.md](CONTRIBUTING.md).

Quick start for contributors:

```bash
git clone https://github.com/CancerDAO/opl-cancer
cd opl-cancer
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev,bio]
pytest tests/ -q -m "not live"   # 1778 passing as of v2.7.0 (clean env)
```

The roadmap is the 6-milestone M1-M6 plan in [`docs/rfc/0001-compositional-paradigm.md`](docs/rfc/0001-compositional-paradigm.md). Highlights:

* **M1** — migrate the remaining gates into the 6 gate-family ABCs
* **M2** — real LLM `compose_role()` for novel expert constraints
* **M3** — register more integrators via entry points; wire `OPL_UNIVERSAL_ADAPTER_LIVE=1`
* **M4** — grow the method-primitive library from 8 → ~50
* **M5** — swap the keyword intake router for an LLM TaskComposer over the full MethodRegistry
* **M6** — wire `cancer_context/` to live PrimeKG + OncoKB + NCCN + CT.gov

Test suite: 1778 tests, 8 skipped (live integrators + heavy bio deps). All PRs must keep the suite green.

### Discipline rules (lifted from `CLAUDE.md`)

1. **No false completion.** Every "done" claim ships paths + line counts + wall-time + ≥ 3 sampling verifications.
2. **TDD.** Failing test → confirm fail → implement → confirm pass → commit. Each BLOCKER fix gets a before/after repro pair.
3. **No mock-only paths to production.** Medical integrators query live APIs; LLM synthesis is never a substitute for evidence retrieval.
4. **No model downgrade.** Opus stays the executor for any LLM work the runner spawns.

PRs that break any of these get bounced.

---

## Ethics & safety

OPL is built on the **founder mode against cancer** philosophy — see [`references/founder-mode-philosophy.md`](references/founder-mode-philosophy.md), [ADR-0023](docs/adr/0023-wave6-manuscript-and-n1a-bundle.md), and [ADR-0025](docs/adr/0025-compositional-paradigm.md).

In short:

* The patient is the sole decision authority. We do not require external sign-off to start a run.
* High-stakes (Level 3 / Level 4) claims emit a **Risk Disclosure Card** and require patient acknowledgement before the brief is closed. Henry's job is **transparency**, not gatekeeping.
* **Drug-class redaction**: speculative recommendations name drug *classes* in the patient brief, not specific compounds (fail-closed since v2.6.0 — unlisted drug-like tokens are redacted, not leaked). The PI brief shows specifics so the clinician can evaluate. Patients do not self-prescribe off the OPL output.
* **Crisis safety floor**: a mechanical self-harm-language gate (G24) fires ahead of all routing (wired in v2.6.0) and routes to crisis support before anything else.
* **N=1 reports are not clinical guidance** — every Wave-6 manuscript and every N1Arxiv submission carries this banner.
* In a medical emergency, dial your local emergency line first (China: **120**; United States: **911**; EU: **112**). OPL is for non-emergency research only.

Full ethics declaration and disclaimer: [DISCLAIMER.md](DISCLAIMER.md). Safety reports: [SECURITY.md](SECURITY.md). Code of conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

---

## Citation

```bibtex
@software{cancerdao_opl_cancer_2026,
  author       = {{CancerDAO Contributors}},
  title        = {{OPL for Cancer: One Person Lab — your own AI scientist team for one cancer patient}},
  year         = {2026},
  version      = {2.6.0},
  url          = {https://github.com/CancerDAO/opl-cancer},
  license      = {Apache-2.0}
}

@software{cancerdao_n1arxiv_2026,
  author       = {{CancerDAO Contributors}},
  title        = {{N1Arxiv: a patient-centered preprint platform for N-of-1 AI-team-authored case reports}},
  year         = {2026},
  url          = {https://github.com/CancerDAO/n1arxiv},
  license      = {CC-BY-4.0 (content); MIT (code)}
}
```

---

## Acknowledgements

OPL stands on the shoulders of giants. The full credit ledger lives in [ATTRIBUTIONS.md](ATTRIBUTIONS.md). Particularly:

* **[SakanaAI/AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2)** — the journal-pattern best-first search that informs Wave 2's audit layer (`orchestrator/best_first_journal.py`).
* **[Leey21/Awesome-Research-Assistant-Prompts](https://github.com/Leey21/Awesome-Research-Assistant-Prompts)** — research-writing prompt patterns that informed several Wave 6 manuscript task packages.
* **[BioTender-max/awesome-bio-agent-skills](https://github.com/BioTender-max/awesome-bio-agent-skills)** (CC0-1.0) — 8 vendored bio-skill primitives for MSI / TMB / COSMIC / ACMG / Open Targets / KM / subgroup / CPIC (v2.2).
* **[Google Co-Scientist](https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/)** — Elo-style hypothesis tournament inspiration for Wave 2.
* **[FutureHouse Robin](https://github.com/Future-House/finch)** — Wave 2 literature-loop pattern + Wave 3 bixbench compute path.
* **[Marinka Zitnik's PrimeKG](https://github.com/mims-harvard/PrimeKG)** — knowledge-graph backbone Maya queries (live wiring tracked for M6).
* **[Cochrane Collaboration](https://www.cochrane.org/)** — Iain's meta-validation lens.

Every expert in OPL is an **archetype**, not an impersonation, of the corresponding real-world clinician/scientist. See [`references/expert-roster.md`](references/expert-roster.md) for the full archetype credits.

---

<div align="center">

**Patient is sole decision authority. OPL surfaces evidence-anchored research directions. Final decisions belong to the patient and their treating clinician.**

[GitHub](https://github.com/CancerDAO/opl-cancer) · [N1Arxiv](https://github.com/CancerDAO/n1arxiv) · [CancerDAO](https://github.com/CancerDAO) · [中文 README](README.zh-CN.md) · [CHANGELOG](CHANGELOG.md) · [LICENSE](LICENSE)

</div>
