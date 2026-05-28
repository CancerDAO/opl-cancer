"""v0 Expert Roster — 20 named archetypes. Spec §2.2.X.

v2.2 ADR-0022 populates `task_package_portfolio` for Bert, Aviv, Mary, Maya
with the new bio-skill task packages (MSI / TMB / COSMIC signatures / ACMG /
OpenTargets evidence / biostats survival+subgroup / CPIC).
"""
from __future__ import annotations

from .base import ExpertProfile

_ROSTER_DATA: tuple[tuple[str, str, str], ...] = (
    ("rosa", "Pathologist", "Juan Rosai — 外科病理学之父"),
    ("bert", "Geneticist (Molecular)", "Bert Vogelstein — TP53/CRC 分子遗传"),
    ("vince", "Oncologist (Treating)", "Vincent DeVita — 联合化疗先驱"),
    ("rick", "Clinical Trial Specialist", "Richard Schilsky — ASCO CMO"),
    ("heddy", "Radiologist", "Hedvig Hricak — 肿瘤影像"),
    ("mary", "Pharmacologist", "Mary Relling — TPMT 药物基因组学"),
    ("aviv", "Bioinformatician", "Aviv Regev — 单细胞 + Broad"),
    ("tyler", "Wet-Lab Designer", "Tyler Jacks — 基因工程小鼠模型"),
    ("iain", "Meta-Analyst", "Iain Chalmers — Cochrane 创始"),
    ("ted", "Radiation Oncologist", "Theodore Lawrence — GI 放疗"),
    ("riad", "Interventional Oncologist", "Riad Salem — HCC TARE"),
    ("jen", "Palliative Specialist", "Jennifer Temel — NEJM 2010 早期 PC + OS 延长"),
    ("kieren", "Infectious Disease", "Kieren Marr — 中性粒减少期 / 侵袭性真菌"),
    ("mark", "Endocrinologist (irAE)", "composite archetype — ASCO + ESMO irAE 内分泌共识"),
    ("hong", "TCM Oncologist", "林洪生 — 中国中医肿瘤奠基"),
    ("frances", "Expanded Access Navigator", "Frances Kelsey — FDA 药物安全 + 访问伦理"),
    ("dennis", "Cross-Border Coordinator", "Dennis Lo 卢煜明 — cfDNA / US-CN-HK 跨界转化"),
    ("steve", "Nutritionist", "David Heber — UCLA Center for Human Nutrition 创始人"),
    # v2.0.0 — paradigm shift (ADR-0010): add KG-synergy reasoner + in-silico medicinal chemist
    ("maya", "Knowledge-Graph Synergy Reasoner", "composite archetype — Marinka Zitnik (PrimeKG / Harvard) + Tijana Milenković (network medicine)"),
    ("julius", "Medicinal Chemist (in silico)", "composite archetype — generative-chemistry lineage (ESMFold + DiffDock + RDKit + medchem filters)"),
)


# v2.2 ADR-0022 — populate the task_package_portfolio fields that were
# stubs in v2.0/v2.1. Each portfolio names the prompt files under
# prompts/tasks/ that this expert owns end-to-end.
_PORTFOLIO_V22: dict[str, list[str]] = {
    "bert": [
        "molecular_ngs_interpretation",
        "msi_detection",                    # v2.2 ADR-0022
        "tmb_calculation",                  # v2.2 ADR-0022
        "cosmic_signature_extraction",      # v2.2 ADR-0022
        "acmg_germline_classification",     # v2.2 ADR-0022
        "hypothesis_generation",
    ],
    "aviv": [
        "dataset_acquisition",
        "bioinformatics_data_analysis",
        "hypothesis_validation",
        "single_cell_reanalysis",
        "pathway_enrichment",
        "biostats_survival",                # v2.2 ADR-0022
        "biostats_subgroup",                # v2.2 ADR-0022
    ],
    "mary": [
        "ddi_adme_dosing",
        "ici_endocrine_irae",
        "pharmacogenomics_cpic",            # v2.2 ADR-0022
    ],
    "maya": [
        "drug_repurposing",
        "opentargets_evidence",             # v2.2 ADR-0022
        "hypothesis_generation",
    ],
}


# v2.2 ADR-0022 — declare preferred integrator families for each expert
# so the planner can prefetch the right integrator outputs before dispatch.
_INTEGRATOR_FAMILIES_V22: dict[str, list[str]] = {
    "bert": ["F_BIO", "F1", "F4"],   # MSI / TMB / COSMIC / ACMG + OncoKB
    "aviv": ["F_BIO", "F1"],         # lifelines + PaperQA + figure_render
    "mary": ["F_BIO", "F3"],         # CPIC + RxNorm
    "maya": ["F9", "F_BIO"],         # OpenTargets + PrimeKG
}


ROSTER: dict[str, ExpertProfile] = {
    name: ExpertProfile(
        name=name,
        role=role,
        inspiration=inspiration,
        persona_summary=f"(P1 stub — full persona prompt at prompts/experts/{name}/persona.md)",
        task_package_portfolio=_PORTFOLIO_V22.get(name, []),
        preferred_integrator_families=_INTEGRATOR_FAMILIES_V22.get(name, []),
    )
    for (name, role, inspiration) in _ROSTER_DATA
}


def get_expert_profile(name: str) -> ExpertProfile:
    if name not in ROSTER:
        raise KeyError(f"unknown expert {name!r}; one of {sorted(ROSTER)}")
    return ROSTER[name]
