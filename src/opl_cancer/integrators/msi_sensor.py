"""MSIsensor / MSIsensor-pro wrapper. v2.2 ADR-0022 — F_BIO family.

source_skill: BioTender-max/awesome-bio-agent-skills/bio-msi-detection
original_license: CC0-1.0

MSI (microsatellite instability) is one of the canonical pan-cancer
immunotherapy biomarkers — MSI-H ≥ 10% unstable sites, MSI-L 3.5-10%, MSS
< 3.5% (MSIsensor-pro default thresholds). Status drives pembrolizumab
tissue-agnostic approval (KEYNOTE-158) and is part of CRC Lynch screening.

Key format: ``tumor:<bam_path>:normal:<bam_path>``

Real execution requires `msisensor-pro` (or legacy `msisensor`) + samtools
on PATH plus a reference microsatellite list. The wrapper is deterministic —
it shells out, parses the output table, and returns the canonical payload.

no-silent-fallback policy — when CLI is absent in live mode, raise
IntegratorError. Mock mode (`mock_mode=True`) is for unit tests only.
"""
from __future__ import annotations

import json
import shutil
from typing import Any

from .base import Integrator, IntegratorError
from .cache import IntegratorCache


_MSI_H_THRESHOLD_DEFAULT = 10.0  # ≥ → MSI-H
_MSI_L_THRESHOLD_DEFAULT = 3.5   # ≥ → MSI-L; < → MSS


def classify_msi_status(
    *,
    msi_score: float,
    msi_h_threshold: float = _MSI_H_THRESHOLD_DEFAULT,
    msi_l_threshold: float = _MSI_L_THRESHOLD_DEFAULT,
) -> dict[str, Any]:
    """Classify MSI status from MSIsensor-pro pct-unstable score.

    Returns: {msi_score, status, threshold_msi_h, threshold_msi_l}.
    """
    if msi_score < 0:
        raise ValueError(f"msi_score must be >= 0, got {msi_score}")
    if msi_score >= msi_h_threshold:
        status = "MSI-H"
    elif msi_score >= msi_l_threshold:
        status = "MSI-L"
    else:
        status = "MSS"
    return {
        "msi_score": float(msi_score),
        "status": status,
        "threshold_msi_h": msi_h_threshold,
        "threshold_msi_l": msi_l_threshold,
    }


class MSIsensorIntegrator(Integrator):
    """Wrapper around msisensor / msisensor-pro CLI.

    family = ``F_BIO``. TTL 30 days (MSI status is sequencing-pinned).
    """

    family = "F_BIO"
    ttl_seconds = 30 * 24 * 3600

    def __init__(
        self,
        cache: IntegratorCache | None = None,
        *,
        mock_mode: bool = False,
        mock_score: float = 18.5,
        mock_sites: int = 150,
        binary_name: str = "msisensor-pro",
    ) -> None:
        super().__init__(cache=cache)
        self.mock_mode = mock_mode
        self.mock_score = float(mock_score)
        self.mock_sites = int(mock_sites)
        self.binary_name = binary_name

    async def fetch(self, key: str) -> dict[str, Any]:
        parts = key.split(":")
        if len(parts) != 4 or parts[0] != "tumor" or parts[2] != "normal":
            raise IntegratorError(
                f"MSIsensor: expected tumor:<bam>:normal:<bam>, got {key!r}"
            )
        tumor_bam, normal_bam = parts[1], parts[3]

        if self.mock_mode:
            cls = classify_msi_status(msi_score=self.mock_score)
            return {
                **cls,
                "n_sites_examined": self.mock_sites,
                "n_sites_unstable": int(round(self.mock_sites * self.mock_score / 100)),
                "engine": "msisensor-mock",
                "tumor_bam": tumor_bam,
                "normal_bam": normal_bam,
                "provenance": "mock_mode=True; deterministic stub for unit tests",
            }

        binary = shutil.which(self.binary_name) or shutil.which("msisensor")
        if not binary:
            raise IntegratorError(
                f"MSIsensor: neither {self.binary_name!r} nor 'msisensor' is on PATH. "
                "Install MSIsensor-pro (https://github.com/xjtu-omics/msisensor-pro) "
                "or enable mock_mode=True for tests. No silent fallback "
                "(no-silent-fallback policy)."
            )

        # Real CLI call delegated to _run_cli (kept separate so unit tests can
        # patch it). We do NOT shell-out in this module by default — the
        # surrounding compute layer (NativeAnalysisRunner) is the real
        # production path; this integrator is the interpretation wrapper.
        result = await self._run_cli(binary=binary, tumor=tumor_bam, normal=normal_bam)
        return result

    async def _run_cli(
        self, *, binary: str, tumor: str, normal: str
    ) -> dict[str, Any]:
        """Real msisensor-pro shell-out. Subclasses / tests may override.

        Default implementation raises — production runs should set up a
        compute container and override this method.
        """
        raise IntegratorError(
            "MSIsensor: _run_cli is the abstract live hook. Wire a compute "
            "container (NativeAnalysisRunner) or override this method in a "
            "subclass. Mock mode is the only built-in path."
        )

    def parse_output_table(self, raw: str) -> dict[str, Any]:
        """Parse msisensor-pro tabular stdout to canonical payload.

        Expected format (tab-separated):
            Total_Number_of_Sites   Number_of_Somatic_Sites   %
            150                     27                        18.00
        """
        lines = [ln for ln in raw.strip().splitlines() if ln.strip()]
        if len(lines) < 2:
            raise IntegratorError(
                f"MSIsensor: output has < 2 lines (header + data): {raw!r}"
            )
        data_line = lines[1].strip()
        cols = data_line.split()
        if len(cols) < 3:
            raise IntegratorError(
                f"MSIsensor: data row has < 3 cols: {data_line!r}"
            )
        try:
            n_sites = int(cols[0])
            n_unstable = int(cols[1])
            score = float(cols[2])
        except (ValueError, IndexError) as e:
            raise IntegratorError(f"MSIsensor: failed to parse {data_line!r}: {e}") from e
        cls = classify_msi_status(msi_score=score)
        return {
            **cls,
            "n_sites_examined": n_sites,
            "n_sites_unstable": n_unstable,
            "engine": "msisensor-pro",
            "raw_stdout": raw,
        }


# Public re-export for the compute layer
__all__ = ["MSIsensorIntegrator", "classify_msi_status"]


def _self_test() -> None:
    """Quick sanity check (also serves as doc)."""
    print(json.dumps(classify_msi_status(msi_score=22.5), indent=2))


if __name__ == "__main__":  # pragma: no cover
    _self_test()
