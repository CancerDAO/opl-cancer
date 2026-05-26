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
        # Carry a minimal subset to the template; renderer Jinja handles missing.
        out.append(
            {
                "id": h.get("id", ""),
                "text": h.get("text", ""),
                "generation_strategy": strategy,
                "claim_layer": "speculative",
                "testability_path": tpath,
                "evidence_refs": h.get("evidence_refs", []),
                "elo_rating": h.get("elo_rating"),
            }
        )

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
