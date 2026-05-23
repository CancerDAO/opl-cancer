"""Hypothesis generation — 4 strategies. P2-T8.

Lift source: ``open-coscientist/src/coscientist/agents/generation.py``.

Strategies (spec §2.4 D2 假设生成):
- literature_gap        — patient profile X exists, no published hypothesis yet
- cross_domain          — combine evidence from non-oncology field (immunology / metabolism)
- novel_mechanism       — propose a previously-unconnected biological mechanism
- feasibility_first     — high-falsifiability hypotheses given available datasets

Each strategy has its own prompt; a meta-critique / EXPERIMENTAL_INSIGHTS
appendage is injected when supplied.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from opl_cancer.llm.base import LLMClient, LLMRequest
from opl_cancer.memory.schemas import ClaimLayer, GenerationStrategy, Hypothesis


STRATEGIES: tuple[GenerationStrategy, ...] = (
    "literature_gap",
    "cross_domain",
    "novel_mechanism",
    "feasibility_first",
)


_GEN_PROMPT_TEMPLATE = """You are a hypothesis generator using the **{strategy}** strategy.

Patient context (JSON): {patient_context}
Integrator evidence (JSON, truncated): {integrator_evidence}
{meta_critique_block}
{experimental_insights_block}

Strategy guidance for {strategy}:
{strategy_guidance}

Founder-mode philosophy: hypotheses are by definition speculative. Label uncertainty
honestly. Do NOT pretend to be established.

Return strict JSON:
{{
  "text": "<one-sentence hypothesis statement>",
  "rationale": "<why this hypothesis given the evidence; 2-4 sentences>",
  "evidence_refs": [{{"type": "pmid"|"dataset"|"knowledge_base", "id": "<id>"}}, ...]
}}.
"""


_STRATEGY_GUIDANCE: dict[str, str] = {
    "literature_gap": "Find a patient-specific clinical/molecular pattern that the literature has NOT addressed. Cite the closest existing PMID and explain the gap.",
    "cross_domain": "Combine evidence from at least one non-oncology field (immunology, metabolism, microbiome, neuroscience, materials science). State the cross-domain bridge.",
    "novel_mechanism": "Propose a biological mechanism connecting two pathways/markers that have not been linked before in this patient's cancer subtype.",
    "feasibility_first": "Prioritise hypotheses that can be tested with publicly available datasets (TCGA / GEO / DepMap). State the validation strategy upfront.",
}


class HypothesisGenerator:
    def __init__(
        self,
        llm_client: LLMClient,
        executor_model_id: str,
        prompt_template: str = _GEN_PROMPT_TEMPLATE,
    ) -> None:
        self.llm_client = llm_client
        self.executor_model_id = executor_model_id
        self.prompt_template = prompt_template

    async def generate(
        self,
        strategy: GenerationStrategy,
        patient_context: dict[str, Any],
        integrator_evidence: dict[str, Any] | None = None,
        meta_critique: str = "",
        experimental_insights: str = "",
    ) -> Hypothesis:
        if strategy not in STRATEGIES:
            raise ValueError(
                f"unknown generation strategy {strategy!r}; one of {STRATEGIES}"
            )
        meta_block = (
            f"Prior round meta-critique to address: {meta_critique}\n"
            if meta_critique
            else ""
        )
        exp_block = (
            f"Experimental insights from prior round: {experimental_insights}\n"
            if experimental_insights
            else ""
        )
        prompt = self.prompt_template.format(
            strategy=strategy,
            patient_context=json.dumps(patient_context, ensure_ascii=False)[:3000],
            integrator_evidence=json.dumps(integrator_evidence or {}, ensure_ascii=False)[:3000],
            meta_critique_block=meta_block,
            experimental_insights_block=exp_block,
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
                f"HypothesisGenerator: non-JSON response: {resp.content[:200]!r}"
            ) from exc
        evidence_refs_raw = parsed.get("evidence_refs", []) or []
        evidence_refs = [e for e in evidence_refs_raw if isinstance(e, dict)]
        return Hypothesis(
            id=f"hyp_{uuid.uuid4().hex[:8]}",
            text=str(parsed.get("text", "")).strip() or "(empty)",
            claim_layer=ClaimLayer.SPECULATIVE,
            rationale=str(parsed.get("rationale", "")),
            generation_strategy=strategy,
            evidence_refs=evidence_refs,
            meta_critique_inherited=[meta_critique] if meta_critique else [],
        )
