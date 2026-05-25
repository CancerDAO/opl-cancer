"""G15: multiple-testing correction required in bioinformatics notebooks.
Spec §7 G15 / §6.5 F2.

Failure mode F2 — naive p-value reporting without family-wise / FDR
correction. Any bioinformatics notebook (.ipynb) attached to a claim must
contain at least one cell whose source mentions Benjamini-Hochberg,
Bonferroni, or FDR/`adj.pval`/`padj`/`q.value` style correction.

The check uses simple regex scanning over the notebook JSON; no kernel
execution is required, satisfying the "no-LLM, no-runtime" mechanical-gate
contract (spec §7).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

_CORRECTION_RE = re.compile(
    r"\b("
    r"benjamini[\s-]?hochberg|bonferroni|holm[\s-]?bonferroni|"
    r"BH(?![A-Za-z])|FDR|q[\s_.-]?value|adj[\s_.-]?p[\s_.-]?val|"
    r"padj|p_adj|fdr_bh|multipletests|p\.adjust"
    r")\b",
    re.IGNORECASE,
)


def _scan_notebook_text(path: Path) -> list[str]:
    """Return the list of correction tokens found in any code cell."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    hits: list[str] = []
    for cell in data.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        src = cell.get("source", "")
        if isinstance(src, list):
            src = "".join(src)
        for m in _CORRECTION_RE.finditer(src):
            hits.append(m.group(1))
    return hits


class G15MultipleTestingCorrectionGate(Gate):
    name = "G15_multiple_testing_correction"
    description = "Bioinformatics notebooks must apply BH/Bonferroni/FDR correction."
    failure_mode_code = "F2"

    def check(self, claim: dict[str, Any]) -> GateResult:
        notebooks = claim.get("notebooks") or []
        if not notebooks:
            return GateResult(
                gate=self.name, status=GateStatus.SKIP, message="no notebooks attached"
            )
        missing: list[str] = []
        evidence: dict[str, list[str]] = {}
        for nb in notebooks:
            nb_path = Path(nb) if isinstance(nb, str) else Path(nb.get("path", ""))
            if not nb_path.is_file():
                missing.append(f"{nb_path} (not found)")
                continue
            hits = _scan_notebook_text(nb_path)
            evidence[str(nb_path)] = hits
            if not hits:
                missing.append(str(nb_path))
        if missing:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"{len(missing)} notebook(s) missing multiple-testing correction "
                    f"(BH/Bonferroni/FDR): {missing}"
                ),
                evidence={"missing_notebooks": missing, "hits_per_notebook": evidence},
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=f"all {len(notebooks)} notebook(s) apply correction",
            evidence={"hits_per_notebook": evidence},
        )
