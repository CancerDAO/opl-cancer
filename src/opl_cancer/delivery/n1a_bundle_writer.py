"""v2.3 — `.n1a` bundle writer (ADR-0023).

Collects every Wave 6 artifact from `patients/<id>/triggers/<run_id>/`,
computes per-file SHA-256, builds `manifest.json`, zips into
`<id>.n1a.zip`, and validates the manifest against
`schemas/n1a_bundle.v0.1.schema.json` before returning.

The writer is intentionally schema-driven — every shape change goes
through the JSON Schema, so the v2.4 N1Arxiv CI can validate the same
bundle without importing the OPL codebase.

Per spec §5.5 P2-#18: non-`real_patient` bundles auto-stamp a banner
string into the manifest AND copy a banner line into manuscript.md
header so downstream readers (and the figure-render PDF watermark)
cannot miss the methodology-demonstration framing.
"""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import jsonschema  # type: ignore[import-not-found]
    _HAS_JSONSCHEMA = True
except ImportError:  # pragma: no cover — fail loud rather than skip
    _HAS_JSONSCHEMA = False


__all__ = [
    "BundleWriteError",
    "N1ABundleWriter",
    "write_bundle",
    "BANNER_METHODOLOGY_DEMO",
    "BANNER_REFERENCE_CASE",
    "BANNER_SYNTHETIC",
]


# Banners enforced by the writer for non-real_patient data_source values.
# Mirrors P2-#18 enforcement.
BANNER_METHODOLOGY_DEMO = "[METHODOLOGY DEMONSTRATION — NOT REAL PATIENT]"
BANNER_REFERENCE_CASE = "[REFERENCE CASE — PUBLIC DATA, NOT THIS PATIENT]"
BANNER_SYNTHETIC = "[SYNTHETIC DATA — NOT REAL PATIENT]"

# data_source → banner
_BANNER_BY_SOURCE: dict[str, str] = {
    "methodology_demo": BANNER_METHODOLOGY_DEMO,
    "reference_case": BANNER_REFERENCE_CASE,
    "synthetic": BANNER_SYNTHETIC,
}


# Files we expect under triggers/<run_id>/ for a complete Wave 6 delivery.
# A bundle MAY ship without some of these; the writer treats them as
# optional but always lists what was found.
EXPECTED_FILES = [
    "manuscript.md",
    "manuscript.pdf",
    "references.bib",
    "provenance.jsonl",
    "reproducibility.md",
    "ethics_declaration.md",
    "ai_authorship_disclosure.md",
    "world_unknown_appendix.md",
    "HENRY_AUDIT.json",
    "manuscript_methods.md",
    "manuscript_introduction.md",
    "manuscript_results.md",
    "manuscript_discussion.md",
    "manuscript_limitations.md",
    "manuscript_abstract.md",
]

REQUIRED_FILES_FOR_BUNDLE = [
    "manuscript.md",
    "ai_authorship_disclosure.md",
    "reproducibility.md",
    "HENRY_AUDIT.json",
]


class BundleWriteError(RuntimeError):
    """Raised when the writer cannot produce a schema-valid bundle."""


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _hash_patient_code(patient_code: str) -> str:
    return hashlib.sha256(patient_code.encode("utf-8")).hexdigest()[:16]


def _load_schema() -> dict[str, Any]:
    # Resolve from the repo root: src/opl_cancer/delivery/ → repo/schemas/
    here = Path(__file__).resolve()
    repo_root = here.parents[3]
    schema_path = repo_root / "schemas" / "n1a_bundle.v0.1.schema.json"
    if not schema_path.is_file():
        # Fallback: also try sibling 'schemas/'
        alt = here.parents[2] / "schemas" / "n1a_bundle.v0.1.schema.json"
        if alt.is_file():
            schema_path = alt
        else:
            raise BundleWriteError(
                f"n1a_bundle schema not found at {schema_path}."
            )
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _inject_banner_into_manuscript(manuscript_text: str, banner: str) -> str:
    """Ensure the banner appears on the first non-empty line of manuscript.md.
    Idempotent — re-running does not duplicate."""
    if banner in manuscript_text.split("\n", 5)[0:5]:
        return manuscript_text
    lines = manuscript_text.splitlines()
    # Insert before the first heading or at top.
    out: list[str] = []
    inserted = False
    for line in lines:
        if not inserted and line.lstrip().startswith("#"):
            out.append(f"> {banner}\n")
            inserted = True
        out.append(line)
    if not inserted:
        out.insert(0, f"> {banner}\n")
    return "\n".join(out) + ("\n" if not manuscript_text.endswith("\n") else "")


class N1ABundleWriter:
    """Build a `.n1a` zip bundle from a Wave 6 trigger directory.

    Usage:
        writer = N1ABundleWriter(
            trigger_dir=Path("patients/007/triggers/abc"),
            patient_code="007-zhiqiang",
            data_source="real_patient",
            opl_version="2.3.0",
            run_id="abc",
        )
        result = writer.write()
        # result.zip_path  → Path to <id>.n1a.zip
        # result.manifest  → manifest dict
    """

    def __init__(
        self,
        *,
        trigger_dir: Path,
        patient_code: str,
        data_source: str = "real_patient",
        opl_version: str = "2.3.0",
        run_id: str | None = None,
        extends_prior_run: str | None = None,
        cost_summary: dict[str, Any] | None = None,
    ) -> None:
        self.trigger_dir = Path(trigger_dir)
        self.patient_code = patient_code
        self.data_source = data_source
        self.opl_version = opl_version
        self.run_id = run_id
        self.extends_prior_run = extends_prior_run
        self.cost_summary = cost_summary

    # ─────────────────────────── public ──────────────────────────────────

    def write(self) -> "BundleResult":
        if not self.trigger_dir.is_dir():
            raise BundleWriteError(
                f"trigger_dir does not exist: {self.trigger_dir}"
            )

        # Apply banner injection BEFORE hashing/zipping so the hash captures
        # the final on-disk content.
        banner = _BANNER_BY_SOURCE.get(self.data_source)
        if banner is not None:
            ms = self.trigger_dir / "manuscript.md"
            if ms.is_file():
                txt = ms.read_text(encoding="utf-8")
                new_txt = _inject_banner_into_manuscript(txt, banner)
                if new_txt != txt:
                    ms.write_text(new_txt, encoding="utf-8")

        # Discover files: any EXPECTED_FILES that exist + any files under
        # figures/ and tables/ subdirectories.
        present: list[Path] = []
        for name in EXPECTED_FILES:
            p = self.trigger_dir / name
            if p.is_file():
                present.append(p)
        for sub in ("figures", "tables"):
            d = self.trigger_dir / sub
            if d.is_dir():
                for f in sorted(d.iterdir()):
                    if f.is_file():
                        present.append(f)

        # Required check
        present_names = {p.relative_to(self.trigger_dir).as_posix() for p in present}
        missing_required = [f for f in REQUIRED_FILES_FOR_BUNDLE if f not in present_names]
        if missing_required:
            raise BundleWriteError(
                f"Bundle is missing required files: {missing_required}. "
                "Cannot ship .n1a without manuscript + audit + repro + disclosure."
            )

        # Hash all files (sorted, relative-path keyed).
        sha256s: dict[str, str] = {}
        file_index: list[str] = []
        for p in sorted(present, key=lambda x: x.relative_to(self.trigger_dir).as_posix()):
            rel = p.relative_to(self.trigger_dir).as_posix()
            sha256s[rel] = _sha256_file(p)
            file_index.append(rel)

        # Henry audit summary (if HENRY_AUDIT.json present).
        henry_summary: dict[str, Any] = {}
        ha_path = self.trigger_dir / "HENRY_AUDIT.json"
        if ha_path.is_file():
            try:
                henry_summary = json.loads(ha_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                henry_summary = {"status": "unparseable"}

        manifest: dict[str, Any] = {
            "schema_version": "0.1",
            "opl_version": self.opl_version,
            "patient_id_hash": _hash_patient_code(self.patient_code),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_source": self.data_source,
            "file_index": file_index,
            "sha256s": sha256s,
        }
        if self.run_id is not None:
            manifest["run_id"] = self.run_id
        if self.extends_prior_run:
            manifest["extends_prior_run"] = self.extends_prior_run
        if self.cost_summary:
            manifest["cost_summary"] = self.cost_summary
        if henry_summary:
            manifest["henry_audit_summary"] = henry_summary
        if banner is not None:
            manifest["banner"] = banner

        # Validate.
        self._validate_manifest(manifest)

        # Write manifest.json into trigger_dir (it's part of the bundle).
        manifest_path = self.trigger_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Build zip filename: <id>_<date>.n1a.zip
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        safe_id = re.sub(r"[^A-Za-z0-9_\-]+", "-", self.patient_code)
        zip_name = f"{safe_id}_{date}.n1a.zip"
        zip_path = self.trigger_dir / zip_name

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(manifest_path, arcname="manifest.json")
            for p in present:
                rel = p.relative_to(self.trigger_dir).as_posix()
                zf.write(p, arcname=rel)

        return BundleResult(
            zip_path=zip_path,
            manifest=manifest,
            manifest_path=manifest_path,
            files_packed=len(present) + 1,  # +1 for manifest.json
        )

    # ────────────────────── private helpers ──────────────────────────────

    def _validate_manifest(self, manifest: dict[str, Any]) -> None:
        if not _HAS_JSONSCHEMA:
            raise BundleWriteError(
                "jsonschema is required for bundle validation but not installed."
            )
        schema = _load_schema()
        try:
            jsonschema.validate(instance=manifest, schema=schema)
        except jsonschema.ValidationError as exc:  # pragma: no cover — defensive
            raise BundleWriteError(
                f"manifest.json failed schema validation: {exc.message} "
                f"at {list(exc.absolute_path)}"
            ) from exc


class BundleResult:
    """Returned from N1ABundleWriter.write()."""

    def __init__(
        self,
        *,
        zip_path: Path,
        manifest: dict[str, Any],
        manifest_path: Path,
        files_packed: int,
    ) -> None:
        self.zip_path = zip_path
        self.manifest = manifest
        self.manifest_path = manifest_path
        self.files_packed = files_packed

    def __repr__(self) -> str:  # pragma: no cover — repr only
        return (
            f"BundleResult(zip={self.zip_path.name}, files={self.files_packed}, "
            f"data_source={self.manifest.get('data_source')})"
        )


def write_bundle(
    *,
    trigger_dir: Path,
    patient_code: str,
    data_source: str = "real_patient",
    opl_version: str = "2.3.0",
    run_id: str | None = None,
    extends_prior_run: str | None = None,
    cost_summary: dict[str, Any] | None = None,
) -> BundleResult:
    """Functional wrapper for one-shot bundle writes."""
    return N1ABundleWriter(
        trigger_dir=trigger_dir,
        patient_code=patient_code,
        data_source=data_source,
        opl_version=opl_version,
        run_id=run_id,
        extends_prior_run=extends_prior_run,
        cost_summary=cost_summary,
    ).write()
