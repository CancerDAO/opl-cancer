"""NCBI E-utilities shared identity params.

NCBI's E-utilities policy (https://www.ncbi.nlm.nih.gov/books/NBK25497/) requires
every request to include `tool=` and `email=` identifiers. Anonymous traffic is
rate-limited to 3 req/sec and may be IP-banned on bursts. Setting NCBI_API_KEY
raises the limit to 10 req/sec.

Used by: pubmed, clinvar, geo, sra integrators (P0-2).
"""
from __future__ import annotations

import os
from typing import Any


_TOOL = "opl-cancer"
_DEFAULT_EMAIL = "contact@cancerdao.org"


def ncbi_identity_params() -> dict[str, str]:
    """Return the identity params NCBI eutils requires on every call.

    Env overrides:
      OPL_NCBI_EMAIL  — contact address, defaults to contact@cancerdao.org
      OPL_NCBI_TOOL   — tool name, defaults to opl-cancer
      NCBI_API_KEY    — if set, raises rate limit from 3 to 10 req/s
    """
    email = os.environ.get("OPL_NCBI_EMAIL", _DEFAULT_EMAIL)
    tool = os.environ.get("OPL_NCBI_TOOL", _TOOL)
    params: dict[str, str] = {"tool": tool, "email": email}
    api_key = os.environ.get("NCBI_API_KEY")
    if api_key:
        params["api_key"] = api_key
    return params


def with_ncbi_identity(base_params: dict[str, Any]) -> dict[str, Any]:
    """Merge `base_params` with NCBI identity. Caller's params win on conflict."""
    merged: dict[str, Any] = dict(ncbi_identity_params())
    merged.update(base_params)
    return merged
