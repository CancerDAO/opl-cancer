"""G11: Integrator no-silent-fallback (spec §7 G11 / D3).

This is a CONTRACT gate — enforced by tests in test_g11_no_silent_fallback.py
that exercise every integrator with mocked API failure and assert
IntegratorError is raised. Runtime check below verifies a claim does not
carry a `integrator_fallback_used` flag (which would mean a synthesised
or stale value snuck through).
"""
from __future__ import annotations

from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


class G11NoSilentFallbackGate(Gate):
    name = "G11_no_silent_fallback"
    description = "Integrator MUST raise on API failure (verified by contract tests)."
    failure_mode_code = "D3"

    def check(self, claim: dict[str, Any]) -> GateResult:
        # Runtime check: confirm no claim carries a "fallback_used" flag
        if claim.get("integrator_fallback_used"):
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message="claim marked integrator_fallback_used=True; G11 violated",
            )
        return GateResult(
            gate=self.name, status=GateStatus.PASS, message="no fallback flag on claim"
        )
