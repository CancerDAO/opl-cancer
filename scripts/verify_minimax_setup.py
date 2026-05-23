"""Manual CLI check for MiniMax-M2.7 setup (Iter 10 task #3).

Usage:
    MINIMAX_API_KEY=sk-cp-... python scripts/verify_minimax_setup.py

Verifies:
  1. MINIMAX_API_KEY is set
  2. Endpoint api.minimaxi.com is reachable
  3. A trivial json_object completion returns 200 + valid JSON content
  4. errcode 2056 surfaces as LLMQuotaError (informational — only if quota hit)

Exit codes:
  0 — all checks pass
  1 — env not set
  2 — transport / 4xx / 5xx
  3 — JSON parse failure
  4 — quota exhausted (LLMQuotaError 2056)
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

from opl_cancer.llm.base import LLMRequest
from opl_cancer.llm.errors import LLMError, LLMQuotaError, LLMResponseParseError
from opl_cancer.llm.minimax_client import MiniMaxClient


async def _main() -> int:
    if not os.environ.get("MINIMAX_API_KEY"):
        print("ERROR: MINIMAX_API_KEY not set in env.", file=sys.stderr)
        return 1

    print("[1/3] Initialising MiniMaxClient ...")
    client = MiniMaxClient()
    print(f"      base_url = {client.base_url}")

    print("[2/3] Sending trivial json_object completion (model=MiniMax-M2.7) ...")
    req = LLMRequest(
        model="MiniMax-M2.7",
        messages=[
            {
                "role": "user",
                "content": 'Reply with ONLY {"status": "ok"}.',
            }
        ],
        max_tokens=256,
        response_format={"type": "json_object"},
    )
    try:
        resp = await client.complete(req)
    except LLMQuotaError as e:
        print(f"[FAIL] errcode 2056 (quota): {e}", file=sys.stderr)
        return 4
    except LLMResponseParseError as e:
        print(f"[FAIL] response parse error: {e}", file=sys.stderr)
        return 3
    except LLMError as e:
        print(f"[FAIL] transport / HTTP error: {e}", file=sys.stderr)
        return 2

    print(f"      HTTP/business OK. model={resp.model} tokens_out={resp.output_tokens}")
    print("[3/3] Parsing response.content as JSON ...")
    try:
        parsed = json.loads(resp.content)
    except json.JSONDecodeError as e:
        print(f"[FAIL] content is not JSON: {e}", file=sys.stderr)
        print(f"      raw content: {resp.content!r}", file=sys.stderr)
        return 3
    print(f"      parsed: {parsed!r}")
    print("\nALL CHECKS PASSED. MiniMax setup verified.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
