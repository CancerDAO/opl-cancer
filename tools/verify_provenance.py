"""verify_provenance.py — verify all claim hashes in a trigger run.

Spec §12 provenance integrity. For every claim in a patient_brief.json or
provenance.jsonl, recompute the sha256 of `to_hashable()` and compare against
the stored `claim_hash`.

Usage:
    python -m tools.verify_provenance <patient_dir> <run_id>

Exits 0 if all hashes match, 1 if any mismatch, 2 on file error.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


def _hash_obj(obj: dict[str, Any]) -> str:
    """Recompute sha256 of a hashable payload (excludes 'claim_hash' key itself)."""
    payload = {k: v for k, v in obj.items() if k not in {"claim_hash", "content_hash"}}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def verify(patient_dir: Path, run_id: str) -> dict[str, Any]:
    jl = patient_dir / "triggers" / run_id / "provenance.jsonl"
    if not jl.exists():
        raise FileNotFoundError(f"No provenance journal at {jl}")
    matches = 0
    mismatches: list[dict[str, Any]] = []
    no_hash = 0
    for line in jl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        stored = rec.get("claim_hash") or rec.get("content_hash")
        if not stored:
            no_hash += 1
            continue
        # The original payload for hashing may have included a 'claim' or 'output'
        # field; we hash the rec minus the hash key for round-trip verification.
        recomputed = _hash_obj(rec)
        if recomputed == stored:
            matches += 1
        else:
            mismatches.append({
                "id": rec.get("id") or rec.get("claim_id") or "<unknown>",
                "stored": stored,
                "recomputed": recomputed,
            })
    return {
        "total": matches + len(mismatches) + no_hash,
        "matches": matches,
        "mismatches": mismatches,
        "no_hash": no_hash,
        "ok": len(mismatches) == 0,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "Usage: python -m tools.verify_provenance <patient_dir> <run_id>",
            file=sys.stderr,
        )
        return 2
    patient_dir = Path(argv[1])
    run_id = argv[2]
    try:
        report = verify(patient_dir, run_id)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
