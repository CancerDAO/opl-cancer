"""v2.4 — `n1arxiv_submitter.py` (ADR-0024).

Cross-repo PR-assembly helper: takes a `.n1a` bundle produced by Wave 6
and prepares a ready-to-PR diff against `CancerDAO/n1arxiv`:

  1. Stages `static/bundles/<paper_id>.n1a.zip` (byte-exact copy)
  2. Generates `content/papers/<paper_id>.md` Hugo content stub from
     `manifest.json` (never duplicates the manuscript prose)
  3. Drafts the PR body (Frances-style, ethics + consent + scope-aware)
  4. Prints the `gh pr create` command and `git push` steps

This helper **NEVER** executes git or gh. Founder-mode invariant: the
patient is the sole decision authority for whether their session
becomes a public preprint. The submitter only prepares a diff.

The companion task package `prompts/tasks/n1arxiv_pr_assembly.md`
expands the PR body with Frances's framing when the wave6 runner has
LLM access; this module ships a deterministic fallback so the diff is
always producible offline.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = [
    "SubmitterError",
    "SubmissionPlan",
    "assemble_submission",
    "build_content_stub",
    "derive_paper_id",
    "draft_pr_body",
]


# Where the n1arxiv repo lives by default (PR-relative).
N1ARXIV_REPO_URL = "https://github.com/CancerDAO/n1arxiv"
N1ARXIV_DEFAULT_BRANCH = "main"


class SubmitterError(RuntimeError):
    """Raised when the submitter cannot produce a usable plan."""


@dataclass
class SubmissionPlan:
    """The plan returned by `assemble_submission`.

    Fields are typed so the CLI can JSON-serialize them without
    re-marshalling. Path fields are repo-relative posix strings.
    """

    paper_id: str
    bundle_source: str
    bundle_target: str
    content_stub_target: str
    pr_body: str
    suggested_commands: str
    data_source: str
    n1arxiv_clone: str | None
    executed_gh_pr_create: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "paper_id": self.paper_id,
            "bundle_source": self.bundle_source,
            "bundle_target": self.bundle_target,
            "content_stub_target": self.content_stub_target,
            "pr_body": self.pr_body,
            "suggested_commands": self.suggested_commands,
            "data_source": self.data_source,
            "n1arxiv_clone": self.n1arxiv_clone,
            "executed_gh_pr_create": self.executed_gh_pr_create,
        }


# ─── helpers ────────────────────────────────────────────────────────────


def _slug(text: str) -> str:
    """Conservative slugify — alphanumeric + dash, lowercase, no leading/trailing dash."""
    out = re.sub(r"[^A-Za-z0-9]+", "-", text.strip().lower())
    return out.strip("-") or "submission"


def _load_manifest_from_zip(bundle_zip: Path) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(bundle_zip) as zf:
            with zf.open("manifest.json") as f:
                return json.load(f)
    except (KeyError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        raise SubmitterError(
            f"Could not read manifest.json from {bundle_zip}: {exc}"
        ) from exc


def derive_paper_id(*, manifest: dict[str, Any], patient_code: str) -> str:
    """Deterministic paper id: <YYYY-MM-DD>-<slug-of-patient-code>.

    Falls back to manifest.patient_id_hash[:8] if patient_code is empty.
    """
    gen = manifest.get("generated_at") or ""
    # ISO-8601 prefix
    date = gen[:10] if len(gen) >= 10 else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if patient_code:
        tail = _slug(patient_code)
    else:
        tail = (manifest.get("patient_id_hash") or "anon")[:8]
    return f"{date}-{tail}".lower()


def build_content_stub(
    *,
    manifest: dict[str, Any],
    paper_id: str,
    bundle_relpath: str,
) -> str:
    """Hugo content stub. Front matter + minimal body + banner surfacing.

    The stub purposely does NOT inline the manuscript prose — readers
    download the bundle to read the paper. This keeps the platform
    schema-light and avoids drift between bundle + stub.
    """
    data_source = str(manifest.get("data_source") or "unknown")
    opl_version = str(manifest.get("opl_version") or "unknown")
    generated_at = str(manifest.get("generated_at") or "")
    patient_id_hash = str(manifest.get("patient_id_hash") or "anon")
    banner = manifest.get("banner") or ""
    extends_prior_run = manifest.get("extends_prior_run") or ""

    title = f"N=1 Case Report ({patient_id_hash})"
    if data_source == "reference_case":
        title = f"Methodology Reference Case ({patient_id_hash})"
    elif data_source == "methodology_demo":
        title = f"[Methodology Demo] ({patient_id_hash})"
    elif data_source == "synthetic":
        title = f"[Synthetic] N=1 Case Report ({patient_id_hash})"

    lines: list[str] = [
        "---",
        f'title: "{title}"',
        f'date: "{generated_at or datetime.now(timezone.utc).isoformat()}"',
        f"paper_id: {paper_id}",
        f"data_source: {data_source}",
        f'opl_version: "{opl_version}"',
        f"patient_id_hash: {patient_id_hash}",
        f"bundle: {bundle_relpath}",
    ]
    if extends_prior_run:
        lines.append(f"extends_prior_run: {extends_prior_run}")
    if banner:
        lines.append(f'banner: "{banner}"')
    lines.append("---")
    lines.append("")

    if banner:
        lines.append(f"> **{banner}**")
        lines.append("")

    lines.append(
        "This page indexes an N=1 case-report bundle generated by "
        "[OPL for Cancer](https://github.com/CancerDAO/opl-cancer). "
        "The full manuscript, audit log, and reproducibility statement "
        f"live in the accompanying `.n1a` bundle (schema "
        f"{manifest.get('schema_version', '0.1')})."
    )
    lines.append("")
    lines.append("## Bundle")
    lines.append("")
    lines.append(f"- Download: [`{Path(bundle_relpath).name}`]({{{{< relref \"/{bundle_relpath}\" >}}}})")
    lines.append(f"- SHA-256s: see `manifest.json` inside the bundle")
    lines.append(f"- Generated: `{generated_at}`")
    lines.append(f"- OPL version: `{opl_version}`")
    if extends_prior_run:
        lines.append(f"- Extends prior run: `{extends_prior_run}`")
    lines.append("")
    lines.append("## Ethics")
    lines.append("")
    lines.append(
        "N=1 reports are **not** clinical guidance. Each report's "
        "`ethics_declaration.md` records the consent state at the time "
        "of publication. Patients retain withdrawal rights — see "
        "`docs/n1_ethics.md` in this repository."
    )
    return "\n".join(lines) + "\n"


def draft_pr_body(
    *,
    manifest: dict[str, Any],
    paper_id: str,
    bundle_relpath: str,
    content_relpath: str,
) -> str:
    """Frances-style PR body. Ethics + consent + scope-aware framing.

    Deterministic fallback when no LLM is available. Surfaces:
      * data_source (banner if non-real_patient)
      * Consent attestation reminder for real_patient
      * Henry G29-G33 summary (if available)
      * File integrity reminder (CI re-verifies SHA-256)
      * Withdrawal policy reminder
    """
    data_source = str(manifest.get("data_source") or "unknown")
    opl_version = str(manifest.get("opl_version") or "unknown")
    banner = manifest.get("banner") or ""
    extends = manifest.get("extends_prior_run") or ""
    henry = manifest.get("henry_audit_summary") or {}

    parts: list[str] = []
    parts.append(f"# N1Arxiv submission — `{paper_id}`")
    parts.append("")
    if banner:
        parts.append(f"> **{banner}**")
        parts.append("")
    parts.append("## Summary")
    parts.append("")
    parts.append(
        "This PR submits an N=1 case-report bundle produced by OPL for "
        f"Cancer v{opl_version}. The bundle is schema-validated against "
        "`schemas/n1a_bundle.v0.1.schema.json` and carries a Henry audit "
        "with all G29-G33 gates evaluated."
    )
    parts.append("")
    parts.append("## Files")
    parts.append("")
    parts.append(f"- `{bundle_relpath}` — the `.n1a` bundle (byte-exact copy)")
    parts.append(f"- `{content_relpath}` — Hugo content stub (auto-generated from `manifest.json`)")
    parts.append("")
    parts.append("## Data source & ethics")
    parts.append("")
    parts.append(f"- `data_source`: `{data_source}`")
    if data_source == "real_patient":
        parts.append(
            "- **real_patient**: CI will refuse this PR unless "
            "`ethics_declaration.md` inside the bundle contains the "
            "canonical consent attestation. The submitting patient "
            "(or caregiver) is the sole decision authority for "
            "publication. Withdrawal at any time is honoured per "
            "`docs/n1_ethics.md`."
        )
    else:
        parts.append(
            "- Non-`real_patient` submission — banner is enforced both "
            "in the bundle's `manuscript.md` header and on the site "
            "detail page."
        )
    if extends:
        parts.append(f"- Extends prior run: `{extends}`")
    parts.append("")

    # Henry gate summary
    parts.append("## Henry audit (G29-G33)")
    parts.append("")
    if henry:
        status = henry.get("status", "unknown")
        parts.append(f"- Overall status: `{status}`")
        results = henry.get("results") or []
        if isinstance(results, list):
            for r in results:
                if not isinstance(r, dict):
                    continue
                gate = r.get("gate", "?")
                gs = r.get("status", "?")
                parts.append(f"  - `{gate}`: {gs}")
    else:
        parts.append("- Audit summary not embedded in manifest; see `HENRY_AUDIT.json` inside the bundle.")
    parts.append("")
    parts.append("## CI checks (automatic)")
    parts.append("")
    parts.append(
        "- `validate_submission.yml` will: unzip the bundle, validate "
        "`manifest.json` against the schema, re-compute SHA-256 for "
        "every file, read `HENRY_AUDIT.json`, and refuse if any G29-G33 "
        "= FAIL. real_patient submissions additionally require the "
        "consent attestation in `ethics_declaration.md`."
    )
    parts.append("")
    parts.append("## Reviewer guidance")
    parts.append("")
    parts.append(
        "- N=1 reports are not clinical guidance. Please verify the "
        "framing language in the manuscript stays single-subject."
    )
    parts.append(
        "- Bundle SHA-256s are inside `manifest.json` — CI re-verifies "
        "them; manual review can focus on content sanity."
    )
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("Generated by `opl wave6 --submit-to-n1arxiv` (ADR-0024).")
    return "\n".join(parts) + "\n"


def _suggested_commands(
    *,
    n1arxiv_clone: Path | None,
    paper_id: str,
    bundle_target: str,
    content_stub_target: str,
) -> str:
    repo = str(n1arxiv_clone) if n1arxiv_clone else "<path/to/n1arxiv-clone>"
    return (
        "# 1. Review the staged files\n"
        f"cd {repo}\n"
        f"git status\n"
        "# 2. Create a topic branch\n"
        f"git checkout -b submit/{paper_id}\n"
        f"git add {bundle_target} {content_stub_target}\n"
        f"git commit -m 'Submit {paper_id}'\n"
        "# 3. Push your fork (replace origin with your fork remote if needed)\n"
        "git push -u origin HEAD\n"
        "# 4. Open the pull request\n"
        "gh pr create --base main --title "
        f"'Submit {paper_id}' --body-file PR_BODY.md\n"
    )


# ─── public API ─────────────────────────────────────────────────────────


def assemble_submission(
    *,
    bundle_zip: Path,
    n1arxiv_clone: Path | None,
    patient_code: str,
    execute: bool = False,
) -> dict[str, Any]:
    """Stage a .n1a bundle into an n1arxiv clone (or just plan it).

    Parameters
    ----------
    bundle_zip
        Path to the `.n1a.zip` produced by Wave 6.
    n1arxiv_clone
        Optional local clone of `CancerDAO/n1arxiv`. When provided, the
        bundle is byte-copied into `static/bundles/` and a content stub
        is written into `content/papers/`. When `None`, only the plan
        is produced (paths shown as repo-relative posix strings).
    patient_code
        Human-readable patient identifier (slugified into the paper id;
        never written to disk).
    execute
        Founder-mode safety belt. Must be False (the default). The
        submitter NEVER calls `git push` or `gh pr create`. The flag
        exists only so the CLI signature can pass it through honestly
        and future callers can detect mis-use.

    Returns
    -------
    dict
        Serializable plan (see :class:`SubmissionPlan`).
    """
    bundle_zip = Path(bundle_zip)
    if not bundle_zip.is_file():
        raise SubmitterError(f"bundle_zip does not exist: {bundle_zip}")
    if execute:
        # Hard refusal — keep founder-mode invariant explicit.
        raise SubmitterError(
            "assemble_submission(execute=True) is not supported. The "
            "submitter never auto-PRs. Run the printed `gh pr create` "
            "yourself after reviewing the diff."
        )

    manifest = _load_manifest_from_zip(bundle_zip)
    paper_id = derive_paper_id(manifest=manifest, patient_code=patient_code)
    bundle_target = f"static/bundles/{paper_id}.n1a.zip"
    content_stub_target = f"content/papers/{paper_id}.md"

    content_stub = build_content_stub(
        manifest=manifest,
        paper_id=paper_id,
        bundle_relpath=bundle_target,
    )
    pr_body = draft_pr_body(
        manifest=manifest,
        paper_id=paper_id,
        bundle_relpath=bundle_target,
        content_relpath=content_stub_target,
    )
    suggested = _suggested_commands(
        n1arxiv_clone=n1arxiv_clone,
        paper_id=paper_id,
        bundle_target=bundle_target,
        content_stub_target=content_stub_target,
    )

    if n1arxiv_clone is not None:
        n1arxiv_clone = Path(n1arxiv_clone)
        if not n1arxiv_clone.is_dir():
            raise SubmitterError(
                f"n1arxiv clone path does not exist: {n1arxiv_clone}"
            )
        bundles_dir = n1arxiv_clone / "static" / "bundles"
        papers_dir = n1arxiv_clone / "content" / "papers"
        bundles_dir.mkdir(parents=True, exist_ok=True)
        papers_dir.mkdir(parents=True, exist_ok=True)

        target_zip = bundles_dir / f"{paper_id}.n1a.zip"
        target_md = papers_dir / f"{paper_id}.md"

        # Byte-exact copy
        shutil.copyfile(bundle_zip, target_zip)
        # Spot-check the copy
        src_sha = hashlib.sha256(bundle_zip.read_bytes()).hexdigest()
        dst_sha = hashlib.sha256(target_zip.read_bytes()).hexdigest()
        if src_sha != dst_sha:  # pragma: no cover — defensive
            target_zip.unlink(missing_ok=True)
            raise SubmitterError(
                f"Bundle copy hash mismatch: src={src_sha} dst={dst_sha}"
            )

        target_md.write_text(content_stub, encoding="utf-8")

    plan = SubmissionPlan(
        paper_id=paper_id,
        bundle_source=str(bundle_zip),
        bundle_target=bundle_target,
        content_stub_target=content_stub_target,
        pr_body=pr_body,
        suggested_commands=suggested,
        data_source=str(manifest.get("data_source") or "unknown"),
        n1arxiv_clone=str(n1arxiv_clone) if n1arxiv_clone else None,
        executed_gh_pr_create=False,
    )
    return plan.as_dict()
