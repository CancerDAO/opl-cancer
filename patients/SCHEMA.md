# patients/<patient_code>/ Directory Schema

> **PHI**: This directory is gitignored. Never commit real patient data. Schema lives here so contributors know the contract.

Reference: spec §3 Repo Layout / §5 Memory Schema / §17.6 risk register.

## Top-level structure

```
patients/<patient_code>/
├── profile.json
├── readiness.json
├── timeline.md
├── case_text.md
├── 01_当前状态/ … 11_诊断证明/
├── inbox/
├── pi_session/
│   ├── conversation.jsonl
│   ├── preferences.json
│   ├── outstanding/
│   └── push_budget.json
├── memory/
│   ├── version.json
│   ├── memory.sqlite
│   └── provenance/
│       └── index.jsonl
├── triggers/<run_id>/
└── archives/
```

## profile.json schema

```json
{
  "patient_code": "anon_001",
  "demographics": { "age": 56, "sex": "M", "ethnicity": "Han-Chinese", "weight_kg": 68 },
  "diagnosis": {
    "primary_site": "liver", "histology": "HCC",
    "stage_TNM": "T3N0M0", "stage_BCLC": "B",
    "diagnosis_date": "2024-11-12"
  },
  "treatment_history": [
    { "line": 1, "regimen": "TACE", "start": "2024-12-01", "end": "2025-08-15", "best_response": "PR" }
  ],
  "comorbidities": ["HBV chronic", "Child-Pugh A"],
  "preferences": { "depth": "technical", "language": "zh-CN" }
}
```
