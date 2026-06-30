"""Gate-inventory truth — single source of truth for "how many gates, and are
they all actually wired".

The 2026-06-30 audit found three different gate counts circulating in docs
(42 / 54 / 55) while the real number is 58, and that the four delivery-only
gates (G56/57/58/61) live OUTSIDE all_gate_classes() — invoked by direct import
in delivery_gate_runner. This test pins the real inventory so docs can cite a
verifiable number and a future orphan (registered-but-never-called) gate fails
CI.
"""
from __future__ import annotations

import re
from pathlib import Path

import opl_cancer.validators.gates as G
from opl_cancer.validators.mechanical_gates import all_gate_classes

# Gates invoked directly in the delivery path rather than the registry sweep.
# Each MUST be referenced in delivery_gate_runner.py (asserted below).
DELIVERY_ONLY = {"G56", "G57", "G58", "G61"}
# Numbers intentionally not implemented (folded elsewhere / reserved branches).
RESERVED = {38, 44, 59}

REGISTRY_COUNT = 54
TOTAL_IMPLEMENTED = 58  # 54 registry-swept + 4 delivery-only


def _num(name: str) -> int:
    return int(re.match(r"G(\d+)", name).group(1))


def test_registry_count_is_54() -> None:
    assert len(all_gate_classes()) == REGISTRY_COUNT


def test_total_implemented_is_58() -> None:
    reg = {c.__name__ for c in all_gate_classes()}
    exported = {n for n in G.__all__ if re.match(r"G\d+", n)}
    assert reg <= exported, "every registry gate must be exported in __all__"
    assert len(exported) == TOTAL_IMPLEMENTED


def test_delivery_only_gates_are_outside_registry() -> None:
    reg_prefixes = {c.__name__[: len(p)] for c in all_gate_classes() for p in DELIVERY_ONLY}
    reg_names = {c.__name__ for c in all_gate_classes()}
    for p in DELIVERY_ONLY:
        assert not any(n.startswith(p + "Wave") or n.startswith(p + "Value")
                       or n.startswith(p + "SoC") or n.startswith(p + "Jurisdiction")
                       for n in reg_names), f"{p} must be delivery-only, not in registry"


def test_delivery_only_gates_are_actually_invoked() -> None:
    """Anti-orphan: a delivery-only gate that is never called is theatre."""
    runner = Path(__file__).resolve().parents[2] / "src/opl_cancer/glue/delivery_gate_runner.py"
    src = runner.read_text(encoding="utf-8")
    name_for = {
        "G56": "G56ValueSourceBindingGate",
        "G57": "G57SoCFloorPresentGate",
        "G58": "G58JurisdictionAvailabilityGate",
        "G61": "G61Wave3SubstanceGate",
    }
    for p in DELIVERY_ONLY:
        assert name_for[p] in src, f"{p} ({name_for[p]}) not invoked in delivery_gate_runner"


def test_reserved_numbers_are_unused() -> None:
    used = {_num(n) for n in G.__all__ if re.match(r"G\d+", n)}
    for r in RESERVED:
        assert r not in used, f"G{r} is reserved but now implemented — update RESERVED/docs"
