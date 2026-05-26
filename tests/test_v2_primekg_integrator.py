"""v2 paradigm tests — PrimeKG integrator stub.

Live client wiring tracked in iter/v2-followup-primekg (ADR-0013).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from opl_cancer.integrators import PrimeKGClient
from opl_cancer.integrators.primekg import PrimeKGClient as PrimeKGClientDirect


FIXTURE = json.loads(
    Path("tests/fixtures/v2/primekg_synergy_response.json").read_text(encoding="utf-8")
)


def test_primekg_client_exports_from_package():
    # Re-export check — must be importable both ways
    assert PrimeKGClient is PrimeKGClientDirect


async def test_primekg_query_synergy_returns_stub():
    client = PrimeKGClient(stub_response=FIXTURE)
    result = await client.query_synergy(gene_a="KRAS", gene_b="SHP2")
    assert result["kg_source"] == "PrimeKG"
    assert result["kg_version"] == "2024.1"
    assert len(result["edges"]) >= 1
    assert any(e["target"] == "PTPN11" for e in result["edges"])


async def test_primekg_query_synthetic_lethal_returns_stub():
    client = PrimeKGClient(stub_response=FIXTURE)
    result = await client.query_synthetic_lethal(gene="MTAP")
    assert result["kg_source"] == "PrimeKG"


async def test_primekg_live_query_raises_not_implemented():
    """Per memory:feedback_no_offline_only — stub raises loud, not silent empty."""
    client = PrimeKGClient()
    with pytest.raises(NotImplementedError, match="iter/v2-followup-primekg"):
        await client.query_synergy(gene_a="KRAS", gene_b="SHP2")
    with pytest.raises(NotImplementedError, match="iter/v2-followup-primekg"):
        await client.query_synthetic_lethal(gene="MTAP")
