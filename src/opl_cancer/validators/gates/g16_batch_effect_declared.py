"""G16: batch effect must be declared in bioinformatics tasks. Spec §7 G16 / §6.5 F3.

Failure mode F3 — undeclared batch effect. Bioinformatics analyses across
multi-cohort / multi-platform data must explicitly enumerate the batch
variable (e.g. "TCGA project", "sequencing center", "library prep batch")
both in the task prompt AND in the notebook (as a model covariate or
explicit ``ComBat`` / ``removeBatchEffect`` / ``sva`` call).

G16 BLOCKs when both the task spec and the notebook are silent on batch.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

_BATCH_DECL_RE = re.compile(
    r"\b("
    r"batch[\s_-]?(effect|variable|covariate)|"
    r"ComBat|removeBatchEffect|"
    r"sva\b|surrogate[\s_-]?variable|"
    r"~\s*batch|covariates?\s*=\s*\[?[\"']?batch|"
    r"批次效应|批次变量"
    r")\b",
    re.IGNORECASE,
)


def _scan_text_for_batch(text: str) -> list[str]:
    return [m.group(1) for m in _BATCH_DECL_RE.finditer(text)]


def _scan_notebook(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    hits: list[str] = []
    for cell in data.get("cells", []):
        src = cell.get("source", "")
        if isinstance(src, list):
            src = "".join(src)
        hits.extend(_scan_text_for_batch(src))
    return hits


class G16BatchEffectDeclaredGate(Gate):
    name = "G16_batch_effect_declared"
    description = "Bioinformatics tasks must declare batch variable in prompt + notebook."
    failure_mode_code = "F3"

    def check(self, claim: dict[str, Any]) -> GateResult:
        task_type = (claim.get("task_type") or claim.get("task_package") or "").lower()
        if "bioinformatic" not in task_type and "omics" not in task_type:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message=f"task_type={task_type!r} — G16 not applicable",
            )
        prompt = claim.get("task_prompt") or claim.get("prompt") or ""
        prompt_hits = _scan_text_for_batch(str(prompt))
        notebooks = claim.get("notebooks") or []
        nb_hits: dict[str, list[str]] = {}
        for nb in notebooks:
            nb_path = Path(nb) if isinstance(nb, str) else Path(nb.get("path", ""))
            if nb_path.is_file():
                nb_hits[str(nb_path)] = _scan_notebook(nb_path)
        any_nb_hits = any(v for v in nb_hits.values())
        if not prompt_hits and not any_nb_hits:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message="bioinformatics task silent on batch effect in both prompt and notebook",
                evidence={"prompt_hits": prompt_hits, "notebook_hits": nb_hits},
            )
        if not prompt_hits:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=False,
                message="batch declared in notebook but NOT in task prompt — Reviewer flag",
                evidence={"prompt_hits": prompt_hits, "notebook_hits": nb_hits},
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message="batch effect declared in prompt + notebook",
            evidence={"prompt_hits": prompt_hits, "notebook_hits": nb_hits},
        )
