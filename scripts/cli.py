#!/usr/bin/env python3
"""Skill-form entry shim. Allows ``python ~/.claude/skills/opl-cancer/scripts/cli.py …``
to invoke the same CLI as the installed ``opl-cancer`` entry-point.

Why this file exists: when OPL is installed via ``npx skills add CancerDAO/opl-cancer-skill``
the user gets a directory at ``~/.claude/skills/opl-cancer/`` but the Python package
under ``src/opl_cancer/`` may not yet be on ``sys.path``. This shim:

  1. Inserts the repo's ``src/`` onto ``sys.path`` if not already importable.
  2. Delegates to ``opl_cancer.cli:main``.

If ``opl_cancer`` is already pip-installed (editable or wheel), the shim is a
zero-cost no-op.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"

try:
    import opl_cancer  # noqa: F401
except ImportError:
    if SRC.exists() and str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))
    try:
        import opl_cancer  # noqa: F401
    except ImportError:
        sys.stderr.write(
            "[opl-cancer] Python package not importable. Install once:\n"
            f"    pip install -e {REPO_ROOT}\n"
        )
        sys.exit(3)

from opl_cancer.cli import main

if __name__ == "__main__":
    main()
