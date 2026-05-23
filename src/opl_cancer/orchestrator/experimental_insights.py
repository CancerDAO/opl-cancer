"""Robin EXPERIMENTAL_INSIGHTS_APPENDAGE feedback environment. P2-T15.

Lift source: ``robin/robin/robin/prompts.py:EXPERIMENTAL_INSIGHTS_APPENDAGE``.

After a tournament round produces outcomes, this aggregates them into a
prose appendage that the next-round HypothesisGenerator should consume.
Mirrors the Robin lit-loop: experimental result → updated prompt environment.
"""
from __future__ import annotations

from typing import Any

from opl_cancer.memory.schemas import Hypothesis


_HEADER = (
    "## Experimental insights from the previous round\n"
    "Treat these as feedback — they describe what the tournament round revealed.\n\n"
)


class ExperimentalInsightsFeedback:
    """Formats round results into the EXPERIMENTAL_INSIGHTS appendage prose."""

    @staticmethod
    def append(
        round_outcomes: list[dict[str, str]],
        hypotheses: list[Hypothesis],
    ) -> str:
        """Return prose appendage suitable for injection into next-round prompts."""
        if not round_outcomes and not hypotheses:
            return ""

        hyps_by_id: dict[str, Hypothesis] = {h.id: h for h in hypotheses}
        lines: list[str] = [_HEADER]

        if hypotheses:
            top = sorted(hypotheses, key=lambda h: -h.elo_rating)[:3]
            lines.append("### Top hypotheses by Elo:")
            for h in top:
                lines.append(f"- (elo={h.elo_rating:.1f}) {h.text}")
            lines.append("")

        if round_outcomes:
            lines.append("### Pairwise outcomes:")
            for o in round_outcomes:
                a_id, b_id, winner = o["a"], o["b"], o["winner"]
                a = hyps_by_id.get(a_id)
                b = hyps_by_id.get(b_id)
                a_text = a.text[:120] if a else a_id
                b_text = b.text[:120] if b else b_id
                reason = o.get("reason", "")[:200]
                lines.append(f"- A={a_text} | B={b_text} | winner={winner} | reason={reason}")
            lines.append("")

        lines.append(
            "Use this feedback to: (a) avoid weaknesses identified, "
            "(b) explore neglected mechanisms, (c) re-orient toward higher-Elo lineages."
        )
        return "\n".join(lines)


# Convenience module-level shortcut (mirrors Robin's import style)
def experimental_insights_appendage(
    round_outcomes: list[dict[str, str]],
    hypotheses: list[Hypothesis],
) -> str:
    return ExperimentalInsightsFeedback.append(round_outcomes, hypotheses)


def _format_hypothesis_for_log(h: Hypothesis) -> dict[str, Any]:
    return {"id": h.id, "elo": h.elo_rating, "text": h.text[:160]}
