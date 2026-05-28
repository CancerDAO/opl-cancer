"""TMB harmonization wrapper. v2.2 ADR-0022 — F_BIO family.

source_skill: BioTender-max/awesome-bio-agent-skills/bio-tumor-mutational-burden
original_license: CC0-1.0

TMB (tumor mutational burden) → KEYNOTE-158 cutoff is ≥ 10 mut/Mb for
TMB-H tissue-agnostic pembrolizumab. But panel vendors compute on different
effective-territory sizes, so raw count → mut/Mb is panel-specific:

* TSO500 (Illumina)     : 1.94 Mb effective
* FoundationOne CDx     : 0.8 Mb effective
* MSK-IMPACT-468        : 1.22 Mb effective
* MSK-IMPACT-505        : 1.41 Mb effective
* Caris MI Profile      : 1.4 Mb effective
* WES (per Buchhalter 2019 / Chalmers 2017): 30 Mb effective

This wrapper exposes:
1. ``classify_tmb_status(tmb_per_mb)`` — pure threshold classifier
2. ``harmonize_tmb(n_mutations | tmb_per_mb, panel)`` — vendor-aware
3. ``TMBHarmonizationIntegrator`` — Integrator-compatible cached wrapper

Key format: ``panel:<vendor>:(n_mutations|tmb_per_mb):<number>``
"""
from __future__ import annotations

from typing import Any

from .base import Integrator, IntegratorError
from .cache import IntegratorCache


# Panel effective-territory (Mb). Numbers from each vendor's published spec
# (TSO500 v1 / FoundationOne v3 / MSK-IMPACT-468 v2 etc.). Update on vendor
# refresh.
PANEL_FOOTPRINTS_MB: dict[str, float] = {
    "TSO500": 1.94,
    "FoundationOne": 0.8,
    "FoundationOneCDx": 0.8,
    "MSK-IMPACT-468": 1.22,
    "MSK-IMPACT-505": 1.41,
    "Caris-MI": 1.4,
    "Caris": 1.4,
    "WES": 30.0,
    "WGS": 30.0,  # restricted to coding for TMB
}


TMB_H_THRESHOLD = 10.0  # mut/Mb — KEYNOTE-158 cutoff (FDA pembrolizumab pan-tumor)


def classify_tmb_status(*, tmb_per_mb: float) -> dict[str, Any]:
    """Pure threshold classifier. ≥ 10 → TMB-H, else TMB-L."""
    if tmb_per_mb < 0:
        raise ValueError(f"tmb_per_mb must be >= 0, got {tmb_per_mb}")
    return {
        "tmb_per_mb": float(tmb_per_mb),
        "status": "TMB-H" if tmb_per_mb >= TMB_H_THRESHOLD else "TMB-L",
        "threshold_used": TMB_H_THRESHOLD,
    }


def harmonize_tmb(
    *,
    panel: str,
    n_mutations: int | None = None,
    tmb_per_mb: float | None = None,
) -> dict[str, Any]:
    """Convert vendor input to the canonical 10/Mb-thresholded record.

    Either ``n_mutations`` (raw count) or ``tmb_per_mb`` (already normalized)
    must be supplied.
    """
    if panel not in PANEL_FOOTPRINTS_MB:
        raise IntegratorError(
            f"TMB: unknown panel {panel!r}. Known: {sorted(PANEL_FOOTPRINTS_MB)}"
        )
    effective_mb = PANEL_FOOTPRINTS_MB[panel]
    if tmb_per_mb is not None:
        per_mb = float(tmb_per_mb)
    elif n_mutations is not None:
        per_mb = float(n_mutations) / effective_mb
    else:
        raise IntegratorError(
            "TMB: must supply either n_mutations or tmb_per_mb"
        )
    cls = classify_tmb_status(tmb_per_mb=per_mb)
    return {
        **cls,
        "panel": panel,
        "effective_mb": effective_mb,
        "n_mutations_input": n_mutations,
        "tmb_per_mb_input": tmb_per_mb,
    }


class TMBHarmonizationIntegrator(Integrator):
    """Cached vendor-aware TMB harmonizer.

    family = ``F_BIO``. TTL 30 days.
    """

    family = "F_BIO"
    ttl_seconds = 30 * 24 * 3600

    def __init__(
        self,
        cache: IntegratorCache | None = None,
    ) -> None:
        super().__init__(cache=cache)

    async def fetch(self, key: str) -> dict[str, Any]:
        parts = key.split(":")
        if len(parts) != 4 or parts[0] != "panel":
            raise IntegratorError(
                "TMB: expected panel:<vendor>:(n_mutations|tmb_per_mb):<number>, "
                f"got {key!r}"
            )
        panel, mode, value_raw = parts[1], parts[2], parts[3]
        try:
            value = float(value_raw)
        except ValueError as e:
            raise IntegratorError(f"TMB: value {value_raw!r} not numeric") from e
        if mode == "n_mutations":
            out = harmonize_tmb(panel=panel, n_mutations=int(value))
        elif mode == "tmb_per_mb":
            out = harmonize_tmb(panel=panel, tmb_per_mb=value)
        else:
            raise IntegratorError(
                f"TMB: unknown mode {mode!r}, expected 'n_mutations' or 'tmb_per_mb'"
            )
        out["engine"] = "tmb-harmonization-v1"
        out["key"] = key
        return out


__all__ = [
    "TMBHarmonizationIntegrator",
    "PANEL_FOOTPRINTS_MB",
    "TMB_H_THRESHOLD",
    "classify_tmb_status",
    "harmonize_tmb",
]
