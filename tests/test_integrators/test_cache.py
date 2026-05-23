"""Test SQLite-backed integrator cache with TTL per family."""
import time
from pathlib import Path

from opl_cancer.integrators.cache import IntegratorCache


def test_cache_stores_and_retrieves(tmp_path: Path) -> None:
    cache = IntegratorCache(db_path=tmp_path / "c.sqlite")
    cache.put(family="pubmed", key="12345", value={"a": 1}, ttl_seconds=60)
    assert cache.get(family="pubmed", key="12345") == {"a": 1}


def test_cache_returns_none_when_expired(tmp_path: Path) -> None:
    cache = IntegratorCache(db_path=tmp_path / "c.sqlite")
    cache.put(family="pubmed", key="x", value={"a": 1}, ttl_seconds=0)
    time.sleep(0.05)
    assert cache.get(family="pubmed", key="x") is None


def test_cache_isolated_by_family(tmp_path: Path) -> None:
    cache = IntegratorCache(db_path=tmp_path / "c.sqlite")
    cache.put(family="pubmed", key="k", value={"src": "pm"}, ttl_seconds=60)
    cache.put(family="oncokb", key="k", value={"src": "ok"}, ttl_seconds=60)
    assert cache.get(family="pubmed", key="k") == {"src": "pm"}
    assert cache.get(family="oncokb", key="k") == {"src": "ok"}
