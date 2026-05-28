"""v2.3 P2-#20 — per-run cost tracker.

Records every LLM call + subagent dispatch into
``runs/<run_id>/cost_log.jsonl`` (one JSON object per line). Aggregates
into ``manifest.json.cost_summary`` at Wave 6 bundle time.

Per-call record shape:
    {
      "ts": "2026-05-28T10:11:12.000Z",
      "model": "claude-opus-4-7",
      "prompt_tokens": 12345,
      "completion_tokens": 6789,
      "usd_at_time": 0.0123,
      "latency_s": 4.2,
      "called_by": "wave1_runner.bert.molecular_ngs_interpretation",
      "wave": "1",
      "expert": "bert"
    }

Append-only — no in-place edits. The aggregator is pure / re-runnable.

This module deliberately avoids hooking into the existing LLM clients
at import time. Instead callers (wave runners, dispatcher) call
``record_call()`` explicitly. This keeps cost tracking opt-in and unit-
testable without monkey-patching globals.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


__all__ = [
    "CostRecord",
    "CostTracker",
    "aggregate_cost_log",
    "load_cost_log",
]


# Conservative USD-per-token pricing snapshot (Anthropic + OpenAI + Gemini +
# MiniMax public list prices as of 2026-05-28). The cost tracker is a
# best-effort accountant — exact values are recalibrated at session end
# from real provider invoices when available. Per-million tokens.
DEFAULT_PRICING: dict[str, tuple[float, float]] = {
    # model_id_prefix -> (input_usd_per_million, output_usd_per_million)
    "claude-opus-4": (15.0, 75.0),
    "claude-sonnet-4": (3.0, 15.0),
    "claude-haiku-4": (0.80, 4.0),
    "gpt-5": (10.0, 30.0),
    "gpt-4o": (2.50, 10.0),
    "gemini-2.5-pro": (1.25, 5.0),
    "gemini-2.5-flash": (0.075, 0.30),
    "MiniMax-M2": (1.0, 5.0),
}


def _estimate_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Return best-effort USD estimate based on prefix-match pricing."""
    model_lc = model.lower()
    for prefix, (in_usd_per_m, out_usd_per_m) in DEFAULT_PRICING.items():
        if model_lc.startswith(prefix.lower()):
            return (
                prompt_tokens * in_usd_per_m / 1_000_000.0
                + completion_tokens * out_usd_per_m / 1_000_000.0
            )
    # Unknown model — return 0 rather than guess. The aggregator will
    # surface untracked models in a separate bucket.
    return 0.0


@dataclass
class CostRecord:
    ts: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    usd_at_time: float = 0.0
    latency_s: float = 0.0
    called_by: str = ""
    wave: str = ""
    expert: str = ""
    extras: dict[str, Any] = field(default_factory=dict)

    def to_json_line(self) -> str:
        d = asdict(self)
        # extras are emitted at top level for grep-ability.
        extras = d.pop("extras")
        d.update(extras)
        return json.dumps(d, ensure_ascii=False)


class CostTracker:
    """Append-only per-run cost ledger.

    Usage:
        tracker = CostTracker(run_dir=Path("runs/abc"))
        tracker.record_call(
            model="claude-opus-4-7",
            prompt_tokens=12345,
            completion_tokens=6789,
            latency_s=4.2,
            called_by="wave1.bert.molecular_ngs_interpretation",
            wave="1", expert="bert",
        )
        summary = tracker.aggregate()
    """

    def __init__(self, *, run_dir: Path, log_filename: str = "cost_log.jsonl") -> None:
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.run_dir / log_filename

    # ─── recording ──────────────────────────────────────────────────────

    def record_call(
        self,
        *,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        usd_at_time: float | None = None,
        latency_s: float = 0.0,
        called_by: str = "",
        wave: str = "",
        expert: str = "",
        **extras: Any,
    ) -> CostRecord:
        if usd_at_time is None:
            usd_at_time = _estimate_usd(model, prompt_tokens, completion_tokens)
        rec = CostRecord(
            ts=datetime.now(timezone.utc).isoformat(),
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            usd_at_time=float(usd_at_time),
            latency_s=float(latency_s),
            called_by=called_by,
            wave=wave,
            expert=expert,
            extras=extras,
        )
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(rec.to_json_line() + "\n")
        return rec

    def record_subagent(
        self,
        *,
        agent_type: str,
        model: str = "",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_s: float = 0.0,
        called_by: str = "",
        wave: str = "",
        expert: str = "",
        **extras: Any,
    ) -> CostRecord:
        """Convenience wrapper for subagent dispatches. Routes through record_call
        with a tagged extras['agent_type'] for downstream filtering."""
        return self.record_call(
            model=model or agent_type,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_s=latency_s,
            called_by=called_by or f"subagent:{agent_type}",
            wave=wave,
            expert=expert,
            agent_type=agent_type,
            kind="subagent",
            **extras,
        )

    # ─── reading ────────────────────────────────────────────────────────

    def load_records(self) -> list[dict[str, Any]]:
        return load_cost_log(self.log_path)

    def aggregate(self) -> dict[str, Any]:
        return aggregate_cost_log(self.log_path)


def load_cost_log(log_path: Path) -> list[dict[str, Any]]:
    log_path = Path(log_path)
    if not log_path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for raw in log_path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            # Skip corrupt lines — append-only contract is best-effort
            # robust against partial writes.
            continue
    return out


def aggregate_cost_log(log_path: Path) -> dict[str, Any]:
    """Aggregate a cost_log.jsonl into the cost_summary shape expected by
    the n1a manifest schema."""
    records = load_cost_log(log_path)
    total_usd = 0.0
    tokens_input = 0
    tokens_output = 0
    by_model: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"calls": 0, "usd": 0.0, "prompt_tokens": 0, "completion_tokens": 0}
    )
    by_wave: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"calls": 0, "usd": 0.0}
    )
    by_expert: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"calls": 0, "usd": 0.0}
    )

    for rec in records:
        usd = float(rec.get("usd_at_time", 0.0))
        pt = int(rec.get("prompt_tokens", 0))
        ct = int(rec.get("completion_tokens", 0))
        total_usd += usd
        tokens_input += pt
        tokens_output += ct

        m = str(rec.get("model", "unknown"))
        bm = by_model[m]
        bm["calls"] += 1
        bm["usd"] += usd
        bm["prompt_tokens"] += pt
        bm["completion_tokens"] += ct

        w = str(rec.get("wave", "unknown"))
        bw = by_wave[w]
        bw["calls"] += 1
        bw["usd"] += usd

        e = str(rec.get("expert", "unknown"))
        be = by_expert[e]
        be["calls"] += 1
        be["usd"] += usd

    return {
        "total_usd": round(total_usd, 6),
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "by_model": [
            {"model": m, **{k: (round(v, 6) if isinstance(v, float) else v) for k, v in s.items()}}
            for m, s in sorted(by_model.items())
        ],
        "by_wave": [
            {"wave": w, **{k: (round(v, 6) if isinstance(v, float) else v) for k, v in s.items()}}
            for w, s in sorted(by_wave.items())
        ],
        "by_expert": [
            {"expert": e, **{k: (round(v, 6) if isinstance(v, float) else v) for k, v in s.items()}}
            for e, s in sorted(by_expert.items())
        ],
    }
