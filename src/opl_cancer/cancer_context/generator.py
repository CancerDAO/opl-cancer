"""CancerContextGenerator — v2.5 compositional foundation (RFC 0001 §2.3).

If a seed JSON exists at ``references/cancer_contexts/<icdo3>.json`` return it
(deep-loaded). Otherwise return a scaffold stub with ``_status:
"scaffold_pending_M6"`` and an explanation.

M6 will replace the scaffold path with a live PrimeKG + OncoKB + NCCN +
ClinicalTrials.gov pipeline.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DEFAULT_SEED_DIR = _REPO_ROOT / "references" / "cancer_contexts"


SCHEMA_KEYS = (
    "icdo3",
    "snomed",
    "display_name",
    "soc_chain",
    "frequent_actionables",
    "typical_comorbidities",
    "imaging",
    "active_trials_summary",
)


class CancerContextGenerator:
    """Resolve a cancer code → cancer_context.json.

    v2.5 lookup chain:
    1. ``cache_dir / <icdo3>.json`` (the user-supplied output path's directory)
    2. ``references/cancer_contexts/<icdo3>.json`` (the in-tree seed)
    3. Scaffold stub (status: scaffold_pending_M6)

    Live KG queries are M6.
    """

    def __init__(
        self,
        icdo3: str,
        *,
        cache_dir: Path | None = None,
        force_refresh: bool = False,
    ) -> None:
        self.icdo3 = icdo3
        self.cache_dir = cache_dir
        self.force_refresh = force_refresh

    # ─── public API ───────────────────────────────────────────────────────

    def generate(self) -> dict[str, Any]:
        # If force_refresh: skip the cache + seed lookup, go straight to scaffold
        # (also re-writes any existing user cache file).
        if not self.force_refresh:
            for candidate in self._lookup_paths():
                if candidate.is_file():
                    raw = json.loads(candidate.read_text(encoding="utf-8"))
                    if isinstance(raw, dict) and raw.get("icdo3") == self.icdo3:
                        return raw

        return self._scaffold_stub()

    # ─── internals ────────────────────────────────────────────────────────

    def _lookup_paths(self) -> list[Path]:
        out: list[Path] = []
        if self.cache_dir:
            out.append(self.cache_dir / f"{self.icdo3}.json")
        out.append(_DEFAULT_SEED_DIR / f"{self.icdo3}.json")
        return out

    def _scaffold_stub(self) -> dict[str, Any]:
        return {
            "icdo3": self.icdo3,
            "snomed": "",
            "display_name": "",
            "soc_chain": [],
            "frequent_actionables": [],
            "typical_comorbidities": [],
            "imaging": [],
            "active_trials_summary": [],
            "_status": "scaffold_pending_M6",
            "_explanation": (
                f"No seed cancer_context for {self.icdo3!r}. v2.5 returns a "
                "scaffold stub; M6 will hook up live PrimeKG + OncoKB + NCCN "
                "PageIndex + cBioPortal + ClinicalTrials.gov queries to "
                "auto-build a cancer_context.json on demand. Until then, "
                "downstream agents should fall back to the cancer-agnostic "
                "(default) planner row."
            ),
            "_provenance": {
                "source": "v2.5 scaffold",
                "M6_plan": "Live KG-derived context",
            },
        }


__all__ = ["CancerContextGenerator", "SCHEMA_KEYS"]
