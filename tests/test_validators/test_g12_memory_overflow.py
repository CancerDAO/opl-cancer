"""Test G12 memory-overflow gate."""
from opl_cancer.validators.gates.g12_memory_overflow import G12MemoryOverflowGate
from opl_cancer.validators.mechanical_gates import GateStatus


def test_g12_skip_no_memory() -> None:
    gate = G12MemoryOverflowGate(context_window=1000)
    r = gate.check({})
    assert r.status == GateStatus.SKIP


def test_g12_pass_within_threshold() -> None:
    gate = G12MemoryOverflowGate(context_window=1000, threshold=0.8)
    claim = {"memory_context": {"snippet": "hello " * 50}}  # ~75 tokens worth
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g12_fail_over_threshold() -> None:
    gate = G12MemoryOverflowGate(context_window=100, threshold=0.8)
    claim = {"memory_context": {"snippet": "lorem ipsum " * 200}}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert r.evidence["estimated_tokens"] > 80


def test_g12_cjk_token_density() -> None:
    gate = G12MemoryOverflowGate(context_window=50, threshold=0.5)
    claim = {"memory_context": "患者既往乳腺癌史" * 5}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL  # 8 chars * 5 = 40 CJK tokens > 25
