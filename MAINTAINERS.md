# OPL for Cancer Maintainers

| Name | Role | Domain |
|---|---|---|
| zwbao | Project lead | Overall architecture, founder-mode philosophy |
| TBD | Medical reviewer | Required: 2 approvers for prompts/tasks/ + prompts/experts/ |
| TBD | Open-source steward | Apache-2.0 compliance, contributor onboarding |

PR review policy:
- Code-only changes: 1 maintainer approver
- Prompt changes (`prompts/tasks/`, `prompts/experts/`): 2 approvers, at least 1 medical
- Model version changes (`models.yaml`): 1 approver + full golden_set CI pass
- ADR additions / changes: 2 approvers
