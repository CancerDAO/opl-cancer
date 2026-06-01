# DISCLAIMER — Read This Before Using OPL for Cancer

> **Release scope notice — v2.x (research preview).** This is a research-preview release of OPL for Cancer. It is provided **WITHOUT WARRANTY OF ANY KIND**, express or implied, including but not limited to warranties of merchantability, fitness for a particular purpose, accuracy, or non-infringement. It is intended for research, deliberation, and second-opinion drafting only; it is **NOT** validated for clinical decision-making and **NOT** for use in any oncologic emergency.
>
> **Emergencies.** If you or someone in your care has an oncologic emergency — spinal cord compression, febrile neutropenia, tumour lysis syndrome, brain herniation, massive hemoptysis, anaphylaxis, suicidal ideation, or any other acute medical crisis — **stop reading this software and contact emergency services immediately**: dial **120** (China), **911** (United States / Canada), **999** (United Kingdom), **112** (EU), or your local emergency number. This software cannot triage emergencies and must never be substituted for one.
>
> **Jurisdictional notice.** OPL for Cancer is **not** registered, cleared, approved, certified, or licensed by any regulator anywhere in the world — not FDA (US), not NMPA / CFDA (CN), not EMA / CE (EU), not PMDA (JP), not MHRA (UK), not TGA (AU), not Health Canada, not any IRB / ethics committee. It is **not** classified as software-as-a-medical-device (SaMD), in-vitro diagnostic (IVD), clinical decision support (CDS), or any other regulated category. Use of this software does not create a doctor-patient relationship with the authors, CancerDAO, or any contributor. Where local law restricts AI-derived medical content, **you are responsible for complying with that law**; do not use this software where prohibited.

**OPL for Cancer is NOT clinical decision support software. It is NOT a substitute for a qualified physician. It does NOT diagnose, treat, cure, or prevent any disease.**

This project assembles an "AI scientist team" (20 expert archetypes inspired by real clinicians) that drafts **deliberative materials** — literature digests, hypothesis trees, risk cards, evidence-graded options — for **patients and their treating physicians to read together**. Every output is provisional. Every recommendation is conditional. Every claim is hashed back to a primary source.

---

## What this software is

- A reading and deliberation aid for cancer patients who have exhausted standard care, or who want a second look at their options before consenting to the next line of therapy.
- A way to mobilise current literature (PubMed, ClinicalTrials.gov, ChiCTR, NCCN excerpts, OpenFDA, CIViC) on a single patient's actual molecular and clinical profile.
- A provenance-strict drafter — every claim carries a SHA-256 hash that maps back to its source quote, so any physician can verify in minutes.
- An open-source experiment in "founder mode against cancer" — patients steering their own deliberation, with AI as the team they could never afford to hire.

## What this software is NOT

- Not a doctor. Not a medical device. Not FDA-cleared. Not CFDA-approved. Not CE-marked. Not registered as IVD, SaMD, or any regulated category.
- Not a diagnostic. Outputs are hypotheses to discuss with a treating oncologist, not diagnoses.
- Not a prescription. We do not recommend doses. We do not initiate, modify, or terminate any therapy.
- Not a clinical trial matcher of last resort. Eligibility for any trial must be confirmed by the trial's PI, not by this software.
- Not a substitute for emergency care. If you have an oncologic emergency (spinal cord compression, febrile neutropenia, tumour lysis, brain herniation, massive hemoptysis), call your local emergency number now. Do not consult this software.

## Patient decision authority

The patient (or their legally authorised representative) is the **sole decision-maker** about their own treatment. This software does not consent on behalf of any patient. Where outputs concern off-label use, expanded-access pathways, compassionate-use applications, or any Permission-Level-3-or-4 advice, the software will:

1. Render the option as a "risk-disclosure card" with explicit benefits, risks, alternatives, and unknowns.
2. Require the patient to acknowledge the card before the option is included in the final brief.
3. Record the acknowledgement (timestamp + patient-side hash) in the provenance journal.

No external physician sign-off is required to run OPL or to read its briefs — the patient is the sole decision authority for their own case, and OPL never requires a doctor's approval to start a run or close a brief. OPL strongly encourages the patient to discuss any card with their treating clinician before acting on it, but that conversation is the patient's to choose, not a gate the software imposes. The software will not act for the patient.

## Provenance and verification

Every claim emitted by this software:

- Carries a `sha256:<hash>` over its source quote
- Names the source by canonical ID (PMID / NCT / ChiCTR-ID / FDA-label / NCCN-section)
- Carries a three-tier label: `established` / `exploratory` / `speculative`
- Is rebutted, where applicable, by Henry's L1 (mechanical), L2 (reviewer cross-check), L3 (Permission-Level gate), L4 (rollback registry) audit chain

If a claim arrives without these, **do not trust it**. File an issue at https://github.com/CancerDAO/opl-cancer/issues — that is a bug, not a feature.

## Liability

This software is distributed under the Apache License, Version 2.0, "as is" and "as available", **without any warranty whatsoever**. To the maximum extent permitted by law, the authors, contributors, and CancerDAO disclaim all liability for any harm — direct, indirect, incidental, consequential, or otherwise — arising from any use, misuse, or non-use of this software.

You use this software at your own risk. If you are uncertain whether to use it, **do not use it**, and consult a qualified physician.

## Reporting harm

If you believe this software contributed to patient harm, or could plausibly do so, please report immediately:

- Open a public issue: https://github.com/CancerDAO/opl-cancer/issues

We treat safety reports as P0 and will investigate within 72 hours.

---

By using this software you confirm you have read this disclaimer and accept its terms in full.
