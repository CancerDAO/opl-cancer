"""Wave 2 → Wave 5 renderer bridge. v2.0.1 (post-review).

Reads ``wave2_hypotheses.json`` and extracts [S]-with-testability hypotheses
that should populate the patient brief's ``world_unknown_candidates`` section.

This module exists because the v2.0.0-rc1 paradigm shift added the renderer
template branch + the generation strategies, but forgot the bridge — making
the World-Unknown section render-only when test fixtures populated it
directly. See iteration review (2026-05-27) finding #3.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_V2_SPECULATIVE_STRATEGIES = (
    "target_synergy_emergent",
    "undrugged_target_design",
)

# v2.0.2 (round-2 review): specific drug names get redacted to target class
# names so patients cannot misread the brief as an off-label drug list.
# This map covers drugs commonly suggested by Wave 2 for L4+ mCRC; extend per
# cancer type as needed (follow-up: registry-driven dictionary per cancer site).
_DRUG_TO_CLASS_REDACTION: dict[str, str] = {
    # KRAS G12C
    "sotorasib": "KRAS G12C 抑制剂 (class)",
    "adagrasib": "KRAS G12C 抑制剂 (class)",
    "mrtx849": "KRAS G12C 抑制剂 (preclinical/early-phase class)",
    "divarasib": "KRAS G12C 抑制剂 (class, next-gen)",
    "gdc-6036": "KRAS G12C 抑制剂 (preclinical/early-phase class)",
    "jab-21822": "KRAS G12C 抑制剂 (class)",
    "氟泽雷塞": "KRAS G12C 抑制剂 (class)",
    "格索雷塞": "KRAS G12C 抑制剂 (class)",
    "d-1553": "KRAS G12C 抑制剂 (class)",
    # SHP2
    "rmc-4630": "SHP2 抑制剂 (preclinical/early-phase class)",
    "jab-3312": "SHP2 抑制剂 (early-phase class)",
    "tno155": "SHP2 抑制剂 (early-phase class)",
    # pan-RAS
    "rmc-6236": "pan-RAS(ON) 抑制剂 (preclinical/early-phase class)",
    "daraxonrasib": "pan-RAS(ON) 抑制剂 (early-phase class)",
    # mTOR / PI3K
    "everolimus": "mTORC1 抑制剂 (class — 此处仅作机制示例，不构成具体用药建议)",
    "sirolimus": "mTORC1 抑制剂 (class — 此处仅作机制示例，不构成具体用药建议)",
    "alpelisib": "PI3K-α 抑制剂 (class)",
    # MEK / RAF
    "trametinib": "MEK 抑制剂 (class)",
    "binimetinib": "MEK 抑制剂 (class)",
    # ferroptosis / metabolic
    "ml210": "GPX4 抑制剂 (research-tool class)",
    "rsl3": "GPX4 抑制剂 (research-tool class)",
    "withaferin a": "GPX4 抑制剂 (research-tool class)",
    "sulfasalazine": "system Xc− 抑制剂 (老药新用类，需医师指导)",
    # generic chemo / panitumumab / cetuximab — preserve (standard care, not speculative)
}


import re as _re  # noqa: E402 — intentional: placed after the curated redaction dict

# v2.6.0 fail-closed backstop. The curated dict above is mCRC-biased and finite;
# the review found it fails OPEN (a novel speculative drug renders verbatim in the
# patient brief). These patterns catch drug-LIKE tokens the dict missed and redact
# them to a generic class placeholder so no specific compound can leak. This is the
# mechanical floor; the proper generalization fix is an RxNorm/OncoKB/LLM class
# resolver (kept out of this deterministic safety gate on purpose —
# memory:feedback_default_prompt_over_script).
_FAIL_CLOSED_PLACEHOLDER = "[研究阶段候选药物——具体名称见 PI 临床简报，不构成用药建议]"
# Investigational codes: 2-6 letters + optional hyphen + 3-5 digits (MRTX1133,
# GDC-6036, JAB-21822). Trial IDs (NCT + 8 digits) and gene variants (G12C) do
# not match (digit-count / shape differ).
_INVESTIGATIONAL_CODE = _re.compile(r"\b[A-Za-z]{2,6}-?\d{3,5}\b")
# INN-stem small-molecule inhibitors (…ib: -nib/-sib/-rasib/-parib/-ciclib/-lisib)
# and monoclonal antibodies (…mab), ≥6 chars so short prose words don't trip.
_INN_STEM = _re.compile(r"\b[A-Za-z]{4,}(?:ib|mab)\b", _re.IGNORECASE)
# Tokens with an investigational-code shape that are NOT drugs (registry/trial ids).
_CODE_ALLOWLIST = _re.compile(r"^(?:NCT|PMID|ISRCTN|ChiCTR|EudraCT|GRCh)\d*$", _re.IGNORECASE)


def _redact_drug_specifics(text: str) -> tuple[str, list[str]]:
    """Replace specific drug names with target-class equivalents — FAIL CLOSED.

    Returns (redacted_text, list_of_redacted_drugs_for_audit). Backstop catches
    are recorded as ``fail_closed:<token>`` so the audit distinguishes the
    deterministic floor firing from a curated-dict class mapping.
    """
    if not isinstance(text, str):
        return text, []
    redacted_list: list[str] = []
    out = text
    # Pass 1 — precise curated class mapping.
    for drug, cls in _DRUG_TO_CLASS_REDACTION.items():
        pattern = _re.compile(rf"\b{_re.escape(drug)}\b", _re.IGNORECASE)
        if pattern.search(out):
            redacted_list.append(drug)
            out = pattern.sub(cls, out)

    # Pass 2 — fail-closed backstop for drug-like tokens the dict missed.
    def _redact_token(m: "_re.Match[str]") -> str:
        tok = m.group(0)
        if _CODE_ALLOWLIST.match(tok):
            return tok
        redacted_list.append(f"fail_closed:{tok}")
        return _FAIL_CLOSED_PLACEHOLDER

    out = _INVESTIGATIONAL_CODE.sub(_redact_token, out)
    out = _INN_STEM.sub(_redact_token, out)
    return out, redacted_list


# E3/ADR-0039 de-scripting: the _TIER_KEYWORDS substring table was REMOVED.
# Actionability tiering is LLM judgment — it reasons about assay turnaround +
# regulatory / data-access constraints (prompts/tasks/actionability_tier_classification.md)
# and sets `actionability_tier` on the candidate. Python only validates the
# provided tier + enforces the deterministic speculative SAFETY floor below.
_VALID_TIERS = ("actionable_this_week", "weeks", "months_or_more", "research_only")


def normalize_actionability_tier(
    provided_tier: str | None, *, allow_actionable_this_week: bool = True,
) -> str:
    """Validate a HOST-PROVIDED actionability tier and apply the safety floor.

    E3 / ADR-0039: the CLASSIFICATION (which tier a testability path falls in) is
    LLM judgment and is set on the candidate as ``actionability_tier``. This
    function no longer keyword-matches; it (a) validates the provided tier against
    the enum and (b) enforces the deterministic SAFETY floor that must stay in
    Python: a speculative [S] item may NEVER carry the "actionable_this_week"
    badge (it would mislead a patient into thinking an unproven hypothesis is an
    immediate clinical action), so with ``allow_actionable_this_week=False`` that
    tier is floored to "weeks". Absent / invalid → "research_only" (conservative,
    never guessed from keywords).
    """
    tier = provided_tier if provided_tier in _VALID_TIERS else "research_only"
    if not allow_actionable_this_week and tier == "actionable_this_week":
        return "weeks"
    return tier


_ACTIONABILITY_LABEL_ZH: dict[str, str] = {
    "actionable_this_week": "✅ 本周内可执行 (Actionable this week)",
    "weeks": "🟡 数周可执行 (Weeks)",
    "months_or_more": "🟠 数月以上 / 需科研合作 (Months+)",
    "research_only": "⚪ 纯研究方向 / 暂无患者级路径 (Research-only)",
}


def actionability_label_zh(tier: str) -> str:
    return _ACTIONABILITY_LABEL_ZH.get(tier, _ACTIONABILITY_LABEL_ZH["research_only"])


def load_soc_floor(run_dir: Path) -> str | None:
    """Read the stage-appropriate standard-of-care FLOOR statement (G57).

    A complete run names the global standard of care for the patient's stage
    BEFORE any beyond-guideline frontier. The treating-oncologist expert
    (Vince) writes ``triggers/<run_id>/soc_floor.json`` with keys
    ``{stage, standard, pivotal_pmid?}``. Rendering is deterministic: this
    loader surfaces it into the brief's ``[SOC-FLOOR]`` section.

    Returns ``None`` when absent/malformed → the section is omitted → G57
    blocks delivery. That is the gate working as designed: a frontier-only
    brief that skips the floor is the exact failure G57 guards against
    (ADR-0030 / project_opl_cancer_v211_hardening — the missed PACIFIC /
    durvalumab consolidation incident).
    """
    fp = run_dir / "soc_floor.json"
    if not fp.exists():
        return None
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    stage = str(data.get("stage") or "").strip()
    standard = str(data.get("standard") or "").strip()
    if not stage or not standard:
        return None
    line = f"{stage} — 标准治疗地板 / stage-appropriate standard of care: {standard}"
    pmid = str(data.get("pivotal_pmid") or "").strip()
    if pmid:
        line += f" [PMID:{pmid}]"
    return line


def load_world_unknown_candidates(run_dir: Path) -> list[dict[str, Any]]:
    """Read wave2_hypotheses.json from run_dir, return [S]-with-testability list.

    Filters:
    - claim_layer == "speculative"
    - testability_path is a non-empty string of plausible length (≥20 chars)
    - generation_strategy is one of the v2 strategies OR has the
      ``testability_path`` field (i.e., authored intentionally as world-unknown)

    Returns empty list if wave2 file absent or malformed — caller may then
    omit the section.
    """
    wave2_path = run_dir / "wave2_hypotheses.json"
    if not wave2_path.exists():
        return []
    try:
        payload = json.loads(wave2_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    hyps = payload.get("hypotheses") or payload.get("top_k_hypotheses") or []
    out: list[dict[str, Any]] = []
    for h in hyps:
        if h.get("claim_layer") != "speculative":
            continue
        tpath = h.get("testability_path") or ""
        if not isinstance(tpath, str) or len(tpath.strip()) < 20:
            # Skip hypotheses whose testability_path is missing / placeholder
            # ("TBD", "see references" would fall below the threshold).
            continue
        strategy = h.get("generation_strategy", "")
        if (
            strategy not in _V2_SPECULATIVE_STRATEGIES
            and "testability_path" not in h
        ):
            continue
        # v2.0.2 (round-2 review): redact specific drug names → target class
        text_redacted, drugs_redacted_text = _redact_drug_specifics(h.get("text", ""))
        tpath_redacted, drugs_redacted_path = _redact_drug_specifics(tpath)
        all_redacted = sorted(set(drugs_redacted_text + drugs_redacted_path))

        # Actionability tier — host-provided (LLM classifier), validated + floored.
        # P0.4: these are ALL speculative [S] items → forbid the
        # "actionable_this_week" badge (a speculative direction is never an
        # immediate clinical action). Earliest tier is "weeks".
        tier = normalize_actionability_tier(
            h.get("actionability_tier"), allow_actionable_this_week=False,
        )

        # Carry a minimal subset to the template; renderer Jinja handles missing.
        out.append(
            {
                "id": h.get("id", ""),
                "text": text_redacted,
                "generation_strategy": strategy,
                "claim_layer": "speculative",
                "testability_path": tpath_redacted,
                "actionability_tier": tier,
                "actionability_label_zh": actionability_label_zh(tier),
                "evidence_refs": h.get("evidence_refs", []),
                "elo_rating": h.get("elo_rating"),
                "redacted_drug_names": all_redacted,  # audit trail
            }
        )

    # v2.0.2: sort by actionability — patient-facing brief should show
    # actionable-first, research-only-last (round-2 review consensus).
    _TIER_ORDER = {
        "actionable_this_week": 0,
        "weeks": 1,
        "months_or_more": 2,
        "research_only": 3,
    }
    out.sort(key=lambda c: _TIER_ORDER.get(c["actionability_tier"], 9))

    # Conservative cap — patient brief should not surface > 5 candidates
    # without context. Anything beyond is deferred to a separate "extended"
    # research-direction appendix.
    return out[:5]


def passes_testability_keyword_floor(tpath: str) -> bool:
    """Soft sanity check — testability path mentions a recognised assay/dataset.

    Per medical reviewer finding #3: pure "non-empty string" is a fig leaf;
    the path should reference at least one of the recognised testability
    primitives. Returns True if any keyword present, False otherwise.
    Caller may use this to gate display.
    """
    if not tpath:
        return False
    lower = tpath.lower()
    keywords = (
        "depmap",
        "tcga",
        "geo:",
        "gse",
        "pdx",
        "crispr",
        "bli",  # bio-layer interferometry
        "spr",  # surface plasmon resonance
        "ctdna",
        "scrna",
        "scrna-seq",
        "bulk rna",
        "esmfold",
        "alphafold",
        "diffdock",
        "vina",
        "phenotypic",
        "organoid",
        "co-essentiality",
        "co-knockout",
        "rna-seq",
        "pdo",
        "patient-derived",
    )
    return any(k in lower for k in keywords)
