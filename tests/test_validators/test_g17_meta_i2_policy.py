"""Test G17 meta-analysis I² policy gate."""
from opl_cancer.validators.gates.g17_meta_i2_policy import G17MetaI2PolicyGate
from opl_cancer.validators.mechanical_gates import GateStatus


def test_g17_skip_no_meta() -> None:
    gate = G17MetaI2PolicyGate()
    r = gate.check({})
    assert r.status == GateStatus.SKIP


def test_g17_pass_low_i2_fixed_effects() -> None:
    gate = G17MetaI2PolicyGate()
    claim = {"meta_analysis": {"i_squared": 0.20, "model": "fixed-effects"}}
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g17_fail_high_i2_fixed_model() -> None:
    gate = G17MetaI2PolicyGate()
    claim = {"meta_analysis": {"i_squared": 0.62, "model": "fixed-effects"}}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


def test_g17_pass_high_i2_random_model() -> None:
    gate = G17MetaI2PolicyGate()
    claim = {"meta_analysis": {"i_squared": 0.62, "model": "random-effects"}}
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g17_fail_very_high_i2_missing_marker() -> None:
    gate = G17MetaI2PolicyGate()
    claim = {
        "meta_analysis": {"i_squared": 0.82, "model": "random-effects", "note": "ok"},
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert "高异质性" in r.message or "heterogeneity" in r.message


def test_g17_pass_very_high_i2_with_marker() -> None:
    gate = G17MetaI2PolicyGate()
    claim = {
        "meta_analysis": {
            "i_squared": 82.0,
            "model": "random-effects",
            "warning_marker": "高异质性，池化可疑",
        }
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS
