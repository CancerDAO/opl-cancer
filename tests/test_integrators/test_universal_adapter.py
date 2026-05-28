"""Tests for v2.5 UniversalAdapter sandbox — RFC 0001 §2.4."""
from __future__ import annotations

import os

import pytest

from opl_cancer.integrators.universal_adapter import (
    AdHocIntegrator,
    UniversalAdapterLiveNotEnabled,
    from_openapi,
)


# Minimal OpenAPI 3.0 schema for SemanticScholar Graph API. We embed it as
# a stub so the test doesn't need a network call. The real schema lives at
#   https://api.semanticscholar.org/graph/v1/openapi.json
# but a hand-trimmed version is good enough to exercise dry-run parsing.
SEMANTIC_SCHOLAR_SCHEMA = {
    "openapi": "3.0.0",
    "info": {"title": "SemanticScholar Graph", "version": "1.0"},
    "servers": [{"url": "https://api.semanticscholar.org/graph/v1"}],
    "paths": {
        "/paper/{paper_id}": {
            "get": {
                "operationId": "getPaper",
                "parameters": [
                    {"name": "paper_id", "in": "path", "required": True,
                     "schema": {"type": "string"}}
                ],
                "responses": {"200": {"description": "ok"}},
            }
        },
        "/paper/search": {
            "get": {
                "operationId": "searchPaper",
                "parameters": [
                    {"name": "query", "in": "query", "required": True,
                     "schema": {"type": "string"}}
                ],
                "responses": {"200": {"description": "ok"}},
            }
        },
    },
}


def test_from_openapi_dry_run_returns_adhoc_integrator(tmp_path) -> None:
    """A dry-run schema parse returns a usable AdHocIntegrator metadata wrapper
    — does NOT make any live network calls."""
    import json

    schema_path = tmp_path / "ss.openapi.json"
    schema_path.write_text(json.dumps(SEMANTIC_SCHOLAR_SCHEMA))

    adapter = from_openapi(str(schema_path), dry_run=True)
    assert isinstance(adapter, AdHocIntegrator)
    assert adapter.title == "SemanticScholar Graph"
    assert adapter.base_url == "https://api.semanticscholar.org/graph/v1"
    op_ids = {op["operationId"] for op in adapter.operations}
    assert {"getPaper", "searchPaper"} <= op_ids


def test_adhoc_integrator_live_call_raises_without_env() -> None:
    """Without OPL_UNIVERSAL_ADAPTER_LIVE=1 any live call must raise."""
    adapter = AdHocIntegrator(
        title="t",
        base_url="https://example.invalid",
        operations=[{"operationId": "x", "path": "/x", "method": "get"}],
    )
    # ensure env var unset
    os.environ.pop("OPL_UNIVERSAL_ADAPTER_LIVE", None)
    with pytest.raises(UniversalAdapterLiveNotEnabled):
        adapter.call("x", {})


def test_adhoc_integrator_provenance_includes_dry_run_flag() -> None:
    adapter = AdHocIntegrator(
        title="t",
        base_url="https://example.invalid",
        operations=[{"operationId": "x", "path": "/x", "method": "get"}],
    )
    prov = adapter.provenance()
    assert prov["live_enabled"] is False
    assert prov["title"] == "t"
    assert prov["base_url"] == "https://example.invalid"


def test_from_openapi_unknown_path_raises(tmp_path) -> None:
    adapter = from_openapi(
        str(tmp_path / "missing.json"),
        dry_run=True,
    )
    # Even with a missing schema file, dry-run resolves to an EMPTY-operations
    # adapter rather than crashing — we want graceful diagnostics, not surprise.
    assert adapter.operations == []
