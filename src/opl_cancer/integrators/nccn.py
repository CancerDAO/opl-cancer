"""NCCN Guidelines — local excerpts (spec §15 G7 copyright safe)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .base import Integrator, IntegratorError


def _excerpts_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "knowledge" / "nccn_excerpts"
        if candidate.is_dir():
            return candidate
    raise IntegratorError("NCCN: knowledge/nccn_excerpts/ not found")


class NCCNPageIndexIntegrator(Integrator):
    family = "F2"
    ttl_seconds = 30 * 24 * 3600  # spec §17.5 P2: NCCN 30-day TTL
    family_config_key = "nccn"  # Iter 18: read from models.yaml.integrator_ttl_seconds

    async def fetch(self, key: str) -> dict[str, Any]:
        if ":" not in key:
            raise IntegratorError(f"NCCN: expected <CANCER>:<context>, got {key!r}")
        cancer, ctx = key.split(":", 1)
        cancer_lower = cancer.strip().lower()
        excerpts_dir = _excerpts_dir()
        path = excerpts_dir / f"{cancer_lower}_2025.json"
        if not path.exists():
            raise IntegratorError(f"NCCN: no excerpts file for {cancer!r} ({path.name})")
        data = json.loads(path.read_text())
        ctx_tokens = {w.lower() for w in re.findall(r"[a-zA-Z一-鿿]+", ctx) if len(w) > 2}
        matches = []
        for node in data["decision_nodes"]:
            node_text = (node["context"] + " " + node["excerpt"]).lower()
            if any(t in node_text for t in ctx_tokens):
                matches.append(node)
        return {
            "cancer_type": data["cancer_type"],
            "guideline": data["guideline"],
            "version": data["version"],
            "version_date": data["version_date"],
            "url": data["url"],
            "matches": matches,
        }
