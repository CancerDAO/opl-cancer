"""Test mechanical gate framework (no-LLM hard rules). Spec §7."""
from opl_cancer.validators.mechanical_gates import (
    Gate, GateResult, GateStatus, run_gates,
)


class _AlwaysPassGate(Gate):
    name = "always_pass"
    description = "test fixture"
    failure_mode_code = "T0"

    def check(self, claim: dict) -> GateResult:
        return GateResult(gate=self.name, status=GateStatus.PASS, message="ok")


class _AlwaysFailGate(Gate):
    name = "always_fail"
    description = "test fixture"
    failure_mode_code = "T1"

    def check(self, claim: dict) -> GateResult:
        return GateResult(gate=self.name, status=GateStatus.FAIL, message="nope")


def test_gate_result_status_enum() -> None:
    r = GateResult(gate="g", status=GateStatus.PASS, message="m")
    assert r.status == GateStatus.PASS


def test_run_gates_collects_all_results() -> None:
    results = run_gates({"claim": "x"}, gates=[_AlwaysPassGate(), _AlwaysFailGate()])
    assert len(results) == 2
    assert results[0].status == GateStatus.PASS
    assert results[1].status == GateStatus.FAIL


def test_run_gates_short_circuits_on_critical_block() -> None:
    class _BlockGate(Gate):
        name = "blocker"
        description = "stops further gates"
        failure_mode_code = "B"

        def check(self, claim: dict) -> GateResult:
            return GateResult(gate=self.name, status=GateStatus.FAIL, message="blocked", block=True)

    class _NeverRunGate(Gate):
        name = "never"
        description = "should not run after blocker"
        failure_mode_code = "N"

        def check(self, claim: dict) -> GateResult:  # pragma: no cover
            raise AssertionError("should not be invoked")

    results = run_gates({"x": 1}, gates=[_BlockGate(), _NeverRunGate()])
    assert len(results) == 1
    assert results[0].gate == "blocker"
