"""G56 value-source binding (伪精度 gate) — negative + positive coverage.

The 2026-06-30 adversarial review found G56 read claim['claim_text'] while the
real pipeline emits the prose under 'text', so G56 SKIPped every real claim —
the block path was dead. These tests pin the field-reading fix AND the actual
block behaviour (an efficacy number cited to a PMID that lacks it BLOCKS).
"""
from __future__ import annotations

from typing import Any

import pytest

from opl_cancer.validators.gates import G56ValueSourceBindingGate


class _FakePubMed:
    """Returns a fixed abstract per PMID; raises for unknown (mirrors live)."""

    def __init__(self, records: dict[str, str]) -> None:
        self._records = records

    async def cached_fetch(self, key: str) -> dict[str, Any]:
        pmid = key.split(":", 1)[1] if ":" in key else key
        if pmid not in self._records:
            from opl_cancer.integrators.base import IntegratorError
            raise IntegratorError(f"no record for {pmid}")
        return {"title": "", "abstract": self._records[pmid], "journal": ""}


@pytest.mark.asyncio
async def test_real_claim_uses_text_field_and_blocks_misbound_number() -> None:
    # fabricated HR 0.49 cited to a PMID whose abstract says HR 0.31 → BLOCK.
    # The prose lives in 'text' (canonical wave-1 record), NOT 'claim_text'.
    gate = G56ValueSourceBindingGate(_FakePubMed({"30000001": "Adagrasib HR 0.31 in cohort."}))
    r = await gate.check_async({
        "text": "Adagrasib gave median PFS with HR 0.49 in this setting.",
        "evidence": [{"type": "pmid", "id": "30000001"}],
    })
    assert r.status.value == "fail"
    assert r.block is True


@pytest.mark.asyncio
async def test_real_claim_passes_when_number_present_in_abstract() -> None:
    gate = G56ValueSourceBindingGate(_FakePubMed({"30000002": "Median PFS HR 0.49 (95% CI 0.31-0.70)."}))
    r = await gate.check_async({
        "text": "Reported HR 0.49 for the regimen.",
        "evidence": [{"type": "pmid", "id": "30000002"}],
    })
    assert r.status.value in ("pass", "skip")
    assert r.block is False


@pytest.mark.asyncio
async def test_point_estimate_does_not_bind_to_ci_bound() -> None:
    # fabricated HR 0.49 where 0.49 appears ONLY as a CI bound in the abstract
    # (true point estimate is 0.31) → must BLOCK, not pass on the bound.
    gate = G56ValueSourceBindingGate(
        _FakePubMed({"30000004": "Overall survival HR 0.31 (95% CI 0.20-0.49)."})
    )
    r = await gate.check_async({
        "text": "Reported HR 0.49 for the regimen.",
        "evidence": [{"type": "pmid", "id": "30000004"}],
    })
    assert r.status.value == "fail"
    assert r.block is True


@pytest.mark.asyncio
async def test_combined_paren_ci_bound_blocks() -> None:
    # "(HR 0.49, 95% CI 0.31-0.70)" — fabricated HR 0.31 (a CI bound) → BLOCK.
    gate = G56ValueSourceBindingGate(
        _FakePubMed({"30000005": "Benefit (HR 0.49, 95% CI 0.31-0.70) was seen."})
    )
    r = await gate.check_async({
        "text": "Reported HR 0.31 for the regimen.",
        "evidence": [{"type": "pmid", "id": "30000005"}],
    })
    assert r.status.value == "fail" and r.block is True


@pytest.mark.asyncio
async def test_no_paren_ci_bound_blocks() -> None:
    # "95% CI 0.20 to 0.49" with no parens — fabricated HR 0.49 → BLOCK.
    gate = G56ValueSourceBindingGate(
        _FakePubMed({"30000006": "Hazard ratio favorable, 95% CI 0.20 to 0.49 overall."})
    )
    r = await gate.check_async({
        "text": "Reported HR 0.49.",
        "evidence": [{"type": "pmid", "id": "30000006"}],
    })
    assert r.status.value == "fail" and r.block is True


@pytest.mark.asyncio
async def test_point_estimate_in_combined_paren_passes() -> None:
    # legit HR 0.49 reported only inside a combined paren must NOT be over-blocked.
    gate = G56ValueSourceBindingGate(
        _FakePubMed({"30000007": "Outcome (95% CI 0.31 to 0.70, p=0.001, HR 0.49)."})
    )
    r = await gate.check_async({
        "text": "Reported HR 0.49.",
        "evidence": [{"type": "pmid", "id": "30000007"}],
    })
    assert r.block is False


@pytest.mark.asyncio
async def test_number_in_text_field_not_shadowed_by_claim_text() -> None:
    # field-shadow exploit: claim_text is number-free but the shipped `text` has
    # the fabricated number → must still be bound-checked and BLOCK.
    gate = G56ValueSourceBindingGate(_FakePubMed({"30000008": "HR 0.31 vs control."}))
    r = await gate.check_async({
        "claim_text": "a favorable hazard ratio was observed",
        "text": "HR 0.49 vs control",
        "evidence": [{"type": "pmid", "id": "30000008"}],
    })
    assert r.status.value == "fail" and r.block is True


@pytest.mark.asyncio
async def test_no_efficacy_number_skips() -> None:
    gate = G56ValueSourceBindingGate(_FakePubMed({"30000003": "irrelevant"}))
    r = await gate.check_async({
        "text": "The drug is an option to discuss with your oncologist.",
        "evidence": [{"type": "pmid", "id": "30000003"}],
    })
    assert r.status.value == "skip"
