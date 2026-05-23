"""Hypothesis evolution — 6 strategies. P2-T9.

Lift source: ``open-coscientist/src/coscientist/agents/evolution.py``.

Strategies (Co-Sci §"Evolution agent"):
- combination       — merge two parent hypotheses into a single richer one
- simplification    — strip incidentals from a parent
- extension         — extend a parent further (add mechanism / patient subgroup)
- analogy           — apply parent's mechanism to a structurally similar setting
- resilience        — harden parent against the meta-critique
- outside_box       — radical re-imagining of parent

Output is a child Hypothesis whose ``parent_chain`` is prepended with parent ID.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from opl_cancer.llm.base import LLMClient, LLMRequest
from opl_cancer.memory.schemas import ClaimLayer, GenerationStrategy, Hypothesis


STRATEGIES: tuple[str, ...] = (
    "combination",
    "simplification",
    "extension",
    "analogy",
    "resilience",
    "outside_box",
)


_EVOLVE_PROMPT_TEMPLATE = """You are a hypothesis evolution agent using the **{strategy}** strategy.

Parent hypothesis: {parent_text}
Parent rationale: {parent_rationale}

{sibling_block}

Patient context (JSON): {patient_context}
Meta-critique to address: {meta_critique}

Strategy guidance:
{strategy_guidance}

Founder-mode philosophy: stay speculative; never claim established without PMIDs.

Return strict JSON: {{"text": "<one-sentence hypothesis>", "rationale": "<2-4 sentences>", "evidence_refs": [{{"type": "pmid"|"dataset", "id": "<id>"}}, ...]}}.
"""


_STRATEGY_GUIDANCE: dict[str, str] = {
    "combination": "Merge parent + sibling hypotheses into one richer claim. State the joint mechanism.",
    "simplification": "Strip incidental parts from the parent to expose the testable core.",
    "extension": "Extend the parent — add a downstream mechanism, a new patient subgroup, or a new therapeutic angle.",
    "analogy": "Apply the parent's mechanism to a structurally similar cancer type / drug class. State the analogy.",
    "resilience": "Re-derive the parent so it survives the explicit meta-critique objection.",
    "outside_box": "Radically re-imagine the parent — change one core assumption and follow the implications.",
}


class EvolutionStrategist:
    def __init__(
        self,
        llm_client: LLMClient,
        executor_model_id: str,
        prompt_template: str = _EVOLVE_PROMPT_TEMPLATE,
    ) -> None:
        self.llm_client = llm_client
        self.executor_model_id = executor_model_id
        self.prompt_template = prompt_template

    async def evolve(
        self,
        strategy: str,
        parent: Hypothesis,
        sibling: Hypothesis | None = None,
        context: dict[str, Any] | None = None,
        meta_critique: str = "",
    ) -> Hypothesis:
        if strategy not in STRATEGIES:
            raise ValueError(
                f"unknown evolution strategy {strategy!r}; one of {STRATEGIES}"
            )
        if strategy == "combination" and sibling is None:
            raise ValueError("'combination' requires a sibling hypothesis")
        sibling_block = (
            f"Sibling hypothesis: {sibling.text}\nSibling rationale: {sibling.rationale or '(none)'}\n"
            if sibling
            else ""
        )
        prompt = self.prompt_template.format(
            strategy=strategy,
            parent_text=parent.text,
            parent_rationale=parent.rationale or "(none)",
            sibling_block=sibling_block,
            patient_context=json.dumps(context or {}, ensure_ascii=False)[:2000],
            meta_critique=meta_critique or "(none)",
            strategy_guidance=_STRATEGY_GUIDANCE[strategy],
        )
        req = LLMRequest(
            model=self.executor_model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
        resp = await self.llm_client.complete(req)
        try:
            parsed: dict[str, Any] = json.loads(resp.content)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"EvolutionStrategist: non-JSON: {resp.content[:200]!r}"
            ) from exc
        evidence_refs_raw = parsed.get("evidence_refs", []) or []
        evidence_refs = [e for e in evidence_refs_raw if isinstance(e, dict)]
        new_strategy: GenerationStrategy = f"evolution_{strategy}"  # type: ignore[assignment]
        return Hypothesis(
            id=f"hyp_{uuid.uuid4().hex[:8]}",
            text=str(parsed.get("text", "")).strip() or "(empty)",
            claim_layer=ClaimLayer.SPECULATIVE,
            rationale=str(parsed.get("rationale", "")),
            generation_strategy=new_strategy,
            evidence_refs=evidence_refs,
            parent_chain=[parent.id, *parent.parent_chain],
            meta_critique_inherited=[meta_critique] if meta_critique else [],
        )
