"""v2.6.0 — patient-facing drug-class redaction must FAIL CLOSED.

Independent review (2026-05-29): `_DRUG_TO_CLASS_REDACTION` is a ~25-entry,
mCRC-biased dictionary; `_redact_drug_specifics` only substitutes drugs literally
present in that dict, so ANY speculative drug name not in the dict (a novel
investigational code like MRTX1133, a HER2 ADC, a menin inhibitor) renders
VERBATIM in the patient brief — defeating the "patients cannot misread this as an
off-label drug list" safety intent (fails OPEN). The fix: a fail-closed backstop
that redacts drug-like tokens (INN stems + investigational codes) it can't map to
a known class, so no specific compound leaks into a patient-facing speculative
section. (The proper generalization fix is an RxNorm/OncoKB/LLM class resolver —
this is the mechanical safety floor behind it; memory:feedback_default_prompt_over_script.)

Failing-first tests.
"""
from __future__ import annotations

from opl_cancer.glue.render_bridge import _redact_drug_specifics


def test_known_dict_drug_redacted_to_class() -> None:
    text = "考虑 sotorasib 单药。"
    out, redacted = _redact_drug_specifics(text)
    assert "sotorasib" not in out.lower()
    assert "KRAS G12C" in out
    assert "sotorasib" in [r.lower() for r in redacted]


def test_unlisted_investigational_code_fails_closed() -> None:
    # MRTX1133 (KRAS G12D) is NOT in the dict — must NOT leak verbatim.
    text = "Wave 2 候选: MRTX1133 靶向 KRAS G12D。"
    out, redacted = _redact_drug_specifics(text)
    assert "MRTX1133" not in out, out
    assert redacted, "fail-closed backstop must record the redacted token"


def test_unlisted_inn_stem_drug_fails_closed() -> None:
    # datopotamab (-mab) and revumenib (-ib) are not in the dict.
    text = "探索 datopotamab 与 revumenib 的组合。"
    out, _ = _redact_drug_specifics(text)
    assert "datopotamab" not in out.lower(), out
    assert "revumenib" not in out.lower(), out


def test_does_not_over_redact_genes_or_prose() -> None:
    # Gene/variant tokens and normal clinical prose must be preserved.
    text = "您的 KRAS G12D 突变意味着标准化疗之外还有研究方向。请与主治医生讨论。"
    out, redacted = _redact_drug_specifics(text)
    assert "KRAS G12D" in out, out
    assert "主治医生" in out
    assert redacted == [], f"over-redacted non-drug tokens: {redacted}"
