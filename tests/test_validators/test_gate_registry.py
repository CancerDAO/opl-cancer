"""Gate registry must list all spec-§7 + ADR-0022 gates.

Through v1.5.5 only G1-G20 + G22-G24 were registered (23). G21/G25/G26/G27
were defined and re-exported in `gates/__init__.py` but never picked up by
the orchestrator loop because `all_gate_classes()` skipped them — fixed in
v2.1 P0-3.

v2.2 adds G28 absolute_date (ADR-0022) — closes the v2.1 LLM
"5 weeks → 5 months" failure mode.
"""
from __future__ import annotations

import re

from opl_cancer.validators.mechanical_gates import all_gate_classes


EXPECTED_GATE_COUNT = 28


def test_registry_returns_all_gates() -> None:
    gates = all_gate_classes()
    assert len(gates) == EXPECTED_GATE_COUNT, (
        f"expected {EXPECTED_GATE_COUNT} gates, got {len(gates)}: "
        f"{[g.__name__ for g in gates]}"
    )


def test_registry_covers_g1_through_last() -> None:
    names = {g.__name__ for g in all_gate_classes()}
    for n in range(1, EXPECTED_GATE_COUNT + 1):
        # at least one gate class must start with G<n><non-digit>
        # (so G1 doesn't match G10)
        pattern = re.compile(rf"^G{n}\D")
        matching = [name for name in names if pattern.match(name)]
        assert matching, f"no class registered for G{n}; have {sorted(names)}"


def test_registry_order_is_canonical_g1_to_last() -> None:
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


def test_g28_absolute_date_present() -> None:
    """v2.2 ADR-0022 — G28 must be the new tail-end of the registry."""
    gates = all_gate_classes()
    names = [g.__name__ for g in gates]
    assert "G28AbsoluteDateGate" in names
    # G28 must come after G27 in canonical order
    assert names.index("G28AbsoluteDateGate") > names.index("G27PrivacyScrubGate")
