"""G11 contract: every integrator MUST raise IntegratorError on API failure
(no silent fallback). Spec §7 G11 / D3.

Two parameterised sweeps over all 13 P1 integrators:
- HTTP 500 → IntegratorError
- Network error (httpx.ConnectError) → IntegratorError

Plus a runtime check on the G11 gate flag.
"""
from __future__ import annotations

from typing import Any, Callable

import httpx
import pytest
import respx
from httpx import Response

from opl_cancer.integrators.base import Integrator, IntegratorError
from opl_cancer.integrators.cbioportal import CBioPortalIntegrator
from opl_cancer.integrators.chictr import ChiCTRIntegrator
from opl_cancer.integrators.civic import CIViCIntegrator
from opl_cancer.integrators.clinicaltrials import ClinicalTrialsGovIntegrator
from opl_cancer.integrators.clinvar import ClinVarIntegrator
from opl_cancer.integrators.fda_eap import FDAEAPIntegrator
from opl_cancer.integrators.gdc import GDCIntegrator
from opl_cancer.integrators.gnomad import GnomADIntegrator
from opl_cancer.integrators.nmpa_eap import NMPAEAPIntegrator
from opl_cancer.integrators.pubmed import PubMedIntegrator
from opl_cancer.integrators.retractiondb import RetractionDBIntegrator
from opl_cancer.integrators.rxnorm import RxNormIntegrator
from opl_cancer.integrators.unpaywall import UnpaywallIntegrator
from opl_cancer.validators.gates.g11_no_silent_fallback import G11NoSilentFallbackGate
from opl_cancer.validators.mechanical_gates import GateStatus

# (factory, url_pattern, fetch_key) — 13 P1 integrators
_INTEGRATOR_CASES: list[tuple[Callable[[], Integrator], str, str]] = [
    (lambda: PubMedIntegrator(cache=None), r".*eutils\.ncbi.*", "PMID:1"),
    (
        lambda: UnpaywallIntegrator(cache=None, contact_email="t@t"),
        r".*unpaywall.*",
        "DOI:10.1/x",
    ),
    (lambda: RetractionDBIntegrator(cache=None), r".*crossref.*", "DOI:10.1/x"),
    (lambda: ClinicalTrialsGovIntegrator(cache=None), r".*clinicaltrials\.gov.*", "NCT:NCT01"),
    (lambda: ChiCTRIntegrator(cache=None), r".*chictr.*", "search:x"),
    (lambda: CIViCIntegrator(cache=None), r".*civicdb.*", "EGFR:L858R"),
    (lambda: ClinVarIntegrator(cache=None), r".*eutils\.ncbi.*", "variant:EGFR L858R"),
    (lambda: GnomADIntegrator(cache=None), r".*gnomad.*", "variant:1-1-A-T:GRCh38"),
    (lambda: CBioPortalIntegrator(cache=None), r".*cbioportal.*", "mutations:lihc_tcga:TP53"),
    (lambda: GDCIntegrator(cache=None), r".*gdc\.cancer.*", "project:TCGA-LIHC"),
    (lambda: FDAEAPIntegrator(cache=None), r".*api\.fda\.gov.*", "search:x"),
    (lambda: NMPAEAPIntegrator(cache=None), r".*nmpa.*", "search:x"),
    (lambda: RxNormIntegrator(cache=None), r".*rxnav.*", "brand:tylenol"),
]


@pytest.mark.parametrize("factory,pattern,key", _INTEGRATOR_CASES)
@respx.mock
async def test_g11_integrator_raises_on_500(
    factory: Callable[[], Integrator], pattern: str, key: str
) -> None:
    respx.route(url__regex=pattern).mock(return_value=Response(500, text="server error"))
    integ = factory()
    with pytest.raises(IntegratorError):
        await integ.fetch(key)


@pytest.mark.parametrize("factory,pattern,key", _INTEGRATOR_CASES)
@respx.mock
async def test_g11_integrator_raises_on_network_error(
    factory: Callable[[], Integrator], pattern: str, key: str
) -> None:
    respx.route(url__regex=pattern).mock(side_effect=httpx.ConnectError("dns fail"))
    integ = factory()
    with pytest.raises(IntegratorError):
        await integ.fetch(key)


def test_g11_runtime_check_passes_without_flag() -> None:
    gate = G11NoSilentFallbackGate()
    r = gate.check({"evidence": [{"type": "pmid", "id": "1"}]})
    assert r.status == GateStatus.PASS


def test_g11_runtime_check_fails_with_fallback_flag() -> None:
    gate = G11NoSilentFallbackGate()
    claim: dict[str, Any] = {"integrator_fallback_used": True}
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
