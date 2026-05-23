"""LLM-driven pairwise hypothesis debate judge. P2-T6.

Lift source: ``open-coscientist/src/coscientist/agents/ranking.py`` `_debate_pair`.

Per spec §6.3:
- Reviewer model (G13) judges the pair — different from hypothesis Executor.
- Returns ``{"winner": "A"/"B"/"draw", "reason": "..."}`` parsed from JSON.
"""
from __future__ import annotations

import json
from typing import Any

from opl_cancer.llm.base import LLMClient, LLMRequest
from opl_cancer.memory.schemas import Hypothesis


_DEFAULT_JUDGE_PROMPT = """You are an impartial scientific judge comparing two hypotheses for a single cancer patient.

Patient context (JSON): {patient_context}

Hypothesis A: {hyp_a_text}
A rationale: {hyp_a_rationale}

Hypothesis B: {hyp_b_text}
B rationale: {hyp_b_rationale}

Inherited meta-critique from prior rounds (may be empty): {meta_critique}

Judge on:
1. Novelty (is the hypothesis world-unknown vs literature already says it?)
2. Plausibility (mechanism + biology consistency)
3. Patient relevance (matches this patient's cancer type / molecular profile)
4. Falsifiability (can it be tested in available datasets / trials?)

Return strict JSON: {{"winner": "A" | "B" | "draw", "reason": "<one paragraph>"}}.
"""


class DebateJudge:
    """LLM-driven pairwise comparator for hypothesis tournaments."""

    def __init__(
        self,
        llm_client: LLMClient,
        reviewer_model_id: str,
        judge_prompt: str = _DEFAULT_JUDGE_PROMPT,
    ) -> None:
        self.llm_client = llm_client
        self.reviewer_model_id = reviewer_model_id
        self.judge_prompt = judge_prompt

    async def judge_pair(
        self,
        hyp_a: Hypothesis,
        hyp_b: Hypothesis,
        context: dict[str, Any] | None = None,
        meta_critique: str = "",
    ) -> dict[str, str]:
        ctx = context or {}
        prompt = self.judge_prompt.format(
            patient_context=json.dumps(ctx, ensure_ascii=False)[:2000],
            hyp_a_text=hyp_a.text,
            hyp_a_rationale=hyp_a.rationale or "(none)",
            hyp_b_text=hyp_b.text,
            hyp_b_rationale=hyp_b.rationale or "(none)",
            meta_critique=meta_critique or "(none)",
        )
        req = LLMRequest(
            model=self.reviewer_model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        resp = await self.llm_client.complete(req)
        try:
            parsed = json.loads(resp.content)
        except json.JSONDecodeError:
            return {"winner": "draw", "reason": "judge returned non-JSON; default to draw"}
        winner = parsed.get("winner", "draw")
        if winner not in ("A", "B", "draw"):
            winner = "draw"
        return {"winner": winner, "reason": str(parsed.get("reason", ""))[:1000]}
