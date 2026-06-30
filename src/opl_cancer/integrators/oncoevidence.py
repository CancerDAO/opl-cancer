"""OncoEvidence — local 375k-statement evidence corpus as a grounding backend.

Why (first-principles audit 2026-06-30): OPL's "retrieve the world-known" half
rode entirely on live PubMed (rate-limited, and historically truncated
abstracts). A local OncoEvidence corpus — a DuckDB fact table of ~375k
PMID-anchored statements, each carrying a ``verbatim_quote`` + gene / variant /
cancer / drug / metric — sits next to it. When present, it is a faster, fuller,
deterministic grounding source: G2 (quote-match) and G56 (value-source binding)
can confirm a PMID's verbatim quote against the LOCAL corpus first, and the
literature step can pull real PMID-anchored statements without a network round
trip.

Design constraints (so OPL stays shippable as an open-source skill):
  * **Decoupled** — we do NOT import the private ``oe`` package. We query the
    DuckDB file directly via the optional ``duckdb`` lib against the known
    ``evidence`` schema. No dependency on the OncoEvidence repo being installed.
  * **Opt-in by environment** — active only when ``OPL_ONCOEVIDENCE_DB`` (or
    ``ONCOEVIDENCE_DATA``) points at a real ``evidence.duckdb``. Unset → the
    backend is simply unavailable and OPL behaves exactly as before (live
    PubMed). This is *prefer-when-present*, never a hard dependency.
  * **No silent fallback** — if the env var IS set but the DB or ``duckdb`` is
    missing/unreadable, ``fetch`` RAISES ``IntegratorError`` (loud), per the
    OPL Evidence Contract. We never quietly fabricate or skip.

Key forms accepted by ``fetch(key)``:
  * ``pmid:<id>``               — all statements citing that PMID
  * ``biomarker:<GENE>``        — statements for a gene
  * ``biomarker:<GENE>/<VAR>``  — narrowed by variant substring
  * ``drug:<name>``             — statements involving a drug
Each returned row carries ``pmid`` + ``verbatim_quote`` (+ gene/variant/cancer/
drug/metric), which is exactly what the grounding gates verify against.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, ClassVar

from .base import Integrator, IntegratorError

_ENV_DB = "OPL_ONCOEVIDENCE_DB"      # explicit path to evidence.duckdb
_ENV_HOME = "ONCOEVIDENCE_DATA"      # OncoEvidence data dir (holds evidence.duckdb)

# Columns we read — a stable subset of the OncoEvidence `evidence` schema.
_COLS = (
    "gene, variant, cancer, drugs AS drug, pmid, year, source_kind, "
    "evidence_level AS level, metric_name, metric_value, verbatim_quote"
)


def resolve_db_path() -> Path | None:
    """The evidence.duckdb path from the environment, or None if not configured."""
    explicit = os.environ.get(_ENV_DB, "").strip()
    if explicit:
        return Path(explicit)
    home = os.environ.get(_ENV_HOME, "").strip()
    if home:
        return Path(home) / "evidence.duckdb"
    return None


def is_available() -> bool:
    """True iff the corpus is configured AND queryable (env + duckdb + file)."""
    p = resolve_db_path()
    if p is None or not p.is_file():
        return False
    try:
        import duckdb  # noqa: F401
    except ImportError:
        return False
    return True


class OncoEvidenceIntegrator(Integrator):
    family = "F1"  # literature / evidence corpus
    ttl_seconds = 7 * 24 * 3600
    family_config_key: ClassVar[str | None] = None

    def __init__(self, db_path: str | Path | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._db_path = Path(db_path) if db_path else resolve_db_path()

    def _connect(self):  # -> duckdb connection
        if self._db_path is None:
            raise IntegratorError(
                "OncoEvidence not configured — set OPL_ONCOEVIDENCE_DB or "
                "ONCOEVIDENCE_DATA to use the local corpus (no silent fallback)."
            )
        if not self._db_path.is_file():
            raise IntegratorError(f"OncoEvidence DB not found: {self._db_path}")
        try:
            import duckdb
        except ImportError as e:  # pragma: no cover - env-dependent
            raise IntegratorError(
                "OncoEvidence configured but `duckdb` is not installed "
                "(`pip install duckdb`) — refusing to silently skip."
            ) from e
        try:
            return duckdb.connect(str(self._db_path), read_only=True)
        except Exception as e:  # duckdb.Error
            raise IntegratorError(f"OncoEvidence DB open failed: {e}") from e

    def _query(self, where: str, params: list[Any], k: int) -> list[dict[str, Any]]:
        sql = (
            f"SELECT {_COLS} FROM evidence WHERE {where} "
            "ORDER BY (source_kind='civic') DESC, year DESC NULLS LAST LIMIT ?"
        )
        con = self._connect()
        try:
            cur = con.execute(sql, [*params, int(k)])
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        except Exception as e:  # duckdb.Error — malformed query / schema drift
            raise IntegratorError(f"OncoEvidence query failed: {e}") from e
        finally:
            con.close()

    async def fetch(self, key: str) -> dict[str, Any]:
        """Return ``{"key", "rows": [...]}``; rows carry pmid + verbatim_quote."""
        kind, _, rest = key.partition(":")
        rest = rest.strip()
        if not rest:
            raise IntegratorError(f"OncoEvidence: empty selector in key {key!r}")
        if kind == "pmid":
            rows = self._query("pmid = ?", [rest.lstrip("PMID:").strip()], 50)
        elif kind == "drug":
            rows = self._query("lower(drugs) LIKE '%' || lower(?) || '%'", [rest], 25)
        elif kind == "biomarker":
            gene, _, variant = rest.partition("/")
            where = "gene = upper(?)"
            params: list[Any] = [gene.strip()]
            if variant.strip():
                where += " AND variant ILIKE '%' || ? || '%'"
                params.append(variant.strip())
            rows = self._query(where, params, 25)
        else:
            raise IntegratorError(
                f"OncoEvidence: unknown key kind {kind!r} "
                "(expected pmid: / biomarker: / drug:)"
            )
        return {"key": key, "rows": rows, "source": "oncoevidence_local"}

    # ── grounding helpers (deterministic; used by G2 / G56 when available) ──
    def quotes_for_pmid(self, pmid: str) -> list[str]:
        """All non-empty verbatim quotes the corpus holds for a PMID."""
        rows = self._query("pmid = ? AND verbatim_quote <> ''", [str(pmid).strip()], 50)
        return [str(r["verbatim_quote"]) for r in rows if r.get("verbatim_quote")]
