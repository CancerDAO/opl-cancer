"""Rollback / withdraw protocol. Spec §11."""
from __future__ import annotations

from opl_cancer.memory.schemas import ClaimLayer
from opl_cancer.memory.store import ProjectMemoryStore
from opl_cancer.provenance.journal import ProvenanceJournal


def withdraw_with_cascade(
    store: ProjectMemoryStore,
    insight_id: str,
    version: int,
    reason: str,
    at: str,
    evidence: str = "",
    journal: ProvenanceJournal | None = None,
) -> set[str]:
    """Withdraw a claim + return set of downstream insight IDs needing cascade review.

    Cascade rule: any insight whose `supersedes` references the withdrawn
    insight is flagged for re-review. Spec §11.

    If `journal` is provided, append an immutable withdrawal event for
    audit-trail (safety eval S3 — append-only invariant beyond SQLite REPLACE).
    """
    store.withdraw_insight(insight_id, version, reason=reason, at=at, evidence=evidence)

    if journal is not None:
        journal.append({
            "event": "withdraw",
            "insight_id": insight_id,
            "version": version,
            "reason": reason,
            "at": at,
            "evidence": evidence,
        })

    # Transitive cascade — BFS over supersedes graph (Code quality eval rec).
    affected: set[str] = set()
    frontier = {insight_id}
    while frontier:
        next_frontier: set[str] = set()
        for layer in (ClaimLayer.ESTABLISHED, ClaimLayer.EXPLORATORY, ClaimLayer.SPECULATIVE):
            for c in store.query_by_layer(layer, include_withdrawn=False):
                if c.supersedes in frontier and c.id not in affected:
                    affected.add(c.id)
                    next_frontier.add(c.id)
        frontier = next_frontier
    return affected
