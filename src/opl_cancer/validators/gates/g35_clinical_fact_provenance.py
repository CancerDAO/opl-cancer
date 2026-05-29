"""G35: clinical_fact_provenance — every measured clinical value must trace to an OCR sidecar.

v2.7.0 (ADR-0026 / session 0d1017d4 fix). The driving incident: the executor
wrote concrete lab values (creatinine 88 "normal", GGT 19, "Child-Pugh A") into
the case **before OCR finished** — i.e. it *fabricated* clinical facts. They were
clinically wrong and dangerous. No gate caught it because:

* the fakery sniffer only matched *placeholder* language (TODO / 占位符), not a
  confidently-stated but invented value;
* nothing required a clinical value to be anchored to its source document.

G35 closes that hole. It is a **no-LLM, mechanical** gate. For any text that
asserts a measured clinical value — lab numbers (creatinine / GGT / AST / ALT /
bilirubin / eGFR / LDH / tumour markers), organ-function scores (Child-Pugh /
ECOG / NYHA / LVEF), staging (TNM / stage), or a molecular call (KRAS / NRAS /
BRAF / MSI / TMB / HRD with a state) — the asserting line MUST carry a resolvable
``[[src:<relative-path>#<locator>]]`` provenance anchor pointing to an existing
file under the patient directory (canonical: an ``ocr/`` sidecar). A value with
no anchor, or an anchor whose target file does not exist, FAILs and BLOCKs.

Grammar (shared with cancer-buddy-organize, documented in
``references/patient-data-layout.md``):

    [[src:ocr/05_labs_2024-05.txt#L12]]
    [[src:01_当前状态/report.pdf]]

Unknown values are written ``UNKNOWN`` (or 未知 / 未查) — that is honest and
passes. Inventing a number to fill a gap is what this gate exists to stop.

Caller passes one of:
  * ``clinical_text`` — raw markdown / text to scan (e.g. case_text.md), OR
  * ``case_text_path`` — path to a file to read, OR
  * ``profile`` — a profile.json dict (clinical fields scanned), OR
  * ``patient_dir`` — resolves ``case_text.md`` + ``profile.json`` under it.

``patient_dir`` is required to resolve anchor targets; if absent we still flag
unanchored values (the more dangerous case) but cannot verify target existence.
Lines tagged ``[BACKGROUND]`` are exempt (epidemiology prose, not a patient fact).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

# ── value patterns that assert a *measured* clinical fact ───────────────────
# Each pattern targets a value-bearing token, not a bare mention. We are
# deliberately conservative: a mention without a number/state (e.g. "肌酐 is a
# renal marker") does not fire; "肌酐 88" does.
_LAB_NAMES = (
    r"肌酐|creatinine|GGT|γ-?GT|谷氨酰转肽酶|AST|ALT|谷丙转氨酶|谷草转氨酶|"
    r"总胆红素|bilirubin|胆红素|eGFR|肌酐清除|LDH|乳酸脱氢酶|"
    r"AFP|甲胎蛋白|CEA|癌胚抗原|CA[\s-]?125|CA[\s-]?199|CA[\s-]?15[\s-]?3|PSA|"
    r"白蛋白|albumin|血红蛋白|hemoglobin|hgb|血小板|platelet|中性粒|"
    r"白细胞|WBC|嗜中性|ANC"
)
_VALUE_TOKEN = r"[:：=\s]*[<>≤≥]?\s*\d+(?:\.\d+)?"

_CLINICAL_VALUE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("lab_value", re.compile(rf"(?:{_LAB_NAMES})\s*{_VALUE_TOKEN}", re.IGNORECASE)),
    # organ-function / performance scores with a grade
    ("organ_score", re.compile(
        r"(?:Child[\s-]?Pugh\s*[:：]?\s*[ABC]|ECOG\s*[:：]?\s*[0-5]|"
        r"NYHA\s*[:：]?\s*(?:I{1,3}|IV)|LVEF\s*[:：]?\s*\d{1,3}\s*%?|"
        r"KPS\s*[:：]?\s*\d{1,3})",
        re.IGNORECASE,
    )),
    # staging
    ("staging", re.compile(
        r"\b[cpyr]?T[0-4][a-c]?\s*N[0-3][a-c]?\s*M[01][a-c]?\b|"
        r"\b(?:stage|分期)\s*[:：]?\s*(?:IV|III|II|I|0)\b",
        re.IGNORECASE,
    )),
    # molecular call with an explicit state (mut/amp/pos/neg/wild-type/H/L)
    ("molecular_call", re.compile(
        r"\b(?:KRAS|NRAS|BRAF|EGFR|ALK|ROS1|HER2|ERBB2|TP53|ATM|BRCA[12]|MSI|TMB|HRD|PD-?L1)\b"
        r"[^\n]{0,24}?\b(?:G\d+[A-Z]|V600[A-Z]|exon\s*\d+|突变|mut(?:ation|ant|ated)?|"
        r"扩增|amplif\w*|阳性|阴性|positive|negative|野生型|wild[\s-]?type|"
        r"MSI-?[HL]|MSS|[HL]igh|[HL]ow|≥?\s*\d+\s*%)",
        re.IGNORECASE,
    )),
]

# A [[src:path#locator]] anchor anywhere on the line satisfies provenance.
_SRC_ANCHOR_RE = re.compile(r"\[\[src:\s*([^\]\#]+?)(?:#([^\]]+))?\s*\]\]")
_BACKGROUND_TAG_RE = re.compile(r"\[BACKGROUND\]", re.IGNORECASE)
# Honest "we don't know" tokens — these are the CORRECT thing to write for a
# missing value and must never be flagged.
_UNKNOWN_RE = re.compile(
    r"\b(?:UNKNOWN|N/?A|未知|未查|未检测|未做|待查|not\s+tested|not\s+reported|pending)\b",
    re.IGNORECASE,
)

# profile.json fields whose values are clinical facts requiring provenance.
_PROFILE_CLINICAL_FIELDS = (
    "labs", "lab_values", "child_pugh", "ecog", "lvef", "nyha", "kps",
    "stage", "tnm", "biomarkers", "molecular", "ngs", "organ_function",
)


def _scan_line_for_values(line: str) -> list[str]:
    """Return the kinds of clinical value asserted on the line (empty = none)."""
    if _BACKGROUND_TAG_RE.search(line) or _UNKNOWN_RE.search(line):
        return []
    kinds: list[str] = []
    for kind, pat in _CLINICAL_VALUE_PATTERNS:
        if pat.search(line):
            kinds.append(kind)
    return kinds


def _anchor_targets_exist(line: str, patient_dir: Path | None) -> tuple[bool, list[str]]:
    """True if the line carries ≥1 [[src:...]] anchor that resolves to a file.

    Returns (ok, unresolved_targets). When patient_dir is None we accept the
    presence of any anchor (cannot verify target existence) but still report it.
    """
    anchors = _SRC_ANCHOR_RE.findall(line)
    if not anchors:
        return False, []
    if patient_dir is None:
        return True, []  # anchor present; existence unverifiable
    unresolved: list[str] = []
    any_ok = False
    for rel, _loc in anchors:
        rel = rel.strip()
        target = (patient_dir / rel)
        if target.exists():
            any_ok = True
        else:
            unresolved.append(rel)
    return any_ok, unresolved


def _gather_clinical_lines(claim: dict[str, Any]) -> tuple[list[tuple[str, int, str]], Path | None]:
    """Collect (origin, line_no, text) lines that may assert clinical facts."""
    patient_dir: Path | None = None
    if claim.get("patient_dir"):
        patient_dir = Path(claim["patient_dir"])

    lines: list[tuple[str, int, str]] = []

    def _add_text(origin: str, text: str) -> None:
        for i, ln in enumerate(text.splitlines(), start=1):
            lines.append((origin, i, ln))

    if claim.get("clinical_text"):
        _add_text("clinical_text", str(claim["clinical_text"]))
    if claim.get("case_text_path"):
        p = Path(claim["case_text_path"])
        if p.is_file():
            _add_text(str(p), p.read_text(encoding="utf-8"))
    if patient_dir is not None:
        ct = patient_dir / "case_text.md"
        if ct.is_file() and not claim.get("case_text_path"):
            _add_text(str(ct), ct.read_text(encoding="utf-8"))

    # profile.json clinical fields → flatten to "field: value" lines.
    profile = claim.get("profile")
    if profile is None and patient_dir is not None:
        pj = patient_dir / "profile.json"
        if pj.is_file():
            try:
                profile = json.loads(pj.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                profile = None
    if isinstance(profile, dict):
        for field in _PROFILE_CLINICAL_FIELDS:
            if field in profile and profile[field] not in (None, "", [], {}):
                lines.append(("profile.json:" + field, 0, f"{field}: {json.dumps(profile[field], ensure_ascii=False)}"))
    return lines, patient_dir


class G35ClinicalFactProvenanceGate(Gate):
    """Every asserted clinical value must carry a resolvable [[src:...]] anchor."""

    name = "G35_clinical_fact_provenance"
    description = (
        "Measured clinical values (labs / organ-function scores / staging / "
        "molecular calls) must each carry a [[src:<sidecar>#<locator>]] anchor "
        "resolving to an existing patient-dir file. Stops the 'fabricated "
        "creatinine before OCR' failure mode. Unknown values must be written "
        "UNKNOWN, never invented."
    )
    failure_mode_code = "A3-FABRICATED-CLINICAL-FACT"
    family_id = "provenance"

    def check(self, claim: dict[str, Any]) -> GateResult:
        lines, patient_dir = _gather_clinical_lines(claim)
        if not lines:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message="G35 SKIP — no clinical text / profile fields to scan.",
            )

        violations: list[dict[str, Any]] = []
        scanned = 0
        for origin, ln, text in lines:
            kinds = _scan_line_for_values(text)
            if not kinds:
                continue
            scanned += 1
            ok, unresolved = _anchor_targets_exist(text, patient_dir)
            if not ok:
                reason = (
                    f"anchor target(s) not found under patient_dir: {unresolved}"
                    if unresolved
                    else "no [[src:...]] provenance anchor"
                )
                violations.append({
                    "origin": origin,
                    "line": ln,
                    "kinds": kinds,
                    "excerpt": text.strip()[:160],
                    "reason": reason,
                })

        if violations:
            sample = "; ".join(
                f"{v['origin']}:L{v['line']} {v['excerpt']!r} ({v['reason']})"
                for v in violations[:4]
            )
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"G35 FAIL — {len(violations)} clinical value(s) asserted with "
                    f"no resolvable [[src:...]] provenance anchor. These may be "
                    f"fabricated. First: {sample}. Write UNKNOWN for any value not "
                    "read from a source document."
                ),
                evidence={"violations": violations[:20], "scanned_value_lines": scanned},
            )

        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=(
                f"G35 OK — {scanned} clinical value line(s) all carry resolvable "
                "[[src:...]] provenance anchors."
            ),
            evidence={"scanned_value_lines": scanned},
        )
