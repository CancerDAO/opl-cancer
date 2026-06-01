# Canonical Patient Data Layout + `[[src:...]]` Provenance Grammar

OPL is **downstream of records organization** — it does not OCR or triage raw
uploads. Before any Wave runs, the patient's records must be organized into the
canonical layout below (by a records-organization tool or an equivalent). This is the
single source of truth shared by the SKILL, the readiness gate, and
`G35 clinical_fact_provenance`.

## Directory layout

```
~/CancerDAO/patients/<patient_code>/
├── 01_当前状态/ … 11_诊断证明/   # 11-bucket organized source documents
├── ocr/                          # OCR sidecars (one .txt/.md per source doc)
│   ├── 05_labs_2024-05.txt
│   └── 02_pathology_report.txt
├── profile.json                  # structured profile (schema_v1)
├── case_text.md                  # narrative case text — every clinical value [[src:]]-anchored
├── timeline.md                   # clinical events
├── readiness.json                # {grade: A|B|C|D|F, domains:[...], blocking_gaps:[...]}
├── inbox/                        # new file drop → triggers a new run
└── triggers/<run_id>/            # one Wave run (plan.json, run_manifest.json, tasks/, delivery/, provenance.jsonl)
```

`profile.json` and `case_text.md` are **required** before OPL will plan a run;
`opl-cancer go` refuses raw input that lacks them (it will not OCR or invent).

## `[[src:...]]` provenance anchor grammar

Every **measured clinical value** in `case_text.md` and in any established-layer
claim — lab numbers (creatinine, GGT, AST/ALT, bilirubin, eGFR, LDH, tumour
markers), organ-function scores (Child-Pugh, ECOG, NYHA, LVEF, KPS), staging
(TNM / stage), and molecular calls (KRAS/NRAS/BRAF/EGFR/HER2/TP53/ATM/MSI/TMB/HRD
with a state) — MUST carry a `[[src:...]]` anchor to the OCR sidecar it was read
from. This is what `G35` checks; an un-anchored value is treated as potentially
fabricated and blocks delivery.

```
[[src:<relative-path>#<locator>]]
```

* `<relative-path>` — a path **relative to the patient directory**, normally an
  `ocr/` sidecar (e.g. `ocr/05_labs_2024-05.txt`) or a source document
  (e.g. `01_当前状态/report.pdf`). The target file MUST exist.
* `<locator>` — optional; a line/region hint (e.g. `#L12`, `#p2`, `#table1`).

### Examples

```markdown
肌酐 88 µmol/L [[src:ocr/05_labs_2024-05.txt#L12]]
ECOG 1 [[src:ocr/03_clinic_note.txt#L4]]
KRAS p.G12C 突变 (VAF 11.5%) [[src:ocr/07_ngs_report.txt#L31]]
cT3N1M1 [[src:01_当前状态/staging.pdf]]
```

### Unknown values are honest — never invented

If a value was not measured / not in the records, write it as `UNKNOWN` (or
未知 / 未检测 / 未查). This passes `G35`. Inventing a number to fill the gap is the
exact failure (`AP-16`) the anchor requirement exists to stop.

```markdown
NRAS: UNKNOWN（未检测）          ✓ honest
BRAF V600E 状态未知              ✓ honest
肌酐 88 (正常)                   ✗ blocked by G35 — no [[src:]] anchor
```
