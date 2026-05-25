"""G13: reviewer model must be distinct from executor model. Spec §7 G13 / §6.5 E6.

Failure mode E6 — same-model echo chamber: when Reviewer runs on the SAME
underlying LLM as Executor, disagreements collapse and the audit loop
degenerates into self-confirmation. G13 BLOCKs whenever
``claim.executor.model_id == claim.reviewer.model_id``.

The allowed (executor → reviewer) pairings are loaded from models.yaml
(``reviewer_pairings`` + ``executor_model`` + ``reviewer_pool``); if a
claim's reviewer is not in the pool at all, gate still BLOCKs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ..mechanical_gates import Gate, GateResult, GateStatus


def _load_models_yaml(path: Path | None) -> dict[str, Any]:
    if path is None:
        # Walk up from this file looking for models.yaml at repo root
        here = Path(__file__).resolve()
        for parent in here.parents:
            cand = parent / "models.yaml"
            if cand.is_file():
                path = cand
                break
    if path is None or not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


class G13ReviewerModelDistinctGate(Gate):
    name = "G13_reviewer_model_distinct"
    description = "Reviewer model_id must differ from Executor model_id (no echo-chamber)."
    failure_mode_code = "E6"

    def __init__(self, models_yaml_path: Path | None = None) -> None:
        cfg = _load_models_yaml(models_yaml_path)
        self.executor_model_id = (cfg.get("executor_model") or {}).get("id")
        self.reviewer_pool_ids: set[str] = {
            r.get("id") for r in (cfg.get("reviewer_pool") or []) if r.get("id")
        }

    def check(self, claim: dict[str, Any]) -> GateResult:
        executor = (claim.get("executor") or {}).get("model_id") or self.executor_model_id
        reviewer = (claim.get("reviewer") or {}).get("model_id")
        if not executor or not reviewer:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message=f"missing model ids (executor={executor!r}, reviewer={reviewer!r})",
            )
        if executor == reviewer:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"reviewer.model_id == executor.model_id == {executor!r} — "
                    "echo-chamber risk (G13 / E6)"
                ),
                evidence={"executor": executor, "reviewer": reviewer},
            )
        if self.reviewer_pool_ids and reviewer not in self.reviewer_pool_ids:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"reviewer.model_id={reviewer!r} not in reviewer_pool "
                    f"{sorted(self.reviewer_pool_ids)}"
                ),
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=f"executor={executor} != reviewer={reviewer}",
        )
