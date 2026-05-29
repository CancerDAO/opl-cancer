"""G34: delivery_attestation — a delivered brief must be backed by a REAL run.

v2.7.0 (ADR-0026 / session 0d1017d4 fix). The keystone gate. The driving
incident: the executor free-handed a 100%-LLM-synthesised brief — no plan, no
wave artifacts, no provenance journal, no Henry audit — and shipped it. The
documented terminal command (``render``) was a ``mkdir + {"ok":true}`` stub that
verified nothing, so every safety mechanism stayed dormant.

G34 is the mechanical handshake binding the chat-delivered brief to a verifiable
on-disk OPL run. At delivery it requires, under ``<run_root>``:

1. ``run_manifest.json`` with a non-empty ``run_token`` (minted at ``plan``,
   threaded through the waves). A free-handed reply has no token.
2. ``provenance.jsonl`` with ≥1 record whose recorded ``hash`` **recomputes**
   via ``hasher.hash_claim`` over its ``claim`` payload — this catches both an
   absent journal and a hand-typed ``sha256:`` string.
3. ``HENRY_AUDIT.json`` (or ``HENRY_VERDICT.json``) with ``henry_real_audit ==
   true`` and ``claims_audited > 0`` — proof the real audit ran, not the scaffold.
4. (when a rendered brief is present) every ``[PMID:...]`` / ``[NCT...]`` anchor in
   the brief appears in the provenance journal or claims manifest — a brief
   cannot contain a claim with no provenance record.

Lightweight forge-resistance (Fork C, founder decision): token + recomputable
hashes. This stops the *accidental/lazy* free-hand that actually happened (the
agent wasn't adversarial — it was token-optimising). Hashing live integrator
response bodies for adversarial forge-resistance is a future layer.

No-LLM, synchronous. Caller passes ``run_root``; optionally ``out_dir``
(the ``delivery/`` sub-dir) and/or ``brief_path`` for the PMID cross-check.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from opl_cancer.provenance.hasher import hash_claim
from opl_cancer.provenance.journal import ProvenanceJournal

from ..mechanical_gates import Gate, GateResult, GateStatus

_PMID_RE = re.compile(r"\[PMID\s*:?\s*(\d{4,9})\]", re.IGNORECASE)
_NCT_RE = re.compile(r"\b(NCT\d{8})\b")


def _resolve_run_root(claim: dict[str, Any]) -> Path | None:
    if claim.get("run_root"):
        return Path(claim["run_root"])
    if claim.get("out_dir"):
        return Path(claim["out_dir"]).parent
    return None


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _structured_pmids(obj: Any) -> set[str]:
    """Recursively collect ids of {type:'pmid', id:...} evidence dicts."""
    out: set[str] = set()
    if isinstance(obj, dict):
        if str(obj.get("type", "")).lower() == "pmid" and obj.get("id"):
            out.add(str(obj["id"]))
        for v in obj.values():
            out |= _structured_pmids(v)
    elif isinstance(obj, list):
        for v in obj:
            out |= _structured_pmids(v)
    return out


def _journal_pmids_and_integrity(run_root: Path) -> tuple[set[str], int, bool]:
    """Return (pmids in journal, record count, ≥1 hash recomputes)."""
    jpath = run_root / "provenance.jsonl"
    if not jpath.exists():
        return set(), 0, False
    pmids: set[str] = set()
    count = 0
    hash_ok = False
    for rec in ProvenanceJournal(jpath).iter_records():
        count += 1
        # collect PMIDs both as [PMID:...] text and as structured evidence ids
        blob = json.dumps(rec, ensure_ascii=False)
        pmids.update(_PMID_RE.findall(blob))
        pmids.update(_structured_pmids(rec))
        # integrity: recorded hash must recompute from the recorded claim payload
        recorded = rec.get("hash")
        payload = rec.get("claim")
        if recorded and isinstance(payload, dict):
            try:
                if hash_claim(payload) == recorded:
                    hash_ok = True
            except (TypeError, ValueError):
                pass
    return pmids, count, hash_ok


def _claims_pmids(run_root: Path, out_dir: Path | None) -> set[str]:
    pmids: set[str] = set()
    candidates = [run_root / "claims.json"]
    if out_dir is not None:
        candidates.append(out_dir / "claims.json")
    for c in candidates:
        data = _load_json(c)
        if data is not None:
            pmids.update(_PMID_RE.findall(json.dumps(data, ensure_ascii=False)))
            pmids.update(_structured_pmids(data))
    return pmids


def _brief_anchors(out_dir: Path | None, brief_path: str | None) -> tuple[Path | None, set[str], set[str]]:
    """Return (brief_path_used, pmids, ncts) found in the rendered brief, if any."""
    candidates: list[Path] = []
    if brief_path:
        candidates.append(Path(brief_path))
    if out_dir is not None:
        for name in ("patient_pi_brief.md", "patient_brief.html", "patient_plain_brief.md", "pi_delivery.md"):
            candidates.append(out_dir / name)
    for p in candidates:
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            return p, set(_PMID_RE.findall(text)), set(_NCT_RE.findall(text))
    return None, set(), set()


class G34DeliveryAttestationGate(Gate):
    """A delivered brief must be backed by a verifiable on-disk OPL run."""

    name = "G34_delivery_attestation"
    description = (
        "Delivery requires run_manifest.json (run_token), a provenance.jsonl with "
        "≥1 recomputable-hash record, and a real Henry audit (henry_real_audit=true, "
        "claims_audited>0). Brief PMIDs must appear in the provenance/claims record. "
        "Free-handed briefs (no run) are mechanically refused."
    )
    failure_mode_code = "AP-FREE-HANDED-DELIVERY"
    family_id = "provenance"

    def check(self, claim: dict[str, Any]) -> GateResult:
        run_root = _resolve_run_root(claim)
        if run_root is None or not run_root.exists():
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=True,
                message="G34 FAIL — no run_root; a delivered brief must reference a real run dir.",
                evidence={"run_root": str(run_root)},
            )
        out_dir = Path(claim["out_dir"]) if claim.get("out_dir") else (run_root / "delivery")
        problems: list[str] = []

        # (1) run manifest + token
        manifest = _load_json(run_root / "run_manifest.json")
        run_token = (manifest or {}).get("run_token") if isinstance(manifest, dict) else None
        if not run_token:
            problems.append("run_manifest.json missing or has no run_token (no real run was started)")

        # (2) provenance journal integrity
        jpmids, jcount, hash_ok = _journal_pmids_and_integrity(run_root)
        if jcount == 0:
            problems.append("provenance.jsonl missing/empty (no claim was ever journalled — free-hand)")
        elif not hash_ok:
            problems.append(
                "provenance.jsonl present but NO record's hash recomputes from its "
                "claim payload (hand-typed/forged sha256 strings)"
            )

        # (3) real Henry audit
        audit = _load_json(out_dir / "HENRY_AUDIT.json") or _load_json(out_dir / "HENRY_VERDICT.json") \
            or _load_json(run_root / "HENRY_AUDIT.json")
        if not isinstance(audit, dict) or not audit.get("henry_real_audit") or int(audit.get("claims_audited", 0) or 0) <= 0:
            problems.append(
                "no real Henry audit (HENRY_AUDIT.json with henry_real_audit=true & "
                "claims_audited>0) — the scaffold is not a finished, audited delivery"
            )

        # (4) brief PMID cross-check (only if a brief is rendered)
        brief_p, brief_pmids, _ncts = _brief_anchors(out_dir, claim.get("brief_path"))
        if brief_p is not None and brief_pmids:
            known = jpmids | _claims_pmids(run_root, out_dir)
            orphan = sorted(brief_pmids - known)
            if orphan:
                problems.append(
                    f"brief cites PMID(s) with no provenance record: {orphan[:8]} "
                    f"(in {brief_p.name}) — a claim was invented at render time"
                )

        if problems:
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=True,
                message="G34 FAIL — delivery is not backed by a verifiable run: " + " | ".join(problems),
                evidence={
                    "run_root": str(run_root),
                    "has_manifest_token": bool(run_token),
                    "journal_records": jcount,
                    "journal_hash_recomputes": hash_ok,
                    "problems": problems,
                },
            )
        return GateResult(
            gate=self.name, status=GateStatus.PASS,
            message=(
                f"G34 OK — delivery attested: run_token present, {jcount} journalled "
                "claim(s) with recomputable provenance, real Henry audit ran."
            ),
            evidence={"run_root": str(run_root), "journal_records": jcount},
        )
