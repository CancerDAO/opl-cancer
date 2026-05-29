"""Unit tests for G41 soc_completeness (ADR-0026 P1/P2, session 0d1017d4).

Imports the gate module DIRECTLY so the test runs before the orchestrator
registers G41 in mechanical_gates / gates_registry. Replays Finding 6
(MAJOR): missing patient-specific standard-of-care — re-biopsy/ctDNA urgency
on 3-yr-old tissue, local consolidative therapy for lung oligoprogression,
recurrence-pattern characterization — as the WARN (FAIL, block=False) case,
plus a clean PASS and a missing-field SKIP.

Run:
  PYTHONPATH=/Users/baozhiwei/cancerdao-review/repos/opl-cancer/src \
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest \
  tests/test_validators/test_g41_reasoning.py -q
"""
from __future__ import annotations

from opl_cancer.validators.gates.g41_soc_completeness import G41SoCCompletenessGate
from opl_cancer.validators.mechanical_gates import GateStatus


def _gate() -> G41SoCCompletenessGate:
    return G41SoCCompletenessGate()


# ── contract / wiring ───────────────────────────────────────────────────────
def test_class_attributes_match_contract():
    g = _gate()
    assert g.name == "G41_soc_completeness"
    assert g.family_id == "reasoning-quality"
    assert g.failure_mode_code == "Q6-SOC-UNDERDELIVERED"
    assert isinstance(g.description, str) and g.description


# ── blocking (WARN) case: Finding 6 replay ──────────────────────────────────
def test_finding6_missing_soc_warns_loudly_but_does_not_block():
    """KRAS-G12C/MSS mCRC: the brief silently dropped warranted SoC options.

    The producer's checklist records them as status=='missing' — G41 must
    FAIL (so it lands in the attestation) and surface them LOUDLY in evidence,
    but block=False (quality gate, does NOT fail delivery).
    """
    claim = {
        "claim_id": "c_finding6",
        "claim_text": "Recommended next-line regimen for KRAS-G12C / MSS mCRC.",
        "soc_checklist": [
            {
                "item": "re-biopsy / ctDNA — molecular profile rests on 3-yr-old archival tissue",
                "status": "missing",
                "note": "",
            },
            {
                "item": "local consolidative therapy for lung oligoprogression",
                "status": "missing",
                "note": "",
            },
            {
                "item": "recurrence-pattern characterization",
                "status": "missing",
                "note": "",
            },
            {"item": "germline testing", "status": "addressed", "note": "covered in section 4"},
        ],
    }
    r = _gate().check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False  # Fork A: quality gate → WARN, never blocks delivery
    # The three dropped SoC options surface loudly in evidence.
    missing = {m["item"] for m in r.evidence["missing_items"]}
    assert any("re-biopsy" in m for m in missing)
    assert any("local consolidative therapy" in m for m in missing)
    assert any("recurrence-pattern" in m for m in missing)
    assert r.evidence["item_count"] == 4
    assert r.evidence["addressed"] == 1
    assert "WARN" in r.message and "MISSING" in r.message


def test_missing_item_with_note_still_warns():
    """A 'missing' item is still under-delivery even if it carries a note —
    a warranted SoC element the brief did not cover."""
    claim = {
        "claim_id": "c_1",
        "claim_text": "x",
        "soc_checklist": [
            {"item": "palliative care referral", "status": "missing",
             "note": "patient declined at last visit, but should be re-offered"},
        ],
    }
    r = _gate().check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False
    assert r.evidence["missing_items"][0]["item"] == "palliative care referral"


def test_na_without_note_warns():
    """status=='na' must carry a reason; bare 'na' is a coherence violation."""
    claim = {
        "claim_id": "c_2",
        "claim_text": "x",
        "soc_checklist": [
            {"item": "anti-EGFR if RAS wild-type", "status": "na", "note": ""},
        ],
    }
    r = _gate().check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False
    assert any(i["status"] == "na" for i in r.evidence["items_missing_note"])


def test_malformed_status_warns():
    """An out-of-vocabulary status is recorded-but-incoherent → WARN."""
    claim = {
        "claim_id": "c_3",
        "claim_text": "x",
        "soc_checklist": [
            {"item": "germline testing", "status": "covered"},  # not in enum
        ],
    }
    r = _gate().check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False
    assert r.evidence["malformed_items"]


# ── clean PASS case ──────────────────────────────────────────────────────────
def test_all_addressed_or_na_passes():
    """Every warranted SoC item addressed or explicitly na-with-reason."""
    claim = {
        "claim_id": "c_clean",
        "claim_text": "Recommended next-line regimen for KRAS-G12C / MSS mCRC.",
        "soc_checklist": [
            {"item": "re-biopsy / ctDNA on aged tissue", "status": "addressed",
             "note": "ctDNA urgency flagged in §2 — archival tissue is 3 yr old"},
            {"item": "local consolidative therapy for lung oligoprogression",
             "status": "addressed", "note": "discussed in §5"},
            {"item": "recurrence-pattern characterization", "status": "addressed",
             "note": "documented in §1"},
            {"item": "immunotherapy", "status": "na",
             "note": "MSS — checkpoint-inhibitor monotherapy not indicated"},
        ],
    }
    r = _gate().check(claim)
    assert r.status == GateStatus.PASS
    assert r.block is False
    assert r.evidence["item_count"] == 4
    assert r.evidence["addressed"] == 3
    assert r.evidence["na"] == 1


def test_run_level_checklist_is_read():
    """The checklist may be carried at run level (claim['run']['soc_checklist'])."""
    claim = {
        "claim_id": "c_run",
        "claim_text": "x",
        "run": {
            "soc_checklist": [
                {"item": "germline testing", "status": "addressed", "note": "§4"},
            ]
        },
    }
    r = _gate().check(claim)
    assert r.status == GateStatus.PASS


# ── SKIP case: field absent ─────────────────────────────────────────────────
def test_absent_field_skips_non_blocking():
    """No soc_checklist recorded → SKIP (block=False), with the standard note."""
    claim = {"claim_id": "c_skip", "claim_text": "some claim with no SoC checklist"}
    r = _gate().check(claim)
    assert r.status == GateStatus.SKIP
    assert r.block is False
    assert "SoC completeness not recorded" in r.message


def test_empty_list_warns_not_skip():
    """An empty list is a recorded-but-vacuous check → WARN, distinct from SKIP."""
    claim = {"claim_id": "c_empty", "claim_text": "x", "soc_checklist": []}
    r = _gate().check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False
    assert r.evidence["item_count"] == 0


def test_non_list_field_warns():
    claim = {"claim_id": "c_bad", "claim_text": "x", "soc_checklist": "re-biopsy"}
    r = _gate().check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is False
