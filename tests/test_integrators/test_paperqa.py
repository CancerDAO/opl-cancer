"""Test PaperQA2Integrator — local RAG over a corpus directory."""
from pathlib import Path

import pytest

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.paperqa import PaperQA2Integrator


async def test_query_returns_answer_with_quote(tmp_path: Path) -> None:
    corpus = tmp_path / "papers"
    corpus.mkdir()
    (corpus / "p1.txt").write_text(
        "PubMed ID: 38219045. WNT/β-catenin activation correlated with reduced ICI response (HR 2.10, 95%CI 1.32-3.36) in HCC."
    )
    i = PaperQA2Integrator(corpus_dir=corpus, cache=None)
    r = await i.fetch("query:What is the HR for WNT in HCC?")
    assert "2.10" in r["quote"] or "HR 2.10" in r["quote"]
    assert "38219045" in r["sources"] or r["sources"]


async def test_query_empty_corpus_raises(tmp_path: Path) -> None:
    corpus = tmp_path / "papers"
    corpus.mkdir()
    i = PaperQA2Integrator(corpus_dir=corpus, cache=None)
    with pytest.raises(IntegratorError):
        await i.fetch("query:anything")
