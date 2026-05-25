"""ICGC / ICGC ARGO data portal — controlled-access cohort. Spec §2.5 F5 + F6 hybrid.

The International Cancer Genome Consortium (ICGC) Data Portal hosts
pan-cancer somatic / germline / clinical data from ~50 cancer projects.
The current platform (ICGC ARGO + DCC v6) splits access:

  * Aggregated, de-identified summary statistics → public via DCC API
    (https://dcc.icgc.org/api/v1/) and ICGC ARGO Songa / Score / Maestro.
  * Patient-level raw sequencing reads + clinical → EGA (European Genome-
    phenome Archive) controlled-access; requires DAC approval (DAC =
    Data Access Committee, per-project + central EGA review).

This integrator stub does not fabricate a cohort response. It raises
``IntegratorError`` pointing at the canonical access path. A later v1.4
follow-on may wire the public-aggregate DCC API for population-frequency
queries only, leaving patient-level on EGA-DAR pathway.

Public references:
  * Data portal: https://dcc.icgc.org/
  * ICGC ARGO: https://platform.icgc-argo.org/
  * EGA controlled-access: https://ega-archive.org/dac
  * Descriptor: ICGC/TCGA Pan-Cancer Analysis of Whole Genomes Consortium,
    Nature 2020 — PMID: 32025007
"""
from __future__ import annotations

from typing import Any

from .base import Integrator, IntegratorError


_DCC_URL = "https://dcc.icgc.org/"
_ARGO_URL = "https://platform.icgc-argo.org/"
_EGA_DAC_URL = "https://ega-archive.org/dac"
_DESCRIPTOR_PMID = "32025007"  # ICGC/TCGA PCAWG, Nature 2020


class ICGCIntegrator(Integrator):
    family = "F5"
    ttl_seconds = 30 * 24 * 3600

    async def fetch(self, key: str) -> dict[str, Any]:
        raise IntegratorError(
            "ICGC data has two access tiers: aggregated population-frequency "
            f"queries via the public DCC API ({_DCC_URL}api/v1/), and patient-"
            "level raw + clinical via EGA controlled-access (per-project DAC "
            f"approval at {_EGA_DAC_URL}). The current ICGC ARGO programme is "
            f"accessible at {_ARGO_URL}. Descriptor: PMID {_DESCRIPTOR_PMID} "
            "(ICGC/TCGA Pan-Cancer Analysis of Whole Genomes, Nature 2020). "
            "This integrator stub does not fabricate a cohort response from "
            "training data — v1.4 may wire the public-aggregate DCC tier "
            "directly; patient-level joining will continue to require EGA-"
            f"DAR. Requested key={key!r}."
        )
