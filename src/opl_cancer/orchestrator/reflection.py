"""Hypothesis reflection — 6 modes. P2-T10.

Lift source: ``open-coscientist/src/coscientist/agents/reflection.py``.

Modes:
- basic               — assumption sanity check
- simulation          — mentally simulate the mechanism
- observation         — what observable would the hypothesis predict?
- deep_verification   — verify each chained claim
- full_review         — comprehensive critique
- falsification       — try hardest to break the hypothesis

Returns ``{"verdict": "passes"|"weakened"|"falsified", "rationale": "..."}``.
"""
from __future__ import annotations

import json
from typing import Any, Literal

from opl_cancer.llm.base import LLMClient, LLMRequest
from opl_cancer.memory.schemas import Hypothesis


MODES: tuple[str, ...] = (
    "basic",
    "simulation",
    "observation",
    "deep_verification",
    "full_review",
    "falsification",
)


ReflectionVerdict = Literal["passes", "weakened", "falsified"]


_REFLECT_PROMPT_TEMPLATE = """You are a reflection agent in **{mode}** mode.

Hypothesis: {text}
Rationale: {rationale}

Patient context (JSON): {context}

Mode guidance:
{mode_guidance}

Return strict JSON: {{"verdict": "passes" | "weakened" | "falsified", "rationale": "<2-4 sentences>"}}.
"""


_MODE_GUIDANCE: dict[str, str] = {
    "basic": "Check the hypothesis for assumption sanity. Are any core premises clearly wrong given the patient's profile?",
    "simulation": "Simulate the proposed mechanism step-by-step. Does each step survive ordinary biology?",
    "observation": "What observable should the hypothesis predict in the patient's data? Is that observable consistent with what's already on the chart?",
    "deep_verification": "Verify each chained claim in the rationale individually. Mark any that fail.",
    "full_review": "Comprehensive critique — novelty / plausibility / patient relevance / falsifiability.",
    "falsification": "Try hardest to break the hypothesis. State the strongest counter-evidence you can produce.",
}


class Reflector:
    def __init__(
        self,
        llm_client: LLMClient,
        reviewer_model_id: str,
        prompt_template: str = _REFLECT_PROMPT_TEMPLATE,
    ) -> None:
        self.llm_client = llm_client
        self.reviewer_model_id = reviewer_model_id
        self.prompt_template = prompt_template

    async def reflect(
        self,
        mode: str,
        hyp: Hypothesis,
        context: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        if mode not in MODES:
            raise ValueError(f"unknown reflection mode {mode!r}; one of {MODES}")
        prompt = self.prompt_template.format(
            mode=mode,
            text=hyp.text,
            rationale=hyp.rationale or "(none)",
            context=json.dumps(context or {}, ensure_ascii=False)[:2000],
            mode_guidance=_MODE_GUIDANCE[mode],
        )
        req = LLMRequest(
            model=self.reviewer_model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            response_format={"type": "json_object"},
        )
        resp = await self.llm_client.complete(req)
        try:
            parsed = json.loads(resp.content)
        except json.JSONDecodeError:
            return {"verdict": "weakened", "rationale": "reflector returned non-JSON"}
        verdict_raw = parsed.get("verdict", "weakened")
        if verdict_raw not in ("passes", "weakened", "falsified"):
            verdict_raw = "weakened"
        return {
            "verdict": verdict_raw,
            "rationale": str(parsed.get("rationale", ""))[:1000],
            "mode": mode,
        }
