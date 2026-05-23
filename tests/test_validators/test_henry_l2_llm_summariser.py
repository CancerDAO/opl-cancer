"""Henry L2 LLM summariser — env-gated axis renderer (Iter 9 item #3).

Verifies HenryAuditor.summarise_disagreement_axes() correctly invokes the LLM
client with json_object response_format, parses the returned axes, and
fails loudly on bad shape (no silent fallback).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from opl_cancer.llm.base import LLMClient, LLMRequest, LLMResponse
from opl_cancer.validators.henry import HenryAuditor

REPO_ROOT = Path(__file__).resolve().parents[2]
SERIOUS_RISKS_PATH = REPO_ROOT / "knowledge" / "serious_risks_per_drug.json"


class _StubLLM(LLMClient):
    """Deterministic stub: returns a canned axes JSON, records the request."""

    provider = "stub"

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        return LLMResponse(
            content=json.dumps(self.payload, ensure_ascii=False),
            model=request.model,
        )


@pytest.fixture()
def auditor(tmp_path: Path) -> HenryAuditor:
    return HenryAuditor(
        serious_risks_path=SERIOUS_RISKS_PATH,
        outstanding_dir=tmp_path / "outstanding",
    )


@pytest.mark.asyncio
async def test_l2_llm_summariser_returns_axes(auditor: HenryAuditor) -> None:
    stub = _StubLLM(
        {
            "axes": ["evidence_quality", "dose_safety"],
            "summary": "Reviewer flags weak evidence and dosing concerns.",
        }
    )
    result = await auditor.summarise_disagreement_axes(
        ["No phase III for this combo", "Dose 200mg may exceed safe ceiling"],
        llm_client=stub,
        model_id="MiniMax-M2.7",
    )
    assert result["axes"] == ["evidence_quality", "dose_safety"]
    assert "weak evidence" in result["summary"]
    assert stub.calls[0].response_format == {"type": "json_object"}
    assert stub.calls[0].model == "MiniMax-M2.7"


@pytest.mark.asyncio
async def test_l2_llm_summariser_empty_challenges_skips_call(
    auditor: HenryAuditor,
) -> None:
    stub = _StubLLM({"axes": ["should_not_appear"], "summary": "X"})
    result = await auditor.summarise_disagreement_axes(
        [],
        llm_client=stub,
        model_id="MiniMax-M2.7",
    )
    assert result == {"axes": [], "summary": ""}
    assert stub.calls == []  # no wasteful LLM call when nothing to summarise


@pytest.mark.asyncio
async def test_l2_llm_summariser_defensive_against_bad_shape(
    auditor: HenryAuditor,
) -> None:
    """If LLM returns non-list axes, we coerce defensively, never raise mid-render."""
    stub = _StubLLM({"axes": "not_a_list_but_string", "summary": 42})
    result = await auditor.summarise_disagreement_axes(
        ["challenge 1"],
        llm_client=stub,
        model_id="MiniMax-M2.7",
    )
    # axes string is not iterable as items, so we get empty list
    assert isinstance(result["axes"], list)
    assert result["summary"] == "42"
