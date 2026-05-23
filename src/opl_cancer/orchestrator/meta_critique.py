"""Meta-critique aggregator. P2-T7.

Lift source: ``open-coscientist/src/coscientist/agents/meta_review.py``.

After each tournament round, a single LLM call synthesises round outcomes into
a one-paragraph meta-critique, which is appended to the next round's
Generation / Debate prompts.
"""
from __future__ import annotations

import json
from typing import Any

from opl_cancer.llm.base import LLMClient, LLMRequest
from opl_cancer.memory.schemas import Hypothesis


_DEFAULT_META_PROMPT = """You are the meta-reviewer of a hypothesis tournament round.

Round outcomes (winner/reason per pair): {outcomes_json}
Current hypotheses (id + text + elo): {hyps_json}

Synthesise a SINGLE paragraph (<= 6 sentences) capturing:
- What kinds of weakness / blind-spot the round surfaced
- Which evidence buckets were under-used
- One direction the next round's hypothesis generation should explore

Return strict JSON: {{"meta_critique": "<paragraph>"}}.
"""


class MetaCritiqueAggregator:
    def __init__(
        self,
        llm_client: LLMClient,
        reviewer_model_id: str,
        prompt: str = _DEFAULT_META_PROMPT,
    ) -> None:
        self.llm_client = llm_client
        self.reviewer_model_id = reviewer_model_id
        self.prompt = prompt

    async def aggregate(
        self,
        round_outcomes: list[dict[str, str]],
        hypotheses: list[Hypothesis],
    ) -> str:
        hyps_payload = [
            {"id": h.id, "text": h.text[:200], "elo": h.elo_rating} for h in hypotheses
        ]
        prompt = self.prompt.format(
            outcomes_json=json.dumps(round_outcomes, ensure_ascii=False),
            hyps_json=json.dumps(hyps_payload, ensure_ascii=False),
        )
        req = LLMRequest(
            model=self.reviewer_model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            response_format={"type": "json_object"},
        )
        resp = await self.llm_client.complete(req)
        try:
            parsed: dict[str, Any] = json.loads(resp.content)
            return str(parsed.get("meta_critique", ""))[:2000]
        except json.JSONDecodeError:
            return ""
