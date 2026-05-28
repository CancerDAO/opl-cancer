"""UniversalAdapter sandbox — v2.5 compositional foundation (RFC 0001 §2.4).

Given an OpenAPI schema URL or path, parse it and return an ``AdHocIntegrator``
that knows the operations + base URL. v2.5 ships the SANDBOX only — live calls
raise ``UniversalAdapterLiveNotEnabled`` unless ``OPL_UNIVERSAL_ADAPTER_LIVE=1``.

Live mode lands in M3 with LLM-generated request shaping + sanity probes.
This module deliberately does not make any HTTP calls during dry_run.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:  # pragma: no cover - convenience
    import httpx  # noqa: F401  (used by future live-mode wiring)
except Exception:  # pragma: no cover
    httpx = None  # type: ignore[assignment]


class UniversalAdapterLiveNotEnabled(RuntimeError):
    """Raised when an AdHoc adapter tries to make a live call without
    ``OPL_UNIVERSAL_ADAPTER_LIVE=1`` set. v2.5 ships sandbox-only."""


@dataclass
class AdHocIntegrator:
    """An LLM-discovered adapter wrapped around an OpenAPI schema.

    v2.5: holds the metadata only. ``call()`` raises in dry-run.
    """

    title: str
    base_url: str
    operations: list[dict[str, Any]] = field(default_factory=list)

    def provenance(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "base_url": self.base_url,
            "operations": [op.get("operationId") for op in self.operations],
            "live_enabled": _live_enabled(),
            "module": "universal_adapter",
            "milestone_for_live": "M3",
        }

    def call(self, operation_id: str, params: dict[str, Any] | None = None) -> Any:
        """Make a live call. Raises in v2.5 unless env opt-in."""
        if not _live_enabled():
            raise UniversalAdapterLiveNotEnabled(
                "v2.5 ships UniversalAdapter in dry-run only. Set "
                "OPL_UNIVERSAL_ADAPTER_LIVE=1 to enable live calls (M3 ships "
                "the full live-mode safety harness)."
            )
        # v2.5 doesn't ship the live request shaper. M3 work.
        raise NotImplementedError(
            "Live request shaping is M3 work — not yet wired in v2.5."
        )


def _live_enabled() -> bool:
    return os.environ.get("OPL_UNIVERSAL_ADAPTER_LIVE") == "1"


# ─── public API ────────────────────────────────────────────────────────────


def from_openapi(schema_url: str, *, dry_run: bool = True) -> AdHocIntegrator:
    """Parse an OpenAPI schema (file path OR http(s) URL) into AdHocIntegrator.

    v2.5: dry_run MUST be True. We never fetch over the network in dry_run.
    Live fetching is M3.
    """
    if not dry_run:
        raise UniversalAdapterLiveNotEnabled(
            "v2.5 from_openapi() requires dry_run=True. Live schema fetch + "
            "execution lands in M3."
        )

    raw = _load_schema(schema_url)
    if raw is None:
        # Schema not reachable in dry-run; return empty adapter for graceful
        # downstream handling.
        return AdHocIntegrator(title="<unreachable>", base_url="", operations=[])

    title = (raw.get("info") or {}).get("title", "<untitled>")
    servers = raw.get("servers") or []
    base_url = servers[0]["url"] if servers else ""
    ops: list[dict[str, Any]] = []
    for path, methods in (raw.get("paths") or {}).items():
        if not isinstance(methods, dict):
            continue
        for method, op_def in methods.items():
            if not isinstance(op_def, dict):
                continue
            ops.append(
                {
                    "operationId": op_def.get("operationId") or f"{method.upper()}_{path}",
                    "path": path,
                    "method": method,
                    "parameters": op_def.get("parameters", []),
                }
            )

    return AdHocIntegrator(title=title, base_url=base_url, operations=ops)


def _load_schema(schema_url: str) -> dict[str, Any] | None:
    """Read schema from a local file in v2.5. Network fetch deferred to M3."""
    parsed = urlparse(schema_url)
    if parsed.scheme in ("http", "https"):
        # v2.5 dry-run: refuse to fetch over network so unit tests are
        # hermetic. Caller should download + pass a local path.
        return None
    path = Path(schema_url)
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml

            return yaml.safe_load(text)
        except Exception:  # pragma: no cover
            return None


__all__ = [
    "AdHocIntegrator",
    "UniversalAdapterLiveNotEnabled",
    "from_openapi",
]
