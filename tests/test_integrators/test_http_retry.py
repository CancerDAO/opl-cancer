"""P0-4: request_with_retry exponential backoff on 429/5xx + transport errors.

Wave-concurrent dispatch hits NCBI/CIViC etc with 10+ parallel requests;
without retry, a single 429 fails the whole expert run. This test verifies
the retry loop actually retries (and that permanent 4xx aren't retried).
"""
from __future__ import annotations

import httpx
import pytest
import respx
from httpx import Response

from opl_cancer.integrators._http import request_with_retry


@pytest.mark.asyncio
@respx.mock
async def test_retries_on_429_then_succeeds() -> None:
    route = respx.get("https://api.example.com/x").mock(
        side_effect=[
            Response(429, headers={"Retry-After": "0"}, text="rate-limited"),
            Response(429, headers={"Retry-After": "0"}, text="rate-limited"),
            Response(200, text="ok"),
        ]
    )
    async with httpx.AsyncClient(timeout=5.0) as http:
        r = await request_with_retry(http, "GET", "https://api.example.com/x", family="test")
    assert r.status_code == 200
    assert route.call_count == 3


@pytest.mark.asyncio
@respx.mock
async def test_retries_on_5xx_then_succeeds() -> None:
    route = respx.get("https://api.example.com/y").mock(
        side_effect=[
            Response(503, text="unavail"),
            Response(200, text="ok"),
        ]
    )
    async with httpx.AsyncClient(timeout=5.0) as http:
        r = await request_with_retry(http, "GET", "https://api.example.com/y", family="test")
    assert r.status_code == 200
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_no_retry_on_404() -> None:
    """4xx other than 429 are permanent — no retry, return immediately."""
    route = respx.get("https://api.example.com/z").mock(
        return_value=Response(404, text="not found")
    )
    async with httpx.AsyncClient(timeout=5.0) as http:
        r = await request_with_retry(http, "GET", "https://api.example.com/z", family="test")
    assert r.status_code == 404
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_retries_on_transport_error_then_succeeds() -> None:
    route = respx.get("https://api.example.com/w").mock(
        side_effect=[
            httpx.ConnectError("conn refused"),
            httpx.ReadTimeout("slow"),
            Response(200, text="ok"),
        ]
    )
    async with httpx.AsyncClient(timeout=5.0) as http:
        r = await request_with_retry(http, "GET", "https://api.example.com/w", family="test")
    assert r.status_code == 200
    assert route.call_count == 3


@pytest.mark.asyncio
@respx.mock
async def test_exhausts_retries_and_returns_last_response() -> None:
    route = respx.get("https://api.example.com/perm5xx").mock(
        return_value=Response(500, text="server error always")
    )
    async with httpx.AsyncClient(timeout=5.0) as http:
        r = await request_with_retry(http, "GET", "https://api.example.com/perm5xx", family="test", max_attempts=2)
    assert r.status_code == 500
    assert route.call_count == 2
