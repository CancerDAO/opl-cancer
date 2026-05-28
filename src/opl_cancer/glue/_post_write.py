"""v2.5.1 B3 — shared post-write safety helpers for wave runners.

Originally lived inside ``wave1_runner.py``; v2.5.1 extracts the two
helpers so wave2/3/4/6 can wire the same fakery_sniffer + reviewer_hook
discipline without duplicating the code.

Two helpers:

* ``post_write_safety_check(report_path, run_root)`` — run the fakery
  sniffer; on any hit emit ``<run_root>/SNIFFER_HALT.md`` + a row to
  ``<run_root>/pushback_trigger_log.jsonl`` and raise ``SnifferHalt``.
* ``run_reviewer_pairing_for(report_path, primary_expert, primary_model)``
  — thin re-export of the existing ``orchestrator.reviewer_hook``.

Use pattern in every wave runner immediately after a per-task/per-claim
file write:

    report_path.write_text(...)
    post_write_safety_check(report_path, run_root=run_dir)
    run_reviewer_pairing(
        report_path=report_path,
        primary_expert=expert_name,
        primary_model=reviewer_model_id,
    )

Tests live in ``tests/test_glue/test_sniffer_halt_wave{2,3,4,6}.py``
mimicking the existing ``test_sniffer_halt.py`` shape.
"""
from __future__ import annotations

from pathlib import Path

from opl_cancer.validators.fakery_sniffer import scan_artifact


class SnifferHalt(RuntimeError):
    """v2.1 P1-#9 / v2.5.1 B3: raised when the fakery sniffer flags a
    freshly written artifact in any wave. Downstream waves freeze until
    the artifact is fixed (per the v2.1 ADR-0021 invariant)."""


def post_write_safety_check(report_path: Path, run_root: Path) -> None:
    """Run the fakery sniffer on a freshly written artifact.

    On any hit:

    1. Emit ``<run_root>/SNIFFER_HALT.md`` listing each finding.
    2. Append a row to ``<run_root>/pushback_trigger_log.jsonl`` so the
       SKILL main thread sees the trigger (P2-#19).
    3. Raise ``SnifferHalt`` so the wave runner can short-circuit.

    Clean artifacts return silently — caller proceeds.
    """
    findings = scan_artifact(report_path)
    if not findings:
        return
    # SNIFFER_HALT.md is the human-readable freeze surface.
    halt_path = run_root / "SNIFFER_HALT.md"
    lines = [f"# SNIFFER HALT — {report_path.name}", "", "## Findings"]
    for f in findings:
        lines.append(f"- L{f.line_number}: `{f.pattern}` → `{f.excerpt}`")
    lines.append(
        "\nDownstream waves frozen. Invoke "
        "`prompts/tasks/patient_pushback_handling.md`."
    )
    halt_path.write_text("\n".join(lines), encoding="utf-8")
    # Pushback router auto-trigger (P2-#19).
    try:
        from opl_cancer.orchestrator.pushback_router import log_trigger
        log_trigger(
            run_root / "pushback_trigger_log.jsonl",
            reason="fakery_sniffer",
            excerpt=findings[0].excerpt,
            source=str(report_path),
        )
    except Exception:  # pragma: no cover — pushback router optional dep
        pass
    raise SnifferHalt(
        f"fakery detected in {report_path.name}: {len(findings)} finding(s)"
    )


__all__ = ["SnifferHalt", "post_write_safety_check"]
