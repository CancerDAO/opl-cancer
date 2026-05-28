"""v2.1 P0-#4: goal-keyword → expert routing.

Reads ``goal_router.yaml`` at import time. ``route_goal(text)`` returns a
deduplicated list of expert names whose keyword pattern matched the goal.

ADR-0021 invariant: this *supplements* the comorbid_planner trigger
expansion — both run. A pattern hit only ADDS experts; it never removes
ones already chosen by the baseline skeleton.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

import yaml

_CONFIG_PATH = Path(__file__).parent / "goal_router.yaml"

with _CONFIG_PATH.open() as f:
    _CONFIG = yaml.safe_load(f)

# Compile once at import time. Each entry is (compiled_pattern, [experts]).
_COMPILED: list[tuple[re.Pattern[str], list[str]]] = [
    (re.compile(pattern, re.IGNORECASE), list(experts))
    for pattern, experts in _CONFIG["keywords"].items()
]


def route_goal(goal_text: str) -> List[str]:
    """Return deduplicated list of experts whose pattern matched ``goal_text``.

    Order preserved by first-match-first-add.
    """
    seen: list[str] = []
    if not goal_text:
        return seen
    for pat, experts in _COMPILED:
        if pat.search(goal_text):
            for e in experts:
                if e not in seen:
                    seen.append(e)
    return seen


def fired_patterns(goal_text: str) -> List[str]:
    """Return the list of regex patterns that fired on ``goal_text``.

    Used by the planner to surface which keyword rules pulled which experts.
    """
    if not goal_text:
        return []
    return [pat.pattern for pat, _ in _COMPILED if pat.search(goal_text)]
