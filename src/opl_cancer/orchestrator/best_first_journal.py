"""Best-first journal — v2.5 compositional foundation (RFC 0001 §8 item 12).

ADAPTATION NOTE — license-respecting borrow:
    This module adapts the journal/tree-search pattern from
    **SakanaAI/AI-Scientist-v2** (Cong Lu et al., ICLR 2025 workshop) under
    their Responsible-AI v1.0 license. We adopt the **journal pattern**
    (typed Node + Journal with add / best / prune / serialize) — we do NOT
    use their unguarded LLM code-gen sandbox. OPL stays closed-world for
    drug / trial / dose IDs (RFC 0001 §6 risk note); composition here is
    over hypothesis branches, never over facts.

Wired into Wave 2 hypothesis tournament as an **audit layer**: every
generated → reviewed → pruned hypothesis branch is recorded in a Journal
and serialized to ``patients/<id>/triggers/<run>/journal.jsonl``. The
tournament loop itself is unchanged; the journal records, doesn't drive.

M5 may evolve this into a primary driver of the tournament; for v2.5 it
is read-only audit infrastructure.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Node:
    """One branch of a hypothesis tournament tree."""

    id: str
    parent_id: str | None
    payload: dict[str, Any]
    metric: float
    status: str  # alive / pruned / accepted
    children: list[str] = field(default_factory=list)


class Journal:
    """Best-first journal — RFC 0001 §8 item 12 (Sakana borrow)."""

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}

    # ─── mutation ─────────────────────────────────────────────────────────

    def add_node(self, node: Node) -> None:
        if node.id in self._nodes:
            raise ValueError(f"duplicate node id: {node.id!r}")
        self._nodes[node.id] = node
        if node.parent_id and node.parent_id in self._nodes:
            self._nodes[node.parent_id].children.append(node.id)

    def prune_below(self, threshold: float) -> list[Node]:
        """Mark every node with metric < threshold as 'pruned'. Returns the
        pruned nodes (in insertion order) for caller audit."""
        pruned: list[Node] = []
        for node in self._nodes.values():
            if node.status == "alive" and node.metric < threshold:
                node.status = "pruned"
                pruned.append(node)
        return pruned

    # ─── access ───────────────────────────────────────────────────────────

    def best_node(self, by: str = "metric") -> Node:
        if not self._nodes:
            raise ValueError("journal is empty; no best_node available")
        if by != "metric":
            raise ValueError(f"unsupported ranking key {by!r}; v2.5 supports 'metric'")
        return max(self._nodes.values(), key=lambda n: n.metric)

    def find(self, node_id: str) -> Node:
        return self._nodes[node_id]

    def children_of(self, node_id: str) -> list[Node]:
        node = self._nodes[node_id]
        return [self._nodes[cid] for cid in node.children]

    def all_nodes(self) -> list[Node]:
        return list(self._nodes.values())

    def killed_candidates(self) -> list[dict[str, object]]:
        """C1/ADR-0031 — pruned nodes as kill records for killed_candidates.jsonl.

        A real tournament discards weak candidates; this exposes the ones
        prune_below() killed so the run can record them (G50 verifies a >=4
        candidate tournament recorded its kills)."""
        return [
            {
                "hyp_id": n.payload.get("hypothesis_id", n.id) if isinstance(n.payload, dict) else n.id,
                "final_elo": n.metric,
                "kill_reason": "below tournament prune threshold (dominated)",
            }
            for n in self._nodes.values()
            if n.status == "pruned"
        ]

    # ─── serialization ────────────────────────────────────────────────────

    def to_jsonl(self, path: str | Path) -> None:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            for node in self._nodes.values():
                f.write(json.dumps(asdict(node), ensure_ascii=False) + "\n")


__all__ = ["Journal", "Node"]
