"""IntegratorABC + IntegratorRegistry — v2.5 compositional foundation
(RFC 0001 §2.4).

v2.5 adds a NEW thin protocol that lives alongside the existing
``opl_cancer.integrators.base.Integrator`` ABC. v2.4 integrators keep
working unchanged; the ABC + entry-point registry are voluntary
upgrades. v2.5 ships:

- IntegratorABC: declares id / query() / normalize() / provenance()
- IntegratorRegistry.discover(): walks the
  ``opl_cancer.integrators`` Python entry-point group and returns a
  name → class map
- ClinicalTrialsGovIntegrator + OpenTargetsIntegrator are the first two
  proof-of-protocol multi-inheritors (also inherit IntegratorABC)
- 5 existing integrators (pubmed, opentargets, clinicaltrials, cbioportal,
  oncokb) registered as entry points in pyproject.toml
- 39 others tagged for M3 migration

Pre-Python-3.10 fallback for importlib.metadata.entry_points is not needed
(requires-python ≥ 3.11 already).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from importlib import metadata
from typing import Any, ClassVar


ENTRY_POINT_GROUP = "opl_cancer.integrators"


class IntegratorABC(ABC):
    """v2.5 thin integrator protocol — query / normalize / provenance.

    Concrete v2.4 integrators inherit ``Integrator`` (base.py); v2.5 adds
    THIS abc as a parallel protocol. An integrator can multiply-inherit
    both (transition path). ``IntegratorRegistry.discover()`` returns the
    classes the entry-point group exposes.
    """

    id: ClassVar[str] = ""  # entry-point name

    @abstractmethod
    def query(self, key: str) -> Any:
        """Look up a record by key. Sync or async — concrete classes choose."""

    @abstractmethod
    def normalize(self, raw: Any) -> dict[str, Any]:
        """Normalize raw integrator output to the integrator-catalog schema."""

    @abstractmethod
    def provenance(self) -> dict[str, Any]:
        """Return integrator provenance — name + endpoint + ttl + version."""


class IntegratorRegistry:
    """Walks the ``opl_cancer.integrators`` entry-point group."""

    def __init__(self, classes: dict[str, type] | None = None) -> None:
        self._classes: dict[str, type] = dict(classes or {})

    @classmethod
    def discover(cls) -> "IntegratorRegistry":
        out: dict[str, type] = {}
        eps = metadata.entry_points(group=ENTRY_POINT_GROUP)
        for ep in eps:
            try:
                out[ep.name] = ep.load()
            except Exception as exc:  # noqa: BLE001
                # Don't crash discovery on a single bad plugin; we log later.
                out[ep.name] = _LoadFailure(ep.name, str(exc))
        return cls(out)

    def keys(self) -> list[str]:
        return list(self._classes.keys())

    def get(self, name: str) -> type:
        if name not in self._classes:
            raise KeyError(f"unknown integrator entry-point: {name!r}")
        return self._classes[name]

    def describe(self) -> list[dict[str, Any]]:
        """Machine-readable inventory for CLI/MCP dashboards."""
        rows: list[dict[str, Any]] = []
        for name, cls in sorted(self._classes.items()):
            if isinstance(cls, _LoadFailure):
                rows.append({
                    "name": name,
                    "ok": False,
                    "error": cls.message,
                })
                continue
            rows.append({
                "name": name,
                "ok": True,
                "module": getattr(cls, "__module__", ""),
                "class": getattr(cls, "__name__", repr(cls)),
                "id": getattr(cls, "id", ""),
                "family": getattr(cls, "family", ""),
                "implements_integrator_abc": (
                    isinstance(cls, type) and issubclass(cls, IntegratorABC)
                ),
            })
        return rows

    def __contains__(self, name: str) -> bool:
        return name in self._classes


class _LoadFailure:
    """Placeholder when an entry point fails to load."""

    def __init__(self, name: str, message: str) -> None:
        self.name = name
        self.message = message

    def __repr__(self) -> str:  # pragma: no cover
        return f"<LoadFailure {self.name}: {self.message}>"


__all__ = [
    "ENTRY_POINT_GROUP",
    "IntegratorABC",
    "IntegratorRegistry",
]
