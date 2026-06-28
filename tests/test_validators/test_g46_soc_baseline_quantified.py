"""G46 — a treatment-line claim that ranks options must carry a tuned SoC baseline.

B1 / ADR-0029. Per the SMTB lesson, a framework can HURT decision-restraint vs a
properly tuned baseline. OPL must state honestly what the current guideline (and
the patient's own oncologist) already offer — with a quantitative anchor — and
make every option beat THAT, not a strawman. G46 BLOCKS a treatment-line claim
that ranks options without a populated, quantified soc_baseline. Verifiable.
"""
from __future__ import annotations

from opl_cancer.validators.gates.g46_soc_baseline_quantified import (
    G46SoCBaselineQuantifiedGate,
)
from opl_cancer.validators.mechanical_gates import GateStatus


def test_skip_when_claim_does_not_rank_options():
    res = G46SoCBaselineQuantifiedGate().check(
        {"claim_id": "c1", "claim_text": "a single observation"}
    )
    assert res.status == GateStatus.SKIP


def test_block_when_options_ranked_but_no_soc_baseline():
    res = G46SoCBaselineQuantifiedGate().check(
        {
            "claim_id": "tl1",
            "claim_text": "3L options",
            "options": [{"name": "regimen A"}, {"name": "regimen B"}],
        }
    )
    assert res.status == GateStatus.FAIL
    assert res.block is True


def test_block_when_soc_baseline_lacks_quantitative_anchor():
    res = G46SoCBaselineQuantifiedGate().check(
        {
            "claim_id": "tl1",
            "claim_text": "3L options",
            "options": [{"name": "regimen A"}, {"name": "regimen B"}],
            "soc_baseline": {"best_option": "FTD/TPI + bev"},  # no HR/PFS/OS/PMID
        }
    )
    assert res.status == GateStatus.FAIL
    assert res.block is True


def test_pass_when_soc_baseline_quantified():
    res = G46SoCBaselineQuantifiedGate().check(
        {
            "claim_id": "tl1",
            "claim_text": "3L options",
            "options": [{"name": "regimen A", "delta_vs_baseline": "+1.2mo PFS"}],
            "soc_baseline": {
                "best_option": "trifluridine/tipiracil + bevacizumab",
                "expected_os_months": 10.8,
                "hr": 0.61,
                "ci": "0.49-0.77",
                "pmid": "37133585",
            },
        }
    )
    assert res.status == GateStatus.PASS
