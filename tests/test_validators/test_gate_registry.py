"""Gate registry must list all spec-§7 + ADR-0022 + ADR-0023 gates.

Through v1.5.5 only G1-G20 + G22-G24 were registered (23). G21/G25/G26/G27
were defined and re-exported in `gates/__init__.py` but never picked up by
the orchestrator loop because `all_gate_classes()` skipped them — fixed in
v2.1 P0-3.

v2.2 adds G28 absolute_date (ADR-0022) — closes the v2.1 LLM
"5 weeks → 5 months" failure mode.

v2.3 adds G29-G33 (ADR-0023) for Wave 6 manuscript invariants:
  G29 manuscript_authorship_disclosed
  G30 claim_pmid_anchored
  G31 figure_reproducible
  G32 data_availability_declared
  G33 n1_design_transparent
"""
from __future__ import annotations

import re

from opl_cancer.validators.mechanical_gates import all_gate_classes


EXPECTED_GATE_COUNT = 42  # v2.7.1: G1-G37 + G39-G43 (G38 reserved — see registry)
# Gate numbering may have intentional gaps (G38 reserved: citation-provenance
# completeness is covered by G1/G2/G36 via the delivery gate runner). The
# authoritative set of registered gate numbers:
EXPECTED_GATE_NUMBERS = set(range(1, 38)) | {39, 40, 41, 42, 43}  # 37 + 5 = 42


def test_registry_returns_all_gates() -> None:
    gates = all_gate_classes()
    assert len(gates) == EXPECTED_GATE_COUNT, (
        f"expected {EXPECTED_GATE_COUNT} gates, got {len(gates)}: "
        f"{[g.__name__ for g in gates]}"
    )


def test_registry_covers_expected_gate_numbers() -> None:
    """Every expected gate number has exactly one class; no unexpected gaps."""
    nums: list[int] = []
    for g in all_gate_classes():
        m = re.match(r"^G(\d+)\D", g.__name__)
        assert m, f"unexpected gate name {g.__name__}"
        nums.append(int(m.group(1)))
    assert set(nums) == EXPECTED_GATE_NUMBERS, (
        f"registered gate numbers {sorted(set(nums))} != expected "
        f"{sorted(EXPECTED_GATE_NUMBERS)} (G38 is intentionally reserved)"
    )
    assert len(nums) == len(set(nums)), f"duplicate gate numbers: {sorted(nums)}"


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
    """v2.2 ADR-0022 — G28 must come after G27 in canonical order."""
    gates = all_gate_classes()
    names = [g.__name__ for g in gates]
    assert "G28AbsoluteDateGate" in names
    # G28 must come after G27 in canonical order
    assert names.index("G28AbsoluteDateGate") > names.index("G27PrivacyScrubGate")


def test_g29_through_g33_present() -> None:
    """v2.3 ADR-0023 — G29-G33 (Wave 6 manuscript gates) must register."""
    gates = all_gate_classes()
    names = [g.__name__ for g in gates]
    assert "G29ManuscriptAuthorshipDisclosedGate" in names
    assert "G30ClaimPMIDAnchoredGate" in names
    assert "G31FigureReproducibleGate" in names
    assert "G32DataAvailabilityDeclaredGate" in names
    assert "G33N1DesignTransparentGate" in names
    # And they must come AFTER G28 (canonical order):
    assert names.index("G29ManuscriptAuthorshipDisclosedGate") > names.index(
        "G28AbsoluteDateGate"
    )
    # And G33 follows G29-G32 (no longer the tail — G34-G37 added in v2.7.0).
    assert names.index("G33N1DesignTransparentGate") > names.index(
        "G29ManuscriptAuthorshipDisclosedGate"
    )


def test_g34_through_g37_present() -> None:
    """v2.7.0 ADR-0026 — delivery-integrity gates must register after G33."""
    gates = all_gate_classes()
    names = [g.__name__ for g in gates]
    for cls in (
        "G34DeliveryAttestationGate",
        "G35ClinicalFactProvenanceGate",
        "G36PMIDTopicRelevanceGate",
        "G37ServiceCompletenessGate",
    ):
        assert cls in names, f"{cls} not registered"
    # Canonical order: G34-G37 come after G33.
    assert names.index("G34DeliveryAttestationGate") > names.index(
        "G33N1DesignTransparentGate"
    )


def test_g39_through_g43_reasoning_present() -> None:
    """v2.7.1 ADR-0026 (P1) — reasoning-quality gates register as the new tail."""
    names = [g.__name__ for g in all_gate_classes()]
    for cls in (
        "G39BiomarkerContingencyGate",
        "G40DrugComorbiditySafetyGate",
        "G41SoCCompletenessGate",
        "G42TierDisciplineGate",
        "G43EpistemicSymmetryGate",
    ):
        assert cls in names, f"{cls} not registered"
    # G38 is intentionally NOT present (reserved).
    assert not any(re.match(r"^G38\D", n) for n in names), "G38 is reserved — should be absent"
    # G39-G43 come after G37, and G43 is the new tail.
    assert names.index("G39BiomarkerContingencyGate") > names.index("G37ServiceCompletenessGate")
    assert names[-1] == "G43EpistemicSymmetryGate"
