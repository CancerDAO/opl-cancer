#!/usr/bin/env python3
"""v2 E2E verifier — checks ADR-0010 success criteria on a run dir.

Verifies that a completed run actually surfaces World-Unknown candidates,
as the v2 paradigm shift promises. Exits 0 on PASS, 1 on FAIL with a
specific list of which checks failed (so the user can trace the seam).

Usage:
    python scripts/verify_v2_e2e.py <run_dir>

Expected layout:
    <run_dir>/
        wave2_hypotheses.json          # produced by Wave 2 runner
        delivery/patient_brief.html    # produced by Wave 5 renderer
        delivery/patient_brief.md      # produced by Wave 5 renderer (optional)

The script does NOT call any LLM. It is a pure artifact-reader, suitable
for CI and for trust-but-verify after a real run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def verify(run_dir: Path) -> tuple[bool, list[str]]:
    failures: list[str] = []

    # ---- Wave 2 output checks ---------------------------------------------
    wave2 = run_dir / "wave2_hypotheses.json"
    if not wave2.exists():
        failures.append(f"missing {wave2}")
        return False, failures

    try:
        payload = json.loads(wave2.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"wave2_hypotheses.json not valid JSON: {exc}")
        return False, failures

    hyps = payload.get("hypotheses") or payload.get("top_k_hypotheses") or []
    strats = {h.get("generation_strategy") for h in hyps}

    if "target_synergy_emergent" not in strats:
        failures.append(
            "no hypothesis with generation_strategy=target_synergy_emergent "
            "(Maya's signature output — paradigm shift not engaged)"
        )
    if "undrugged_target_design" not in strats:
        failures.append(
            "no hypothesis with generation_strategy=undrugged_target_design "
            "(Julius's signature output — paradigm shift not engaged)"
        )

    spec_with_testability = [
        h
        for h in hyps
        if h.get("claim_layer") == "speculative" and h.get("testability_path")
    ]
    if len(spec_with_testability) < 2:
        failures.append(
            f"expected ≥2 [S]-with-testability hypotheses, got "
            f"{len(spec_with_testability)} — patient brief World-Unknown "
            f"section will be sparse"
        )

    # ---- Wave 5 patient brief checks --------------------------------------
    brief_html = run_dir / "delivery" / "patient_brief.html"
    if not brief_html.exists():
        failures.append(f"missing {brief_html}")
    else:
        text = brief_html.read_text(encoding="utf-8")
        if "World-Unknown" not in text:
            failures.append(
                "patient_brief.html missing the World-Unknown section header "
                "(renderer template wasn't updated, or world_unknown_candidates "
                "context was empty)"
            )
        if "未发表" not in text:
            failures.append(
                "patient_brief.html World-Unknown section missing 未发表 framing"
            )
        if "research direction" not in text.lower():
            failures.append(
                "patient_brief.html World-Unknown section missing "
                "'research direction' framing — violates ADR-0010 anti-recommendation rule"
            )

    return not failures, failures


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: python scripts/verify_v2_e2e.py <run_dir>", file=sys.stderr
        )
        return 2
    run_dir = Path(sys.argv[1])
    if not run_dir.exists():
        print(f"❌ run_dir does not exist: {run_dir}", file=sys.stderr)
        return 2
    ok, fails = verify(run_dir)
    if ok:
        print(f"✅ v2 E2E verification PASS — {run_dir}")
        return 0
    print(f"❌ v2 E2E verification FAIL — {run_dir}:", file=sys.stderr)
    for f in fails:
        print(f"  - {f}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
