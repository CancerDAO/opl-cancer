"""Test NMPAEAPIntegrator — 临床急需进口药品 list scrape."""
import respx
from httpx import Response

from opl_cancer.integrators.nmpa_eap import NMPAEAPIntegrator


_MOCK_HTML = """<html><body>
<table>
<tr><td>1</td><td>多抗多肽注射液</td><td>用于晚期肝癌</td><td>2024-12-01</td></tr>
<tr><td>2</td><td>奥希替尼</td><td>EGFR突变NSCLC</td><td>2023-08-15</td></tr>
</table></body></html>"""


@respx.mock
async def test_fetch_search_for_hcc() -> None:
    respx.get(url__regex=r"https?://www\.nmpa\.gov\.cn/.*").mock(
        return_value=Response(200, text=_MOCK_HTML)
    )
    i = NMPAEAPIntegrator(cache=None)
    r = await i.fetch("search:肝癌")
    assert len(r["entries"]) >= 1
    assert any("多抗多肽" in e["drug"] for e in r["entries"])


def test_family_is_F8() -> None:
    assert NMPAEAPIntegrator(cache=None).family == "F8"
