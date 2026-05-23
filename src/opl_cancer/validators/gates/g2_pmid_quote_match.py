"""G2: every PMID claim must carry a quote that retrieval-matches in corpus."""
from __future__ import annotations

from typing import Any

from opl_cancer.integrators.paperqa import PaperQA2Integrator

from ..mechanical_gates import Gate, GateResult, GateStatus


class G2PMIDQuoteMatchGate(Gate):
    name = "G2_pmid_quote_match"
    description = "Each PMID's quote must be retrievable via PaperQA2 RAG."
    failure_mode_code = "A2"

    def __init__(self, paperqa: PaperQA2Integrator) -> None:
        self.paperqa = paperqa

    def check(self, claim: dict[str, Any]) -> GateResult:
        raise NotImplementedError("G2 is async; call check_async()")

    async def check_async(self, claim: dict[str, Any]) -> GateResult:
        failures: list[dict[str, Any]] = []
        for e in claim.get("evidence", []):
            if e.get("type") != "pmid":
                continue
            quote = (e.get("quote") or "").strip()
            if not quote:
                failures.append({"pmid": e["id"], "reason": "empty quote"})
                continue
            try:
                hit = await self.paperqa.cached_fetch(f"query:{quote}")
            except Exception as exc:  # noqa: BLE001 — convert to gate fail not raise
                failures.append({"pmid": e["id"], "reason": f"retrieval error: {exc}"})
                continue
            sources = hit.get("sources", []) or []
            retrieved_quote = (hit.get("quote") or "").lower()
            quote_tokens = {w.lower() for w in quote.split() if len(w) > 2}
            retrieved_tokens = {w.lower() for w in retrieved_quote.split() if len(w) > 2}
            overlap = len(quote_tokens & retrieved_tokens)
            if e["id"] not in sources and overlap < max(1, len(quote_tokens) // 3):
                failures.append({"pmid": e["id"], "reason": "quote not found in retrieval"})
        if failures:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=f"{len(failures)} quote-match failures",
                evidence={"failures": failures},
            )
        return GateResult(gate=self.name, status=GateStatus.PASS, message="all quotes matched")
