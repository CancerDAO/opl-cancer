"""Wave 6 — manuscript + `.n1a` bundle orchestrator (ADR-0023).

Sibling to Wave 5 (which produces `patient_plain_brief.md` +
`patient_pi_brief.md`). Wave 6 takes a completed Wave 5 delivery and
emits a publication-ready preprint draft + a self-contained `.n1a`
bundle.

CLI: ``opl wave6 --patient-dir ... --run-id ... [--draft|--final]``.
Refuses if Wave 5 has not shipped both briefs.

Transactional envelope copied from `delivery_runner.py` (v2.2 P1-#16):
every Wave 6 file written during the attempted commit is rolled back if
any later step fails. The patient never sees a half-shipped manuscript.

Wave 6 output structure under ``patients/<id>/triggers/<run_id>/``:

```
manuscript.md
manuscript.pdf                  # via any2pdf; markdown-only fallback OK
figures/                        # PNG + reproducer .py per fig
tables/                         # CSV + caption .md per table
references.bib
provenance.jsonl
reproducibility.md
ethics_declaration.md
ai_authorship_disclosure.md
world_unknown_appendix.md
manuscript_introduction.md (sub-section files for transparency)
manuscript_methods.md
manuscript_results.md
manuscript_discussion.md
manuscript_limitations.md
manuscript_abstract.md
HENRY_AUDIT.json (G29-G33 included)
<id>_<date>.n1a.zip
```

The runner itself owns the transactional shell + skeleton creation +
gate dispatch + bundle build. The actual prose generation is delegated
to LLM sub-skill prompts (the 8 task packages under prompts/tasks/).
This module does NOT call any LLM directly; it scaffolds the artifacts
and runs the mechanical gates / bundle build.

Per founder-mode philosophy: the runner can also operate in
``manuscript_provided`` mode where the caller has pre-written
manuscript.md and Wave 6 just validates + bundles. This is the
default for the v2.3 release-engineer pipeline because manuscript
authoring happens in the same session main thread.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from opl_cancer.delivery.n1a_bundle_writer import (
    BundleWriteError,
    N1ABundleWriter,
)
from opl_cancer.memory.cost_tracker import aggregate_cost_log
from opl_cancer.validators.gates import (
    G29ManuscriptAuthorshipDisclosedGate,
    G30ClaimPMIDAnchoredGate,
    G31FigureReproducibleGate,
    G32DataAvailabilityDeclaredGate,
    G33N1DesignTransparentGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


__all__ = [
    "Wave6Failure",
    "Wave6PrerequisiteError",
    "Wave6Runner",
    "run_wave6",
]


# Required Wave 5 outputs the runner expects to find before starting.
WAVE5_PREREQUISITES = ("patient_plain_brief.md", "patient_pi_brief.md")

# Files the runner expects to be present (or scaffolds with TODO stubs in
# draft mode) before running the gates + bundle.
WAVE6_ARTIFACTS = (
    "manuscript.md",
    "manuscript_introduction.md",
    "manuscript_methods.md",
    "manuscript_results.md",
    "manuscript_discussion.md",
    "manuscript_limitations.md",
    "manuscript_abstract.md",
    "references.bib",
    "provenance.jsonl",
    "reproducibility.md",
    "ethics_declaration.md",
    "ai_authorship_disclosure.md",
    "world_unknown_appendix.md",
    "HENRY_AUDIT.json",
)


class Wave6PrerequisiteError(RuntimeError):
    """Wave 5 has not shipped its required outputs (plain + pi brief)."""


class Wave6Failure(RuntimeError):
    """Wave 6 transactional commit failed; bundle rolled back."""


class Wave6Runner:
    """Wave 6 transactional orchestrator.

    Modes:
      * ``mode="final"`` — full gate enforcement; G29-G33 must pass.
      * ``mode="draft"`` — relaxed enforcement; G29-G33 produce warnings
        but do not block. Bundle is still emitted with a draft marker.
      * ``mode="dry_run"`` — return planned actions without touching disk.

    Patient_code is the human-readable identifier used to derive the
    `<id>` portion of the zip filename. The bundle's `patient_id_hash`
    is always SHA-256-derived (writer-internal).
    """

    def __init__(
        self,
        *,
        patient_dir: Path,
        run_id: str,
        patient_code: str,
        opl_version: str = "2.3.0",
        data_source: str = "real_patient",
        extends_prior_run: str | None = None,
        mode: str = "final",
    ) -> None:
        self.patient_dir = Path(patient_dir)
        self.run_id = run_id
        self.patient_code = patient_code
        self.opl_version = opl_version
        self.data_source = data_source
        self.extends_prior_run = extends_prior_run
        if mode not in {"final", "draft", "dry_run"}:
            raise ValueError(
                f"mode must be 'final' | 'draft' | 'dry_run', got {mode!r}"
            )
        self.mode = mode
        self.run_dir = self.patient_dir / "triggers" / run_id
        self._written: list[Path] = []
        # P2-#17: detect prior run if not explicitly passed.
        if extends_prior_run is None:
            self.extends_prior_run = self._detect_prior_run()

    # ─── helpers ────────────────────────────────────────────────────────

    def _detect_prior_run(self) -> str | None:
        """Look under runs/ for any prior `chair_final_report.md` and pick
        the lexicographically-latest one OTHER than the current run_id.
        Returns the prior run_id, or None."""
        runs_root = self.patient_dir / "runs"
        if not runs_root.is_dir():
            return None
        candidates: list[tuple[str, Path]] = []
        for d in sorted(runs_root.iterdir()):
            if not d.is_dir():
                continue
            if d.name == self.run_id:
                continue
            if (d / "chair_final_report.md").is_file():
                candidates.append((d.name, d))
        if not candidates:
            return None
        return candidates[-1][0]

    def _require_wave5(self) -> None:
        missing = [
            f for f in WAVE5_PREREQUISITES
            if not (self.run_dir / f).is_file()
        ]
        if missing:
            raise Wave6PrerequisiteError(
                f"Wave 6 cannot start: Wave 5 outputs missing in "
                f"{self.run_dir}: {missing}. Ship plain + pi briefs first."
            )

    def _run_gates(self) -> dict[str, Any]:
        """Run G29-G33 against the bundle root. Returns a HENRY_AUDIT
        payload contribution that we merge into HENRY_AUDIT.json."""
        bundle_root = str(self.run_dir)
        gates = [
            G29ManuscriptAuthorshipDisclosedGate(),
            G30ClaimPMIDAnchoredGate(),
            G31FigureReproducibleGate(),
            G32DataAvailabilityDeclaredGate(),
            G33N1DesignTransparentGate(),
        ]
        results: list[dict[str, Any]] = []
        any_block = False
        for g in gates:
            r = g.check({
                "bundle_root": bundle_root,
                "run_stage": "wave6",
            })
            results.append({
                "gate": r.gate,
                "status": r.status.value,
                "block": r.block,
                "message": r.message,
                "evidence": r.evidence,
            })
            if r.block:
                any_block = True
        return {
            "gates_run": len(gates),
            "results": results,
            "any_block": any_block,
        }

    def _merge_henry_audit(self, gate_results: dict[str, Any]) -> Path:
        """Read existing HENRY_AUDIT.json (if any), merge G29-G33 results,
        write back. Returns the path."""
        path = self.run_dir / "HENRY_AUDIT.json"
        existing: dict[str, Any] = {}
        if path.is_file():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                existing = {}
        # Preserve existing fields; overlay v2.3 fields.
        existing.setdefault("audit_version", "v2.3")
        existing["audit_version"] = "v2.3"
        existing["opl_version"] = self.opl_version
        existing["gates_run"] = max(
            existing.get("gates_run", 0), 33
        )  # at least 33 with v2.3
        existing["wave6_gate_results"] = gate_results["results"]
        existing["wave6_any_block"] = gate_results["any_block"]
        existing["wave6_generated_at"] = datetime.now(timezone.utc).isoformat()
        # Status is "pass" if no blocks; else "fail".
        status = "pass" if not gate_results["any_block"] else "fail"
        # If existing status is fail, preserve fail.
        if existing.get("status") == "fail":
            status = "fail"
        existing["status"] = status

        path.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._written.append(path)
        return path

    def _aggregate_cost(self) -> dict[str, Any] | None:
        """Aggregate the run's cost_log.jsonl if it exists. P2-#20."""
        # Two conventional locations: run_dir/cost_log.jsonl OR
        # patient_dir/runs/<run_id>/cost_log.jsonl
        for candidate in (
            self.run_dir / "cost_log.jsonl",
            self.patient_dir / "runs" / self.run_id / "cost_log.jsonl",
        ):
            if candidate.is_file():
                return aggregate_cost_log(candidate)
        return None

    def _scaffold_missing_artifacts(self) -> list[str]:
        """Draft-mode helper: create empty stubs for any missing required
        artifacts so the bundle build does not fail on file-not-found.
        Returns the list of scaffolded files (for the deviations log).
        """
        scaffolded: list[str] = []
        for name in WAVE6_ARTIFACTS:
            p = self.run_dir / name
            if p.is_file():
                continue
            if name == "HENRY_AUDIT.json":
                p.write_text(
                    json.dumps(
                        {
                            "audit_version": "v2.3",
                            "status": "draft_stub",
                            "gates_run": 33,
                            "wave6_generated_at": datetime.now(
                                timezone.utc
                            ).isoformat(),
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            elif name == "provenance.jsonl":
                p.write_text(
                    json.dumps({
                        "stub": True,
                        "run_id": self.run_id,
                        "generated_at": datetime.now(
                            timezone.utc
                        ).isoformat(),
                    }) + "\n",
                    encoding="utf-8",
                )
            elif name == "references.bib":
                p.write_text(
                    "% draft references.bib — populate via "
                    "prompts/tasks/citation_assembly.md\n",
                    encoding="utf-8",
                )
            else:
                p.write_text(
                    f"<!-- draft stub for {name}; populate via Wave 6 "
                    f"prompts in `prompts/tasks/{Path(name).stem}.md` -->\n",
                    encoding="utf-8",
                )
            scaffolded.append(name)
            self._written.append(p)
        return scaffolded

    def _rollback(self) -> None:
        for p in reversed(self._written):
            try:
                if p.exists() and p.is_file():
                    p.unlink()
            except OSError:  # pragma: no cover — defensive
                pass
        self._written = []

    # ─── public entry ───────────────────────────────────────────────────

    def run(self) -> dict[str, Any]:
        if self.mode == "dry_run":
            return {
                "status": "dry_run",
                "run_dir": str(self.run_dir),
                "mode": "dry_run",
                "planned_steps": [
                    "_require_wave5",
                    "_scaffold_missing_artifacts (draft mode)",
                    "_run_gates G29-G33",
                    "_merge_henry_audit",
                    "_aggregate_cost",
                    "N1ABundleWriter.write",
                ],
            }

        try:
            self._require_wave5()
            scaffolded = (
                self._scaffold_missing_artifacts()
                if self.mode == "draft"
                else []
            )
            gate_results = self._run_gates()
            audit_path = self._merge_henry_audit(gate_results)

            # Enforce: in final mode, blocks are fatal.
            if self.mode == "final" and gate_results["any_block"]:
                blocked = [
                    r["gate"] for r in gate_results["results"] if r["block"]
                ]
                raise Wave6Failure(
                    f"Wave 6 BLOCKED in final mode: gates fired block on "
                    f"{blocked}. Resolve before rerunning."
                )

            cost_summary = self._aggregate_cost()
            writer = N1ABundleWriter(
                trigger_dir=self.run_dir,
                patient_code=self.patient_code,
                data_source=self.data_source,
                opl_version=self.opl_version,
                run_id=self.run_id,
                extends_prior_run=self.extends_prior_run,
                cost_summary=cost_summary,
            )
            result = writer.write()
            self._written.append(result.zip_path)
            self._written.append(result.manifest_path)

            return {
                "status": "ok",
                "mode": self.mode,
                "run_dir": str(self.run_dir),
                "manifest_path": str(result.manifest_path),
                "zip_path": str(result.zip_path),
                "files_packed": result.files_packed,
                "scaffolded_in_draft": scaffolded,
                "extends_prior_run": self.extends_prior_run,
                "henry_audit_path": str(audit_path),
                "wave6_gate_results": gate_results,
                "cost_summary": cost_summary,
            }
        except (Wave6PrerequisiteError, BundleWriteError, Wave6Failure):
            # Pre-condition / bundle failures: do NOT roll back files the
            # caller produced; only roll back files THIS runner wrote.
            self._rollback()
            raise
        except Exception as exc:
            self._rollback()
            raise Wave6Failure(
                f"Wave 6 atomic commit failed: {exc}. Rolled back "
                f"{len(self._written)} runner-written files. The patient "
                "sees no half-shipped manuscript."
            ) from exc


def run_wave6(
    *,
    patient_dir: Path,
    run_id: str,
    patient_code: str,
    opl_version: str = "2.3.0",
    data_source: str = "real_patient",
    extends_prior_run: str | None = None,
    mode: str = "final",
) -> dict[str, Any]:
    """Functional one-shot wrapper around Wave6Runner.run()."""
    return Wave6Runner(
        patient_dir=patient_dir,
        run_id=run_id,
        patient_code=patient_code,
        opl_version=opl_version,
        data_source=data_source,
        extends_prior_run=extends_prior_run,
        mode=mode,
    ).run()
