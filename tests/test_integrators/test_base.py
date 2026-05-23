"""Test Integrator abstract base — fail-loud, no silent fallback."""
import pytest

from opl_cancer.integrators.base import Integrator, IntegratorError


class _FakeOnlineIntegrator(Integrator):
    family = "test_family"
    ttl_seconds = 60

    def __init__(self, *, online: bool) -> None:
        self._online = online

    def fetch(self, key: str) -> dict:
        if not self._online:
            raise IntegratorError(f"{self.family}: API unreachable; not falling back silently")
        return {"key": key, "data": "result"}


def test_integrator_fetch_returns_data_when_online() -> None:
    i = _FakeOnlineIntegrator(online=True)
    assert i.fetch("x") == {"key": "x", "data": "result"}


def test_integrator_fetch_raises_when_offline_no_silent_fallback() -> None:
    """memory:feedback_no_offline_only — must raise, NOT degrade to LLM-guessed answer."""
    i = _FakeOnlineIntegrator(online=False)
    with pytest.raises(IntegratorError):
        i.fetch("x")
