"""Regression: the REAL load_soc_floor → rendered-brief output must survive
BOTH G57 (floor present) AND G35 (clinical-fact provenance).

The 2026-06-30 adversarial review caught that the original load_soc_floor put
stage + standard + PMID on one line with no [[src:]] anchor, so a real run that
rendered the floor self-blocked on G35 — while the E2E fixture hand-wrote a
different, G35-safe brief and hid the bug. This test exercises the actual
loader output (not a hand-authored brief) through both gates.
"""
from __future__ import annotations

import json
from pathlib import Path

import jinja2

from opl_cancer.glue.render_bridge import load_soc_floor
from opl_cancer.validators.gates import (
    G35ClinicalFactProvenanceGate,
    G57SoCFloorPresentGate,
)

_TEMPLATE = (
    "## Summary\nTeam analysis.\n\n"
    "{% if soc_floor is defined and soc_floor %}"
    "## 标准治疗地板 / Standard-of-care floor [SOC-FLOOR]\n{{ soc_floor }}\n"
    "{% endif %}\n"
)


def _render(soc_floor: str | None) -> str:
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    return env.from_string(_TEMPLATE).render(soc_floor=soc_floor)


def test_real_soc_floor_passes_g57_and_g35(tmp_path: Path) -> None:
    patient = tmp_path / "patient"
    run_dir = patient / "triggers" / "r1"
    out = run_dir / "delivery"
    (patient / "ocr").mkdir(parents=True)
    (patient / "ocr" / "stage.txt").write_text("Stage IV metastatic disease\n", encoding="utf-8")
    run_dir.mkdir(parents=True)
    (run_dir / "soc_floor.json").write_text(json.dumps({
        "stage": "Stage IV metastatic",
        "stage_src": "ocr/stage.txt#L1",
        "standard": "PACIFIC-style durvalumab consolidation",
        "pivotal_pmid": "28885881",
    }), encoding="utf-8")

    soc_floor = load_soc_floor(run_dir)
    assert soc_floor is not None
    # the loader must NOT inline the PMID with the stage value (G35 collision)
    stage_line = soc_floor.splitlines()[0]
    assert "[[src:ocr/stage.txt#L1]]" in stage_line
    assert "PMID" not in stage_line

    out.mkdir(parents=True)
    (out / "patient_brief.md").write_text(_render(soc_floor), encoding="utf-8")

    g57 = G57SoCFloorPresentGate().check({"out_dir": str(out)})
    assert g57.status.value == "pass", g57.message

    g35 = G35ClinicalFactProvenanceGate().check(
        {"delivery_dir": str(out), "patient_dir": str(patient)}
    )
    assert g35.status.value != "fail", g35.message


def test_g57_blocks_when_floor_absent(tmp_path: Path) -> None:
    # Negative: a brief with no [SOC-FLOOR] marker must BLOCK (the gate's reason
    # to exist — a frontier-only brief that skips the floor).
    out = tmp_path / "delivery"
    out.mkdir(parents=True)
    (out / "patient_brief.md").write_text(
        "## Summary\nStage IV metastatic disease. Frontier options below.\n",
        encoding="utf-8",
    )
    g57 = G57SoCFloorPresentGate().check({"out_dir": str(out)})
    assert g57.status.value == "fail"
    assert g57.block is True


def test_g57_blocks_hollow_marker_with_stage_word_elsewhere(tmp_path: Path) -> None:
    # Gameability: a hollow "[SOC-FLOOR] TBD" heading + the word 'metastatic' in
    # a trial title elsewhere must NOT pass (the marker/stage were OR-ed before).
    out = tmp_path / "delivery"
    out.mkdir(parents=True)
    (out / "patient_brief.md").write_text(
        "## Floor [SOC-FLOOR]\nTBD\n\n"
        "## Trials\nA trial in metastatic disease (NCT01).\n",
        encoding="utf-8",
    )
    g57 = G57SoCFloorPresentGate().check({"out_dir": str(out)})
    assert g57.status.value == "fail"
    assert g57.block is True


def test_g57_blocks_long_gibberish_filler(tmp_path: Path) -> None:
    # adversarial round-2: 25+ chars of filler + a stage word must NOT pass — a
    # real floor must NAME a standard of care, not just be long.
    out = tmp_path / "delivery"
    out.mkdir(parents=True)
    (out / "patient_brief.md").write_text(
        "## Floor [SOC-FLOOR]\n"
        "aaaa bbbb cccc dddd eeee ffff gggg hhhh iiii jjjj. Stage IV.\n",
        encoding="utf-8",
    )
    r = G57SoCFloorPresentGate().check({"out_dir": str(out)})
    assert r.status.value == "fail" and r.block is True


def test_g57_no_standard_chemotherapy_is_not_honest_none(tmp_path: Path) -> None:
    # adversarial round-2: "no standard chemotherapy" must NOT trigger the
    # no-SoC-remains ESCAPE. The reviewer's exact input has no stage, so the
    # honest-none path was the only way it passed; with the tightened _NO_SOC it
    # no longer matches → stage+substance required → BLOCK.
    out = tmp_path / "delivery"
    out.mkdir(parents=True)
    (out / "patient_brief.md").write_text(
        "## Floor [SOC-FLOOR]\n"
        "For this rare disease, there is no standard chemotherapy regimen available.\n",
        encoding="utf-8",
    )
    r = G57SoCFloorPresentGate().check({"out_dir": str(out)})
    assert r.status.value == "fail" and r.block is True


def test_g57_blocks_pending_placeholder(tmp_path: Path) -> None:
    out = tmp_path / "delivery"
    out.mkdir(parents=True)
    (out / "patient_brief.md").write_text(
        "## Floor [SOC-FLOOR]\nPENDING - to be filled by clinician. Stage IV metastatic.\n",
        encoding="utf-8",
    )
    r = G57SoCFloorPresentGate().check({"out_dir": str(out)})
    assert r.status.value == "fail" and r.block is True


def test_g57_honest_no_standard_remains_passes(tmp_path: Path) -> None:
    # Honest escape: a genuine late-line patient with no remaining SoC can say so.
    out = tmp_path / "delivery"
    out.mkdir(parents=True)
    (out / "patient_brief.md").write_text(
        "## 标准治疗地板 [SOC-FLOOR]\n"
        "在 Stage IV 多线进展后，标准治疗已用尽；以下为研究方向，非标准替代。\n",
        encoding="utf-8",
    )
    g57 = G57SoCFloorPresentGate().check({"out_dir": str(out)})
    assert g57.status.value == "pass", g57.message


def test_soc_floor_without_stage_src_still_safe(tmp_path: Path) -> None:
    # When no stage_src is given, the loader must not emit a 'Stage <numeral>'
    # value that G35 would demand an anchor for. A descriptive setting word
    # (metastatic) satisfies G57 without tripping G35's staging pattern.
    run_dir = tmp_path / "patient" / "triggers" / "r1"
    out = run_dir / "delivery"
    run_dir.mkdir(parents=True)
    (run_dir / "soc_floor.json").write_text(json.dumps({
        "stage": "metastatic setting",
        "standard": "best supportive care + clinical-trial referral",
    }), encoding="utf-8")
    soc_floor = load_soc_floor(run_dir)
    assert soc_floor is not None
    out.mkdir(parents=True)
    (out / "patient_brief.md").write_text(_render(soc_floor), encoding="utf-8")
    g57 = G57SoCFloorPresentGate().check({"out_dir": str(out)})
    assert g57.status.value == "pass", g57.message
    g35 = G35ClinicalFactProvenanceGate().check({"delivery_dir": str(out)})
    assert g35.status.value != "fail", g35.message
