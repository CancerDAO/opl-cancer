#!/usr/bin/env python3
"""Skill-form entry shim — agent-agnostic first-run bootstrap (v2.6.1).

Lets any agent (Claude Code, Codex, Cursor, OpenCode, …) invoke the same CLI as
the installed ``opl-cancer`` entry-point via ``python <skill_dir>/scripts/cli.py …``.

v2.6.1 fix (first-run BLOCKER): the previous shim put ``src/`` on ``sys.path`` so
``import opl_cancer`` succeeded, then immediately did ``from opl_cancer.cli import
main`` — which imports ``click``/``pydantic``/… On a fresh machine those runtime
deps are absent, so the documented Step-0 command crashed with a raw
``ModuleNotFoundError: No module named 'click'`` traceback (and SKILL.md's
"auto-runs pip install" claim was false — the shim only handled a missing
*package*, never missing *deps*).

Now: a single ``_load_main()`` covers BOTH the package and its deps. On any
ImportError the shim attempts ONE bootstrap (``pip install -e <repo>``) unless
disabled, then retries; if it still can't import it exits cleanly (code 3) with an
actionable, copy-pasteable message — never a raw traceback. Set
``OPL_NO_AUTO_BOOTSTRAP=1`` to skip the auto-install and just print the hint.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"


def _load_main():
    """Import opl_cancer.cli:main, putting src/ on the path first.

    Raises ImportError if the package OR any runtime dependency is missing.
    """
    if SRC.exists() and str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))
    from opl_cancer.cli import main  # noqa: F401 — ImportError covers deps too

    return main


def _hint() -> str:
    ver = (
        f"[opl-cancer] This interpreter is Python {sys.version_info.major}."
        f"{sys.version_info.minor}, but OPL requires Python 3.11+. Re-run with a\n"
        "Python 3.11+ interpreter (the package will not install on older Python).\n\n"
        if sys.version_info < (3, 11)
        else ""
    )
    return (
        ver
        + "[opl-cancer] Not ready to run — the Python package and/or its runtime\n"
        "dependencies are not installed in this interpreter.\n\n"
        "Run this ONCE (works on any agent / OS), then re-run your command:\n"
        f'    pip install -e "{REPO_ROOT}"\n\n'
        "After that, the `opl-cancer` command is on your PATH everywhere — you no\n"
        "longer need any file path. (Auto-bootstrap can be disabled with\n"
        "OPL_NO_AUTO_BOOTSTRAP=1.)\n"
    )


def _pip(*args: str) -> bool:
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", *args], check=True, timeout=900
        )
        return True
    except Exception:  # network/proxy/permissions/no-pip
        return False


def _bootstrap() -> bool:
    """Best-effort one-time install of the harness. Never raises.

    Robust across pip versions: old pip cannot do a PEP-660 editable install of a
    pyproject-only (hatchling) project (``editable mode requires a setuptools-based
    build``), so we (1) try to upgrade pip, (2) try editable, (3) fall back to a
    regular (non-editable) install — which works on far more environments and still
    yields a working ``opl-cancer`` entry point + importable package.
    """
    repo = str(REPO_ROOT)
    _pip("install", "--upgrade", "pip", "-q")  # best-effort; ignore result
    if _pip("install", "-e", repo, "-q"):
        return True
    return _pip("install", repo, "-q")  # non-editable fallback


def _resolve_main():
    try:
        return _load_main()
    except ImportError:
        auto = os.environ.get("OPL_NO_AUTO_BOOTSTRAP", "").lower() not in ("1", "true", "yes")
        if auto and _bootstrap():
            try:
                return _load_main()
            except ImportError:
                pass
        sys.stderr.write(_hint())
        sys.exit(3)


if __name__ == "__main__":
    _resolve_main()()
