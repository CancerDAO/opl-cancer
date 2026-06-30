"""Claim-level evidence graph builder.

The patient brief is a rendering. This module builds the structured graph below
it: claim nodes, evidence-source nodes, gate verdict nodes, risk-card nodes, and
typed edges between them. It is deterministic and LLM-free; it does not decide
clinical truth.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from opl_cancer.provenance.hasher import hash_claim

SCHEMA = "opl.claim_evidence_graph.v1"


def _claim_id(claim: dict[str, Any], idx: int) -> str:
    return str(claim.get("claim_id") or claim.get("id") or f"claim_{idx + 1:03d}")


def _source_id(evidence: dict[str, Any]) -> str:
    etype = str(evidence.get("type") or "other").strip().lower() or "other"
    eid = str(evidence.get("id") or "unknown").strip()
    return f"source:{etype}:{eid}"


def _gate_result_dict(result: Any) -> dict[str, Any]:
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    return dict(result)


def _risk_card_dict(card: Any) -> dict[str, Any]:
    if hasattr(card, "model_dump"):
        return card.model_dump(mode="json")
    return dict(card)


def build_claim_evidence_graph(
    claims: list[dict[str, Any]],
    *,
    gate_results_by_claim: dict[str, list[Any]] | None = None,
    risk_cards: list[Any] | None = None,
) -> dict[str, Any]:
    """Build a normalized graph from structured claim objects."""
    gate_results_by_claim = gate_results_by_claim or {}
    risk_cards = risk_cards or []

    claim_nodes: list[dict[str, Any]] = []
    source_nodes_by_id: dict[str, dict[str, Any]] = {}
    gate_nodes: list[dict[str, Any]] = []
    card_nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    claim_ids_by_hash: dict[str, str] = {}
    claim_ids_by_text: dict[str, str] = {}

    for idx, claim in enumerate(claims):
        cid = _claim_id(claim, idx)
        c_hash = hash_claim(claim)
        claim_ids_by_hash[c_hash] = cid
        claim_ids_by_text[str(claim.get("claim_text") or "")] = cid
        claim_nodes.append({
            "id": f"claim:{cid}",
            "claim_id": cid,
            "claim_hash": c_hash,
            "claim_text": claim.get("claim_text") or "",
            "tier": claim.get("tier"),
            "level": claim.get("level"),
            "entities": list(claim.get("entities") or []),
        })

        for evidence in claim.get("evidence") or []:
            if not isinstance(evidence, dict):
                continue
            sid = _source_id(evidence)
            source_nodes_by_id.setdefault(sid, {
                "id": sid,
                "source_type": evidence.get("type") or "other",
                "source_id": evidence.get("id") or "unknown",
                "tier": evidence.get("tier"),
                "source_section": evidence.get("source_section"),
                "quote_hash": hash_claim({"quote": evidence.get("quote")})
                if evidence.get("quote") else None,
            })
            edges.append({
                "from": f"claim:{cid}",
                "to": sid,
                "type": "supported_by",
            })

        for result in gate_results_by_claim.get(cid, []):
            r = _gate_result_dict(result)
            gid = f"gate:{cid}:{r.get('gate') or 'unknown'}"
            gate_nodes.append({
                "id": gid,
                "claim_id": cid,
                "gate": r.get("gate"),
                "status": str(r.get("status")),
                "block": bool(r.get("block")),
                "message": r.get("message") or "",
                "evidence": r.get("evidence") or {},
            })
            edges.append({
                "from": gid,
                "to": f"claim:{cid}",
                "type": "checked",
            })

    for card in risk_cards:
        c = _risk_card_dict(card)
        card_id = str(c.get("card_id") or c.get("id") or f"card_{len(card_nodes) + 1:03d}")
        source_hash = c.get("source_claim_hash")
        cid = c.get("claim_id")
        if not cid and source_hash:
            cid = claim_ids_by_hash.get(str(source_hash))
        if not cid:
            cid = claim_ids_by_text.get(str(c.get("claim_text") or ""))
        card_nodes.append({
            "id": f"risk_card:{card_id}",
            "card_id": card_id,
            "claim_id": cid,
            "level": c.get("level"),
            "requires_patient_acknowledgment": c.get(
                "requires_patient_acknowledgment", True
            ),
            "patient_acknowledged_at": c.get("patient_acknowledged_at"),
            "source_claim_hash": source_hash,
        })
        if cid:
            edges.append({
                "from": f"risk_card:{card_id}",
                "to": f"claim:{cid}",
                "type": "discloses_risk_for",
            })

    graph = {
        "schema": SCHEMA,
        "nodes": {
            "claims": claim_nodes,
            "sources": sorted(source_nodes_by_id.values(), key=lambda n: n["id"]),
            "gates": gate_nodes,
            "risk_cards": card_nodes,
        },
        "edges": edges,
    }
    graph["summary"] = summarize_claim_evidence_graph(graph)
    return graph


def summarize_claim_evidence_graph(graph: dict[str, Any]) -> dict[str, int]:
    nodes = graph.get("nodes") or {}
    return {
        "claims": len(nodes.get("claims") or []),
        "sources": len(nodes.get("sources") or []),
        "gates": len(nodes.get("gates") or []),
        "risk_cards": len(nodes.get("risk_cards") or []),
        "edges": len(graph.get("edges") or []),
    }


def validate_claim_evidence_graph(graph: dict[str, Any]) -> dict[str, Any]:
    """Validate graph referential integrity and surface ungrounded claims."""
    nodes = graph.get("nodes") or {}
    node_ids = {
        n.get("id")
        for group in nodes.values()
        for n in (group or [])
        if isinstance(n, dict)
    }
    problems: list[dict[str, str]] = []

    for edge in graph.get("edges") or []:
        src = edge.get("from")
        dst = edge.get("to")
        if src not in node_ids or dst not in node_ids:
            problems.append({
                "code": "BROKEN_EDGE",
                "message": f"{src!r} -> {dst!r} references a missing node",
            })

    source_edges = {
        edge.get("from")
        for edge in graph.get("edges") or []
        if edge.get("type") == "supported_by"
    }
    for claim in nodes.get("claims") or []:
        if claim.get("id") not in source_edges:
            problems.append({
                "code": "CLAIM_WITHOUT_SOURCE",
                "message": f"{claim.get('claim_id')} has no evidence-source edge",
            })

    return {
        "ok": not problems,
        "problems": problems,
        "summary": summarize_claim_evidence_graph(graph),
    }


def write_claim_evidence_graph(graph: dict[str, Any], out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
