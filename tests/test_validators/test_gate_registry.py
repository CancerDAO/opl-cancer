"""P0-3: gate registry must list all 27 spec-§7 gates.

Through v1.5.5 only G1-G20 + G22-G24 were registered (23). G21/G25/G26/G27
were defined and re-exported in `gates/__init__.py` but never picked up by
the orchestrator loop because `all_gate_classes()` skipped them.
"""
from __future__ import annotations

import re

from opl_cancer.validators.mechanical_gates import all_gate_classes


def test_registry_returns_all_27_gates() -> None:
    gates = all_gate_classes()
    assert len(gates) == 27, f"expected 27 gates, got {len(gates)}: {[g.__name__ for g in gates]}"


def test_registry_covers_g1_through_g27() -> None:
    names = {g.__name__ for g in all_gate_classes()}
    for n in range(1, 28):
        # at least one gate class must start with G<n><non-digit> (so G1 doesn't match G10)
        pattern = re.compile(rf"^G{n}\D")
        matching = [name for name in names if pattern.match(name)]
        assert matching, f"no class registered for G{n}; have {sorted(names)}"


def test_registry_order_is_canonical_g1_to_g27() -> None:
    """Order matters: run_gates() short-circuits on first blocking gate, so we
    want safety gates (G24 crisis_detection) to run early. Verify the order
    matches the G<n> numbering since that's what spec §7 prescribes."""
    gates = all_gate_classes()
    nums = []
    for g in gates:
        m = re.match(r"^G(\d+)", g.__name__)
        assert m, f"unexpected gate name {g.__name__}"
        nums.append(int(m.group(1)))
    assert nums == sorted(nums), f"gate registry not in G<n> order: {nums}"
