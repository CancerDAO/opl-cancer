# Security & safety reporting

OPL for Cancer is a research-preview open-source skill plugin. It is **not a medical device**, **not a clinical decision-support system**, and **not approved for clinical use**.

That said, OPL processes patient records and produces patient-facing briefs. Both code-security and patient-safety bugs matter.

## What counts as a security / safety report

* **Code-security**: arbitrary-code execution, secrets leakage, key exfiltration, prompt injection that bypasses a Henry gate, dependency-chain compromise.
* **Patient-safety**: a Henry gate that silently passes when it should block, drug-class redaction that leaks a specific compound to the patient brief, a refusal contract that fires when it should not, an integrator that silently returns canned data when the live API is down, any failure mode that could mislead a patient or clinician.

If you are unsure whether something qualifies, **err on the side of reporting privately first.**

## How to report

Please do **NOT** open a public GitHub issue for security / safety reports.

* **Email:** [opl-security@cancerdao.org](mailto:opl-security@cancerdao.org) — monitored by the OPL maintainers.
* **GitHub private security advisory:** open a private vulnerability report via the repo's *Security → Advisories* tab.
* **Backup contact:** if email is unreachable, reach the founder at [founder@cancerdao.org](mailto:founder@cancerdao.org).

Please include:

1. A clear description of the issue
2. Steps to reproduce (anonymised — do not include real patient records)
3. The expected vs observed behaviour
4. Your OPL version (`opl status`), Python version, OS
5. Whether you have a candidate fix in mind

## What happens next

* **Acknowledge** within 5 business days
* **Triage** + initial severity assessment within 10 business days
* **Fix / mitigation** released according to severity (critical security: out-of-band patch; lower-severity: next minor release)
* **Public disclosure** coordinated with the reporter; we credit reporters in CHANGELOG.md unless they prefer anonymity

We treat all reports confidentially.

## Out of scope

* Issues in third-party integrator APIs (report those upstream — we'll happily forward)
* Performance / cost issues that do not affect safety
* Feature requests (use the [feature request](.github/ISSUE_TEMPLATE/feature_request.md) template)
* General "how do I use OPL" questions (use the [patient question](.github/ISSUE_TEMPLATE/patient_question.md) template)

## Patient-data note

OPL never sends patient records to a public surface unless the patient explicitly runs `opl wave6 --final --submit-to-n1arxiv` AND opens the resulting PR themselves (founder mode: the patient is the sole entity that pushes to public). If you observe any code path that violates this invariant, treat it as a **critical patient-safety report** and escalate via the channels above.

## Bug bounty

OPL does not currently run a paid bug bounty programme. We credit serious reporters in CHANGELOG.md and (with permission) on the project README.
