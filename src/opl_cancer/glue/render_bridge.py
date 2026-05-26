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


def _redact_drug_specifics(text: str) -> tuple[str, list[str]]:
    """Replace specific drug names with target-class equivalents.

    Returns (redacted_text, list_of_redacted_drugs_for_audit).
    """
    if not isinstance(text, str):
        return text, []
    redacted_list: list[str] = []
    out = text
    for drug, cls in _DRUG_TO_CLASS_REDACTION.items():
        import re as _re

        pattern = _re.compile(rf"\b{_re.escape(drug)}\b", _re.IGNORECASE)
        if pattern.search(out):
            redacted_list.append(drug)
            out = pattern.sub(cls, out)
    return out, redacted_list


# v2.0.2 (round-2 review): keywords that classify a testability_path by
# clinical actionability tier. Patient + family reviewers explicitly asked
# for priority ranking.
_TIER_KEYWORDS: dict[str, tuple[str, ...]] = {
    "actionable_this_week": (
        "已上市",
        "标准实验室",
        "ngs panel",
        "wes",
        "血清",
        "25-ohd",
        "kit-based ihc",
        "ctdna",
        "guardant",
        "燃石",
        "世和",
        "泛生子",
    ),
    "weeks": (
        "patient-derived organoid",
        "pdo",
        "ihc 多标",
        "回顾性",
        "retrospective",
        "扩展准入",
        "expanded access",
    ),
    "months_or_more": (
        "pdx",
        "crispr",
        "synthesis",
        "ind-enabling",
        "diffdock",
        "esmfold",
        "preclinical",
        "type 1 trial",
    ),
    "research_only": (
        "depmap",
        "kg edge",
        "in silico",
        "tcga",
        "geo:",
        "gse",
        "computational",
    ),
}


def classify_actionability_tier(testability_path: str) -> str:
    """Return the most-actionable tier whose keywords appear in the path."""
    if not testability_path:
        return "research_only"
    lower = testability_path.lower()
    for tier in ("actionable_this_week", "weeks", "months_or_more", "research_only"):
        for kw in _TIER_KEYWORDS[tier]:
            if kw in lower:
                return tier
    return "research_only"


_ACTIONABILITY_LABEL_ZH: dict[str, str] = {
    "actionable_this_week": "✅ 本周内可执行 (Actionable this week)",
    "weeks": "🟡 数周可执行 (Weeks)",
    "months_or_more": "🟠 数月以上 / 需科研合作 (Months+)",
    "research_only": "⚪ 纯研究方向 / 暂无患者级路径 (Research-only)",
}


def actionability_label_zh(tier: str) -> str:
    return _ACTIONABILITY_LABEL_ZH.get(tier, _ACTIONABILITY_LABEL_ZH["research_only"])


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

        # Actionability tier — derived from testability_path keywords
        tier = classify_actionability_tier(tpath_redacted)

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
