"""OncoEvidence local-corpus integrator — decoupled DuckDB grounding backend.

Builds a tiny in-temp `evidence` table matching the OncoEvidence schema and
verifies: opt-in resolution, no-silent-fallback when misconfigured, and that
fetch returns pmid + verbatim_quote rows the grounding gates can use.
"""
from __future__ import annotations

from pathlib import Path

import pytest

duckdb = pytest.importorskip("duckdb")

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.oncoevidence import (
    OncoEvidenceIntegrator,
    is_available,
    resolve_db_path,
)


def _make_db(tmp: Path) -> Path:
    db = tmp / "evidence.duckdb"
    con = duckdb.connect(str(db))
    con.execute(
        "CREATE TABLE evidence (gene VARCHAR, variant VARCHAR, cancer VARCHAR, "
        "drugs VARCHAR, pmid VARCHAR, year INTEGER, source_kind VARCHAR, "
        "evidence_level VARCHAR, metric_name VARCHAR, metric_value VARCHAR, "
        "verbatim_quote VARCHAR)"
    )
    con.execute(
        "INSERT INTO evidence VALUES "
        "('EGFR','T790M','lung','osimertinib','29151359',2017,'civic','A','HR','0.30',"
        "'Osimertinib showed HR 0.30 in T790M NSCLC.'),"
        "('KRAS','G12C','colorectal','adagrasib','36546659',2023,'pubmed','B','ORR','19',"
        "'Adagrasib ORR 19% in KRAS G12C CRC.')"
    )
    con.close()
    return db


def test_resolve_and_availability_opt_in(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPL_ONCOEVIDENCE_DB", raising=False)
    monkeypatch.delenv("ONCOEVIDENCE_DATA", raising=False)
    assert resolve_db_path() is None
    assert is_available() is False  # unset → unavailable, OPL behaves as before

    db = _make_db(tmp_path)
    monkeypatch.setenv("OPL_ONCOEVIDENCE_DB", str(db))
    assert resolve_db_path() == db
    assert is_available() is True


def test_misconfigured_raises_no_silent_fallback(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPL_ONCOEVIDENCE_DB", str(tmp_path / "missing.duckdb"))
    integ = OncoEvidenceIntegrator()
    with pytest.raises(IntegratorError):
        integ.quotes_for_pmid("29151359")


@pytest.mark.asyncio
async def test_fetch_biomarker_and_pmid(tmp_path) -> None:
    db = _make_db(tmp_path)
    integ = OncoEvidenceIntegrator(db_path=db)
    res = await integ.fetch("biomarker:EGFR")
    assert res["source"] == "oncoevidence_local"
    assert any(r["pmid"] == "29151359" for r in res["rows"])
    assert all("verbatim_quote" in r for r in res["rows"])

    res2 = await integ.fetch("pmid:36546659")
    assert res2["rows"][0]["gene"] == "KRAS"

    res3 = await integ.fetch("drug:osimertinib")
    assert res3["rows"][0]["pmid"] == "29151359"


def test_quotes_for_pmid_grounding_helper(tmp_path) -> None:
    db = _make_db(tmp_path)
    integ = OncoEvidenceIntegrator(db_path=db)
    quotes = integ.quotes_for_pmid("29151359")
    assert quotes and "Osimertinib" in quotes[0]


@pytest.mark.asyncio
async def test_unknown_key_kind_raises(tmp_path) -> None:
    integ = OncoEvidenceIntegrator(db_path=_make_db(tmp_path))
    with pytest.raises(IntegratorError):
        await integ.fetch("genome:chr7")
