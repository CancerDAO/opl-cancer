"""PaperQA2-style anti-hallucination RAG over local corpus.

Two implementations:
- If `paper-qa` package importable: thin wrapper around it (preferred).
- Otherwise: LiteRAG fallback — exact substring + sentence-window retrieval.
  Sufficient for v0 G2 quote-match gate (better-than-nothing; P2 swaps in
  full PaperQA2 once robin pin is finalised).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .base import Integrator, IntegratorError
from .cache import IntegratorCache


try:  # pragma: no cover
    import paperqa  # type: ignore[import-not-found]  # noqa: F401
    _HAS_PAPERQA = True
except ImportError:
    _HAS_PAPERQA = False


class PaperQA2Integrator(Integrator):
    family = "F1"
    ttl_seconds = 24 * 3600

    def __init__(self, corpus_dir: Path, cache: IntegratorCache | None = None) -> None:
        super().__init__(cache=cache)
        self.corpus_dir = Path(corpus_dir)
        if not self.corpus_dir.exists():
            raise IntegratorError(f"PaperQA2: corpus dir {self.corpus_dir} missing")

    async def fetch(self, key: str) -> dict[str, Any]:
        if not key.startswith("query:"):
            raise IntegratorError(f"PaperQA2: expected query:<text>, got {key!r}")
        text = key[6:].strip()
        if _HAS_PAPERQA:
            return await self._paperqa_query(text)
        return await self._literag_query(text)

    async def _paperqa_query(self, text: str) -> dict[str, Any]:  # pragma: no cover
        # Wrap paperqa.Docs; defer detailed integration to P2.
        # P1 just calls it; if installed but mis-configured -> raise.
        raise IntegratorError("PaperQA2 wrapper deferred to P2; LiteRAG fallback active")

    async def _literag_query(self, text: str) -> dict[str, Any]:
        # Tokenise query into content words; score corpus docs by token overlap.
        q_tokens = {w.lower() for w in re.findall(r"[a-zA-Z一-鿿]+", text) if len(w) > 2}
        if not q_tokens:
            raise IntegratorError("LiteRAG: query had no usable tokens")

        scored: list[tuple[int, Path, str]] = []
        for p in self.corpus_dir.rglob("*.txt"):
            body = p.read_text(encoding="utf-8", errors="replace")
            tokens = {w.lower() for w in re.findall(r"[a-zA-Z一-鿿]+", body) if len(w) > 2}
            score = len(q_tokens & tokens)
            if score > 0:
                # find best sentence
                sentences = re.split(r"(?<=[.!?。!?])\s+", body)
                best = max(
                    sentences,
                    key=lambda s: sum(1 for t in q_tokens if t in s.lower()),
                    default="",
                )
                scored.append((score, p, best))

        if not scored:
            raise IntegratorError("LiteRAG: no documents matched query tokens")

        scored.sort(reverse=True, key=lambda x: x[0])
        _, top_path, top_quote = scored[0]
        # try extract PMID-looking number from top_path file body
        body = top_path.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"PubMed ID:?\s*(\d{6,9})", body) or re.search(r"PMID[:\s]+(\d{6,9})", body)
        pmid = m.group(1) if m else ""
        return {
            "query": text,
            "quote": top_quote.strip(),
            "sources": [pmid] if pmid else [str(top_path.name)],
            "engine": "literag",
        }
