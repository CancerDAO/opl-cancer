"""Tests for v2.2 ADR-0022 OpenTargets evidence extensions.

v2.0 OpenTargets integrator covers target / disease / target_disease. v2.2
adds an ``evidence_query`` key form returning datasource-level evidence
breakdown that Maya uses in Wave 1/2 to support hypothesis tournaments.

The underlying HTTP is mocked so the test stays offline.
"""
from __future__ import annotations

import asyncio

import pytest

from opl_cancer.integrators.base import IntegratorError
from opl_cancer.integrators.open_targets import OpenTargetsIntegrator


def test_evidence_query_key_parses(monkeypatch) -> None:
    integ = OpenTargetsIntegrator()
    captured = {}

    async def _fake_post(self, query, variables):
        captured["query"] = query
        captured["variables"] = variables
        return {
            "target": {
                "id": "ENSG00000146648",
                "approvedSymbol": "EGFR",
                "evidences": {
                    "count": 42,
                    "rows": [
                        {"datasource": "chembl",
                         "score": 0.92,
                         "disease": {"id": "EFO_0003060", "name": "lung carcinoma"},
                         "drug": {"name": "OSIMERTINIB"}},
                        {"datasource": "europepmc",
                         "score": 0.55,
                         "disease": {"id": "EFO_0003060", "name": "lung carcinoma"},
                         "literature": ["38123456"]},
                    ],
                },
            }
        }

    monkeypatch.setattr(OpenTargetsIntegrator, "_post", _fake_post, raising=True)
    out = asyncio.run(integ.fetch("evidence:EGFR:EFO_0003060"))
    assert out["symbol"] == "EGFR"
    assert out["disease_efo"] == "EFO_0003060"
    assert len(out["evidence_by_datasource"]) >= 1
    assert any(d["datasource"] == "chembl" for d in out["evidence_by_datasource"])


def test_evidence_query_rejects_missing_efo() -> None:
    integ = OpenTargetsIntegrator()
    with pytest.raises(IntegratorError):
        asyncio.run(integ.fetch("evidence:EGFR"))


def test_evidence_query_empty_evidence_raises(monkeypatch) -> None:
    """No silent fallback per memory:feedback_no_offline_only."""
    integ = OpenTargetsIntegrator()

    async def _fake_post(self, query, variables):
        return {"target": None}

    monkeypatch.setattr(OpenTargetsIntegrator, "_post", _fake_post, raising=True)
    with pytest.raises(IntegratorError):
        asyncio.run(integ.fetch("evidence:NOTAGENE:EFO_999"))


def test_evidence_query_groups_by_datasource(monkeypatch) -> None:
    integ = OpenTargetsIntegrator()

    async def _fake_post(self, query, variables):
        return {
            "target": {
                "id": "ENSG00000146648",
                "approvedSymbol": "EGFR",
                "evidences": {
                    "count": 4,
                    "rows": [
                        {"datasource": "chembl", "score": 0.9,
                         "disease": {"id": "EFO_0003060", "name": "lung carcinoma"}},
                        {"datasource": "chembl", "score": 0.7,
                         "disease": {"id": "EFO_0003060", "name": "lung carcinoma"}},
                        {"datasource": "europepmc", "score": 0.4,
                         "disease": {"id": "EFO_0003060", "name": "lung carcinoma"}},
                        {"datasource": "reactome", "score": 0.6,
                         "disease": {"id": "EFO_0003060", "name": "lung carcinoma"}},
                    ],
                },
            }
        }

    monkeypatch.setattr(OpenTargetsIntegrator, "_post", _fake_post, raising=True)
    out = asyncio.run(integ.fetch("evidence:EGFR:EFO_0003060"))
    sources = {d["datasource"] for d in out["evidence_by_datasource"]}
    assert sources == {"chembl", "europepmc", "reactome"}
    # chembl should have count=2
    chembl = [d for d in out["evidence_by_datasource"] if d["datasource"] == "chembl"][0]
    assert chembl["row_count"] == 2
