"""G18: meta-analysis must declare PRISMA search strategy + plots. Spec §7 G18 / §6.5 F5.

Failure mode F5 — undocumented systematic search. Any meta_analysis output
must carry:
  * `search_strategy.databases`     (e.g. ["PubMed", "Cochrane", "Embase"])
  * `search_strategy.query`         the actual query string(s)
  * `search_strategy.inclusion`     inclusion criteria
  * `search_strategy.exclusion`     exclusion criteria
  * `forest_plot_path`              (existing file)
  * `funnel_plot_path`              (existing file)
  * `prisma_flow_diagram_path`      (existing file)

G18 BLOCKs when any of these are missing or the referenced files do not exist.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

_REQUIRED_STRATEGY_FIELDS = ("databases", "query", "inclusion", "exclusion")
_REQUIRED_FILE_FIELDS = (
    "forest_plot_path",
    "funnel_plot_path",
    "prisma_flow_diagram_path",
)


class G18MetaSearchStrategyGate(Gate):
    name = "G18_meta_search_strategy"
    description = "Meta-analysis must declare search strategy + forest + funnel + PRISMA flow."
    failure_mode_code = "F5"

    def check(self, claim: dict[str, Any]) -> GateResult:
        meta = claim.get("meta_analysis") or {}
        if not meta:
            return GateResult(
                gate=self.name, status=GateStatus.SKIP, message="no meta_analysis on claim"
            )
        strategy = meta.get("search_strategy") or {}
        missing_fields: list[str] = [
            f for f in _REQUIRED_STRATEGY_FIELDS if not strategy.get(f)
        ]
        missing_files: list[str] = []
        for f in _REQUIRED_FILE_FIELDS:
            p = meta.get(f)
            if not p:
                missing_files.append(f)
                continue
            if not Path(str(p)).is_file():
                missing_files.append(f"{f} (file not found: {p})")
        if missing_fields or missing_files:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"meta_analysis missing {len(missing_fields)} strategy field(s) "
                    f"+ {len(missing_files)} required artefact(s)"
                ),
                evidence={
                    "missing_strategy_fields": missing_fields,
                    "missing_artefacts": missing_files,
                },
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=(
                "search strategy + inclusion/exclusion + PRISMA flow + forest + funnel "
                "all present"
            ),
        )
