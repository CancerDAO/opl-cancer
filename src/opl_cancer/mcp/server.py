"""Optional MCP server for OPL deterministic harness tools.

The server contains no LLM calls. It forwards tool invocations to
``opl_cancer.mcp.session_ops`` so Claude Code, Codex, or any MCP-capable host can
use OPL's durable state surfaces without scraping CLI text.
"""
from __future__ import annotations

from typing import Any

from . import session_ops as ops

TOOL_NAMES = (
    "observe",
    "validate",
    "events_list",
    "events_append",
    "checkpoint_read",
    "checkpoint_write",
)

_MISSING_SDK_HINT = (
    "The MCP SDK is not installed. Install it with:\n"
    "    pip install 'opl-cancer[mcp]'\n"
)


def build_server() -> Any:
    """Build a FastMCP server, raising a clear error if the SDK is absent."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised by run()
        raise RuntimeError(_MISSING_SDK_HINT) from exc

    server = FastMCP("opl-cancer")

    @server.tool()
    def observe(patient_dir: str, run_id: str) -> dict[str, Any]:
        """Read-only projection of run state; never executes a wave."""
        return ops.observe(patient_dir, run_id)

    @server.tool()
    def validate(patient_dir: str, run_id: str) -> dict[str, Any]:
        """Read-only invariant check over durable run state."""
        return ops.validate(patient_dir, run_id)

    @server.tool()
    def events_list(
        patient_dir: str,
        run_id: str,
        event_type: str | None = None,
        phase: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """List structured run events."""
        return ops.events_list(
            patient_dir, run_id, event_type=event_type, phase=phase, limit=limit
        )

    @server.tool()
    def events_append(
        patient_dir: str,
        run_id: str,
        event_type: str,
        phase: str | None = None,
        severity: str = "info",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append one structured run event."""
        return ops.events_append(
            patient_dir,
            run_id,
            event_type,
            phase=phase,
            severity=severity,
            source="opl_cancer.mcp.server",
            payload=payload,
        )

    @server.tool()
    def checkpoint_read(patient_dir: str, run_id: str) -> dict[str, Any]:
        """Read the latest resumable checkpoint."""
        return ops.checkpoint_read(patient_dir, run_id)

    @server.tool()
    def checkpoint_write(
        patient_dir: str,
        run_id: str,
        reason: str,
        phase: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Write the latest resumable checkpoint."""
        return ops.checkpoint_write(
            patient_dir, run_id, reason=reason, phase=phase, payload=payload
        )

    return server


def run() -> None:
    """Run the MCP server over stdio."""
    build_server().run()
