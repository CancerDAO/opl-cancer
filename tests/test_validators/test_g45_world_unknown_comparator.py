"""G45 — every world-unknown candidate must carry a fair SoC comparator.

B1 / ADR-0029. The false-hope firewall, mapped onto OPL's telos (separating
true from false hope). A desperate late-line patient currently sees an
Elo-rated speculative candidate with NO statement of the best real option for
their setting — an Elo number next to a novel idea reads as absolute strength.
G45 BLOCKS rendering of any world-unknown candidate whose comparator (the best
world-KNOWN option for the same setting) is absent. Machine-verifiable
(comparator present + non-null), so it is a hard gate.
"""
from __future__ import annotations

from opl_cancer.validators.gates.g45_world_unknown_comparator import (
    G45WorldUnknownComparatorGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


def test_skip_when_not_a_world_unknown_candidate():
    res = G45WorldUnknownComparatorGate().check(
        {"claim_id": "c1", "claim_text": "standard option", "claim_layer": "established"}
    )
    assert res.status == GateStatus.SKIP


def test_block_when_world_unknown_candidate_has_no_comparator():
    res = G45WorldUnknownComparatorGate().check(
        {
            "claim_id": "wu1",
            "claim_text": "MTAP-loss → PRMT5 candidate scaffold",
            "world_unknown_candidate": True,
        }
    )
    assert res.status == GateStatus.FAIL
    assert res.block is True


def test_block_when_comparator_best_option_is_empty():
    res = G45WorldUnknownComparatorGate().check(
        {
            "claim_id": "wu1",
            "claim_text": "novel candidate",
            "world_unknown_candidate": True,
            "world_known_comparator": {"best_world_known_option": "", "pmid": "1"},
        }
    )
    assert res.status == GateStatus.FAIL
    assert res.block is True


def test_pass_when_world_unknown_candidate_carries_fair_comparator():
    res = G45WorldUnknownComparatorGate().check(
        {
            "claim_id": "wu1",
            "claim_text": "novel candidate",
            "world_unknown_candidate": True,
            "world_known_comparator": {
                "best_world_known_option": "trifluridine/tipiracil + bevacizumab (SUNLIGHT)",
                "expected_os_months": 10.8,
                "hr": 0.61,
                "ci": "0.49-0.77",
                "pmid": "37133585",
                "human_efficacy_data_for_candidate": "none",
            },
        }
    )
    assert res.status == GateStatus.PASS
