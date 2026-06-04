"""GEPIA3 — TCGA + GTEx differential expression. v1.5 P0-2 (AP-5).

GEPIA3 (Gene Expression Profiling Interactive Analysis 3,
http://gepia3.cancer-pku.cn/) is the canonical TCGA-vs-GTEx normal-tissue
expression browser. The PT-EXAMPLE-A recovery run produced 70/71
successful queries via this service (TROP2 log2FC 2.41, RNF43 4.03/5.35,
FOXP3, AREG/EREG, MAPK pathway co-regulation) — but the skill itself did
not know GEPIA3 existed, so the planner could not dispatch it
(docs/ANTI_PATTERNS_v1.4.md AP-5).

This integrator gives the planner a first-class GEPIA3 capability. Key
shape::

    gepia3:exp:<GENE_SYMBOL>:<TCGA_TYPE>

Example::

    gepia3:exp:TROP2:COAD
    gepia3:exp:RNF43:READ

Returns a dict::

    {
      "gene": "TROP2",
      "cancer_type": "COAD",
      "tumor_n": 275,
      "normal_n": 41,
      "tumor_median_log2tpm": 7.73,
      "normal_median_log2tpm": 5.36,
      "log2fc": 2.41,
      "q_value": 2.4e-83,
      "source_url": "http://gepia3.cancer-pku.cn/...",
      "as_of": "2026-05-25T12:34:56Z",
    }

Per no-silent-fallback policy — never silently degrades. Transport
or parse failures raise ``IntegratorError`` with the actionable detail.

Rate-limit: the recovery run discovered HTTP 429 at burst → 12-second
pacing was sufficient. We expose ``min_request_interval_s`` so callers
(planner / batch runner) can throttle. Default 12s matches the empirical
finding. Set to 0 in tests.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, ClassVar

import httpx

from .base import Integrator, IntegratorError


GEPIA3_BASE_URL = "http://gepia3.cancer-pku.cn"
GEPIA3_EXP_ENDPOINT = "/api/v1/expression"

# Accepted TCGA cancer-type codes — restricted to the most commonly used set
# for the OPL for Cancer skill. Extend as more patient phenotypes hit the
# planner. Full TCGA roster is documented at
# https://gdc.cancer.gov/resources-tcga-users/tcga-code-tables/tcga-study-abbreviations
TCGA_CANCER_TYPES: frozenset[str] = frozenset(
    {
        "ACC", "BLCA", "BRCA", "CESC", "CHOL", "COAD", "COADREAD",
        "DLBC", "ESCA", "GBM", "HNSC", "KICH", "KIRC", "KIRP",
        "LAML", "LGG", "LIHC", "LUAD", "LUSC", "MESO", "OV",
        "PAAD", "PCPG", "PRAD", "READ", "SARC", "SKCM", "STAD",
        "TGCT", "THCA", "THYM", "UCEC", "UCS", "UVM",
    }
)


class GEPIA3Integrator(Integrator):
    """TCGA + GTEx differential-expression lookup via GEPIA3.

    family: F12 (transcriptome) — extends the v1.4 F1..F10 schema with the
    transcriptomic family added in v1.5.
    """

    family = "F12"
    family_config_key: ClassVar[str | None] = "gepia3"
    ttl_seconds = 7 * 24 * 3600  # expression cohorts are slow-changing
    default_min_request_interval_s: ClassVar[float] = 12.0

    def __init__(
        self,
        *,
        base_url: str = GEPIA3_BASE_URL,
        min_request_interval_s: float | None = None,
        request_timeout_s: float = 30.0,
        cache: Any = None,
        ttl_seconds_overrides: dict[str, int] | None = None,
    ) -> None:
        super().__init__(cache=cache, ttl_seconds_overrides=ttl_seconds_overrides)
        self.base_url = base_url.rstrip("/")
        self.request_timeout_s = request_timeout_s
        self.min_request_interval_s = (
            min_request_interval_s
            if min_request_interval_s is not None
            else self.default_min_request_interval_s
        )
        self._last_request_at: float = 0.0

    async def fetch(self, key: str) -> dict[str, Any]:
        gene, cancer_type = self._parse_key(key)
        await self._respect_rate_limit()
        url = f"{self.base_url}{GEPIA3_EXP_ENDPOINT}"
        params = {
            "gene": gene,
            "cancer_type": cancer_type,
            "dataset": "TCGA+GTEx",
            "method": "median",
        }
        try:
            async with httpx.AsyncClient(timeout=self.request_timeout_s) as http:
                r = await http.get(url, params=params)
        except (httpx.HTTPError, ConnectionError, OSError) as e:
            raise IntegratorError(f"GEPIA3 transport: {e}") from e
        if r.status_code == 429:
            raise IntegratorError(
                f"GEPIA3 rate-limited (HTTP 429). Increase "
                f"min_request_interval_s (current={self.min_request_interval_s}s)."
            )
        if r.status_code >= 400:
            raise IntegratorError(
                f"GEPIA3 HTTP {r.status_code} for {gene}/{cancer_type}: "
                f"{r.text[:200]}"
            )
        try:
            payload = r.json()
        except ValueError as e:
            raise IntegratorError(f"GEPIA3 non-JSON response: {e}") from e

        return self._normalize(
            gene=gene, cancer_type=cancer_type, payload=payload, source_url=str(r.url)
        )

    async def batch(
        self, queries: list[tuple[str, str]]
    ) -> dict[tuple[str, str], dict[str, Any] | IntegratorError]:
        """Run a batch of (gene, cancer_type) lookups, respecting rate limit.

        Returns a dict keyed by (gene, cancer_type) with either the
        normalized payload or the IntegratorError raised for that query.
        Errors do not stop the batch — callers see per-query status.
        """
        out: dict[tuple[str, str], dict[str, Any] | IntegratorError] = {}
        for gene, cancer_type in queries:
            key = f"gepia3:exp:{gene}:{cancer_type}"
            try:
                out[(gene, cancer_type)] = await self.fetch(key)
            except IntegratorError as e:
                out[(gene, cancer_type)] = e
        return out

    @staticmethod
    def _parse_key(key: str) -> tuple[str, str]:
        if not key.startswith("gepia3:exp:"):
            raise IntegratorError(
                f"GEPIA3: expected gepia3:exp:<GENE>:<TCGA_TYPE>, got {key!r}"
            )
        rest = key[len("gepia3:exp:"):]
        parts = rest.split(":")
        if len(parts) != 2:
            raise IntegratorError(f"GEPIA3: bad key shape {key!r}")
        gene, cancer_type = parts[0].strip().upper(), parts[1].strip().upper()
        if not gene:
            raise IntegratorError(f"GEPIA3: empty gene symbol in {key!r}")
        if cancer_type not in TCGA_CANCER_TYPES:
            raise IntegratorError(
                f"GEPIA3: unknown TCGA cancer type {cancer_type!r}; "
                f"supported: {sorted(TCGA_CANCER_TYPES)[:8]}..."
            )
        return gene, cancer_type

    async def _respect_rate_limit(self) -> None:
        if self.min_request_interval_s <= 0:
            return
        now = time.monotonic()
        delta = now - self._last_request_at
        if delta < self.min_request_interval_s:
            await asyncio.sleep(self.min_request_interval_s - delta)
        self._last_request_at = time.monotonic()

    def _normalize(
        self,
        *,
        gene: str,
        cancer_type: str,
        payload: dict[str, Any],
        source_url: str,
    ) -> dict[str, Any]:
        # GEPIA3's documented response shape varies; we tolerate the two
        # observed shapes from the recovery run:
        #   shape A — flat: {"tumor_median": x, "normal_median": y, "log2fc": z, "q": q}
        #   shape B — nested: {"result": {...}}
        flat = payload.get("result", payload)
        try:
            tumor_med = float(flat["tumor_median_log2tpm"])
            normal_med = float(flat["normal_median_log2tpm"])
            log2fc = float(flat["log2fc"])
            q_value = float(flat["q_value"])
        except (KeyError, TypeError, ValueError) as e:
            raise IntegratorError(
                f"GEPIA3 payload missing expected field for "
                f"{gene}/{cancer_type}: {e!r}; payload keys={list(flat.keys())[:8]}"
            ) from e
        tumor_n = int(flat.get("tumor_n", 0))
        normal_n = int(flat.get("normal_n", 0))
        return {
            "gene": gene,
            "cancer_type": cancer_type,
            "tumor_n": tumor_n,
            "normal_n": normal_n,
            "tumor_median_log2tpm": tumor_med,
            "normal_median_log2tpm": normal_med,
            "log2fc": log2fc,
            "q_value": q_value,
            "source_url": source_url,
            "as_of": datetime.now(timezone.utc).isoformat(),
        }
