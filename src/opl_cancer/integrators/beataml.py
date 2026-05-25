"""BeatAML 2.0 cohort — Vizome portal-hosted, DAR-gated for patient-level. Spec §2.5 F5.

BeatAML 2.0 is the OHSU-led functional + multi-omics AML cohort (n=562
patients, paired WES + bulk RNA-seq + ex-vivo drug-response screen on 122
small molecules). Aggregated views (drug-response heatmaps, mutation
prevalence) are public via the Vizome interactive portal; patient-level
joined drug-response × omics × clinical data require a Data Access
Request through the BeatAML Data Access Committee.

This integrator stub documents the public + DAR paths. Per
`memory/feedback_no_offline_only.md`, `fetch()` raises
``IntegratorError`` rather than synthesizing a cohort response.

Public references:
  * Vizome portal: https://vizome.org/
  * BeatAML 2.0 descriptor: Bottomly et al. Cancer Cell 2022 — PMID: 36055236
  * BeatAML 1.0 descriptor: Tyner et al. Nature 2018 — PMID: 30333627
  * DAR submission: contact via vizome.org → Data Access
"""
from __future__ import annotations

from typing import Any

from .base import Integrator, IntegratorError


_PORTAL_URL = "https://vizome.org/"
_DESCRIPTOR_PMID_V2 = "36055236"  # Bottomly et al. Cancer Cell 2022 — BeatAML 2.0
_DESCRIPTOR_PMID_V1 = "30333627"  # Tyner et al. Nature 2018 — BeatAML 1.0


class BeatAMLIntegrator(Integrator):
    family = "F5"
    ttl_seconds = 30 * 24 * 3600  # cohort metadata cadence

    async def fetch(self, key: str) -> dict[str, Any]:
        # Vizome interactive portal has no programmatic REST API for patient-
        # level joined data; aggregated views are HTML/JS only. Surface the
        # DAR path explicitly.
        raise IntegratorError(
            "BeatAML 2.0 patient-level data requires a Data Access Request via "
            f"the Vizome portal at {_PORTAL_URL}. Cohort: n=562 AML patients, "
            "paired WES + bulk RNA-seq + ex-vivo drug-response screen on 122 "
            f"small molecules. Descriptor: PMID {_DESCRIPTOR_PMID_V2} (Bottomly "
            f"et al. Cancer Cell 2022, BeatAML 2.0); PMID {_DESCRIPTOR_PMID_V1} "
            "(Tyner et al. Nature 2018, BeatAML 1.0). Aggregated views are "
            "browsable interactively but no public REST API. This integrator "
            "does not synthesize a BeatAML cohort response from training data — "
            f"requested key={key!r}."
        )
