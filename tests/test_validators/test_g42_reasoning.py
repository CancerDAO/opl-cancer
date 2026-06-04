"""Test G42 tier-discipline gate (session 0d1017d4 KRAS-G12C/MSS findings 3, 4, 7).

Imports the gate module DIRECTLY so it runs independently of the orchestrator's
gate registration. Replays the cross-model findings as blocking cases:

  * Finding 3/7: ATM-gated ATRi/PARPi novelty asserted as 'established' on the
    weakest (speculative) evidence  → tier-floor BLOCK.
  * Finding 3/7 (presentation): a speculative claim sitting headline-adjacent →
    adjacency WARN (block=False).
  * Finding 4: 'TP53 biallelic loss' from IHC / different tumour type →
    functional-evidence BLOCK.

Run with:
  PYTHONPATH=.../src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
    python3 -m pytest tests/test_validators/test_g42_reasoning.py -q
"""
from opl_cancer.validators.gates.g42_tier_discipline import G42TierDisciplineGate
from opl_cancer.validators.mechanical_gates import GateStatus


# ── (a) TIER-FLOOR — Finding 3/7 replay ─────────────────────────────────────
def test_g42_block_tier_floor_established_on_speculative() -> None:
    """Finding 3/7: an 'established' claim floated on a speculative evidence link."""
    gate = G42TierDisciplineGate()
    claim = {
        "claim_id": "c_atm_atri",
        "claim_text": "ATM-gated ATRi/PARPi combination is an established next-line option.",
        "tier": "established",
        "evidence": [
            {"type": "pmid", "id": "30000001", "tier": "speculative"},  # mechanistic/preclinical
            {"type": "pmid", "id": "30000002", "tier": "exploratory"},
        ],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert "tier_floor" in r.message
    assert any(v["rule"] == "tier_floor" for v in r.evidence["blocking_violations"])


def test_g42_block_tier_floor_exploratory_on_speculative() -> None:
    """An 'exploratory' claim still cannot rest only on speculative evidence."""
    gate = G42TierDisciplineGate()
    claim = {
        "claim_id": "c_explore",
        "claim_text": "Exploratory synergy claim.",
        "tier": "exploratory",
        "evidence": [{"type": "pmid", "id": "30000003", "tier": "speculative"}],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


# ── (b) FUNCTIONAL-EVIDENCE — Finding 4 replay ──────────────────────────────
def test_g42_block_biallelic_from_ihc() -> None:
    """Finding 4: 'TP53 biallelic loss' asserted from IHC modality → BLOCK."""
    gate = G42TierDisciplineGate()
    claim = {
        "claim_id": "c_tp53",
        "claim_text": "TP53 biallelic loss-of-function supports the strategy.",
        "tier": "exploratory",
        "evidence": [{"type": "pmid", "id": "30000004", "tier": "exploratory"}],
        "functional_evidence": {
            "claim_type": "biallelic",
            "same_tumor_type": True,
            "modality": "IHC",  # cannot establish biallelic genomic LoF
        },
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert "functional_evidence" in r.message
    fe_viol = [v for v in r.evidence["blocking_violations"] if v["rule"] == "functional_evidence"]
    assert fe_viol and "modality" in fe_viol[0]["reason"]


def test_g42_block_loss_of_function_wrong_tumor_type() -> None:
    """Finding 3/7: ATM functional data is breast-cancer-derived (wrong lineage) → BLOCK."""
    gate = G42TierDisciplineGate()
    claim = {
        "claim_id": "c_atm_lof",
        "claim_text": "ATM loss-of-function predicts ATRi sensitivity.",
        "tier": "speculative",
        "evidence": [{"type": "pmid", "id": "30000005", "tier": "speculative"}],
        "functional_evidence": {
            "claim_type": "loss_of_function",
            "same_tumor_type": False,  # data from breast cancer, patient is mCRC
            "modality": "functional_assay",
        },
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    fe_viol = [v for v in r.evidence["blocking_violations"] if v["rule"] == "functional_evidence"]
    assert fe_viol and "same_tumor_type" in fe_viol[0]["reason"]


# ── (c) ADJACENCY — WARN (block=False) ──────────────────────────────────────
def test_g42_warn_speculative_headline_adjacent() -> None:
    """A speculative claim presented as headline → WARN, not block (Fork A)."""
    gate = G42TierDisciplineGate()
    claim = {
        "claim_id": "c_spec_headline",
        "claim_text": "Speculative ATRi novelty.",
        "tier": "speculative",
        "evidence": [{"type": "pmid", "id": "30000006", "tier": "speculative"}],
        "regimen": {"is_headline": True},
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False  # WARN-only
    assert "WARN" in r.message
    assert any(w["rule"] == "adjacency" for w in r.evidence["warnings"])


# ── (d) ESCALATION-MISLABEL — v2.10 P1.5 (dangerous direction only) ─────────
def test_g42_block_speculative_relabelled_established() -> None:
    """A tier relabel speculative→established mislabels a guess as established → BLOCK."""
    gate = G42TierDisciplineGate()
    claim = {
        "claim_id": "c_relabel",
        "claim_text": "ATRi synergy.",
        "tier_relabel": {"from": "speculative", "to": "established"},
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert "escalation_mislabel" in r.message
    assert any(v["rule"] == "escalation_mislabel" for v in r.evidence["blocking_violations"])


def test_g42_block_exploratory_relabelled_established() -> None:
    gate = G42TierDisciplineGate()
    r = gate.check({"claim_id": "c", "tier_relabel": {"from": "exploratory", "to": "established"}})
    assert r.status == GateStatus.FAIL and r.block is True


def test_g42_deescalation_relabel_does_not_block() -> None:
    """Honest down-grading established→speculative is fine — never blocks."""
    gate = G42TierDisciplineGate()
    r = gate.check({"claim_id": "c", "tier_relabel": {"from": "established", "to": "speculative"}})
    assert r.block is False
    assert r.status in (GateStatus.PASS, GateStatus.SKIP)


def test_g42_same_tier_relabel_does_not_block() -> None:
    gate = G42TierDisciplineGate()
    r = gate.check({"claim_id": "c", "tier_relabel": {"from": "exploratory", "to": "exploratory"}})
    assert r.block is False


# ── PASS — clean claim ──────────────────────────────────────────────────────
def test_g42_pass_clean_claim() -> None:
    """Established headline backed by established evidence; biallelic from sequencing."""
    gate = G42TierDisciplineGate()
    claim = {
        "claim_id": "c_clean",
        "claim_text": "Sotorasib + panitumumab is FDA-approved for KRAS-G12C mCRC.",
        "tier": "established",
        "evidence": [
            {"type": "fda_label", "id": "sotorasib", "tier": "established"},
            {"type": "pmid", "id": "37870968", "tier": "established"},
        ],
        "regimen": {"is_headline": True},
        "functional_evidence": {
            "claim_type": "biallelic",
            "same_tumor_type": True,
            "modality": "sequencing",  # functional / genomic — sufficient
        },
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS
    assert r.block is False
    rules = {sr["rule"] for sr in r.evidence["passed_subrules"]}
    assert {"tier_floor", "functional_evidence", "adjacency"} <= rules


def test_g42_pass_speculative_claim_speculative_evidence_not_headline() -> None:
    """A speculative claim on speculative evidence, NOT headline → PASS (honest)."""
    gate = G42TierDisciplineGate()
    claim = {
        "claim_id": "c_honest_spec",
        "claim_text": "Speculative mechanistic hypothesis (clearly labelled, contingent).",
        "tier": "speculative",
        "evidence": [{"type": "pmid", "id": "30000007", "tier": "speculative"}],
        "regimen": {"is_headline": False},
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


# ── SKIP — missing fields ───────────────────────────────────────────────────
def test_g42_skip_no_judgeable_fields() -> None:
    """No tier / evidence-tier / functional_evidence / regimen.is_headline → SKIP."""
    gate = G42TierDisciplineGate()
    claim = {
        "claim_id": "c_bare",
        "claim_text": "Some claim with no structured tier fields.",
        "evidence": [{"type": "pmid", "id": "30000008"}],  # no tier on link
    }
    r = gate.check(claim)
    assert r.status == GateStatus.SKIP
    assert r.block is False


def test_g42_skip_tier_present_but_no_evidence_tiers() -> None:
    """claim.tier set but no evidence link carries a tier → tier-floor cannot judge.

    With nothing else judgeable, the gate SKIPs.
    """
    gate = G42TierDisciplineGate()
    claim = {
        "claim_id": "c_partial",
        "claim_text": "Established claim, but evidence links lack tiers.",
        "tier": "established",
        "evidence": [{"type": "pmid", "id": "30000009"}],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.SKIP
