"""G58 jurisdiction_availability — activation scoping (adversarial review 2026-06-30).

G58 used to regex the WHOLE profile JSON, so any free-text mention of
中国/mainland/CN (hospital name, ancestry, travel history) flipped it on for
non-CN patients. It is now scoped to location-bearing fields. G58 only FLAGs
(never blocks), so the risk was brittle activation, not a false block.
"""
from __future__ import annotations

import json
from pathlib import Path

from opl_cancer.validators.gates import G58JurisdictionAvailabilityGate


def _profile(tmp: Path, prof: dict) -> Path:
    patient = tmp / "patient"
    out = patient / "triggers" / "r1" / "delivery"
    out.mkdir(parents=True)
    (patient / "profile.json").write_text(json.dumps(prof, ensure_ascii=False), encoding="utf-8")
    (out / "patient_brief.md").write_text("## Summary\nno CN-AVAIL section here.\n", encoding="utf-8")
    return out


def test_mainland_cn_by_residence_flags(tmp_path: Path) -> None:
    out = _profile(tmp_path, {"residence": "中国 上海", "diagnosis": "NSCLC"})
    r = G58JurisdictionAvailabilityGate().check({"out_dir": str(out)})
    assert r.status.value == "fail"      # FLAG surfaces as fail/non-block
    assert r.block is False


def test_locale_zh_flags(tmp_path: Path) -> None:
    out = _profile(tmp_path, {"locale": "zh-CN", "diagnosis": "CRC"})
    r = G58JurisdictionAvailabilityGate().check({"out_dir": str(out)})
    assert r.status.value == "fail"
    assert r.block is False


def test_cn_residence_under_location_key_flags(tmp_path: Path) -> None:
    # B1: residence under the bare 'location' key (en-locale) must still FLAG.
    out = _profile(tmp_path, {"locale": "en", "location": "Shanghai, China", "dx": "NSCLC"})
    r = G58JurisdictionAvailabilityGate().check({"out_dir": str(out)})
    assert r.status.value == "fail"
    assert r.block is False


def test_cn_token_in_record_id_does_not_activate(tmp_path: Path) -> None:
    # B2: a record id like 'CN-001' / copy-number 'CN' must NOT trigger.
    out = _profile(tmp_path, {"locale": "en", "country": "United States",
                              "patient_id": "CN-001", "note": "copy number CN gain"})
    r = G58JurisdictionAvailabilityGate().check({"out_dir": str(out)})
    assert r.status.value == "skip", r.message


def test_cn_freetext_note_under_location_key_does_not_activate(tmp_path: Path) -> None:
    # B3: an ancestry/travel note nested under a location key must NOT re-activate.
    out = _profile(tmp_path, {
        "locale": "en",
        "address": {"line1": "350 Memorial Dr, Cambridge MA",
                    "note": "patient born in 中国, emigrated 1998"},
    })
    r = G58JurisdictionAvailabilityGate().check({"out_dir": str(out)})
    assert r.status.value == "skip", r.message


def test_non_cn_with_incidental_cn_freetext_does_not_activate(tmp_path: Path) -> None:
    # US patient whose record free-text mentions a Chinese hospital / ancestry —
    # must NOT activate G58 (the false-activation the review caught).
    out = _profile(tmp_path, {
        "locale": "en-US",
        "country": "United States",
        "history": "second opinion sought at a hospital in 中国; ancestry noted as Chinese",
        "diagnosis": "melanoma",
    })
    r = G58JurisdictionAvailabilityGate().check({"out_dir": str(out)})
    assert r.status.value == "skip", r.message
