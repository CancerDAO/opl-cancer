"""Iter 15 (v1.0.7) — configurable integrator TTL.

Verifies the precedence: instance overrides > class overrides > class default.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from opl_cancer.integrators.base import Integrator
from opl_cancer.integrators.cache import IntegratorCache


class _StubIntegrator(Integrator):
    family = "stub"
    ttl_seconds = 60
    default_ttl_seconds_overrides = {"hot_key": 5}

    async def fetch(self, key: str) -> dict[str, Any]:
        return {"key": key}


def test_ttl_override_precedence() -> None:
    """Instance overrides beat class overrides beat class default."""
    i = _StubIntegrator(ttl_seconds_overrides={"hot_key": 1, "other": 999})
    # Instance override wins over class override
    assert i.resolve_ttl("hot_key") == 1
    # Instance-only override
    assert i.resolve_ttl("other") == 999
    # Falls through to class default
    assert i.resolve_ttl("nothing_set") == 60

    # No instance override -> class override applies
    j = _StubIntegrator()
    assert j.resolve_ttl("hot_key") == 5
    assert j.resolve_ttl("misc") == 60


def test_models_yaml_declares_family_ttls() -> None:
    """models.yaml carries integrator_ttl_seconds with NCCN/PubMed/CT.gov defaults."""
    here = Path(__file__).resolve()
    repo_root = next(p for p in here.parents if (p / "models.yaml").exists())
    cfg = yaml.safe_load((repo_root / "models.yaml").read_text())
    ttl = cfg["integrator_ttl_seconds"]
    assert ttl["nccn"] == 30 * 24 * 3600
    assert ttl["pubmed"] == 7 * 24 * 3600
    assert ttl["clinicaltrials"] == 24 * 3600


async def test_cached_fetch_uses_resolved_ttl(tmp_path: Path) -> None:
    """cached_fetch passes resolve_ttl(key) into cache.put()."""
    captured: dict[str, Any] = {}

    class _CapturingCache(IntegratorCache):
        def put(self, *, family: str, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
            captured["ttl"] = ttl_seconds
            super().put(family=family, key=key, value=value, ttl_seconds=ttl_seconds)

    cache = _CapturingCache(db_path=tmp_path / "c.sqlite")
    i = _StubIntegrator(cache=cache, ttl_seconds_overrides={"vip": 7})
    await i.cached_fetch("vip")
    assert captured["ttl"] == 7
