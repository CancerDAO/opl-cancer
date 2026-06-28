"""Contract test — the research-team iteration fields are declared in the claim
schema (B1 false-hope firewall + B3 attribution/ablation).

The gates read these fields off claim dicts; the schema is the documented
contract the producer prompts fill. This keeps the contract and the gates in
sync.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((REPO / "schemas" / "claim.v2.schema.json").read_text(encoding="utf-8"))
PROPS = SCHEMA["properties"]


def test_b1_false_hope_fields_declared():
    for field in ("options", "soc_baseline", "world_unknown_candidate", "world_known_comparator"):
        assert field in PROPS, f"{field} missing from claim schema (B1/G45/G46)"
    assert "best_option" in PROPS["soc_baseline"]["properties"]
    assert "best_world_known_option" in PROPS["world_known_comparator"]["properties"]


def test_b3_attribution_field_declared():
    assert "attribution" in PROPS, "attribution missing from claim schema (B3)"
    ap = PROPS["attribution"]["properties"]
    for sub in ("primary_carrier_expert", "primary_carrier_evidence_ref", "survives_without_primary"):
        assert sub in ap, f"attribution.{sub} missing"
