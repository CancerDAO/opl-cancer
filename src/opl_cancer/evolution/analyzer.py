"""EvolutionAnalyzer — red-team prompt over a scrubbed TraceDigest.

ADR-0020 §What we add #9. Distinct from main medical agent prompts; framed
as "your job is to detect when OPL might be silently weakening its own
safety or grounding". Configurable model pool via models.yaml
``evolution_analyzer_pool``.

Outputs ``EvolutionCandidates`` (proposals + summary). Falls back to a
deterministic heuristic path when LLM unreachable (no silent degradation —
``used_heuristic_fallback`` flag is recorded explicitly).
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

from .invariant_gate import apply_gate
from .models import (
    EvolutionCandidates,
    EvolutionProposal,
    TraceDigest,
)


RED_TEAM_SYSTEM_PROMPT = """You are the **Evolution Analyzer** for OPL for Cancer.

Your role is FUNDAMENTALLY DIFFERENT from the medical agents you are
reviewing. You are not a clinician. You are not synthesising new medical
content. You are a system-design red-team auditor.

Your single job: read a scrubbed TraceDigest of one completed OPL run and
identify SPECIFIC, LIMITED proposals that would help OPL do better on the
NEXT (different) patient — without weakening any safety surface.

Hard rules:
1. NEVER propose patches that weaken Henry L3/L4 acknowledgment
   requirements, G7 imperative-free voice, G13 reviewer model split,
   the canonical persona prefix, claim_layer enforcement, or
   RetractionDB grounding. The InvariantGate downstream will block such
   patches; flagging them in your output is wasted work.
2. NEVER propose to relax citation requirements. NEVER propose to make
   patient-facing language MORE directive.
3. SKILL ADDITIONS must include a `clinical_anchor` field citing a
   CSCO / NCCN / NCT / PMID reference. Skill proposals lacking this are
   auto-rejected — don't waste a proposal slot on one.
4. TOOL PROPOSALS are review-only; describe what the tool would do, do
   not propose to enable it.
5. Concrete patches preferred over abstract advice. A diff-shaped
   "add `target_synergy_emergent` strategy slot to Wave 2 prompt" beats
   "improve Wave 2 hypothesis quality".
6. Limit total proposals to 5. Quality > quantity.

Return strict JSON:
{
  "analysis_summary": "<2-3 sentences on what the run did well + what gap a
    DIFFERENT patient would also hit>",
  "proposals": [
    {
      "kind": "prompt_patch | skill_addition | tool_proposal",
      "summary": "<1 sentence>",
      "rationale": "<2-4 sentences, MUST cite which TraceDigest field
        triggered this>",
      "target_path": "<file path the patch would apply to, or empty for
        tool_proposal>",
      "proposed_diff": "<unified diff for prompt_patch; SMILES/code/SKILL
        markdown for others>",
      "clinical_anchor": "<MANDATORY for skill_addition; empty OK otherwise>"
    }
  ]
}
"""


class LLMClientProtocol(Protocol):
    async def complete(self, request: Any) -> Any: ...


@dataclass
class EvolutionAnalyzer:
    """Run a red-team analyzer pass over a scrubbed digest.

    Either ``llm_client`` is provided (real LLM call) or the heuristic
    fallback is used. ``model_id`` records which model produced the output
    in the EvolutionCandidates audit trail.
    """

    llm_client: Any | None = None
    model_id: str = "heuristic_fallback"

    async def analyze(
        self,
        digest: TraceDigest,
        iter_n: int = 1,
    ) -> EvolutionCandidates:
        if not digest.is_scrubbed():
            raise ValueError(
                "Evolution analyzer refuses unscrubbed digest — "
                "must run scrubber.scrub(digest) first per ADR-0020 #8."
            )

        if self.llm_client is None:
            return self._heuristic(digest, iter_n=iter_n)

        try:
            return await self._llm_call(digest, iter_n=iter_n)
        except Exception as exc:  # noqa: BLE001 — analyzer must not crash run
            fallback = self._heuristic(digest, iter_n=iter_n)
            fallback.analysis_summary = (
                f"LLM analyzer failed ({type(exc).__name__}); "
                f"heuristic fallback used. {fallback.analysis_summary}"
            )
            fallback.used_heuristic_fallback = True
            return fallback

    # ---- LLM path ----

    async def _llm_call(
        self,
        digest: TraceDigest,
        iter_n: int,
    ) -> EvolutionCandidates:
        from opl_cancer.llm.base import LLMRequest

        prompt = (
            f"# Scrubbed TraceDigest (run {digest.run_id})\n\n"
            f"```json\n{digest.model_dump_json(indent=2)[:80_000]}\n```\n\n"
            f"Apply your role per the system prompt and return JSON."
        )
        req = LLMRequest(
            model=self.model_id,
            messages=[{"role": "user", "content": prompt}],
            system=RED_TEAM_SYSTEM_PROMPT,
            max_tokens=8192,
            response_format={"type": "json_object"},
        )
        resp = await self.llm_client.complete(req)
        parsed = self._safe_parse(resp.content)
        return self._materialise(parsed, iter_n=iter_n, model_id=self.model_id)

    @staticmethod
    def _safe_parse(content: str) -> dict[str, Any]:
        # Tolerate code-fence wrapping
        m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", content, re.DOTALL)
        text = m.group(1) if m else content.strip()
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
        return {"analysis_summary": "(parse failure)", "proposals": []}

    @staticmethod
    def _materialise(
        parsed: dict[str, Any],
        iter_n: int,
        model_id: str,
    ) -> EvolutionCandidates:
        proposals: list[EvolutionProposal] = []
        for raw in parsed.get("proposals") or []:
            if not isinstance(raw, dict):
                continue
            kind = raw.get("kind") or "prompt_patch"
            if kind not in {"prompt_patch", "skill_addition", "tool_proposal"}:
                continue
            p = EvolutionProposal(
                proposal_id=f"p{uuid.uuid4().hex[:6]}",
                kind=kind,  # type: ignore[arg-type]
                summary=str(raw.get("summary", ""))[:300],
                rationale=str(raw.get("rationale", ""))[:1500],
                proposed_diff=str(raw.get("proposed_diff", ""))[:8000],
                target_path=str(raw.get("target_path", ""))[:300],
                clinical_anchor=str(raw.get("clinical_anchor", ""))[:300],
                iter_n=iter_n,
            )
            p = apply_gate(p)
            proposals.append(p)
            if len(proposals) >= 5:
                break
        return EvolutionCandidates(
            iter_n=iter_n,
            proposals=proposals,
            analysis_summary=str(parsed.get("analysis_summary", ""))[:1000],
            analyzer_model=model_id,
            used_heuristic_fallback=False,
        )

    # ---- Heuristic fallback ----

    def _heuristic(self, digest: TraceDigest, iter_n: int) -> EvolutionCandidates:
        """Deterministic rule-based proposals from TraceDigest.

        Used when LLM client is None OR the LLM call failed. Outputs at most
        3 narrow proposals based on observable patterns.
        """
        proposals: list[EvolutionProposal] = []
        strats = {h.strategy: h for h in digest.hypothesis_strategies}

        if "target_synergy_emergent" not in strats:
            p = EvolutionProposal(
                proposal_id=f"p{uuid.uuid4().hex[:6]}",
                kind="prompt_patch",
                summary="Wave 2 produced no target_synergy_emergent hypothesis — surface this gap to Aviv/Maya next run",
                rationale=(
                    "TraceDigest.hypothesis_strategies has no entry for "
                    "target_synergy_emergent (Maya's signature output). Suggests "
                    "either Maya was not dispatched or her prompt failed to "
                    "produce the strategy. Heuristic action: add an "
                    "explicit reminder to the planner that Maya should be "
                    "dispatched when patient has ≥2 actionable variants."
                ),
                target_path="prompts/pi/intent_parser.md",
                proposed_diff=(
                    "--- a/prompts/pi/intent_parser.md\n"
                    "+++ b/prompts/pi/intent_parser.md\n"
                    "@@ -X,Y +X,Y+1 @@\n"
                    "+- When patient profile shows ≥2 actionable molecular "
                    "alterations, include Maya in the dispatch list with task "
                    "'target_synergy_emergent'. (ADR-0010 §5)\n"
                ),
                iter_n=iter_n,
            )
            proposals.append(apply_gate(p))

        if "undrugged_target_design" not in strats:
            p = EvolutionProposal(
                proposal_id=f"p{uuid.uuid4().hex[:6]}",
                kind="prompt_patch",
                summary="Wave 2 produced no undrugged_target_design hypothesis — flag Julius dispatch condition",
                rationale=(
                    "TraceDigest.hypothesis_strategies has no entry for "
                    "undrugged_target_design (Julius's signature output). When the "
                    "patient profile contains an actionable target with no FDA "
                    "drug, Julius should be dispatched."
                ),
                target_path="prompts/pi/intent_parser.md",
                proposed_diff=(
                    "--- a/prompts/pi/intent_parser.md\n"
                    "+++ b/prompts/pi/intent_parser.md\n"
                    "@@ -X,Y +X,Y+1 @@\n"
                    "+- When patient profile includes an undrugged actionable "
                    "target (e.g. MTAP-loss, RB1-loss, undruggable splicing "
                    "variant), include Julius in the dispatch list. (ADR-0010 §5)\n"
                ),
                iter_n=iter_n,
            )
            proposals.append(apply_gate(p))

        if digest.novelty_gate_stats.get("world_unknown_section_present", 0) == 0:
            p = EvolutionProposal(
                proposal_id=f"p{uuid.uuid4().hex[:6]}",
                kind="prompt_patch",
                summary="Patient brief lacks World-Unknown section — verify renderer context wiring",
                rationale=(
                    "TraceDigest.novelty_gate_stats shows "
                    "world_unknown_section_present=0. This means either Wave 2 "
                    "produced no [S]-with-testability hypotheses (covered by "
                    "the strategy proposals above), OR the renderer context did "
                    "not pass world_unknown_candidates. Check renderer call site."
                ),
                target_path="src/opl_cancer/glue/renderer.py",
                proposed_diff="",  # diagnostic only — no concrete patch
                iter_n=iter_n,
            )
            proposals.append(apply_gate(p))

        return EvolutionCandidates(
            iter_n=iter_n,
            proposals=proposals,
            analysis_summary=(
                f"Heuristic fallback ran over digest run_id={digest.run_id}. "
                f"Identified {len(proposals)} structural gaps. Full LLM red-team "
                f"pass requires configuring evolution_analyzer_pool in models.yaml."
            ),
            analyzer_model=self.model_id,
            used_heuristic_fallback=True,
        )
