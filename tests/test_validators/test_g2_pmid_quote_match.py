"""Test G2 PMID-quote-match gate."""
from typing import Any, cast

from opl_cancer.integrators.paperqa import PaperQA2Integrator
from opl_cancer.validators.gates.g2_pmid_quote_match import G2PMIDQuoteMatchGate
from opl_cancer.validators.mechanical_gates import GateStatus


class _FakePaperQA:
    family = "F1"
    ttl_seconds = 60

    def __init__(self, *, retrieved_quotes: dict[str, str]) -> None:
        self.retrieved = retrieved_quotes
        self.cache = None

    async def cached_fetch(self, key: str) -> dict[str, Any]:
        text = key.replace("query:", "")
        # naive: if any retrieved quote shares substring with text, "hit"
        for pmid, q in self.retrieved.items():
            if any(token in q.lower() for token in text.lower().split()[:3]):
                return {"quote": q, "sources": [pmid]}
        return {"quote": "", "sources": []}


async def test_g2_pass_when_quote_matches() -> None:
    pqa = _FakePaperQA(
        retrieved_quotes={
            "38219045": "WNT activation correlated with reduced ICI response HR 2.10",
        },
    )
    gate = G2PMIDQuoteMatchGate(paperqa=cast(PaperQA2Integrator, pqa))
    claim = {
        "evidence": [
            {
                "type": "pmid",
                "id": "38219045",
                "quote": "WNT activation correlated with reduced ICI response",
            }
        ]
    }
    r = await gate.check_async(claim)
    assert r.status == GateStatus.PASS


async def test_g2_fail_block_when_quote_missing() -> None:
    pqa = _FakePaperQA(retrieved_quotes={"38219045": "completely different sentence"})
    gate = G2PMIDQuoteMatchGate(paperqa=cast(PaperQA2Integrator, pqa))
    claim = {
        "evidence": [
            {
                "type": "pmid",
                "id": "38219045",
                "quote": "fabricated quote that doesnotmatchatall",
            }
        ]
    }
    r = await gate.check_async(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


async def test_g2_empty_quote_fails() -> None:
    pqa = _FakePaperQA(retrieved_quotes={})
    gate = G2PMIDQuoteMatchGate(paperqa=cast(PaperQA2Integrator, pqa))
    claim = {"evidence": [{"type": "pmid", "id": "1", "quote": ""}]}
    r = await gate.check_async(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
