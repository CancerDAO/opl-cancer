"""G17: meta-analysis I² heterogeneity policy. Spec §7 G17 / §6.5 F4.

Failure mode F4 — meta-analysis hides heterogeneity. Rules:
  * I² > 50% → MUST use random-effects model (not fixed). BLOCK otherwise.
  * I² > 75% → MUST additionally carry a "高异质性,池化可疑" / "high heterogeneity,
    pooling questionable" warning_marker. BLOCK otherwise.

I² is read from ``claim.meta_analysis.i_squared`` (float, 0.0-1.0 or 0-100).
"""
from __future__ import annotations

import re
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

_HIGH_HETERO_MARKER = re.compile(
    r"(高异质性[,，]?\s*池化可疑|high\s+heterogeneity[,;:]?\s*pooling\s+questionable)",
    re.IGNORECASE,
)


def _normalise_i2(value: Any) -> float | None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v < 0:
        return None
    # accept either 0.0-1.0 or 0-100; normalise to 0-100
    return v if v > 1.0 else v * 100.0


class G17MetaI2PolicyGate(Gate):
    name = "G17_meta_i2_policy"
    description = "Meta-analysis with I²>50% needs random-effects; I²>75% needs heterogeneity marker."
    failure_mode_code = "F4"

    def check(self, claim: dict[str, Any]) -> GateResult:
        meta = claim.get("meta_analysis") or {}
        if not meta:
            return GateResult(
                gate=self.name, status=GateStatus.SKIP, message="no meta_analysis on claim"
            )
        i2 = _normalise_i2(meta.get("i_squared") or meta.get("i2"))
        if i2 is None:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=f"meta_analysis.i_squared missing or unparseable: {meta.get('i_squared')!r}",
            )
        model = (meta.get("model") or "").lower()
        marker_text = " ".join(
            str(meta.get(k, ""))
            for k in ("warning_marker", "note", "interpretation", "discussion")
        )
        problems: list[str] = []
        if i2 > 50.0 and "random" not in model:
            problems.append(
                f"I²={i2:.1f}% > 50% but model={model!r} (random-effects required)"
            )
        if i2 > 75.0 and not _HIGH_HETERO_MARKER.search(marker_text):
            problems.append(
                f"I²={i2:.1f}% > 75% but no 高异质性 / high-heterogeneity marker present"
            )
        if problems:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message="; ".join(problems),
                evidence={"i_squared_pct": i2, "model": model, "problems": problems},
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=f"I²={i2:.1f}% — policy satisfied (model={model!r})",
            evidence={"i_squared_pct": i2, "model": model},
        )
