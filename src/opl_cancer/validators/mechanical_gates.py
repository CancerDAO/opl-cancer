"""Mechanical gate framework — no-LLM hard rules. Spec §7.

P0 ships only the framework (Gate abstract base + run_gates dispatcher).
Concrete gates (G1 PMID-existence, G2 quote-match, …) are implemented in P5.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel


class GateStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


class GateResult(BaseModel):
    gate: str
    status: GateStatus
    message: str
    block: bool = False
    evidence: dict[str, Any] = {}


class Gate(ABC):
    """Abstract base for all mechanical gates. Subclass + override check()."""

    name: str
    description: str
    failure_mode_code: str

    @abstractmethod
    def check(self, claim: dict[str, Any]) -> GateResult:
        ...


def run_gates(claim: dict[str, Any], gates: list[Gate]) -> list[GateResult]:
    """Run gates in order. If a gate returns block=True, stop further checks."""
    results: list[GateResult] = []
    for gate in gates:
        r = gate.check(claim)
        results.append(r)
        if r.block:
            break
    return results
