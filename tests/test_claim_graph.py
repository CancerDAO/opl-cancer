from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from opl_cancer.cli import main
from opl_cancer.delivery.claim_graph import (
    build_claim_evidence_graph,
    validate_claim_evidence_graph,
)
from opl_cancer.delivery.risk_card import RiskDisclosureCard
from opl_cancer.validators.mechanical_gates import GateResult, GateStatus


def _claims() -> list[dict[str, object]]:
    return [
        {
            "claim_id": "c1",
            "claim_text": "KRAS G12C option has phase III evidence.",
            "tier": "established",
            "level": 2,
            "entities": ["KRAS", "G12C"],
            "evidence": [
                {
                    "type": "pmid",
                    "id": "37870974",
                    "quote": "phase III trial",
                    "tier": "established",
                    "source_section": "abstract",
                }
            ],
        }
    ]


def test_build_claim_graph_links_claim_source_gate_and_card() -> None:
    gate = GateResult(
        gate="G42_tier_discipline",
        status=GateStatus.PASS,
        message="ok",
        evidence={"claim_id": "c1"},
    )
    card = RiskDisclosureCard(
        card_id="card-c1",
        claim_text="KRAS G12C option has phase III evidence.",
        level=3,
        epistemic_gaps=["patient-specific uncertainty"],
    )
    graph = build_claim_evidence_graph(
        _claims(),
        gate_results_by_claim={"c1": [gate]},
        risk_cards=[card],
    )

    assert graph["schema"] == "opl.claim_evidence_graph.v1"
    assert graph["summary"] == {
        "claims": 1,
        "sources": 1,
        "gates": 1,
        "risk_cards": 1,
        "edges": 3,
    }
    edge_types = {e["type"] for e in graph["edges"]}
    assert edge_types == {"supported_by", "checked", "discloses_risk_for"}
    assert validate_claim_evidence_graph(graph)["ok"] is True


def test_claim_graph_flags_claim_without_source() -> None:
    graph = build_claim_evidence_graph([
        {"claim_id": "c2", "claim_text": "unsupported", "evidence": []}
    ])
    result = validate_claim_evidence_graph(graph)
    assert result["ok"] is False
    assert result["problems"][0]["code"] == "CLAIM_WITHOUT_SOURCE"


def test_claim_graph_flags_broken_edge() -> None:
    graph = build_claim_evidence_graph(_claims())
    graph["edges"].append({"from": "claim:c1", "to": "source:pmid:missing", "type": "supported_by"})
    result = validate_claim_evidence_graph(graph)
    assert result["ok"] is False
    assert any(p["code"] == "BROKEN_EDGE" for p in result["problems"])


def test_cli_claim_graph_writes_graph(tmp_path: Path) -> None:
    claims_path = tmp_path / "claims.json"
    out_path = tmp_path / "claim_graph.json"
    claims_path.write_text(json.dumps({"claims": _claims()}), encoding="utf-8")

    r = CliRunner().invoke(
        main,
        [
            "claim-graph",
            "--claims-json", str(claims_path),
            "--out", str(out_path),
            "--json",
        ],
    )
    assert r.exit_code == 0, r.output
    payload = json.loads(r.output)
    assert payload["summary"]["claims"] == 1
    assert out_path.is_file()
    assert json.loads(out_path.read_text(encoding="utf-8"))["summary"]["sources"] == 1
