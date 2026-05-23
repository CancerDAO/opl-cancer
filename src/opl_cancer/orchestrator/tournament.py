"""Co-Sci-style Elo tournament for hypothesis ranking. Spec §6.3."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class EloRater:
    initial_rating: int = 1200
    k_factor: int = 32

    def update(
        self,
        rating_a: float,
        rating_b: float,
        outcome: Literal["a", "b", "draw"],
    ) -> tuple[float, float, float, float]:
        """Standard Elo update. Returns (new_a, new_b, delta_a, delta_b)."""
        expected_a = 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400))
        score_a = {"a": 1.0, "b": 0.0, "draw": 0.5}[outcome]
        delta_a = self.k_factor * (score_a - expected_a)
        delta_b = -delta_a
        return rating_a + delta_a, rating_b + delta_b, delta_a, delta_b
