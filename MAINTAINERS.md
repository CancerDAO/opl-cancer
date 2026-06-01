# OPL for Cancer Maintainers

| Name | Role | Domain | Status |
|---|---|---|---|
| zwbao | Project lead | Overall architecture, founder-mode philosophy | Active |
| *(open role — recruiting)* | Medical reviewer | Required: 2 approvers for prompts/tasks/ + prompts/experts/ | **Open** — actively recruiting; see "Open roles" below |
| *(open role — recruiting)* | Open-source steward | Apache-2.0 compliance, contributor onboarding | **Open** — actively recruiting; see "Open roles" below |

> **Open roles.** The Medical-reviewer and Open-source-steward seats are **open and being actively recruited** — they are not silently vacant. Until they are filled, the project lead covers their review duties, and the two-medical-approver rule below is enforced on a best-effort basis with external clinician input. If you are a qualified clinician or open-source maintainer interested in either seat, reach out at [opl-security@cancerdao.org](mailto:opl-security@cancerdao.org).

PR review policy:
- Code-only changes: 1 maintainer approver
- Prompt changes (`prompts/tasks/`, `prompts/experts/`): 2 approvers, at least 1 medical
- Model version changes (`models.yaml`): 1 approver + full golden_set CI pass
- ADR additions / changes: 2 approvers
