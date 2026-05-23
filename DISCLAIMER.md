# DISCLAIMER — Read This Before Using OPL for Cancer

**OPL for Cancer is NOT clinical decision support software. It is NOT a substitute for a qualified physician. It does NOT diagnose, treat, cure, or prevent any disease.**

This project assembles an "AI scientist team" (18 expert archetypes inspired by real clinicians) that drafts **deliberative materials** — literature digests, hypothesis trees, risk cards, evidence-graded options — for **patients and their treating physicians to read together**. Every output is provisional. Every recommendation is conditional. Every claim is hashed back to a primary source.

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

A treating physician must co-sign any decision to act on a card. The software will not act for the patient.

## Provenance and verification

Every claim emitted by this software:

- Carries a `sha256:<hash>` over its source quote
- Names the source by canonical ID (PMID / NCT / ChiCTR-ID / FDA-label / NCCN-section)
- Carries a three-tier label: `established` / `exploratory` / `speculative`
- Is rebutted, where applicable, by Henry's L1 (mechanical), L2 (reviewer cross-check), L3 (Permission-Level gate), L4 (rollback registry) audit chain

If a claim arrives without these, **do not trust it**. File an issue at https://github.com/CancerDAO/opl-for-cancer/issues — that is a bug, not a feature.

## Liability

This software is distributed under the Apache License, Version 2.0, "as is" and "as available", **without any warranty whatsoever**. To the maximum extent permitted by law, the authors, contributors, and CancerDAO disclaim all liability for any harm — direct, indirect, incidental, consequential, or otherwise — arising from any use, misuse, or non-use of this software.

You use this software at your own risk. If you are uncertain whether to use it, **do not use it**, and consult a qualified physician.

## Reporting harm

If you believe this software contributed to patient harm, or could plausibly do so, please report immediately:

- Open a public issue: https://github.com/CancerDAO/opl-for-cancer/issues
- Email: safety@cancerdao.org

We treat safety reports as P0 and will investigate within 72 hours.

---

By using this software you confirm you have read this disclaimer and accept its terms in full.
