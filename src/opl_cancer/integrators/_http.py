"""Shared HTTP-with-retry helper for integrators (P0-4).

Why this exists: the 30 integrators previously all called `httpx.AsyncClient`
with `timeout=30.0` and zero retry. Under Wave-concurrent dispatch (~10
experts × 2-4 integrators each) we trip 429s on PubMed/CIViC/etc within
seconds. This module centralises retry policy so a follow-up can flip the
remaining 26 integrators without changing the policy in 26 places.

Retry policy:
  - up to 4 attempts (1 try + 3 retries)
  - exponential backoff with jitter: 0.5s, 1s, 2s base + 0-1s jitter
  - retry on: httpx.TransportError, httpx.TimeoutException, HTTP 429, HTTP 5xx
  - do NOT retry on 4xx other than 429 — those are permanent
  - respect `Retry-After` header on 429 if present (capped at 30s)

Usage:
    from .base import IntegratorError
    from ._http import request_with_retry

    async with httpx.AsyncClient(timeout=30.0) as http:
        r = await request_with_retry(http, "GET", url, params=..., family="pubmed")
"""
from __future__ import annotations

import logging
import random
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


_log = logging.getLogger(__name__)


class _RetryableHTTPError(Exception):
    """Internal sentinel — raised inside the retry loop to signal a retryable
    HTTP status (429/5xx). Never escapes; callers see the final response or
    the underlying httpx exception."""

    def __init__(self, response: httpx.Response):
        super().__init__(f"HTTP {response.status_code}")
        self.response = response


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    family: str = "integrator",
    max_attempts: int = 4,
    **kwargs: Any,
) -> httpx.Response:
    """Issue a request with exponential backoff retry on transient failures.

    Raises the underlying `httpx.HTTPError` or returns the final response. The
    last response is returned even if its status is >= 400 — caller is
    responsible for raising IntegratorError on permanent failures.
    """
    retryer = AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8.0),
        retry=retry_if_exception_type(
            (httpx.TransportError, httpx.TimeoutException, _RetryableHTTPError)
        ),
        reraise=True,
    )
    last_resp: httpx.Response | None = None
    try:
        async for attempt in retryer:
            with attempt:
                resp = await client.request(method, url, **kwargs)
                last_resp = resp
                if resp.status_code == 429 or 500 <= resp.status_code < 600:
                    retry_after = _parse_retry_after(resp)
                    if retry_after is not None:
                        # tenacity wait is fixed at decoration time; emulate
                        # Retry-After by sleeping inside the attempt before
                        # raising the retry signal.
                        import asyncio
                        await asyncio.sleep(min(retry_after, 30.0))
                    _log.warning(
                        "%s: %s %s → HTTP %d, will retry (attempt %d/%d)",
                        family,
                        method,
                        url,
                        resp.status_code,
                        attempt.retry_state.attempt_number,
                        max_attempts,
                    )
                    raise _RetryableHTTPError(resp)
                return resp
    except RetryError as exc:  # pragma: no cover — reraise=True bypasses RetryError
        raise exc.last_attempt.exception() from exc  # type: ignore[misc]
    except _RetryableHTTPError:
        if last_resp is None:  # pragma: no cover
            raise
        return last_resp
    assert last_resp is not None  # unreachable
    return last_resp


def _parse_retry_after(resp: httpx.Response) -> float | None:
    """Parse Retry-After header (seconds form only; HTTP-date form ignored)."""
    val = resp.headers.get("Retry-After")
    if not val:
        return None
    try:
        # Add a small jitter so a thundering herd doesn't all wake at once.
        return float(val) + random.uniform(0.0, 1.0)
    except ValueError:
        return None
