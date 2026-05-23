"""CCLEIntegrator tests — F7 P3-T5."""
import pytest
import respx
from httpx import Response

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.ccle import CCLEIntegrator


@respx.mock
async def test_fetch_expression() -> None:
    respx.get(url__regex=r".*depmap.org/portal/api/expression.*").mock(
        return_value=Response(
            200,
            json={
                "tpm": 124.5,
                "cell_line_name": "A549",
                "lineage": "lung",
            },
        )
    )
    integ = CCLEIntegrator(cache=None)
    rec = await integ.fetch("EGFR:ACH-000681")
    assert rec["gene"] == "EGFR"
    assert rec["depmap_id"] == "ACH-000681"
    assert rec["tpm"] == 124.5


async def test_fetch_bad_key_raises() -> None:
    integ = CCLEIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await integ.fetch("EGFR_no_colon")


@respx.mock
async def test_fetch_404_raises() -> None:
    respx.get(url__regex=r".*depmap.org/portal/api/expression.*").mock(
        return_value=Response(404)
    )
    integ = CCLEIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await integ.fetch("FOOBAR:ACH-999999")


def test_ccle_family_is_f7() -> None:
    integ = CCLEIntegrator(cache=None)
    assert integ.family == "F7"
