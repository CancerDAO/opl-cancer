"""P2-T8: HypothesisGenerator — 4 strategies + meta-critique injection."""
from __future__ import annotations

import pytest

from opl_cancer._llm_contract import LLMRequest, LLMResponse
from opl_cancer.memory.schemas import ClaimLayer
from opl_cancer.orchestrator.generation import STRATEGIES, HypothesisGenerator


class _FakeClient:
    provider = "fake"

    def __init__(self, content: str) -> None:
        self.content = content
        self.last_request: LLMRequest | None = None

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.last_request = request
        return LLMResponse(content=self.content, model=request.model)


_GOOD_JSON = (
    '{"text": "WNT inhibitor combined with ICI in HBV+ HCC.",'
    ' "rationale": "Mechanistic link via β-catenin.",'
    ' "evidence_refs": [{"type":"pmid","id":"38219045"}]}'
)


async def test_generate_literature_gap() -> None:
    client = _FakeClient(content=_GOOD_JSON)
    gen = HypothesisGenerator(client, executor_model_id="claude-opus-4-7")
    h = await gen.generate("literature_gap", patient_context={"cancer": "HCC"})
    assert h.generation_strategy == "literature_gap"
    assert h.claim_layer == ClaimLayer.SPECULATIVE  # founder-mode default
    assert h.text.startswith("WNT")
    assert h.evidence_refs[0]["id"] == "38219045"


async def test_generate_all_strategies() -> None:
    client = _FakeClient(content=_GOOD_JSON)
    gen = HypothesisGenerator(client, executor_model_id="claude-opus-4-7")
    for s in STRATEGIES:
        h = await gen.generate(s, patient_context={})
        assert h.generation_strategy == s


async def test_generate_invalid_strategy_raises() -> None:
    client = _FakeClient(content=_GOOD_JSON)
    gen = HypothesisGenerator(client, executor_model_id="claude-opus-4-7")
    with pytest.raises(ValueError):
        await gen.generate("unknown", patient_context={})  # type: ignore[arg-type]


async def test_generate_meta_critique_in_prompt() -> None:
    client = _FakeClient(content=_GOOD_JSON)
    gen = HypothesisGenerator(client, executor_model_id="claude-opus-4-7")
    await gen.generate(
        "literature_gap",
        patient_context={},
        meta_critique="Address confounding by HBV status",
    )
    assert client.last_request is not None
    body = client.last_request.messages[0]["content"]
    assert "HBV" in body


async def test_generate_experimental_insights_in_prompt() -> None:
    client = _FakeClient(content=_GOOD_JSON)
    gen = HypothesisGenerator(client, executor_model_id="claude-opus-4-7")
    await gen.generate(
        "literature_gap",
        patient_context={},
        experimental_insights="Top hypothesis used WNT pathway",
    )
    assert client.last_request is not None
    body = client.last_request.messages[0]["content"]
    assert "WNT pathway" in body


async def test_generate_non_json_raises() -> None:
    client = _FakeClient(content="garbage")
    gen = HypothesisGenerator(client, executor_model_id="claude-opus-4-7")
    with pytest.raises(ValueError):
        await gen.generate("literature_gap", patient_context={})


# ── C2/ADR-0032: predict-before-you-look — generation emits the pre-data forecast ──

_FORECAST_JSON = (
    '{"text": "WNT inhibitor + ICI in HBV+ HCC.",'
    ' "rationale": "Mechanistic link.",'
    ' "evidence_refs": [],'
    ' "prior_expectation": {"predicted_wave3_result": "WNT-high cluster enriched",'
    ' "confidence_0_1": 0.7}}'
)


async def test_generate_parses_prior_expectation() -> None:
    """The LLM's pre-data forecast (prior_expectation) flows into the Hypothesis
    so the runner can lock it before Wave-3 — the substrate for taste-training."""
    client = _FakeClient(content=_FORECAST_JSON)
    gen = HypothesisGenerator(client, executor_model_id="claude-opus-4-7")
    h = await gen.generate("literature_gap", patient_context={})
    assert h.prior_expectation == {
        "predicted_wave3_result": "WNT-high cluster enriched",
        "confidence_0_1": 0.7,
    }


async def test_generate_tolerates_missing_prior_expectation() -> None:
    """A response that omits a forecast leaves prior_expectation None (the runner
    must never fabricate one — G49 then SKIPs that hypothesis)."""
    client = _FakeClient(content=_GOOD_JSON)  # _GOOD_JSON carries no forecast
    gen = HypothesisGenerator(client, executor_model_id="claude-opus-4-7")
    h = await gen.generate("literature_gap", patient_context={})
    assert h.prior_expectation is None


async def test_generate_prompt_requests_prior_expectation() -> None:
    client = _FakeClient(content=_GOOD_JSON)
    gen = HypothesisGenerator(client, executor_model_id="claude-opus-4-7")
    await gen.generate("literature_gap", patient_context={})
    assert client.last_request is not None
    body = client.last_request.messages[0]["content"]
    assert "prior_expectation" in body
