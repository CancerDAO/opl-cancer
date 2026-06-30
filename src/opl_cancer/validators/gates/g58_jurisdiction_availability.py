"""G58: jurisdiction_availability — for a mainland-CN patient, options must be
labelled by China availability (WARN, non-blocking).

Third hole the jessie review found: the brief mixed China-unreachable frontier
(US ATR/AURKA/CDC7 trials, tarlatamab) with genuinely CN-available options
(domestic sac-TMT TROP2 ADC, anlotinib, durvalumab consolidation, 2L docetaxel)
without telling the patient which is which — the single most useful thing for a
resource-limited family treated inside China. G58 nudges (does not block) the
delivery to carry a China-availability section so unreachable options are labelled
as such.

Deterministic, no LLM, non-blocking (FLAG). Fires only when the patient is
mainland-CN (``profile.json`` ``locale == 'zh'`` / jurisdiction CN). Marker:
``[CN-AVAIL]``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

_CN_MARKER = re.compile(r"\[CN-?AVAIL\]", re.I)
_BRIEF_GLOBS = ("*brief.md", "*brief.html", "patient_brief.html")


# Only keys that actually denote WHERE the patient lives / is treated count for
# jurisdiction. Scanning the full profile JSON (the original bug) false-activated
# on any free-text mention of 中国/mainland/CN — a hospital name, ancestry note,
# or travel history — flipping G58 on for non-CN patients (adversarial review
# 2026-06-30). Scope to location-bearing fields only.
_LOCATION_KEY = re.compile(
    r"locale|country|nation|国籍|residence|现居|居住|地址|address|jurisdiction|"
    r"region|province|省|城市|city|treat.*location|就诊地",
    re.I,
)
_CN_VALUE = re.compile(r"中国|大陆|内地|mainland|\bPRC\b|\bCN\b", re.I)


def _collect_location_values(obj: Any, key_hit: bool = False) -> list[str]:
    """Values living under a location-bearing key (recursively)."""
    out: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += _collect_location_values(v, key_hit or bool(_LOCATION_KEY.search(str(k))))
    elif isinstance(obj, list):
        for v in obj:
            out += _collect_location_values(v, key_hit)
    elif key_hit and obj is not None:
        out.append(str(obj))
    return out


def _is_mainland_cn(patient_dir: Path | None) -> bool:
    if patient_dir is None:
        return False
    p = patient_dir / "profile.json"
    if not p.is_file():
        return False
    try:
        prof = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(prof, dict):
        return False
    if str(prof.get("locale", "")).lower().startswith("zh"):
        return True
    return any(_CN_VALUE.search(v) for v in _collect_location_values(prof))


class G58JurisdictionAvailabilityGate(Gate):
    """Mainland-CN patient → brief should label options by China availability."""

    name = "G58_jurisdiction_availability"
    description = (
        "For a mainland-CN patient, the delivered brief should carry a [CN-AVAIL] "
        "section labelling each surfaced option by China availability (NMPA-approved "
        "/ ChiCTR-recruiting / 博鳌乐城 / trial-only-abroad), so an unreachable US "
        "frontier option is not mistaken for a real choice. Non-blocking (FLAG)."
    )
    failure_mode_code = "AP-AVAIL-UNLABELLED"
    family_id = "completeness"

    def check(self, claim: dict[str, Any]) -> GateResult:
        out = claim.get("out_dir")
        patient_dir = Path(claim["patient_dir"]) if claim.get("patient_dir") else None
        if patient_dir is None and out:
            d = Path(out)
            # out_dir = <patient>/triggers/<run>/delivery → patient is 3 up
            if d.name == "delivery" and d.parent.parent.name == "triggers":
                patient_dir = d.parent.parent.parent
        if not _is_mainland_cn(patient_dir):
            return GateResult(gate=self.name, status=GateStatus.SKIP,
                              message="G58 SKIP — patient is not mainland-CN (or no profile).")
        briefs: list[Path] = []
        if out:
            for g in _BRIEF_GLOBS:
                briefs.extend(Path(out).glob(g))
        if not briefs:
            return GateResult(gate=self.name, status=GateStatus.SKIP,
                              message="G58 SKIP — no delivered brief.")
        for bp in briefs:
            try:
                if _CN_MARKER.search(bp.read_text(encoding="utf-8", errors="replace")):
                    return GateResult(
                        gate=self.name, status=GateStatus.PASS,
                        message="G58 OK — brief carries a [CN-AVAIL] China-availability section.")
            except OSError:
                continue
        return GateResult(
            gate=self.name, status=GateStatus.FAIL, block=False,  # FLAG, non-blocking
            message=(
                "G58 FLAG — mainland-CN patient but no [CN-AVAIL] section: surfaced "
                "options are not labelled by China availability. A resource-limited "
                "family can't tell a domestic-available drug from an abroad-only "
                "trial. Add a China-availability label per option (non-blocking)."
            ),
            evidence={"briefs": [b.name for b in briefs]},
        )
