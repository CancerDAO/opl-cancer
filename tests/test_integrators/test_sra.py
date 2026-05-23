"""SRAIntegrator tests — F6 P3-T3."""
import pytest
import respx
from httpx import Response

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.sra import SRAIntegrator


_ESEARCH = {"esearchresult": {"idlist": ["12345"], "count": "1"}}
_RUNINFO_CSV = (
    "Run,bases,spots,LibraryStrategy,LibraryLayout,Platform,Experiment,Sample,BioProject\n"
    "SRR1234567,9876543210,33333,RNA-Seq,PAIRED,ILLUMINA,SRX111,SRS222,PRJNA333\n"
)


@respx.mock
async def test_fetch_by_run_accession() -> None:
    respx.get(url__regex=r".*esearch.fcgi.*").mock(
        return_value=Response(200, json=_ESEARCH)
    )
    respx.get(url__regex=r".*efetch.fcgi.*").mock(
        return_value=Response(200, text=_RUNINFO_CSV)
    )
    integ = SRAIntegrator(cache=None)
    rec = await integ.fetch("SRR1234567")
    assert rec["accession"] == "SRR1234567"
    assert rec["run"] == "SRR1234567"
    assert rec["library_strategy"] == "RNA-Seq"
    assert rec["platform"] == "ILLUMINA"


@respx.mock
async def test_fetch_unknown_prefix_raises() -> None:
    integ = SRAIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await integ.fetch("PMID:99")


@respx.mock
async def test_fetch_not_found_raises() -> None:
    respx.get(url__regex=r".*esearch.fcgi.*").mock(
        return_value=Response(200, json={"esearchresult": {"idlist": []}})
    )
    integ = SRAIntegrator(cache=None)
    with pytest.raises(IntegratorError):
        await integ.fetch("SRR9999999")


def test_sra_family_is_f6() -> None:
    integ = SRAIntegrator(cache=None)
    assert integ.family == "F6"
