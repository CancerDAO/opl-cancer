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


DISEASE_FRONTIER_SYSTEM_PROMPT = """You are the **Disease-Frontier Analyzer** for OPL for Cancer.

D4/ADR-0037 re-aim: your subject is THIS patient's DISEASE RESEARCH FRONTIER,
not OPL-the-software. A research team's institutional memory is about the
SCIENCE — what it killed, what reality verdicted, and what it has not yet tested.
You read a scrubbed TraceDigest of one completed run PLUS the patient's
disease-frontier digest (killed_directions, reality_verdicts, systematic_gaps,
open_frontier — built from the compounding research ledger + reality outcomes)
and propose the team's NEXT RESEARCH MOVES for THIS disease.

Aim every proposal at the frontier:
- CHASE an `open_frontier` hypothesis (active, not yet reality-scored) — name the
  smallest concrete test that would resolve it for THIS patient.
- NEVER re-propose a `killed_directions` entry without genuinely new evidence
  (the Darwin log: don't re-derive a falsified direction).
- CLOSE a recurring `systematic_gaps` root cause.

Hard rules:
1. NEVER propose anything that weakens Henry L3/L4 acknowledgment, G7
   imperative-free voice, G13 reviewer model split, the canonical persona
   prefix, claim_layer enforcement, or RetractionDB grounding. The
   InvariantGate downstream blocks such proposals.
2. NEVER relax citation requirements. NEVER make patient-facing language
   MORE directive. You propose research directions; the patient remains the
   sole decision authority and nothing here is auto-applied.
3. A `skill_addition` (a new research capability) must include a
   `clinical_anchor` citing CSCO / NCCN / NCT / PMID — else it is auto-rejected.
4. `tool_proposal` and research-direction proposals are review-only: describe
   the next investigation, do not enable anything.
5. Concrete over abstract: "run a DepMap MTAP/PRMT5 co-essentiality query to
   test open-frontier H3" beats "explore synthetic lethality".
6. Limit total proposals to 5. Quality > quantity.

Return strict JSON:
{
  "analysis_summary": "<2-3 sentences on this disease's frontier: what was killed,
    what reality said, what is still open to chase>",
  "proposals": [
    {
      "kind": "prompt_patch | skill_addition | tool_proposal",
      "summary": "<1 sentence — a research move for THIS disease>",
      "rationale": "<2-4 sentences, MUST cite which frontier/TraceDigest field
        triggered this>",
      "target_path": "<empty for a research direction; a file path only if you
        genuinely mean a software change>",
      "proposed_diff": "<a concrete test/plan; or a unified diff if a software change>",
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
        *,
        frontier: dict[str, Any] | None = None,
    ) -> EvolutionCandidates:
        if not digest.is_scrubbed():
            raise ValueError(
                "Evolution analyzer refuses unscrubbed digest — "
                "must run scrubber.scrub(digest) first per ADR-0020 #8."
            )

        if self.llm_client is None:
            return self._heuristic(digest, iter_n=iter_n, frontier=frontier)

        try:
            return await self._llm_call(digest, iter_n=iter_n, frontier=frontier)
        except Exception as exc:  # noqa: BLE001 — analyzer must not crash run
            fallback = self._heuristic(digest, iter_n=iter_n, frontier=frontier)
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
        frontier: dict[str, Any] | None = None,
    ) -> EvolutionCandidates:
        from opl_cancer._llm_contract import LLMRequest  # transitional shim

        frontier_block = ""
        if frontier:
            frontier_block = (
                f"# Disease-frontier digest (this patient's compounded research memory)\n\n"
                f"```json\n{json.dumps(frontier, ensure_ascii=False, indent=2)[:20_000]}\n```\n\n"
            )
        prompt = (
            f"# Scrubbed TraceDigest (run {digest.run_id})\n\n"
            f"```json\n{digest.model_dump_json(indent=2)[:60_000]}\n```\n\n"
            f"{frontier_block}"
            f"Apply your role per the system prompt and return JSON."
        )
        req = LLMRequest(
            model=self.model_id,
            messages=[{"role": "user", "content": prompt}],
            system=DISEASE_FRONTIER_SYSTEM_PROMPT,
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

    def _heuristic(
        self,
        digest: TraceDigest,
        iter_n: int,
        frontier: dict[str, Any] | None = None,
    ) -> EvolutionCandidates:
        """Deterministic rule-based proposals.

        Used when LLM client is None OR the LLM call failed. When a disease
        frontier is supplied (D4 patient path), proposals are research moves for
        THIS disease; otherwise the legacy structural-gap heuristic runs.
        """
        if frontier is not None:
            return self._heuristic_frontier(digest, frontier, iter_n=iter_n)

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

    def _heuristic_frontier(
        self,
        digest: TraceDigest,
        frontier: dict[str, Any],
        iter_n: int,
    ) -> EvolutionCandidates:
        """D4/ADR-0037 — disease-frontier-aimed proposals from the reality ledger.

        No LLM: propose chasing each open-frontier hypothesis (the team's untested
        directions for THIS disease) and closing the biggest systematic gap. These
        reference the disease, never OPL-the-software, and still flow through the
        invariant gate (no auto-apply). Empty frontier (first run) → an honest
        zero-proposal digest that still names the frontier.
        """
        killed = frontier.get("killed_directions") or []
        open_frontier = frontier.get("open_frontier") or []
        gaps = frontier.get("systematic_gaps") or []
        verdicts = frontier.get("reality_verdicts") or []

        proposals: list[EvolutionProposal] = []
        for item in open_frontier[:4]:
            hid = str(item.get("id", "?"))
            text = str(item.get("text", ""))[:200]
            p = EvolutionProposal(
                proposal_id=f"p{uuid.uuid4().hex[:6]}",
                kind="tool_proposal",  # review-only research direction; nothing enabled
                summary=f"Chase open-frontier direction for this disease: {text}",
                rationale=(
                    f"disease_frontier.open_frontier lists hypothesis {hid} as active "
                    "but not yet scored against the patient's real course — the team's "
                    "live research frontier. Design the smallest reality test that "
                    "would resolve it; do not re-derive a killed direction."
                ),
                target_path="",  # a research move, not an OPL-software patch
                proposed_diff="",
                iter_n=iter_n,
            )
            proposals.append(apply_gate(p))
            if len(proposals) >= 5:
                break

        if gaps and len(proposals) < 5:
            biggest = max(gaps, key=lambda g: g.get("size", 0)) if gaps else {}
            p = EvolutionProposal(
                proposal_id=f"p{uuid.uuid4().hex[:6]}",
                kind="tool_proposal",
                summary=f"Close the recurring failure pile for this disease: {str(biggest.get('root_cause',''))[:160]}",
                rationale=(
                    "disease_frontier.systematic_gaps records this as the biggest "
                    "recurring root cause across runs; the next run should attack it "
                    "directly rather than re-hit it."
                ),
                target_path="",
                proposed_diff="",
                iter_n=iter_n,
            )
            proposals.append(apply_gate(p))

        return EvolutionCandidates(
            iter_n=iter_n,
            proposals=proposals,
            analysis_summary=(
                f"Disease frontier for this patient (run {digest.run_id}): "
                f"{len(killed)} killed direction(s) (do not re-propose), "
                f"{len(open_frontier)} open frontier hypothesis(es) to chase, "
                f"{len(gaps)} systematic gap(s), {len(verdicts)} reality verdict(s). "
                f"Proposed {len(proposals)} next research move(s) for this disease."
            ),
            analyzer_model=self.model_id,
            used_heuristic_fallback=True,
        )
