"""Test G24 crisis-detection gate (v1.3.2 SAFETY hot-fix — round-2 EVAL Patient #17).

G24 is a no-LLM keyword-scan gate. It must:
  * Detect passive_SI / active_SI / active_plan in both Chinese and English.
  * Set GateStatus.FAIL + block=True with a payload describing crisis_grade,
    trigger_phrase (verbatim), jurisdiction_inferred, and recommended_handoff.
  * Not false-positive on adjacent oncology language (palliative / DNR /
    advance-directive / hospice / "撑不下去化疗" with cancer-treatment context
    only — pure-exhaustion phrasing).
  * Not false-negative on edge cases where the SI phrase appears inside
    caregiver_text (e.g. caregiver reports patient's SI).
"""
from opl_cancer.validators.gates.g24_crisis_detection import G24CrisisDetectionGate
from opl_cancer.validators.mechanical_gates import GateStatus


# ─── passive_SI ────────────────────────────────────────────────────────────────

def test_g24_passive_si_zh() -> None:
    """中文 passive_SI: 想结束这一切 → FAIL + block + passive_SI grade."""
    gate = G24CrisisDetectionGate()
    claim = {"patient_text": "化疗这么痛苦,我有时候想结束这一切,真的累了。"}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert r.evidence["crisis_grade"] == "passive_SI"
    assert "结束这一切" in r.evidence["trigger_phrase"]
    assert r.evidence["jurisdiction_inferred"] == "CN"
    assert "cancer-buddy-mind" in r.evidence["recommended_handoff"]
    assert r.evidence["wave_lock"] is True


def test_g24_passive_si_en() -> None:
    """English passive_SI: 'i can't go on' → FAIL + block + passive_SI grade."""
    gate = G24CrisisDetectionGate()
    claim = {"patient_text": "I can't go on like this anymore, everyone would be better off without me."}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert r.evidence["crisis_grade"] == "passive_SI"
    # "everyone would be better off without me" is bank A passive_SI
    # OR "i can't go on" — either passes, both are bank A.
    assert r.evidence["trigger_phrase"]
    assert r.evidence["jurisdiction_inferred"] == "US"


# ─── active_SI ─────────────────────────────────────────────────────────────────

def test_g24_active_si_zh() -> None:
    """中文 active_SI: 我想死 → FAIL + block + active_SI grade."""
    gate = G24CrisisDetectionGate()
    claim = {"patient_text": "医生说没办法了,我想死。"}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert r.evidence["crisis_grade"] == "active_SI"
    assert "想死" in r.evidence["trigger_phrase"]


def test_g24_active_si_en() -> None:
    """English active_SI: 'kill myself' → FAIL + block + active_SI grade."""
    gate = G24CrisisDetectionGate()
    claim = {"patient_text": "I keep thinking about killing myself, the pain is too much."}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert r.evidence["crisis_grade"] == "active_SI"


# ─── active_plan ───────────────────────────────────────────────────────────────

def test_g24_active_plan_zh() -> None:
    """中文 active_plan: 攒了药 → FAIL + block + active_plan grade."""
    gate = G24CrisisDetectionGate()
    claim = {"patient_text": "我已经攒了药,今晚就动手。"}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert r.evidence["crisis_grade"] == "active_plan"
    assert "攒了药" in r.evidence["trigger_phrase"]


def test_g24_active_plan_en() -> None:
    """English active_plan: 'i have a plan' → FAIL + block + active_plan grade."""
    gate = G24CrisisDetectionGate()
    claim = {"patient_text": "I have a plan to overdose tonight, I've stockpiled the pills."}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert r.evidence["crisis_grade"] == "active_plan"


# ─── False-positive avoidance ─────────────────────────────────────────────────

def test_g24_no_false_positive_on_advance_directive() -> None:
    """Advance directive / DNR / hospice discussion is NOT crisis — PASS."""
    gate = G24CrisisDetectionGate()
    claim = {
        "patient_text": (
            "I want to discuss my advance directive — DNR if my heart stops, "
            "and please refer me to hospice if treatment fails. This is end-of-"
            "life planning, not a crisis."
        )
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS, (
        "advance-directive / hospice / DNR discussion must not trigger G24 "
        f"(got {r.status} on {r.message})"
    )


def test_g24_no_false_positive_on_no_text() -> None:
    """Claim with no text → SKIP, not FAIL."""
    gate = G24CrisisDetectionGate()
    claim = {"evidence": [{"pmid": "12345"}]}
    r = gate.check(claim)
    assert r.status == GateStatus.SKIP


# ─── False-negative avoidance ─────────────────────────────────────────────────

def test_g24_caregiver_text_field_also_scanned() -> None:
    """SI phrase in caregiver_text field must still fire G24."""
    gate = G24CrisisDetectionGate()
    claim = {
        "patient_text": "we're managing the chemo cycles.",
        "caregiver_text": "他偷偷跟我说想自杀,我吓坏了。",
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert r.evidence["crisis_grade"] == "active_SI"


def test_g24_grade_picks_highest_when_multiple_banks_hit() -> None:
    """When passive + active_plan both present → active_plan wins (highest)."""
    gate = G24CrisisDetectionGate()
    claim = {
        "patient_text": (
            "I want it to end. I have the pills, by friday I'll be done."
        )
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.evidence["crisis_grade"] == "active_plan"


# ─── Jurisdiction inference ───────────────────────────────────────────────────

def test_g24_jurisdiction_explicit_hint_wins() -> None:
    """profile_jurisdiction_hint overrides language inference."""
    gate = G24CrisisDetectionGate()
    claim = {
        "patient_text": "想结束这一切",
        "profile_jurisdiction_hint": "JP",
    }
    r = gate.check(claim)
    assert r.evidence["jurisdiction_inferred"] == "JP"


def test_g24_jurisdiction_uk_from_location_token() -> None:
    """Location token 'London' overrides default EN→US to UK."""
    gate = G24CrisisDetectionGate()
    claim = {"patient_text": "I'm in London and I can't go on."}
    r = gate.check(claim)
    assert r.evidence["jurisdiction_inferred"] == "UK"
