"""Release-time golden-set regression evaluation.

This module intentionally stays LLM-free and network-free. It gives release
automation one stable JSON surface over the existing golden-set fixtures instead
of scattering release readiness across prose and individual tests.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA = "opl.release_golden_eval.v1"
_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GOLDEN_ROOT = _REPO_ROOT / "validators" / "golden_set"


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _check(
    checks: list[dict[str, Any]],
    *,
    category: str,
    name: str,
    ok: bool,
    message: str,
    evidence: dict[str, Any] | None = None,
    severity: str = "error",
) -> None:
    checks.append(
        {
            "category": category,
            "name": name,
            "ok": bool(ok),
            "severity": severity,
            "message": message,
            "evidence": evidence or {},
        }
    )


def _synthetic_patient_checks(root: Path, checks: list[dict[str, Any]]) -> dict[str, Any]:
    category = "synthetic_patients"
    patient_root = root / category
    dirs = sorted(d for d in patient_root.iterdir() if d.is_dir()) if patient_root.is_dir() else []
    sites: set[str] = set()

    _check(
        checks,
        category=category,
        name="minimum_patient_count",
        ok=len(dirs) >= 4,
        message="synthetic patient set must cover at least four cases",
        evidence={"count": len(dirs)},
    )

    for d in dirs:
        profile_path = d / "profile.json"
        try:
            profile = _read_json(profile_path)
        except Exception as exc:  # noqa: BLE001
            _check(
                checks,
                category=category,
                name=f"{d.name}:profile_parse",
                ok=False,
                message=f"profile.json is not parseable: {exc}",
            )
            continue

        site = str(profile.get("diagnosis", {}).get("primary_site", ""))
        if site:
            sites.add(site)
        treatment_history = profile.get("treatment_history")
        demographics = profile.get("demographics")

        _check(
            checks,
            category=category,
            name=f"{d.name}:patient_code",
            ok=profile.get("patient_code") == d.name and d.name.startswith("anon_"),
            message="profile patient_code must match directory and use anon_ prefix",
            evidence={"patient_code": profile.get("patient_code")},
        )
        _check(
            checks,
            category=category,
            name=f"{d.name}:required_sections",
            ok=isinstance(demographics, dict)
            and isinstance(profile.get("diagnosis"), dict)
            and isinstance(treatment_history, list)
            and len(treatment_history) >= 1,
            message="profile must include demographics, diagnosis, and non-empty treatment history",
            evidence={
                "has_demographics": isinstance(demographics, dict),
                "has_diagnosis": isinstance(profile.get("diagnosis"), dict),
                "treatment_lines": len(treatment_history) if isinstance(treatment_history, list) else 0,
            },
        )
        case_text = d / "case_text.md"
        if case_text.is_file():
            text = case_text.read_text(encoding="utf-8")
            _check(
                checks,
                category=category,
                name=f"{d.name}:synthetic_marker",
                ok="SYNTHETIC" in text,
                message="case_text.md must declare that the case is synthetic",
            )

    _check(
        checks,
        category=category,
        name="minimum_distinct_primary_sites",
        ok=len(sites) >= 4,
        message="synthetic patient set must span at least four primary sites",
        evidence={"sites": sorted(sites), "count": len(sites)},
    )
    return {"count": len(dirs), "distinct_primary_sites": len(sites)}


def _failure_mode_checks(root: Path, checks: list[dict[str, Any]]) -> dict[str, Any]:
    category = "failure_mode_inputs"
    files = sorted((root / category).glob("*.json"))
    gates: set[str] = set()

    _check(
        checks,
        category=category,
        name="minimum_failure_mode_count",
        ok=len(files) >= 8,
        message="golden set must include at least eight failure-mode inputs",
        evidence={"count": len(files)},
    )

    for path in files:
        try:
            data = _read_json(path)
        except Exception as exc:  # noqa: BLE001
            _check(
                checks,
                category=category,
                name=f"{path.stem}:parse",
                ok=False,
                message=f"fixture is not parseable: {exc}",
            )
            continue
        gate = str(data.get("expected_block_gate", ""))
        if gate:
            gates.add(gate)
        _check(
            checks,
            category=category,
            name=f"{path.stem}:shape",
            ok=bool(data.get("test_name")) and bool(gate) and isinstance(data.get("claim"), dict),
            message="failure fixture must declare test_name, expected_block_gate, and claim object",
            evidence={"expected_block_gate": gate},
        )
        _check(
            checks,
            category=category,
            name=f"{path.stem}:gate_code_shape",
            ok=gate.startswith(("G", "C")),
            message="expected_block_gate must be a mechanical gate code",
            evidence={"expected_block_gate": gate},
        )

    _check(
        checks,
        category=category,
        name="minimum_distinct_gates",
        ok=len(gates) >= 5,
        message="failure modes must exercise at least five distinct gates",
        evidence={"gates": sorted(gates), "count": len(gates)},
    )
    return {"count": len(files), "distinct_gates": len(gates)}


def _regression_anchor_checks(root: Path, checks: list[dict[str, Any]]) -> dict[str, Any]:
    category = "regression_anchors"
    files = sorted((root / category).glob("*.json"))

    _check(
        checks,
        category=category,
        name="minimum_anchor_count",
        ok=len(files) >= 2,
        message="golden set must include at least two regression anchors",
        evidence={"count": len(files)},
    )
    for path in files:
        try:
            data = _read_json(path)
        except Exception as exc:  # noqa: BLE001
            _check(
                checks,
                category=category,
                name=f"{path.stem}:parse",
                ok=False,
                message=f"anchor is not parseable: {exc}",
            )
            continue
        _check(
            checks,
            category=category,
            name=f"{path.stem}:shape",
            ok=bool(data.get("anchor_name"))
            and bool(data.get("source"))
            and bool(data.get("acceptance_criterion")),
            message="regression anchor must include anchor_name, source, and acceptance_criterion",
        )
    return {"count": len(files)}


def _boundary_case_checks(root: Path, checks: list[dict[str, Any]]) -> dict[str, Any]:
    category = "boundary_cases"
    files = sorted((root / category).glob("*.json"))

    _check(
        checks,
        category=category,
        name="minimum_boundary_case_count",
        ok=len(files) >= 3,
        message="golden set must include at least three boundary cases",
        evidence={"count": len(files)},
    )
    for path in files:
        try:
            data = _read_json(path)
        except Exception as exc:  # noqa: BLE001
            _check(
                checks,
                category=category,
                name=f"{path.stem}:parse",
                ok=False,
                message=f"boundary case is not parseable: {exc}",
            )
            continue
        expected_behavior = data.get("expected_behavior")
        _check(
            checks,
            category=category,
            name=f"{path.stem}:shape",
            ok=bool(data.get("case_name"))
            and isinstance(data.get("patient_input"), dict)
            and isinstance(expected_behavior, list)
            and len(expected_behavior) >= 1,
            message="boundary case must include case_name, patient_input, and expected_behavior list",
        )
    return {"count": len(files)}


def run_release_golden_eval(golden_root: str | Path | None = None) -> dict[str, Any]:
    """Run deterministic golden-set release checks and return a JSON-ready report."""
    root = Path(golden_root) if golden_root is not None else DEFAULT_GOLDEN_ROOT
    checks: list[dict[str, Any]] = []

    _check(
        checks,
        category="root",
        name="golden_root_exists",
        ok=root.is_dir(),
        message="validators/golden_set must exist",
        evidence={"path": str(root)},
    )
    if not root.is_dir():
        return _report(root, checks, {})

    summary = {
        "synthetic_patients": _synthetic_patient_checks(root, checks),
        "failure_mode_inputs": _failure_mode_checks(root, checks),
        "regression_anchors": _regression_anchor_checks(root, checks),
        "boundary_cases": _boundary_case_checks(root, checks),
    }
    return _report(root, checks, summary)


def _report(root: Path, checks: list[dict[str, Any]], summary: dict[str, Any]) -> dict[str, Any]:
    failed = [c for c in checks if not c["ok"]]
    errors = [c for c in failed if c["severity"] == "error"]
    warnings = [c for c in failed if c["severity"] == "warn"]
    return {
        "schema": SCHEMA,
        "ok": not errors,
        "golden_root": str(root),
        "summary": {
            **summary,
            "checks": len(checks),
            "errors": len(errors),
            "warnings": len(warnings),
        },
        "checks": checks,
    }


def write_release_golden_eval(report: dict[str, Any], out: str | Path) -> Path:
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path

