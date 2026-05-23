# OPL for Cancer

> 让全世界的每一个人都能拥有一个完整的 AI scientist team,只为他/她一个人工作 — 调取世界已知的信息,并主动产生世界未知的新信息,患者本人是自己案例的唯一决策人。

[![CI](https://github.com/CancerDAO/opl-cancer-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/CancerDAO/opl-cancer-skill/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

## Status

**P0 Skeleton.** Repo scaffold + orchestrator framework + 18-name Expert roster (placeholder personas) + validators framework. No working pipeline yet.

## Quick start

```bash
git clone https://github.com/CancerDAO/opl-cancer-skill
cd opl-cancer-skill
pip install -e .[dev]

# Verify install
opl-cancer status
opl-cancer list-experts
opl-cancer init-patient anon_001 --root ~/opl_patients
```

As a skill plugin (post-P0):

```bash
npx skills add CancerDAO/opl-cancer-skill
```

## Architecture

OPL for Cancer is a two-layer fractal AI scientist team:

**Outer layer — 20 named entities**:

- **Sid** (PI / Chief-of-Staff) — single conversational surface to patient
- **Henry** (Auditor) — global IRB-substitute (4-layer transparency)
- **18 named Experts** — Rosa (pathology), Bert (genetics), Vince (oncology), Rick (trials), Heddy (radiology), Mary (pharmacology), Aviv (bioinformatics), Tyler (wet-lab design), Iain (meta-analysis), Ted (radiation oncology), Riad (interventional), Jen (palliative), Kieren (infectious disease), Mark (endocrinology / irAE), Hong (TCM oncology), Frances (expanded access), Dennis (cross-border), Steve (nutrition)

**Inner layer — task-primitive grammar** (each Expert internally uses):

planner → executor (task package) → reviewer (cross-expert peer) → auditor (intra-expert) → integrator → feedback

## Expert Roster

| Name | Role | Inspiration |
|---|---|---|
| Sid | PI / Chief-of-Staff | Siddhartha Mukherjee (clinician + science communicator) |
| Henry | Auditor | Henry Beecher (informed consent / research ethics) |
| Rosa | Pathologist | Juan Rosai (外科病理学之父) |
| Bert | Geneticist | Bert Vogelstein (TP53/CRC genetics) |
| Vince | Oncologist | Vincent DeVita (combination chemo) |
| Rick | Clinical Trials | Richard Schilsky (ASCO CMO) |
| Heddy | Radiologist | Hedvig Hricak (oncologic imaging) |
| Mary | Pharmacologist | Mary Relling (TPMT) |
| Aviv | Bioinformatician | Aviv Regev (single-cell + Broad) |
| Tyler | Wet-Lab Designer | Tyler Jacks (mouse models) |
| Iain | Meta-Analyst | Iain Chalmers (Cochrane) |
| Ted | Radiation Oncologist | Theodore Lawrence (GI radiation) |
| Riad | Interventional Oncologist | Riad Salem (HCC TARE) |
| Jen | Palliative Specialist | Jennifer Temel (NEJM 2010 PC trial) |
| Kieren | Infectious Disease | Kieren Marr (febrile neutropenia) |
| Mark | Endocrinologist (irAE) | Mark Stelfox (ICI irAE) |
| Hong | TCM Oncologist | 林洪生 (中国中医肿瘤) |
| Frances | Expanded Access | Frances Kelsey (FDA safety) |
| Dennis | Cross-Border | Dennis Lo 卢煜明 (cfDNA) |
| Steve | Nutritionist | Stephen Heber (oncology nutrition) |

Names are first-name homages — archetype personas, not impersonations of real individuals.

## License

Apache-2.0. See [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
