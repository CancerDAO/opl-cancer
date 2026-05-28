"""MethodRegistry — loads method primitives from prompts/methods/*.yaml.

v2.5 foundation: ships 8 seed primitives. The registry is in-memory; M4 will
add persistence + namespacing.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import yaml

from ._abc import VALID_DOMAINS, VALID_GATE_FAMILIES, MethodPrimitive


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DEFAULT_METHODS_DIR = _REPO_ROOT / "prompts" / "methods"


class MethodPrimitiveSchemaError(ValueError):
    """Raised when a YAML primitive fails schema validation."""


class MethodRegistry:
    """Registry of method primitives. Load YAML files from prompts/methods/."""

    def __init__(self, methods_dir: Path | None = None) -> None:
        self.methods_dir = methods_dir or _DEFAULT_METHODS_DIR
        self._primitives: dict[str, MethodPrimitive] = {}
        self._loaded = False

    # ─── loading ──────────────────────────────────────────────────────────

    def load_all(self) -> None:
        """Load every *.yaml under methods_dir into the registry."""
        if not self.methods_dir.exists():
            raise FileNotFoundError(f"methods dir not found: {self.methods_dir}")
        self._primitives.clear()
        for path in sorted(self.methods_dir.glob("*.yaml")):
            prim = _load_primitive_from_yaml(path)
            if prim.id in self._primitives:
                raise MethodPrimitiveSchemaError(
                    f"duplicate primitive id {prim.id!r} in {path}"
                )
            self._primitives[prim.id] = prim
        self._loaded = True

    # ─── access ───────────────────────────────────────────────────────────

    def all(self) -> list[MethodPrimitive]:
        self._ensure_loaded()
        return list(self._primitives.values())

    def get(self, primitive_id: str) -> MethodPrimitive:
        self._ensure_loaded()
        try:
            return self._primitives[primitive_id]
        except KeyError as exc:
            raise KeyError(f"unknown method primitive: {primitive_id!r}") from exc

    def find_by_domain(self, domain: str) -> list[MethodPrimitive]:
        self._ensure_loaded()
        if domain not in VALID_DOMAINS:
            raise ValueError(f"unknown domain {domain!r}; valid: {sorted(VALID_DOMAINS)}")
        return [p for p in self._primitives.values() if p.domain == domain]

    def find_by_capability(self, keyword: str) -> list[MethodPrimitive]:
        """Free-form keyword search across id, display_name and assumptions.

        Case-insensitive substring match. Replace with embeddings in M5.
        """
        self._ensure_loaded()
        k = keyword.lower()
        out: list[MethodPrimitive] = []
        for p in self._primitives.values():
            haystack = " ".join([p.id, p.display_name, *p.assumptions]).lower()
            if k in haystack:
                out.append(p)
        return out

    def find_by_gate_family(self, family: str) -> list[MethodPrimitive]:
        self._ensure_loaded()
        if family not in VALID_GATE_FAMILIES:
            raise ValueError(
                f"unknown gate family {family!r}; valid: {sorted(VALID_GATE_FAMILIES)}"
            )
        return [p for p in self._primitives.values() if family in p.applicable_gate_families]

    # ─── internals ────────────────────────────────────────────────────────

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load_all()


# ─── YAML loader ──────────────────────────────────────────────────────────


_REQUIRED_KEYS = {
    "id",
    "domain",
    "display_name",
    "inputs",
    "outputs",
    "assumptions",
    "applicable_gate_families",
    "implementation_ref",
    "literature_refs",
}


def _load_primitive_from_yaml(path: Path) -> MethodPrimitive:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise MethodPrimitiveSchemaError(f"{path}: top-level must be a mapping")
    missing = _REQUIRED_KEYS - set(raw.keys())
    if missing:
        raise MethodPrimitiveSchemaError(f"{path}: missing required keys: {sorted(missing)}")
    domain = raw["domain"]
    if domain not in VALID_DOMAINS:
        raise MethodPrimitiveSchemaError(
            f"{path}: invalid domain {domain!r}; valid: {sorted(VALID_DOMAINS)}"
        )
    fams = raw["applicable_gate_families"]
    if not isinstance(fams, list) or any(f not in VALID_GATE_FAMILIES for f in fams):
        raise MethodPrimitiveSchemaError(
            f"{path}: applicable_gate_families must be a subset of {sorted(VALID_GATE_FAMILIES)}"
        )
    return MethodPrimitive(
        id=str(raw["id"]),
        domain=str(raw["domain"]),
        display_name=str(raw["display_name"]),
        inputs=dict(raw["inputs"] or {}),
        outputs=dict(raw["outputs"] or {}),
        assumptions=list(raw["assumptions"] or []),
        applicable_gate_families=list(fams),
        implementation_ref=str(raw["implementation_ref"]),
        literature_refs=list(raw["literature_refs"] or []),
        fast_path_task_package=raw.get("fast_path_task_package"),
        source_path=str(path),
    )


__all__ = [
    "MethodPrimitive",
    "MethodPrimitiveSchemaError",
    "MethodRegistry",
]


def _iter_default_methods() -> Iterable[Path]:  # pragma: no cover - convenience
    return sorted(_DEFAULT_METHODS_DIR.glob("*.yaml"))
