"""P4.5-T5 — G7 ImperativeDetectorGate tests."""
from __future__ import annotations

from opl_cancer.validators.gates.g7_imperative_detector import G7ImperativeDetectorGate
from opl_cancer.validators.mechanical_gates import GateStatus


def test_g7_pass_clean_claim() -> None:
    gate = G7ImperativeDetectorGate()
    claim = {
        "summary": "Cefepime is IDSA category I for MASCC ≥ 21 [PMID:12345].",
        "recommendations": ["Discuss antibiotic stewardship with treating ID team."],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS
    assert r.block is False


def test_g7_fail_direct_imperative_en() -> None:
    gate = G7ImperativeDetectorGate()
    claim = {"summary": "You should start cefepime immediately."}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert "offending_sentences" in r.evidence


def test_g7_fail_direct_imperative_zh() -> None:
    gate = G7ImperativeDetectorGate()
    claim = {"summary": "应该立即停用免疫治疗。"}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


def test_g7_pass_imperative_with_pmid_and_risk() -> None:
    gate = G7ImperativeDetectorGate()
    claim = {
        "summary": (
            "You must start levothyroxine, however there is risk of "
            "adrenal crisis per PMID:99999."
        )
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g7_fail_imperative_with_pmid_but_no_risk() -> None:
    gate = G7ImperativeDetectorGate()
    claim = {"summary": "You must start levothyroxine per PMID:99999."}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


def test_g7_fail_imperative_nested_in_symptom_plan() -> None:
    gate = G7ImperativeDetectorGate()
    claim = {
        "symptom_plan": [
            {
                "symptom": "pain",
                "intervention": "You should immediately give 10 mg morphine.",
            }
        ]
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


def test_g7_pass_nct_url_with_caveat() -> None:
    """v1.5.7: strict mode requires evidence to be parenthesised (citation form)
    when it appears in the imperative clause. Bare NCT inside the imperative
    is the spoof shape and now fails — clinical writers should write
    `enrolment in (NCT01234567)` not `enrolment in NCT01234567`.
    """
    gate = G7ImperativeDetectorGate()
    claim = {
        "summary": (
            "You should consider enrolment in (NCT01234567) — may have side effect of grade 3 fatigue."
        )
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g7_failure_mode_code_c1() -> None:
    gate = G7ImperativeDetectorGate()
    assert gate.failure_mode_code == "C1"


# ─── P1-6: strict_imperative_isolation closes single-sentence bypass ──────────


def test_g7_default_mode_blocks_single_sentence_spoof() -> None:
    """v1.5.7 — strict_imperative_isolation is the DEFAULT now.

    The v1.4 patient run shipped with G7 flags Henry surfaced but delivery
    proceeded because the gate was permissive on single-sentence imperatives.
    v1.5.7 flips strict on so the bypass blocks at the gate, not just at
    Henry's review layer.
    """
    gate = G7ImperativeDetectorGate()  # default now True
    claim = {"summary": "You must take drug X PMID:12345 — risk of bleeding."}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


def test_g7_explicit_opt_out_restores_legacy_permissive() -> None:
    """Callers that need legacy permissive behaviour pass strict=False."""
    gate = G7ImperativeDetectorGate(strict_imperative_isolation=False)
    claim = {"summary": "You must take drug X PMID:12345 — risk of bleeding."}
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g7_strict_mode_blocks_single_sentence_spoof() -> None:
    """strict_imperative_isolation=True closes the bare-PMID-in-imperative-clause spoof."""
    gate = G7ImperativeDetectorGate(strict_imperative_isolation=True)
    claim = {"summary": "You must take drug X PMID:12345 — risk of bleeding."}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


def test_g7_strict_mode_passes_separated_clauses() -> None:
    """Legitimate clinical sentence: imperative in clause A, evidence + risk in clause B."""
    gate = G7ImperativeDetectorGate(strict_imperative_isolation=True)
    claim = {
        "summary": (
            "You must start levothyroxine, however there is risk of "
            "adrenal crisis per PMID:99999."
        )
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g7_strict_mode_passes_parenthesised_citation() -> None:
    """Parens around evidence mark it as a real citation — should pass."""
    gate = G7ImperativeDetectorGate(strict_imperative_isolation=True)
    claim = {
        "summary": (
            "You should consider enrolment in (NCT01234567) — may have side "
            "effect of grade 3 fatigue."
        )
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS
