"""Method primitives (v2.5 compositional foundation — RFC 0001 §2.2).

8 seed primitives ship in v2.5; full library to ~50 primitives in M4.
"""
from __future__ import annotations

from ._abc import VALID_DOMAINS, VALID_GATE_FAMILIES, MethodPrimitive
from .registry import MethodPrimitiveSchemaError, MethodRegistry

__all__ = [
    "MethodPrimitive",
    "MethodPrimitiveSchemaError",
    "MethodRegistry",
    "VALID_DOMAINS",
    "VALID_GATE_FAMILIES",
]
