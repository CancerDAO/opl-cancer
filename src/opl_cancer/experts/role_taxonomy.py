"""ExpertRole + RoleTaxonomy — v2.5 compositional foundation (RFC 0001 §2.1).

v2.5 ships:
- ExpertRole dataclass (4 axes)
- references/role_taxonomy.yaml — enumeration of valid values per axis
- prompts/experts/_template.md — parametric persona prompt template
- FAST_PATH_ROLES — all 20 v2.4 personas as cached tuples
- compose_role(constraints) — STUB: matches FAST_PATH first; raises
  RoleCompositionNotYetImplemented for novel constraints (real LLM
  composition is M2)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_TAXONOMY_YAML = _REPO_ROOT / "references" / "role_taxonomy.yaml"


# ─── dataclass ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ExpertRole:
    """Compositional expert role — RFC 0001 §2.1."""

    discipline: str
    subspecialty: str
    method_specialty: str
    bridging_role: str


# ─── taxonomy loader ──────────────────────────────────────────────────────


def load_taxonomy() -> dict[str, list[str]]:
    with _TAXONOMY_YAML.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    out: dict[str, list[str]] = {}
    for axis in ("discipline", "subspecialty", "method_specialty", "bridging_role"):
        values = data.get(axis) or []
        out[axis] = [str(v) for v in values]
    return out


# ─── exception ────────────────────────────────────────────────────────────


class RoleCompositionNotYetImplemented(NotImplementedError):
    """Raised in v2.5 when compose_role gets a novel constraint that doesn't
    match any FAST_PATH_ROLES entry. Real LLM composition lands in M2."""


# ─── FAST_PATH_ROLES — the 20 v2.4 personas ────────────────────────────────


# Each FAST_PATH entry maps a v2.4 persona name → its compositional tuple.
# Sourced from references/expert-roster.md + experts/roster.py inspiration
# strings; M2 may refine via LLM-curated review.
FAST_PATH_ROLES: dict[str, ExpertRole] = {
    "rosa": ExpertRole(
        discipline="pathology",
        subspecialty="surgical_pathology",
        method_specialty="histomorphologic_diagnosis",
        bridging_role="clinician_facing",
    ),
    "bert": ExpertRole(
        discipline="genetics",
        subspecialty="cancer_genomics",
        method_specialty="NGS_variant_interpretation",
        bridging_role="precision_medicine_translator",
    ),
    "vince": ExpertRole(
        discipline="oncology",
        subspecialty="solid_tumor_oncology",
        method_specialty="combination_chemotherapy_design",
        bridging_role="clinician_facing",
    ),
    "rick": ExpertRole(
        discipline="clinical_trial_methodology",
        subspecialty="solid_tumor_oncology",
        method_specialty="phase_1_trial_design",
        bridging_role="regulatory_translator",
    ),
    "heddy": ExpertRole(
        discipline="radiology",
        subspecialty="oncologic_imaging",
        method_specialty="tumor_imaging_response",
        bridging_role="imaging_radiologist",
    ),
    "mary": ExpertRole(
        discipline="clinical_pharmacology",
        subspecialty="DDI_ADME",
        method_specialty="tpmt_pharmacogenomics",
        bridging_role="safety_advisor",
    ),
    "aviv": ExpertRole(
        discipline="bioinformatics",
        subspecialty="single_cell_genomics",
        method_specialty="scRNAseq_reanalysis",
        bridging_role="bench_to_bedside",
    ),
    "tyler": ExpertRole(
        discipline="wet_lab_biology",
        subspecialty="mouse_modeling",
        method_specialty="genetic_engineering_mouse_models",
        bridging_role="lab_design",
    ),
    "iain": ExpertRole(
        discipline="meta_research",
        subspecialty="cochrane_systematic_review",
        method_specialty="meta_analysis_methodology",
        bridging_role="meta_analysis_synthesizer",
    ),
    "ted": ExpertRole(
        discipline="radiation_oncology",
        subspecialty="GI_radiation",
        method_specialty="radiation_dose_modeling",
        bridging_role="clinician_facing",
    ),
    "riad": ExpertRole(
        discipline="interventional_oncology",
        subspecialty="HCC_TARE",
        method_specialty="interventional_embolization",
        bridging_role="clinician_facing",
    ),
    "jen": ExpertRole(
        discipline="palliative_care",
        subspecialty="early_integrated_palliative_care",
        method_specialty="end_of_life_communication",
        bridging_role="palliative_specialist",
    ),
    "kieren": ExpertRole(
        discipline="infectious_disease",
        subspecialty="neutropenic_fever",
        method_specialty="antifungal_stewardship",
        bridging_role="safety_advisor",
    ),
    "mark": ExpertRole(
        discipline="endocrinology",
        subspecialty="irAE_endocrine",
        method_specialty="irAE_workup_algorithm",
        bridging_role="irAE_consultant",
    ),
    "hong": ExpertRole(
        discipline="traditional_chinese_medicine",
        subspecialty="TCM_oncology",
        method_specialty="chinese_herbal_pharmacology",
        bridging_role="tcm_oncology_consultant",
    ),
    "frances": ExpertRole(
        discipline="regulatory_affairs",
        subspecialty="expanded_access",
        method_specialty="safe_drug_access_navigation",
        bridging_role="access_navigator",
    ),
    "dennis": ExpertRole(
        discipline="cross_border_medicine",
        subspecialty="cross_border_us_cn_hk",
        method_specialty="cross_jurisdiction_referral",
        bridging_role="cross_border_coordinator",
    ),
    "steve": ExpertRole(
        discipline="nutrition",
        subspecialty="oncology_nutrition",
        method_specialty="macronutrient_oncology_planning",
        bridging_role="oncology_nutritionist",
    ),
    "maya": ExpertRole(
        discipline="knowledge_graph_reasoning",
        subspecialty="network_medicine",
        method_specialty="kg_synergy_reasoning",
        bridging_role="kg_to_treatment_translator",
    ),
    "julius": ExpertRole(
        discipline="medicinal_chemistry",
        subspecialty="in_silico_drug_design",
        method_specialty="de_novo_molecule_design",
        bridging_role="in_silico_designer",
    ),
}


# ─── compose_role (v2.5 stub) ─────────────────────────────────────────────


def compose_role(constraints: dict[str, Any]) -> ExpertRole:
    """v2.5 STUB compose_role.

    Resolution order:
    1. If constraints['persona_name'] matches a FAST_PATH entry, return it.
    2. If (discipline, subspecialty) pair matches exactly one FAST_PATH role,
       return it.
    3. Else raise RoleCompositionNotYetImplemented (real LLM composition: M2).
    """
    # (1) explicit persona name
    name = constraints.get("persona_name")
    if name and name in FAST_PATH_ROLES:
        return FAST_PATH_ROLES[name]

    # (2) discipline + subspecialty pair match
    discipline = constraints.get("discipline")
    subspecialty = constraints.get("subspecialty")
    if discipline and subspecialty:
        matches = [
            r
            for r in FAST_PATH_ROLES.values()
            if r.discipline == discipline and r.subspecialty == subspecialty
        ]
        if len(matches) == 1:
            return matches[0]

    # (3) M2 work
    raise RoleCompositionNotYetImplemented(
        f"compose_role(constraints={constraints!r}) — no FAST_PATH match. "
        "Real LLM composition lands in v2.7 (M2)."
    )


def to_persona_prompt(role: ExpertRole, **extra: Any) -> str:
    """Render prompts/experts/_template.md with role params.

    Lightweight Jinja-style substitution; M2 swaps to real Jinja2 / Liquid.
    """
    template_path = _REPO_ROOT / "prompts" / "experts" / "_template.md"
    text = template_path.read_text(encoding="utf-8")
    subs: dict[str, str] = {
        "discipline": role.discipline,
        "subspecialty": role.subspecialty,
        "method_specialty": role.method_specialty,
        "bridging_role": role.bridging_role,
    }
    for k, v in extra.items():
        subs[k] = str(v)
    out = text
    for k, v in subs.items():
        out = out.replace(f"{{{{{k}}}}}", v)
    return out


__all__ = [
    "ExpertRole",
    "FAST_PATH_ROLES",
    "RoleCompositionNotYetImplemented",
    "compose_role",
    "load_taxonomy",
    "to_persona_prompt",
]
