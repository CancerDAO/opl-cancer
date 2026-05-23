"""P2-T9: EvolutionStrategist — 6 strategies + parent_chain."""
from __future__ import annotations

import pytest

from opl_cancer.llm.base import LLMRequest, LLMResponse
from opl_cancer.memory.schemas import Hypothesis
from opl_cancer.orchestrator.evolution import STRATEGIES, EvolutionStrategist


class _FakeClient:
    provider = "fake"

    def __init__(self, content: str) -> None:
        self.content = content
        self.last_request: LLMRequest | None = None

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.last_request = request
        return LLMResponse(content=self.content, model=request.model)


_OK = '{"text":"evolved hypothesis","rationale":"r","evidence_refs":[]}'


async def test_evolve_extension_preserves_parent_chain() -> None:
    parent = Hypothesis(id="hyp_p", text="parent", parent_chain=["hyp_grandparent"])
    client = _FakeClient(content=_OK)
    ev = EvolutionStrategist(client, executor_model_id="claude-opus-4-7")
    child = await ev.evolve("extension", parent)
    assert child.parent_chain == ["hyp_p", "hyp_grandparent"]
    assert child.generation_strategy == "evolution_extension"


async def test_evolve_combination_requires_sibling() -> None:
    parent = Hypothesis(id="hyp_p", text="parent")
    client = _FakeClient(content=_OK)
    ev = EvolutionStrategist(client, executor_model_id="claude-opus-4-7")
    with pytest.raises(ValueError, match="sibling"):
        await ev.evolve("combination", parent)


async def test_evolve_combination_with_sibling() -> None:
    parent = Hypothesis(id="hyp_p", text="parent")
    sibling = Hypothesis(id="hyp_s", text="sibling")
    client = _FakeClient(content=_OK)
    ev = EvolutionStrategist(client, executor_model_id="claude-opus-4-7")
    child = await ev.evolve("combination", parent, sibling=sibling)
    assert child.generation_strategy == "evolution_combination"


async def test_evolve_all_strategies() -> None:
    parent = Hypothesis(id="hyp_p", text="parent")
    sibling = Hypothesis(id="hyp_s", text="sibling")
    client = _FakeClient(content=_OK)
    ev = EvolutionStrategist(client, executor_model_id="claude-opus-4-7")
    for s in STRATEGIES:
        kwargs = {"sibling": sibling} if s == "combination" else {}
        child = await ev.evolve(s, parent, **kwargs)  # type: ignore[arg-type]
        assert child.generation_strategy == f"evolution_{s}"


async def test_evolve_unknown_strategy() -> None:
    parent = Hypothesis(id="x", text="t")
    client = _FakeClient(content=_OK)
    ev = EvolutionStrategist(client, executor_model_id="claude-opus-4-7")
    with pytest.raises(ValueError, match="unknown"):
        await ev.evolve("nonsense", parent)


async def test_evolve_inherits_meta_critique() -> None:
    parent = Hypothesis(id="hyp_p", text="parent")
    client = _FakeClient(content=_OK)
    ev = EvolutionStrategist(client, executor_model_id="claude-opus-4-7")
    child = await ev.evolve(
        "resilience", parent, meta_critique="Watch out for HBV confounding"
    )
    assert "HBV" in child.meta_critique_inherited[0]


async def test_evolve_non_json_raises() -> None:
    parent = Hypothesis(id="x", text="t")
    client = _FakeClient(content="not json")
    ev = EvolutionStrategist(client, executor_model_id="claude-opus-4-7")
    with pytest.raises(ValueError):
        await ev.evolve("extension", parent)
