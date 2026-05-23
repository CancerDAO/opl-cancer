"""Test ChiCTRIntegrator — Chinese trial registry scrape."""
import pytest
import respx
from httpx import Response

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.chictr import ChiCTRIntegrator


_MOCK_HTML = """<html><body>
<table><tbody>
<tr><td><a href="/showproj.html?proj=12345">ChiCTR2400012345</a></td>
    <td>肝细胞癌 TACE 难治 系统治疗</td>
    <td>招募中</td></tr>
</tbody></table>
</body></html>"""


@respx.mock
async def test_fetch_search_returns_trials() -> None:
    respx.get(url__regex=r"https?://(www\.)?chictr\.org\.cn/.*").mock(
        return_value=Response(200, text=_MOCK_HTML)
    )
    i = ChiCTRIntegrator(cache=None)
    r = await i.fetch("search:肝细胞癌 TACE 难治")
    assert len(r["studies"]) >= 1
    assert r["studies"][0]["chictr_id"] == "ChiCTR2400012345"


@respx.mock
async def test_fetch_raises_on_500() -> None:
    respx.get(url__regex=r"https?://(www\.)?chictr\.org\.cn/.*").mock(return_value=Response(500))
    i = ChiCTRIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await i.fetch("search:gibberish")


def test_family_is_F3() -> None:
    assert ChiCTRIntegrator(cache=None).family == "F3"
