"""G8: Level-3/4 permission requires risk_disclosure_card. Spec §7 G8 / §6.5 C2.

Failure mode C2 — high-stakes recommendation lacks risk-disclosure card.
Per spec §3.4 permission ladder:
  * Level 1 — patient-education only (no card required)
  * Level 2 — informational synthesis (no card required)
  * Level 3 — symptom plan / supportive care: REQUIRES risk_disclosure_card
  * Level 4 — anti-tumour / dose modification: REQUIRES risk_disclosure_card
               (card MUST also include alternative options + watchdog signs)

G8 BLOCKs when level ∈ {3, 4} and the card is missing OR empty OR (for level
4) missing one of the mandatory sub-fields.
"""
from __future__ import annotations

from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

_LEVEL4_REQUIRED = ("risks", "benefits", "alternatives", "watchdog_signs")
_LEVEL3_REQUIRED = ("risks", "watchdog_signs")


def _card_missing_fields(card: dict[str, Any], required: tuple[str, ...]) -> list[str]:
    return [k for k in required if not card.get(k)]


class G8Level34DisclosureGate(Gate):
    name = "G8_level34_disclosure"
    description = "Level-3/4 claims must carry a populated risk_disclosure_card."
    failure_mode_code = "C2"

    def check(self, claim: dict[str, Any]) -> GateResult:
        level = claim.get("permission_level")
        try:
            level_int = int(level) if level is not None else None
        except (TypeError, ValueError):
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=f"permission_level not parseable as int: {level!r}",
            )
        if level_int not in (3, 4):
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message=f"permission_level={level_int} — card not required",
            )
        card = claim.get("risk_disclosure_card")
        if not card or not isinstance(card, dict):
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"permission_level={level_int} requires risk_disclosure_card; "
                    f"got {type(card).__name__}={card!r}"
                ),
            )
        required = _LEVEL4_REQUIRED if level_int == 4 else _LEVEL3_REQUIRED
        missing = _card_missing_fields(card, required)
        if missing:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"permission_level={level_int} card missing required fields: {missing}"
                ),
                evidence={"missing": missing, "required": list(required)},
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=f"L{level_int} risk_disclosure_card complete",
        )
