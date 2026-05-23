"""Co-Sci-style Elo tournament for hypothesis ranking. Spec §6.3.

Lift sources:
- ``open-coscientist/src/coscientist/core/elo.py`` (EloRating/EloTournament)
- ``open-coscientist/src/coscientist/agents/ranking.py`` (pair rotation + debate)

P0 shipped a minimal ``EloRater``. P2 extends to a full machinery:
- ``EloTournament`` with round-robin pair generator, batch round update, top-k,
  and convergence early-stop policy (spec §17.5 P2: top-1 delta < 5 across N
  rounds → stop).
- Backward-compat alias ``EloRater = EloTournament``.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Literal


@dataclass
class EloTournament:
    """Pairwise Elo updater. Stateless wrt persistent storage — caller persists ratings."""

    initial_rating: float = 1200.0
    k_factor: float = 32.0

    # ---- single-pair update -------------------------------------------------

    def update(
        self,
        rating_a: float,
        rating_b: float,
        outcome: Literal["a", "b", "draw", "A", "B"],
    ) -> tuple[float, float, float, float]:
        """Standard Elo update. Returns (new_a, new_b, delta_a, delta_b).

        Accepts both upper (A/B/draw) and lower (a/b/draw) outcome forms.
        """
        expected_a = 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))
        normalized = outcome.lower()
        score_a = {"a": 1.0, "b": 0.0, "draw": 0.5}[normalized]
        delta_a = self.k_factor * (score_a - expected_a)
        delta_b = -delta_a
        return rating_a + delta_a, rating_b + delta_b, delta_a, delta_b

    # ---- pair rotation ------------------------------------------------------

    def pair_rotation(self, hypothesis_ids: list[str]) -> list[tuple[str, str]]:
        """Round-robin pairs of all unordered pairs (i.e. combinations of 2).

        For N=2 → 1 pair, N=3 → 3 pairs, N=4 → 6 pairs.
        """
        return list(combinations(hypothesis_ids, 2))

    # ---- batch round update -------------------------------------------------

    def apply_round(
        self,
        ratings: dict[str, float],
        outcomes: list[dict[str, str]],
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Apply a batch of outcomes to ratings.

        outcomes: list of dicts {"a": id_a, "b": id_b, "winner": "A"/"B"/"draw"}.
        Returns (new_ratings, deltas_per_hypothesis).
        Deltas accumulate when a hypothesis appears in multiple pairings.
        """
        new_ratings = dict(ratings)
        deltas: dict[str, float] = {h: 0.0 for h in ratings}
        for o in outcomes:
            a, b = o["a"], o["b"]
            winner = o["winner"]
            ra, rb = new_ratings[a], new_ratings[b]
            new_a, new_b, da, db = self.update(ra, rb, winner)  # type: ignore[arg-type]
            new_ratings[a] = new_a
            new_ratings[b] = new_b
            deltas[a] = deltas.get(a, 0.0) + da
            deltas[b] = deltas.get(b, 0.0) + db
        return new_ratings, deltas

    # ---- ranking + convergence ---------------------------------------------

    def top_k(self, ratings: dict[str, float], k: int) -> list[tuple[str, float]]:
        return sorted(ratings.items(), key=lambda x: -x[1])[:k]

    @staticmethod
    def convergence_check(
        history: list[dict[str, float]],
        window: int = 2,
        threshold: float = 5.0,
    ) -> bool:
        """Spec §17.5 P2 early-stop: top-1 delta across ``window`` rounds < threshold."""
        if len(history) < window + 1:
            return False
        recent = history[-(window + 1) :]
        top1_ids = [max(r.items(), key=lambda x: x[1])[0] for r in recent]
        if len(set(top1_ids)) > 1:
            return False  # top-1 hypothesis is changing — not converged
        top1 = top1_ids[0]
        deltas = [abs(recent[i][top1] - recent[i - 1][top1]) for i in range(1, len(recent))]
        return all(d < threshold for d in deltas)


# Backward-compat alias — P0 callers reference EloRater.
EloRater = EloTournament
