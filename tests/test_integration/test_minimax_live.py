"""MiniMax live integration test (Iter 10 task #1).

Skipped by default. Set MINIMAX_API_KEY in env to run:

    MINIMAX_API_KEY=sk-cp-... PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \\
        pytest tests/test_integration/test_minimax_live.py -m live -v

Per memory:reference_minimax_llm:
- model: MiniMax-M2.7
- endpoint: api.minimaxi.com/v1/chat/completions
- response_format=json_object honoured
- errcode 2056 → LLMQuotaError
"""
from __future__ import annotations

import json
import os

import pytest

from opl_cancer.llm.base import LLMRequest, LLMResponse
from opl_cancer.llm.errors import LLMQuotaError
from opl_cancer.llm.minimax_client import MiniMaxClient

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not os.environ.get("MINIMAX_API_KEY"),
        reason="MINIMAX_API_KEY not set — live MiniMax test skipped",
    ),
]


async def test_minimax_live_simple_json_call() -> None:
    """Real call to MiniMax with json_object response_format."""
    client = MiniMaxClient()
    resp = await client.complete(
        LLMRequest(
            model="MiniMax-M2.7",
            messages=[
                {
                    "role": "user",
                    "content": (
                        'Return JSON: {"hello": "world", "answer": 42}. '
                        "Respond with ONLY that JSON object."
                    ),
                }
            ],
            max_tokens=512,
            response_format={"type": "json_object"},
        )
    )
    assert isinstance(resp, LLMResponse)
    assert resp.model  # populated
    parsed = json.loads(resp.content)
    assert isinstance(parsed, dict)
    # We do not assert exact keys (LLM may vary); only that it's valid JSON.


async def test_minimax_live_max_tokens_ceiling_honoured() -> None:
    """Verify max_tokens default 96K (per memory) is accepted by the endpoint."""
    client = MiniMaxClient()
    resp = await client.complete(
        LLMRequest(
            model="MiniMax-M2.7",
            messages=[{"role": "user", "content": 'Return JSON {"ok": true}.'}],
            max_tokens=96000,
            response_format={"type": "json_object"},
        )
    )
    json.loads(resp.content)  # asserts valid JSON


async def test_minimax_live_errcode_2056_raised_if_quota() -> None:
    """If quota happens to be exhausted, our client surfaces LLMQuotaError.

    This is informational — the test only asserts that IF a quota error
    is raised, it is the typed LLMQuotaError (not a generic exception).
    """
    client = MiniMaxClient()
    try:
        await client.complete(
            LLMRequest(
                model="MiniMax-M2.7",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=64,
                response_format={"type": "json_object"},
            )
        )
    except LLMQuotaError:
        # Expected behaviour when quota hit; test still passes.
        pytest.skip("MiniMax reported quota exhausted (errcode 2056) — expected typed error.")
