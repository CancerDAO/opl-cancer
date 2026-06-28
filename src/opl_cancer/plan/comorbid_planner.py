"""Multi-comorbid planner expansion. v1.5 P0-6.

The v1.4 deterministic skeleton plan (cli.py:plan) produced t1-t9 with
Rosa/Bert/Rick/Aviv/Iain only. The PT-EXAMPLE-A run — an L4+ post-ICI
patient with CKD3b + CAD-PCI + active thyroiditis — needed Mark (irAE),
Mary (DDI), Frances (EAP), Riad (Chinese-drug-access), Dennis (border),
and Heddy (imaging) added to be useful. The assistant silently
hand-expanded the plan at T15-T20 — correct call, but undocumented and
not reproducible (docs/ANTI_PATTERNS_v1.4.md AP-9).

This module adds explicit trigger-based expansion. The plan() CLI calls
``maybe_expand_for_comorbid(tasks, profile)`` after building the
baseline skeleton; that function:

  * reads triggers from ``profile.json`` (and optionally
    ``readiness.json``),
  * appends additional Task entries for each trigger that fires,
  * narrates *which* triggers fired in the returned ``triggers_fired``
    list — the CLI surfaces this to the user.

This is deliberately deterministic + readable, not LLM-driven. The
LLM-driven planner (v1.6+) will override; for v1.5 the skeleton is the
floor not the ceiling.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .schemas import Task

# v2.1 P0-#5: explicit profile-key registry. Used by schema_validator to
# detect typos like "active_irrae" → "active_irae" (Did-you-mean) without
# accidentally rejecting future fields. Keep in sync with the profile
# schema (schemas/profile.schema.json) + the helpers below.
TRIGGER_KEYS: set[str] = {
    "prior_lines",
    "prior_therapy_lines",
    "concurrent_meds",
    "concurrent_medications",
    "egfr_ml_min",
    "lvef_pct",
    "age_years",
    "active_irae",
    "toxicity_history",
    "comorbidities",
    "comorbidities_text",
    "country",
    "city",
    "imaging_gaps",
    "diagnosis",
    "current_status",
    "concise_summary",
    "active_problems",
    "patient_value_hierarchy",
    "patient_id_hash",
}

# Trigger thresholds. Calibrated against the PT-EXAMPLE-A case + the
# CancerDAO synthetic golden set; refined when v1.6 LLM-planner is wired.
PRIOR_LINES_TRIGGER = 3
CONCURRENT_MEDS_TRIGGER = 3
EGFR_TRIGGER_CKD = 60.0   # mL/min — at-or-below counts as CKD
LVEF_TRIGGER_CARDIAC = 50.0   # percentage — at-or-below counts as cardiac risk
AGE_TRIGGER_ELDERLY = 70   # years — elderly imaging frequency considerations


@dataclass(frozen=True)
class ExpansionTrigger:
    """A single trigger that justifies adding a particular expert task."""

    name: str
    rationale: str
    task: Task


def _normalise_text_fields(profile: dict[str, Any]) -> str:
    bits: list[str] = []
    for key in (
        "diagnosis",
        "current_status",
        "concise_summary",
        "active_problems",
        "comorbidities_text",
    ):
        v = profile.get(key)
        if isinstance(v, str):
            bits.append(v)
        elif isinstance(v, list):
            bits.extend(str(x) for x in v if x)
    return " ".join(bits).lower()


def _has_active_irae(profile: dict[str, Any]) -> bool:
    tox = profile.get("toxicity_history") or {}
    if isinstance(tox, dict):
        if tox.get("active_immune_related") is True:
            return True
        # Allow nested structures e.g. {"thyroiditis": {"active": true}}
        for v in tox.values():
            if isinstance(v, dict) and v.get("active") is True:
                return True
    text = _normalise_text_fields(profile)
    return any(
        kw in text
        for kw in (
            "active irae",
            "active immune-related",
            "ongoing thyroiditis",
            "active thyroiditis",
            "active pneumonitis",
            "ongoing myocarditis",
            "活动期甲状腺炎",
            "免疫相关炎症未控",
        )
    )


def _prior_lines_count(profile: dict[str, Any]) -> int:
    lines = profile.get("prior_therapy_lines")
    if isinstance(lines, int):
        return lines
    if isinstance(lines, list):
        return len(lines)
    # Fallback: text-pattern "L2", "L3", "L4", etc.
    text = _normalise_text_fields(profile)
    matches = re.findall(r"\bl(\d+)\b", text)
    if matches:
        return max(int(m) for m in matches)
    return 0


def _concurrent_med_count(profile: dict[str, Any]) -> int:
    meds = profile.get("concurrent_medications")
    if isinstance(meds, list):
        return len(meds)
    if isinstance(meds, dict):
        return len(meds)
    if isinstance(meds, int):
        return meds
    return 0


def _has_cardiac_comorbidity(profile: dict[str, Any]) -> bool:
    co = profile.get("comorbidities") or []
    co_list = co if isinstance(co, list) else [co] if isinstance(co, str) else []
    co_lower = " ".join(str(c).lower() for c in co_list)
    text = _normalise_text_fields(profile) + " " + co_lower
    if any(
        kw in text
        for kw in (
            "cad",
            "pci",
            "myocardial infarction",
            "heart failure",
            "chf",
            "coronary",
            "冠心病",
            "心衰",
            "支架",
        )
    ):
        return True
    lvef = profile.get("lvef_pct")
    if isinstance(lvef, (int, float)) and lvef <= LVEF_TRIGGER_CARDIAC:
        return True
    return False


def _has_ckd(profile: dict[str, Any]) -> bool:
    co = profile.get("comorbidities") or []
    co_list = co if isinstance(co, list) else [co] if isinstance(co, str) else []
    co_lower = " ".join(str(c).lower() for c in co_list)
    text = _normalise_text_fields(profile) + " " + co_lower
    if any(
        kw in text
        for kw in (
            "ckd",
            "chronic kidney disease",
            "肾功能不全",
            "慢性肾病",
        )
    ):
        return True
    egfr = profile.get("egfr_ml_min")
    if isinstance(egfr, (int, float)) and egfr <= EGFR_TRIGGER_CKD:
        return True
    return False


def _is_cross_border_candidate(profile: dict[str, Any]) -> bool:
    """If patient is in mainland China + on multi-line history → likely
    needs cross-border / EAP / NMPA-import navigation."""
    country = (profile.get("country") or "").lower()
    if country in {"cn", "china", "中国"}:
        return True
    city = (profile.get("city") or "").lower()
    if any(c in city for c in ("beijing", "shanghai", "guangzhou", "shenzhen", "北京", "上海", "广州", "深圳", "杭州")):
        return True
    return False


def _has_imaging_gap(profile: dict[str, Any]) -> bool:
    """If imaging is overdue / missing per readiness flags."""
    flags = profile.get("imaging_gaps") or []
    if isinstance(flags, list) and len(flags) > 0:
        return True
    age = profile.get("age_years")
    if isinstance(age, (int, float)) and age >= AGE_TRIGGER_ELDERLY:
        return True  # elderly patients warrant Heddy review by default
    return False


def compute_expansion_triggers(
    profile: dict[str, Any], existing_task_ids: list[str]
) -> list[ExpansionTrigger]:
    """Return the ordered list of triggers that fire for this profile.

    ``existing_task_ids`` is used to allocate fresh task IDs (t10, t11, ...).
    """
    next_id = max(
        (int(tid[1:]) for tid in existing_task_ids if tid.startswith("t") and tid[1:].isdigit()),
        default=9,
    ) + 1

    triggers: list[ExpansionTrigger] = []

    def add(expert: str, package: str, sub_goal: str, name: str, rationale: str) -> None:
        nonlocal next_id
        triggers.append(
            ExpansionTrigger(
                name=name,
                rationale=rationale,
                task=Task(
                    id=f"t{next_id}",
                    expert=expert,
                    task_package=package,
                    sub_goal=sub_goal,
                ),
            )
        )
        next_id += 1

    if _has_active_irae(profile):
        add(
            "mark",
            "irae_rechallenge",
            "active irAE → irae rechallenge / cumulative-organ-load review",
            "active_irae",
            "profile shows active immune-related adverse event",
        )

    prior_lines = _prior_lines_count(profile)
    if prior_lines >= PRIOR_LINES_TRIGGER:
        add(
            "frances",
            "expanded_access_navigation",
            f"≥{PRIOR_LINES_TRIGGER} prior lines — chart EAP / NMPA / NRDL pathways",
            "multi_line_history",
            f"prior_therapy_lines={prior_lines} ≥ {PRIOR_LINES_TRIGGER}",
        )

    med_count = _concurrent_med_count(profile)
    if med_count >= CONCURRENT_MEDS_TRIGGER:
        add(
            "mary",
            "ddi_adme_dosing",
            f"{med_count} concurrent meds — DDI / dose-adjust review",
            "polypharmacy",
            f"concurrent_medications={med_count} ≥ {CONCURRENT_MEDS_TRIGGER}",
        )

    if _has_cardiac_comorbidity(profile):
        add(
            "mary",
            "ddi_adme_dosing",
            "cardiac comorbidity — re-check anti-VEGF / TKI cardiotoxicity DDIs",
            "cardiac_comorbidity",
            "CAD/PCI/CHF/LVEF≤50 detected",
        )

    if _has_ckd(profile):
        add(
            "mary",
            "ddi_adme_dosing",
            "CKD — renal dose adjustment review (raltitrexed/TAS-102/regorafenib)",
            "ckd",
            "CKD diagnosis OR eGFR ≤ 60 detected",
        )

    if _is_cross_border_candidate(profile):
        add(
            "riad",
            "interventional_oncology",
            "China mainland patient — interventional-oncology / liver-directed review for cross-border options",
            "china_patient_io",
            "patient in mainland China; IR is a cross-border-relevant lens",
        )
        add(
            "dennis",
            "cross_border_navigation",
            "China mainland patient — Boao / HK / overseas trial logistics",
            "cross_border_candidate",
            "patient in mainland China; Dennis lens covers border ops",
        )

    if _has_imaging_gap(profile):
        add(
            "heddy",
            "recist_progression",
            "imaging gap or elderly → RECIST review + image-acquisition plan",
            "imaging_gap",
            "imaging_gaps flagged OR age ≥ 70",
        )

    return triggers


def maybe_attach_prior_run(
    profile: dict[str, Any],
    patient_dir: Any = None,  # Path | str | None
    current_run_id: str | None = None,
) -> str | None:
    """v2.3 P2-#17 — peek at prior runs and return the latest prior run_id.

    The caller (planner / CLI) can carry this into the Plan metadata as
    ``extends_prior_run`` and propagate it down to Wave 6 manuscript
    framing ("this report extends prior MTB run X").

    Returns None if ``patient_dir`` is missing or no prior runs are
    present. The profile is read only for the optional
    ``patient_dir_override`` field.
    """
    if patient_dir is None:
        patient_dir = profile.get("patient_dir_override")
    if patient_dir is None:
        return None
    try:
        from pathlib import Path

        from opl_cancer.plan.prior_run_ingestion import (
            latest_prior_run_id,
        )
        return latest_prior_run_id(Path(patient_dir), current_run_id=current_run_id)
    except Exception:  # pragma: no cover — defensive
        return None


def maybe_expand_for_comorbid(
    base_tasks: list[Task],
    profile: dict[str, Any],
) -> tuple[list[Task], list[ExpansionTrigger]]:
    """Expand a plan with the comorbid red-line floor tasks.

    De-duplicates by (expert, task_package) — if a task already covers the
    expansion's expert+package, we skip it so each appears at most once.

    De-script (ADR-0040): this is now PURELY the deterministic safety floor
    (comorbid red-line thresholds). Goal→expert routing was a keyword router
    (``goal_router``) and is removed — team composition is the host LLM
    planner's job (``prompts/pi/goal_backward_planner.md``); Python only
    computes the floor the LLM agenda must cover (G55).
    """
    existing_ids = [t.id for t in base_tasks]
    existing_combos = {(t.expert, t.task_package) for t in base_tasks}
    triggers = compute_expansion_triggers(profile, existing_ids)
    expanded = list(base_tasks)
    fired_triggers: list[ExpansionTrigger] = []
    for trig in triggers:
        combo = (trig.task.expert, trig.task.task_package)
        if combo in existing_combos:
            continue
        existing_combos.add(combo)
        expanded.append(trig.task)
        fired_triggers.append(trig)
    return expanded, fired_triggers
