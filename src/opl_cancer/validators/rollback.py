"""Rollback / withdraw protocol. Spec §11."""
from __future__ import annotations

from opl_cancer.memory.schemas import ClaimLayer
from opl_cancer.memory.store import ProjectMemoryStore


def withdraw_with_cascade(
    store: ProjectMemoryStore,
    insight_id: str,
    version: int,
    reason: str,
    at: str,
    evidence: str = "",
) -> set[str]:
    """Withdraw a claim + return set of downstream insight IDs needing cascade review.

    Cascade rule: any insight whose `supersedes` field references the withdrawn
    insight is flagged for re-review. Spec §11.
    """
    store.withdraw_insight(insight_id, version, reason=reason, at=at, evidence=evidence)

    affected: set[str] = set()
    for layer in (ClaimLayer.ESTABLISHED, ClaimLayer.EXPLORATORY, ClaimLayer.SPECULATIVE):
        for c in store.query_by_layer(layer, include_withdrawn=False):
            if c.supersedes == insight_id:
                affected.add(c.id)
    return affected
