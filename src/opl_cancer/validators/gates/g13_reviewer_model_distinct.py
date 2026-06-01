"""G13: the two host-agent subagent reports must DECLARE distinct model identities.

Spec §7 G13 / §6.5 E6. Failure mode E6 — *same-model echo chamber*: when the
Reviewer subagent runs on the SAME underlying LLM as the Executor subagent,
disagreements collapse and the audit loop degenerates into self-confirmation.

Harness-split redefinition (docs/iteration/HARNESS_SPLIT_PRD.md)
----------------------------------------------------------------
Path B is gone. Reasoning is now produced by **two independent host-agent
subagent dispatches**: an *executor* subagent that writes the expert report,
and a *reviewer* subagent that audits it. There is no in-process Python LLM
call whose ``model_id`` we can compare. Instead, each subagent report carries
its own model declaration in its artifact metadata, and G13 verifies that the
two declared model identities differ.

What this gate reads
--------------------
``check(claim)`` accepts the two report artifacts (or their already-extracted
metadata) and resolves a *declared model id* from each:

  * **Executor report** — the model declaration lives in the report ``_meta``
    block (``_meta.model`` / ``_meta.model_id`` / ``_meta.produced_by_model``),
    or top-level ``executor_model`` / ``model_id``. The legacy
    ``claim.executor.model_id`` shape is still accepted.
  * **Reviewer report** — the model declaration lives at top-level
    ``reviewer_model`` (see ``prompts/tasks/source_verification.md`` and
    ``claim_audit.md``), or in its ``_meta`` block, or the legacy
    ``claim.reviewer.model_id`` shape.

Decision (deterministic Python — RED LINE, never delegated to a prompt):

  * **either declaration ABSENT** → ``FAIL block=True``. A report that does not
    declare which model produced it makes the echo-chamber check unverifiable;
    an unverifiable distinctness claim is treated as a violation, NOT a pass.
  * **executor model == reviewer model** → ``FAIL block=True`` (E6 echo chamber).
  * **reviewer model not in ``reviewer_pool``** (when the pool is configured) →
    ``FAIL block=True``.
  * **otherwise** → ``PASS``.

models.yaml note
----------------
``models.yaml`` ``reviewer_pairings`` / ``executor_model`` / ``reviewer_pool``
now describe the *expected distinctness* of the executor↔reviewer pairing — a
declarative roster of which model families should appear on each side — rather
than Python model-routing config (the patient-delivery path no longer reads
models.yaml to call an LLM; the host agent is the executor). G13 still consults
``executor_model.id`` (as a fallback executor declaration) and ``reviewer_pool``
(to confirm the declared reviewer model is an allowed reviewer), but a missing
declaration on the report artifact is never papered over by these defaults.
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


# Model-declaration field names we accept on a report artifact, in priority
# order. The same field set is scanned at the report top level and inside its
# ``_meta`` block. Sentinel/placeholder values (empty, "unknown", a bare
# "host-agent" with no model suffix) do NOT count as a declaration.
_MODEL_FIELDS: tuple[str, ...] = (
    "model_id",
    "model",
    "reviewer_model",
    "executor_model",
    "produced_by_model",
)

_PLACEHOLDER_DECLS: frozenset[str] = frozenset(
    {"", "unknown", "n/a", "na", "none", "null", "host-agent", "host-agent-reviewer"}
)


def _coerce_id(value: Any) -> str | None:
    """Normalise a declared model value; reject placeholders/sentinels."""
    if not isinstance(value, str):
        return None
    v = value.strip()
    if not v or v.lower() in _PLACEHOLDER_DECLS:
        return None
    return v


def _extract_declared_model(report: Any) -> str | None:
    """Pull a declared model id from a report artifact dict.

    Scans top-level fields, then the nested ``_meta`` block. Returns None when
    no usable (non-placeholder) declaration is present.
    """
    if not isinstance(report, dict):
        return None
    for field in _MODEL_FIELDS:
        got = _coerce_id(report.get(field))
        if got:
            return got
    meta = report.get("_meta")
    if isinstance(meta, dict):
        for field in _MODEL_FIELDS:
            got = _coerce_id(meta.get(field))
            if got:
                return got
    return None


class G13ReviewerModelDistinctGate(Gate):
    name = "G13_reviewer_model_distinct"
    description = (
        "Executor & reviewer subagent reports must DECLARE distinct model "
        "identities (no echo-chamber); a missing declaration BLOCKs."
    )
    failure_mode_code = "E6"

    def __init__(self, models_yaml_path: Path | None = None) -> None:
        cfg = _load_models_yaml(models_yaml_path)
        # Fallback executor declaration ONLY (used when the executor report
        # itself carries no model field is NOT allowed — see check()).
        self.executor_model_id = _coerce_id((cfg.get("executor_model") or {}).get("id"))
        self.reviewer_pool_ids: set[str] = {
            rid
            for r in (cfg.get("reviewer_pool") or [])
            if (rid := _coerce_id(r.get("id")))
        }

    def _resolve_executor(self, claim: dict[str, Any]) -> str | None:
        # 1) explicit executor report artifact
        for key in ("executor_report", "executor_output"):
            got = _extract_declared_model(claim.get(key))
            if got:
                return got
        # 2) legacy nested shape: claim.executor.model_id
        executor = claim.get("executor")
        if isinstance(executor, dict):
            got = _coerce_id(executor.get("model_id")) or _extract_declared_model(executor)
            if got:
                return got
        return None

    def _resolve_reviewer(self, claim: dict[str, Any]) -> str | None:
        # 1) explicit reviewer report artifact (carries top-level reviewer_model)
        for key in ("reviewer_report", "review", "reviewer_output"):
            got = _extract_declared_model(claim.get(key))
            if got:
                return got
        # 2) legacy nested shape: claim.reviewer.model_id
        reviewer = claim.get("reviewer")
        if isinstance(reviewer, dict):
            got = _coerce_id(reviewer.get("model_id")) or _extract_declared_model(reviewer)
            if got:
                return got
        # 3) top-level reviewer_model (a bare claim that is itself a reviewer report)
        return _coerce_id(claim.get("reviewer_model"))

    def check(self, claim: dict[str, Any]) -> GateResult:
        executor = self._resolve_executor(claim)
        reviewer = self._resolve_reviewer(claim)

        # Absent declaration => BLOCK (an unverifiable distinctness claim is a
        # violation, not a pass). models.yaml's executor_model is a last-resort
        # fallback for the executor side only; the reviewer side has no fallback
        # because its model is what we are trying to verify.
        if not executor:
            executor = self.executor_model_id
        if not executor:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    "executor report carries no model declaration "
                    "(checked _meta.model/model_id/executor_model and "
                    "models.yaml executor_model.id) — cannot verify G13/E6 "
                    "distinctness; blocking"
                ),
                evidence={"executor": executor, "reviewer": reviewer},
            )
        if not reviewer:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    "reviewer report carries no model declaration "
                    "(checked reviewer_model and _meta.model/model_id) — "
                    "cannot verify G13/E6 distinctness; blocking"
                ),
                evidence={"executor": executor, "reviewer": reviewer},
            )

        if executor == reviewer:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"reviewer model == executor model == {executor!r} — "
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
                    f"reviewer model={reviewer!r} not in reviewer_pool "
                    f"{sorted(self.reviewer_pool_ids)}"
                ),
                evidence={"executor": executor, "reviewer": reviewer},
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=f"executor={executor} != reviewer={reviewer}",
            evidence={"executor": executor, "reviewer": reviewer},
        )
