"""External data source integrators. Spec §2.5.

Re-exports the integrator class registry so callers can do
``from opl_cancer.integrators import HartwigIntegrator`` etc. without
remembering the per-module file name. Modules continue to live under
their family-specific files (``hartwig.py`` / ``isrctn.py`` / …) so
the preflight import-loop in ``cli.py`` still verifies one module per
integrator.

v1.3.1 — 7 new integrators added (Hartwig + BeatAML + ICGC + ISRCTN +
EU-CTR + EMA EAP + Open Targets) bringing the wired total to 28.

v1.4.0 — HKCTR (Hong Kong) added; wired total 28 → 29.
"""
from __future__ import annotations

from .arrayexpress import ArrayExpressIntegrator
from .base import Integrator, IntegratorError
from .beataml import BeatAMLIntegrator
from .cbioportal import CBioPortalIntegrator
from .ccle import CCLEIntegrator
from .chictr import ChiCTRIntegrator
from .civic import CIViCIntegrator
from .clinicaltrials import ClinicalTrialsGovIntegrator
from .clinvar import ClinVarIntegrator
from .depmap import DepMapIntegrator
from .ema_eap import EMAEAPIntegrator
from .eu_ctr import EUCTRIntegrator
from .fda_eap import FDAEAPIntegrator
from .gdc import GDCIntegrator
from .geo import GEOIntegrator
from .gnomad import GnomADIntegrator
from .hartwig import HartwigIntegrator
from .hkctr import HKCTRIntegrator
from .icgc import ICGCIntegrator
from .isrctn import ISRCTNIntegrator
from .nccn import NCCNPageIndexIntegrator
from .nmpa_eap import NMPAEAPIntegrator
from .oncokb import OncoKBIntegrator
from .open_targets import OpenTargetsIntegrator
from .paperqa import PaperQA2Integrator
from .pubmed import PubMedIntegrator
from .retractiondb import RetractionDBIntegrator
from .rxnorm import RxNormIntegrator
from .sra import SRAIntegrator
from .unpaywall import UnpaywallIntegrator

__all__ = [
    "ArrayExpressIntegrator",
    "BeatAMLIntegrator",
    "CBioPortalIntegrator",
    "CCLEIntegrator",
    "ChiCTRIntegrator",
    "CIViCIntegrator",
    "ClinicalTrialsGovIntegrator",
    "ClinVarIntegrator",
    "DepMapIntegrator",
    "EMAEAPIntegrator",
    "EUCTRIntegrator",
    "FDAEAPIntegrator",
    "GDCIntegrator",
    "GEOIntegrator",
    "GnomADIntegrator",
    "HartwigIntegrator",
    "HKCTRIntegrator",
    "ICGCIntegrator",
    "ISRCTNIntegrator",
    "Integrator",
    "IntegratorError",
    "NCCNPageIndexIntegrator",
    "NMPAEAPIntegrator",
    "OncoKBIntegrator",
    "OpenTargetsIntegrator",
    "PaperQA2Integrator",
    "PubMedIntegrator",
    "RetractionDBIntegrator",
    "RxNormIntegrator",
    "SRAIntegrator",
    "UnpaywallIntegrator",
]
