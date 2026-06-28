"""v2.3 P2-#17 — prior-run ingestion at plan stage.

When the planner detects a prior MTB / OPL run under
``patients/<id>/runs/<prior>/``, it ingests the prior
``chair_final_report.md`` summary so that the new plan can:

1. Skip duplicate investigations already settled in the prior run.
2. Tag the new plan with ``extends_prior_run: <prior_run_id>`` so
   Wave 6 manuscript framing can declare "this report extends prior
   MTB run X" (matches the n1a manifest field).

The ingestion is intentionally read-only — we never modify the prior
run's files.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


__all__ = ["PriorRunSummary", "ingest_prior_runs", "latest_prior_run_id"]


@dataclass(frozen=True)
class PriorRunSummary:
    run_id: str
    chair_report_path: Path
    chair_report_text: str
    headings: list[str]
    cited_pmids: list[str]


_HEADING_RE = re.compile(r"^#{1,4}\s+(.+?)\s*$", re.MULTILINE)
_PMID_RE = re.compile(r"\[PMID\s*:\s*(\d{4,9})\]")


def _summarise(report_path: Path) -> PriorRunSummary:
    text = report_path.read_text(encoding="utf-8")
    headings = _HEADING_RE.findall(text)
    pmids = sorted(set(_PMID_RE.findall(text)))
    return PriorRunSummary(
        run_id=report_path.parent.name,
        chair_report_path=report_path,
        chair_report_text=text,
        headings=headings,
        cited_pmids=pmids,
    )


def ingest_prior_runs(
    patient_dir: Path, current_run_id: str | None = None
) -> list[PriorRunSummary]:
    """Return summaries of every prior run that emitted a
    ``chair_final_report.md`` under ``patients/<id>/runs/<run>/``.

    Excludes the current run if its id is passed."""
    patient_dir = Path(patient_dir)
    runs_root = patient_dir / "runs"
    if not runs_root.is_dir():
        return []
    out: list[PriorRunSummary] = []
    for d in sorted(runs_root.iterdir()):
        if not d.is_dir():
            continue
        if current_run_id and d.name == current_run_id:
            continue
        report = d / "chair_final_report.md"
        if report.is_file():
            try:
                out.append(_summarise(report))
            except OSError:
                # Skip unreadable prior reports — fail open, not fail loud,
                # because prior-run ingestion is informational.
                continue
    return out


def latest_prior_run_id(
    patient_dir: Path, current_run_id: str | None = None
) -> str | None:
    """Return the lex-latest prior run_id (excluding current)."""
    summaries = ingest_prior_runs(patient_dir, current_run_id=current_run_id)
    if not summaries:
        return None
    return summaries[-1].run_id


def patient_value_hierarchy_weights(profile: dict[str, Any]) -> list[str]:
    """v2.3 P2-#21 — extract the patient-value hierarchy ordering from
    ``profile.json``.

    Convention: the profile may carry ``patient_value_hierarchy`` (or
    legacy ``value_hierarchy``) — an ordered list of strings such as
    ``["survival_extension", "quality_of_life", "minimise_iv", ...]``.

    NOT YET WIRED INTO RANKING (honesty fix, A1/ADR-0027). The original
    docstring claimed "the Wave 2 / Wave 3 ranking code pre-pends these
    weights" — but the function had zero callers, the canonical
    looks-like-vs-is-like orphan the audit flagged. The actual wiring of
    patient value into candidate ranking lands with the outcome-backward
    planner (D1/E1, ADR-0034); until then this is a pure extractor and the
    no-orphan CI guard (tests/test_no_orphans.py) tracks it.

    Returns an empty list if neither field is present.
    """
    raw = profile.get("patient_value_hierarchy") or profile.get("value_hierarchy")
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw if isinstance(x, (str, int, float))]
