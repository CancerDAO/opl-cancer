"""Tests for GEPIA3Integrator — TCGA + GTEx differential expression.

v1.5 P0-2 (docs/ANTI_PATTERNS_v1.4.md AP-5).
"""
from __future__ import annotations

import pytest
import respx
from httpx import Response

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.gepia3 import (
    GEPIA3_BASE_URL,
    GEPIA3_EXP_ENDPOINT,
    TCGA_CANCER_TYPES,
    GEPIA3Integrator,
)


def _trop2_coad_payload() -> dict[str, float | int]:
    return {
        "tumor_n": 275,
        "normal_n": 41,
        "tumor_median_log2tpm": 7.73,
        "normal_median_log2tpm": 5.36,
        "log2fc": 2.41,
        "q_value": 2.4e-83,
    }


def test_family_is_F12() -> None:
    assert GEPIA3Integrator().family == "F12"


def test_tcga_cancer_types_include_common_set() -> None:
    for t in {"COAD", "READ", "BRCA", "LUAD", "STAD", "PAAD"}:
        assert t in TCGA_CANCER_TYPES


def test_parse_key_rejects_bad_prefix() -> None:
    i = GEPIA3Integrator()
    with pytest.raises(IntegratorError, match="expected gepia3:exp"):
        i._parse_key("foo:bar:baz:qux")


def test_parse_key_rejects_unknown_cancer_type() -> None:
    i = GEPIA3Integrator()
    with pytest.raises(IntegratorError, match="unknown TCGA cancer type"):
        i._parse_key("gepia3:exp:TROP2:NOTACANCER")


def test_parse_key_normalizes_case() -> None:
    i = GEPIA3Integrator()
    gene, ct = i._parse_key("gepia3:exp:trop2:coad")
    assert gene == "TROP2"
    assert ct == "COAD"


@respx.mock
async def test_fetch_trop2_coad_happy_path() -> None:
    respx.get(url__regex=rf"{GEPIA3_BASE_URL}{GEPIA3_EXP_ENDPOINT}.*").mock(
        return_value=Response(200, json=_trop2_coad_payload())
    )
    i = GEPIA3Integrator(min_request_interval_s=0)
    r = await i.fetch("gepia3:exp:TROP2:COAD")
    assert r["gene"] == "TROP2"
    assert r["cancer_type"] == "COAD"
    assert r["log2fc"] == pytest.approx(2.41)
    assert r["q_value"] == pytest.approx(2.4e-83)
    assert r["tumor_n"] == 275
    assert r["normal_n"] == 41
    assert "as_of" in r
    assert r["source_url"].startswith(GEPIA3_BASE_URL)


@respx.mock
async def test_fetch_handles_nested_result_shape() -> None:
    respx.get(url__regex=rf"{GEPIA3_BASE_URL}{GEPIA3_EXP_ENDPOINT}.*").mock(
        return_value=Response(200, json={"result": _trop2_coad_payload()})
    )
    i = GEPIA3Integrator(min_request_interval_s=0)
    r = await i.fetch("gepia3:exp:TROP2:COAD")
    assert r["log2fc"] == pytest.approx(2.41)


@respx.mock
async def test_fetch_raises_on_rate_limit() -> None:
    respx.get(url__regex=rf"{GEPIA3_BASE_URL}{GEPIA3_EXP_ENDPOINT}.*").mock(
        return_value=Response(429, text="rate limited")
    )
    i = GEPIA3Integrator(min_request_interval_s=0)
    with pytest.raises(IntegratorError, match="rate-limited"):
        await i.fetch("gepia3:exp:RNF43:COAD")


@respx.mock
async def test_fetch_raises_on_500() -> None:
    respx.get(url__regex=rf"{GEPIA3_BASE_URL}{GEPIA3_EXP_ENDPOINT}.*").mock(
        return_value=Response(500, text="internal error")
    )
    i = GEPIA3Integrator(min_request_interval_s=0)
    with pytest.raises(IntegratorError, match="HTTP 500"):
        await i.fetch("gepia3:exp:ERBB4:COAD")


@respx.mock
async def test_fetch_raises_on_missing_field() -> None:
    respx.get(url__regex=rf"{GEPIA3_BASE_URL}{GEPIA3_EXP_ENDPOINT}.*").mock(
        return_value=Response(200, json={"tumor_median_log2tpm": 7.73})  # missing rest
    )
    i = GEPIA3Integrator(min_request_interval_s=0)
    with pytest.raises(IntegratorError, match="missing expected field"):
        await i.fetch("gepia3:exp:TROP2:COAD")


@respx.mock
async def test_batch_collects_per_query_status() -> None:
    payload = _trop2_coad_payload()
    respx.get(url__regex=rf".*gene=TROP2.*").mock(
        return_value=Response(200, json=payload)
    )
    respx.get(url__regex=rf".*gene=ERBB4.*").mock(
        return_value=Response(500, text="boom")
    )
    i = GEPIA3Integrator(min_request_interval_s=0)
    out = await i.batch([("TROP2", "COAD"), ("ERBB4", "COAD")])
    assert isinstance(out[("TROP2", "COAD")], dict)
    assert isinstance(out[("ERBB4", "COAD")], IntegratorError)


def test_min_request_interval_default_matches_empirical_finding() -> None:
    # The PT-EXAMPLE-A recovery used 12 s pacing to clear HTTP 429.
    # Encode this as the default so future planners do not re-trip.
    assert GEPIA3Integrator.default_min_request_interval_s == 12.0
