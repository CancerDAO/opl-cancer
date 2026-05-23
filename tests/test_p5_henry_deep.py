"""P5 — deep parametric tests for Henry auditor across all catalogued drugs +
all reviewer pairings.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SERIOUS_RISKS_PATH = REPO_ROOT / "knowledge" / "serious_risks_per_drug.json"
_CATALOGUE = json.loads(SERIOUS_RISKS_PATH.read_text(encoding="utf-8"))
DRUGS = [k for k in _CATALOGUE if not k.startswith("_")]

_PAIRINGS = (
    yaml.safe_load((REPO_ROOT / "models.yaml").read_text(encoding="utf-8")).get(
        "reviewer_pairings"
    )
    or {}
)


@pytest.fixture()
def auditor(tmp_path: Path) -> object:
    from opl_cancer.validators.henry import HenryAuditor

    return HenryAuditor(
        serious_risks_path=SERIOUS_RISKS_PATH,
        outstanding_dir=tmp_path / "outstanding",
    )


@pytest.mark.parametrize("drug", DRUGS)
def test_henry_l3_surfaces_drug_specific_risks(drug: str, auditor: object) -> None:
    from opl_cancer.validators.permission_levels import Level

    res = auditor.audit_claim(  # type: ignore[attr-defined]
        claim_id=f"d-{drug}",
        claim_text=f"recommend {drug} for refractory disease",
        level=Level.L3_HIGH_RISK,
        drugs_mentioned=[drug],
    )
    inn = _CATALOGUE[drug]["inn"]
    assert any(inn in r for r in res.layer3_serious_risks)
    assert res.layer1_card is not None


@pytest.mark.parametrize("drug", DRUGS)
def test_henry_l4_card_contains_serious_risks_in_render(
    drug: str, auditor: object
) -> None:
    from opl_cancer.delivery.risk_card import render_risk_card_markdown
    from opl_cancer.validators.permission_levels import Level

    res = auditor.audit_claim(  # type: ignore[attr-defined]
        claim_id=f"d2-{drug}",
        claim_text=f"off-label {drug}",
        level=Level.L4_BOUNDARY,
        drugs_mentioned=[drug],
    )
    assert res.layer1_card is not None
    md = render_risk_card_markdown(res.layer1_card)
    assert "Level 4" in md
    inn = _CATALOGUE[drug]["inn"]
    assert inn in md


@pytest.mark.parametrize("drug", DRUGS)
def test_henry_l0_no_card_even_with_drug(drug: str, auditor: object) -> None:
    from opl_cancer.validators.permission_levels import Level

    res = auditor.audit_claim(  # type: ignore[attr-defined]
        claim_id=f"d3-{drug}",
        claim_text="background info",
        level=Level.L0_INFORMATION,
        drugs_mentioned=[drug],
    )
    assert res.layer1_card is None
    assert res.layer4_ack_required is False


@pytest.mark.parametrize("producer,reviewer", sorted(_PAIRINGS.items()))
def test_reviewer_pairing_no_self_review(producer: str, reviewer: str) -> None:
    assert producer != reviewer


@pytest.mark.parametrize("producer,reviewer", sorted(_PAIRINGS.items()))
def test_reviewer_pairing_reviewer_in_roster(producer: str, reviewer: str) -> None:
    from opl_cancer.experts.roster import ROSTER

    assert reviewer in ROSTER, f"reviewer {reviewer!r} for {producer!r} not in roster"


@pytest.mark.parametrize("producer,reviewer", sorted(_PAIRINGS.items()))
def test_reviewer_pairing_producer_in_roster(producer: str, reviewer: str) -> None:
    from opl_cancer.experts.roster import ROSTER

    assert producer in ROSTER, f"producer {producer!r} not in roster"


def test_henry_writes_outstanding_record_with_expected_fields(tmp_path: Path) -> None:
    from opl_cancer.validators.henry import HenryAuditor
    from opl_cancer.validators.permission_levels import Level

    out = tmp_path / "out"
    auditor = HenryAuditor(serious_risks_path=SERIOUS_RISKS_PATH, outstanding_dir=out)
    res = auditor.audit_claim(
        claim_id="cw1",
        claim_text="claim X",
        level=Level.L3_HIGH_RISK,
        drugs_mentioned=["atezolizumab"],
    )
    assert res.layer4_ack_pending_path is not None
    rec = json.loads(Path(res.layer4_ack_pending_path).read_text(encoding="utf-8"))
    for key in (
        "card_id",
        "claim_id",
        "claim_text",
        "level",
        "known_serious_risks",
        "epistemic_gaps",
        "alternatives",
        "created_at",
        "patient_acknowledged_at",
    ):
        assert key in rec, f"outstanding record missing {key}"
    assert rec["patient_acknowledged_at"] is None
    assert rec["level"] == 3


def test_henry_acknowledge_persists_timestamp(tmp_path: Path) -> None:
    from opl_cancer.validators.henry import HenryAuditor
    from opl_cancer.validators.permission_levels import Level

    out = tmp_path / "out"
    auditor = HenryAuditor(serious_risks_path=SERIOUS_RISKS_PATH, outstanding_dir=out)
    res = auditor.audit_claim(
        claim_id="cw2",
        claim_text="claim Y",
        level=Level.L4_BOUNDARY,
        drugs_mentioned=["bevacizumab"],
    )
    assert res.layer1_card is not None
    cid = res.layer1_card.card_id
    auditor.acknowledge(cid, acknowledged_at="2026-05-24T15:00:00+00:00")
    rec = json.loads((out / f"{cid}.json").read_text(encoding="utf-8"))
    assert rec["patient_acknowledged_at"] == "2026-05-24T15:00:00+00:00"
