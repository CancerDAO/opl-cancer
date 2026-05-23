"""Test Integrator abstract base — fail-loud, no silent fallback."""
import pytest

from opl_cancer.integrators.base import Integrator, IntegratorError


class _FakeOnlineIntegrator(Integrator):
    family = "test_family"
    ttl_seconds = 60

    def __init__(self, *, online: bool) -> None:
        super().__init__(cache=None)
        self._online = online

    async def fetch(self, key: str) -> dict:
        if not self._online:
            raise IntegratorError(f"{self.family}: API unreachable; not falling back silently")
        return {"key": key, "data": "result"}


async def test_integrator_fetch_returns_data_when_online() -> None:
    i = _FakeOnlineIntegrator(online=True)
    assert await i.fetch("x") == {"key": "x", "data": "result"}


async def test_integrator_fetch_raises_when_offline_no_silent_fallback() -> None:
    """memory:feedback_no_offline_only — must raise, NOT degrade to LLM-guessed answer."""
    i = _FakeOnlineIntegrator(online=False)
    with pytest.raises(IntegratorError):
        await i.fetch("x")


async def test_cached_fetch_uses_cache_when_present(tmp_path) -> None:
    from opl_cancer.integrators.cache import IntegratorCache

    cache = IntegratorCache(db_path=tmp_path / "c.sqlite")
    cache.put(family="test_family", key="pre", value={"hit": True}, ttl_seconds=60)
    i = _FakeOnlineIntegrator(online=False)
    i.cache = cache
    result = await i.cached_fetch("pre")
    assert result == {"hit": True}  # served from cache, fetch() not called
