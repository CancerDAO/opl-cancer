"""No-orphan CI guard (A1 / E4, ADR-0027).

The audit's dominant finding: OPL's compounding mechanisms were all
*built-but-disconnected* — `save_insight` only called by `withdraw`,
`ingest_prior_runs` never called by any plan/wave runner, etc. — so the
memory/ ledger advertised in SKILL.md was a Potemkin directory and every run
started cold.

This guard fails if a compounding-critical persistence symbol is defined but
not actually *called* from the production deliver/attest/plan path. It is the
mechanical promise that the spine stays wired (and would have caught the
original orphans). It deliberately ignores the symbol's own definition module
and all test files — only a real production caller counts.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

# (symbol, definition-module-to-ignore, globs where a real caller must appear)
CRITICAL_WIRING = [
    (
        "ingest_prior_runs",
        "src/opl_cancer/plan/prior_run_ingestion.py",
        ["src/opl_cancer/cli.py", "src/opl_cancer/plan/*.py", "src/opl_cancer/glue/*.py"],
    ),
    (
        "save_hypothesis",
        "src/opl_cancer/memory/store.py",
        ["src/opl_cancer/glue/*.py", "src/opl_cancer/cli.py"],
    ),
    (
        "save_tournament_round",
        "src/opl_cancer/memory/store.py",
        ["src/opl_cancer/glue/*.py", "src/opl_cancer/cli.py"],
    ),
    (
        "save_insight",
        "src/opl_cancer/memory/store.py",
        ["src/opl_cancer/glue/*.py"],
    ),
    (
        # The persistence module itself must be CALLED by the delivery path,
        # else it is just a new orphan.
        "persist_run_to_ledger",
        "src/opl_cancer/glue/ledger_persist.py",
        ["src/opl_cancer/glue/*.py", "src/opl_cancer/cli.py"],
    ),
    (
        # A2 reality loop must be reachable via the CLI, not a dead module.
        "persist_outcomes",
        "src/opl_cancer/glue/outcome_reconcile.py",
        ["src/opl_cancer/cli.py", "src/opl_cancer/glue/*.py"],
    ),
]


def _production_caller(symbol: str, def_module: str, patterns: list[str]) -> str | None:
    def_path = (REPO / def_module).resolve()
    for pat in patterns:
        for f in REPO.glob(pat):
            if f.resolve() == def_path:
                continue  # the definition itself is not a caller
            try:
                if symbol in f.read_text(encoding="utf-8"):
                    return str(f.relative_to(REPO))
            except (OSError, UnicodeDecodeError):
                continue
    return None


@pytest.mark.parametrize("symbol,def_module,patterns", CRITICAL_WIRING)
def test_compounding_symbol_is_wired_in_production(symbol, def_module, patterns):
    caller = _production_caller(symbol, def_module, patterns)
    assert caller is not None, (
        f"ORPHAN: '{symbol}' is defined in {def_module} but never called from "
        f"production code {patterns}. The compounding spine is only real if "
        f"deliver/attest + the planner actually call it (A1, ADR-0027)."
    )
