"""Tournament loop orchestrator. P2-T11.

Glues EloTournament + DebateJudge + MetaCritiqueAggregator + EXPERIMENTAL_INSIGHTS
into a multi-round loop. Caller assembles components and feeds hypotheses;
returns history + final ratings + meta-critique chain.

Per ADR-2026-04-22 main-thread only — no recursive fork; the loop runs in
the calling thread.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from opl_cancer.memory.schemas import Hypothesis, TournamentOutcome, TournamentRound
from opl_cancer.orchestrator.debate import DebateJudge
from opl_cancer.orchestrator.experimental_insights import (
    ExperimentalInsightsFeedback,
)
from opl_cancer.orchestrator.meta_critique import MetaCritiqueAggregator
from opl_cancer.orchestrator.tournament import EloTournament


async def run_tournament(
    hypotheses: list[Hypothesis],
    judge: DebateJudge,
    aggregator: MetaCritiqueAggregator,
    *,
    max_rounds: int = 5,
    k_factor: float = 32.0,
    convergence_window: int = 2,
    convergence_threshold: float = 5.0,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run Co-Sci-style Elo tournament with meta-critique propagation.

    Returns dict with rounds (list[TournamentRound dump]), final_ratings,
    top_k, meta_critique_chain, experimental_insights_chain, and the updated
    hypotheses list (Elo + meta_critique_inherited mutated in place).
    """
    if len(hypotheses) < 2:
        return {
            "rounds": [],
            "final_ratings": {h.id: h.elo_rating for h in hypotheses},
            "top_k": [(h.id, h.elo_rating) for h in hypotheses],
            "meta_critique_chain": [],
            "experimental_insights_chain": [],
            "hypotheses": hypotheses,
        }

    tournament = EloTournament(k_factor=k_factor)
    ratings: dict[str, float] = {h.id: h.elo_rating for h in hypotheses}
    rounds_log: list[dict[str, Any]] = []
    history: list[dict[str, float]] = [dict(ratings)]
    meta_chain: list[str] = []
    insights_chain: list[str] = []

    for round_idx in range(max_rounds):
        pairs = tournament.pair_rotation([h.id for h in hypotheses])
        hyps_by_id = {h.id: h for h in hypotheses}

        outcomes_raw: list[dict[str, str]] = []
        outcomes_models: list[TournamentOutcome] = []
        for a_id, b_id in pairs:
            verdict = await judge.judge_pair(
                hyps_by_id[a_id],
                hyps_by_id[b_id],
                context=context,
                meta_critique=meta_chain[-1] if meta_chain else "",
                experimental_insights=insights_chain[-1] if insights_chain else "",
            )
            outcomes_raw.append({"a": a_id, "b": b_id, "winner": verdict["winner"], "reason": verdict["reason"]})
            outcomes_models.append(
                TournamentOutcome(a=a_id, b=b_id, winner=verdict["winner"], reason=verdict["reason"])  # type: ignore[arg-type]
            )

        new_ratings, deltas = tournament.apply_round(ratings, outcomes_raw)
        ratings = new_ratings
        history.append(dict(ratings))

        # Propagate ratings back to hypothesis objects
        for h in hypotheses:
            h.elo_rating = ratings[h.id]

        # Round-N meta-critique → injected into round-N+1
        critique = await aggregator.aggregate(outcomes_raw, hypotheses)
        meta_chain.append(critique)
        for h in hypotheses:
            if critique:
                h.meta_critique_inherited.append(critique)

        insights = ExperimentalInsightsFeedback.append(outcomes_raw, hypotheses)
        insights_chain.append(insights)

        round_id = f"round_{uuid.uuid4().hex[:6]}"
        rounds_log.append(
            TournamentRound(
                round_id=round_id,
                wave_index=2,
                participants=[h.id for h in hypotheses],
                pairings=list(pairs),
                outcomes=outcomes_models,
                elo_deltas=[deltas],
                meta_critique=critique,
                created_at=datetime.now(timezone.utc).isoformat(),
            ).model_dump()
        )

        if tournament.convergence_check(
            history, window=convergence_window, threshold=convergence_threshold
        ):
            break

    return {
        "rounds": rounds_log,
        "final_ratings": ratings,
        "top_k": tournament.top_k(ratings, k=min(len(hypotheses), 5)),
        "meta_critique_chain": meta_chain,
        "experimental_insights_chain": insights_chain,
        "hypotheses": hypotheses,
    }
