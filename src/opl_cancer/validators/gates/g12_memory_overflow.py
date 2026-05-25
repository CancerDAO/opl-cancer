"""G12: memory context overflow guard. Spec §7 G12 / §6.5 A6.

Failure mode A6 — silent truncation of memory context: when memory snippets
fed into a producer's prompt approach the model's context window, harnesses
sometimes silently truncate from the head, dropping critical patient facts.
G12 BLOCKs whenever the assembled memory context exceeds 80% of the model's
context window, forcing the caller to either (a) prune via the curator
sub-skill, or (b) split the task — never silently truncate.

Token estimation: char-count / 4 (rough English token average) plus an
explicit factor for CJK-heavy text (CJK char = ~1 token).
"""
from __future__ import annotations

import re
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

_CJK_RE = re.compile(r"[㐀-鿿]")


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    cjk = len(_CJK_RE.findall(text))
    non_cjk = len(text) - cjk
    return cjk + max(1, non_cjk // 4)


def _walk_text(node: Any) -> int:
    if isinstance(node, str):
        return _estimate_tokens(node)
    if isinstance(node, dict):
        return sum(_walk_text(v) for v in node.values())
    if isinstance(node, list):
        return sum(_walk_text(v) for v in node)
    return 0


class G12MemoryOverflowGate(Gate):
    name = "G12_memory_overflow"
    description = "Block when memory_context exceeds 80% of model context window."
    failure_mode_code = "A6"

    def __init__(self, context_window: int, threshold: float = 0.8) -> None:
        if context_window <= 0:
            raise ValueError("context_window must be > 0")
        self.context_window = context_window
        self.threshold = threshold

    def check(self, claim: dict[str, Any]) -> GateResult:
        mem = claim.get("memory_context") or claim.get("memory") or {}
        if not mem:
            return GateResult(
                gate=self.name, status=GateStatus.SKIP, message="no memory_context attached"
            )
        tokens = _walk_text(mem)
        ratio = tokens / self.context_window
        if ratio >= self.threshold:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"memory_context ~{tokens} tokens = {ratio:.0%} of window "
                    f"({self.context_window}); ≥ {self.threshold:.0%} threshold — "
                    "trigger pruning, do NOT silently truncate"
                ),
                evidence={
                    "estimated_tokens": tokens,
                    "context_window": self.context_window,
                    "ratio": round(ratio, 3),
                    "threshold": self.threshold,
                },
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=f"memory_context ~{tokens} tokens = {ratio:.0%} of window — safe",
            evidence={"estimated_tokens": tokens, "ratio": round(ratio, 3)},
        )
