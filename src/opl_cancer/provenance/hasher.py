"""Canonical SHA-256 hashing for reproducible claim provenance."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def hash_claim(data: dict[str, Any]) -> str:
    """SHA-256 of canonical JSON encoding (sorted keys, no spaces).

    Use for any patient-facing claim. The hash is reproducible IFF the
    same dict (regardless of key order) is hashed. Spec §17 reproducibility.
    """
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
