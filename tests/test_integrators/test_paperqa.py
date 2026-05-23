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


# ---------------------------------------------------------------------------
# P2-T14: full PaperQA2 wrapper path (monkey-patched paperqa module)
# ---------------------------------------------------------------------------


class _FakeContext:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeAnswer:
    def __init__(self, answer: str, sources: list[str]) -> None:
        self.answer = answer
        self.contexts = [_FakeContext(s) for s in sources]
        self.context = answer


class _FakeDocs:
    def __init__(self) -> None:
        self.added: list[str] = []

    async def aadd(self, path: str) -> None:
        self.added.append(path)

    async def aquery(self, text: str) -> _FakeAnswer:
        return _FakeAnswer(
            answer="WNT/β-catenin activation correlated with HR 2.10 in HCC.",
            sources=["38219045"],
        )


async def test_paperqa2_wrapper_uses_aquery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """P2-T14: when paper-qa is importable, fetch() returns engine='paperqa2'."""
    corpus = tmp_path / "papers"
    corpus.mkdir()
    (corpus / "p1.txt").write_text("PubMed ID: 38219045. WNT/β-catenin activation in HCC.")

    import sys
    import types

    fake_module = types.SimpleNamespace(Docs=_FakeDocs)
    monkeypatch.setitem(sys.modules, "paperqa", fake_module)
    monkeypatch.setattr("opl_cancer.integrators.paperqa._HAS_PAPERQA", True)

    i = PaperQA2Integrator(corpus_dir=corpus, cache=None)
    r = await i.fetch("query:What is the HR for WNT in HCC?")
    assert r["engine"] == "paperqa2"
    assert "WNT" in r["quote"]
    assert "38219045" in r["sources"]


async def test_paperqa2_wrapper_raises_on_empty_corpus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    corpus = tmp_path / "papers"
    corpus.mkdir()

    import sys
    import types

    monkeypatch.setitem(sys.modules, "paperqa", types.SimpleNamespace(Docs=_FakeDocs))
    monkeypatch.setattr("opl_cancer.integrators.paperqa._HAS_PAPERQA", True)

    i = PaperQA2Integrator(corpus_dir=corpus, cache=None)
    with pytest.raises(IntegratorError):
        await i.fetch("query:anything")
