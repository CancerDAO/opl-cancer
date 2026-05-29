"""v2.6.1 — agent-agnostic portability + first-run regression guards.

Independent review (2026-05-29) found two BLOCKERs for the "seamless across
Claude Code / Codex / Cursor / OpenCode" promise: (1) SKILL.md hardcoded
`~/.claude/skills/opl-cancer/scripts/cli.py` in 12-13 places — every command
dies on a nonexistent path on a non-CC agent; (2) the first-run shim crashed
with a raw `ModuleNotFoundError: click` because it bootstrapped the package path
but not its runtime deps. These tests lock the fixes.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load_shim():
    spec = importlib.util.spec_from_file_location("opl_cli_shim", REPO / "scripts" / "cli.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # safe: _resolve_main only runs under __main__
    return mod


def test_shim_fails_with_actionable_message_not_traceback() -> None:
    mod = _load_shim()
    hint = mod._hint()
    assert "pip install -e" in hint, "shim must tell the user the exact bootstrap command"
    assert "traceback" not in hint.lower()
    # Auto-bootstrap is attempted but disableable + degrades to the hint.
    assert hasattr(mod, "_bootstrap") and hasattr(mod, "_resolve_main")
    src = (REPO / "scripts" / "cli.py").read_text(encoding="utf-8")
    assert "OPL_NO_AUTO_BOOTSTRAP" in src
    assert "sys.exit(3)" in src, "missing deps must exit cleanly (code 3), not raise"


def test_skill_md_has_no_hardcoded_claude_command_paths() -> None:
    text = (REPO / "SKILL.md").read_text(encoding="utf-8")
    assert "python ~/.claude/skills/opl-cancer/scripts/cli.py" not in text, (
        "SKILL.md must not hardcode the ~/.claude path — breaks every step on non-CC agents"
    )
    # Commands must go through the portable console entry point.
    assert "opl-cancer preflight" in text


def test_skill_md_points_to_agent_portability_reference() -> None:
    text = (REPO / "SKILL.md").read_text(encoding="utf-8")
    assert "agent-portability.md" in text


def test_agent_portability_reference_is_complete() -> None:
    p = REPO / "references" / "agent-portability.md"
    assert p.exists(), "references/agent-portability.md must exist (cross-agent contract)"
    t = p.read_text(encoding="utf-8")
    for needle in ("Codex", "Cursor", "OPL_EXECUTOR_PROVIDER", "G13", "<skill_dir>"):
        assert needle in t, f"agent-portability.md missing {needle!r}"


def test_skill_description_frontmatter_is_lean() -> None:
    """The frontmatter description was 3699 chars (over-stuffed → bad triggering).
    Keep it operational/lean."""
    import re

    t = (REPO / "SKILL.md").read_text(encoding="utf-8")
    m = re.search(r"^description:\s*(.+)$", t, re.M)
    assert m, "no description frontmatter"
    assert len(m.group(1)) < 1600, f"description re-bloated ({len(m.group(1))} chars)"
