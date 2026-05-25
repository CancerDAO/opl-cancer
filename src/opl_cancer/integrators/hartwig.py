"""Hartwig Medical Foundation cohort — DUA-gated (no public REST API). Spec §2.5 F5.

Hartwig Medical Foundation operates a pan-cancer WGS + clinical-outcomes
cohort (≈ 5000 metastatic-cancer patients, paired-tumour-normal, deep
clinical annotation including treatment-line + RECIST + survival). The
data is **not** accessible via public REST API; access is granted only
after signing a Data-Access Agreement (DAR-class) and being approved by
the Hartwig Data Access Board.

This integrator stub documents the canonical application path. It does
NOT fabricate a cohort response from training data — per
`memory/feedback_no_offline_only.md`, `fetch()` raises
``IntegratorError`` with the published DAR application URL so the
caller (Aviv / Tyler / Iain) knows the right next step.

Public references:
  * Application portal: https://www.hartwigmedicalfoundation.nl/applications/
  * Data dictionary: https://www.hartwigmedicalfoundation.nl/onderzoek-met-onze-data/
  * Cohort descriptor: Priestley et al. Nature 2019 — PMID: 31645765
"""
from __future__ import annotations

from typing import Any

from .base import Integrator, IntegratorError


_APPLICATION_URL = "https://www.hartwigmedicalfoundation.nl/applications/"
_DATA_DICTIONARY_URL = "https://www.hartwigmedicalfoundation.nl/onderzoek-met-onze-data/"
_DESCRIPTOR_PMID = "31645765"


class HartwigIntegrator(Integrator):
    family = "F5"
    ttl_seconds = 30 * 24 * 3600  # cohort metadata changes slowly; per-key DUA reapply

    async def fetch(self, key: str) -> dict[str, Any]:
        # Hartwig has no public REST endpoint. Surface the DUA path explicitly.
        raise IntegratorError(
            "Hartwig requires a Data-Access Agreement before any cohort query. "
            f"Apply at {_APPLICATION_URL} (Hartwig Data Access Board review, "
            "typical turnaround 6-12 weeks). Cohort descriptor: PMID "
            f"{_DESCRIPTOR_PMID} (Priestley et al. Nature 2019, n≈5000 metastatic-"
            "cancer patients, paired tumour-normal WGS + treatment-line + RECIST "
            f"+ survival). Data dictionary: {_DATA_DICTIONARY_URL}. "
            f"This integrator does not synthesize a Hartwig cohort response from "
            f"training data — requested key={key!r}."
        )
