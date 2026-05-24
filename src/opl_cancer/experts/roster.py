"""v0 Expert Roster — 18 named archetypes. Spec §2.2.X."""
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
)


ROSTER: dict[str, ExpertProfile] = {
    name: ExpertProfile(
        name=name,
        role=role,
        inspiration=inspiration,
        persona_summary=f"(P1 stub — full persona prompt at prompts/experts/{name}/persona.md)",
        task_package_portfolio=[],
        preferred_integrator_families=[],
    )
    for (name, role, inspiration) in _ROSTER_DATA
}


def get_expert_profile(name: str) -> ExpertProfile:
    if name not in ROSTER:
        raise KeyError(f"unknown expert {name!r}; one of {sorted(ROSTER)}")
    return ROSTER[name]
