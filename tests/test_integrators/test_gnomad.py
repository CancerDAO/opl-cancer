"""Test gnomADIntegrator — allele frequency lookup."""
import pytest
import respx
from httpx import Response

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.gnomad import GnomADIntegrator


@respx.mock
async def test_fetch_variant_af() -> None:
    respx.post("https://gnomad.broadinstitute.org/api").mock(
        return_value=Response(
            200,
            json={
                "data": {
                    "variant": {
                        "variant_id": "7-55249071-T-G",
                        "exome": {"af": 0.0001, "ac": 5, "an": 50000},
                    }
                }
            },
        )
    )
    i = GnomADIntegrator(cache=None)
    r = await i.fetch("variant:7-55249071-T-G:GRCh38")
    assert r["af"] == 0.0001
    assert r["allele_count"] == 5


@respx.mock
async def test_fetch_raises_on_500() -> None:
    respx.post("https://gnomad.broadinstitute.org/api").mock(return_value=Response(500))
    i = GnomADIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await i.fetch("variant:1-1-A-T:GRCh38")


def test_family_is_F4() -> None:
    assert GnomADIntegrator(cache=None).family == "F4"
