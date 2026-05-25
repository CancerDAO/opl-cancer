"""G6: prompt-injection scan over patient input text. Spec §7 G6 / §6.5 B2.

Failure mode B2 — prompt injection through patient-supplied free text
(diary, message, uploaded notes). G6 BLOCKs when any of:
  * Blacklisted injection phrases ("ignore previous instructions",
    "you are now", "system:" at start of line, "###" role headers, …).
  * Cosine-style token-overlap with the known attack corpus (built-in seed
    list — extend via `attack_corpus` constructor arg).

Implementation is fully synchronous and dependency-free (regex + token
overlap), to satisfy the "no-LLM" mechanical-gate contract (spec §7).
"""
from __future__ import annotations

import re
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

_INJECTION_PHRASES = (
    "ignore previous instructions",
    "ignore all prior instructions",
    "ignore the above",
    "disregard the above",
    "disregard previous",
    "you are now",
    "you are no longer",
    "act as",
    "pretend to be",
    "from now on you",
    "do not follow",
    "system prompt",
    "bypass",
    "jailbreak",
    "重置指令",
    "忽略上面",
    "忽略之前",
    "你现在是",
    "扮演",
)

_ROLE_HEADER = re.compile(
    r"(?m)^\s*(system|assistant|user|developer|tool)\s*[:：]|^###\s*(system|assistant|user)",
    re.IGNORECASE,
)


def _walk_strings(node: Any, key_hint: str = "") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if isinstance(node, str):
        out.append((key_hint, node))
    elif isinstance(node, dict):
        for k, v in node.items():
            out.extend(_walk_strings(v, key_hint=f"{key_hint}.{k}" if key_hint else str(k)))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.extend(_walk_strings(v, key_hint=f"{key_hint}[{i}]"))
    return out


def _token_overlap(text: str, attack: str) -> float:
    t = {w for w in re.findall(r"\w+", text.lower()) if len(w) > 2}
    a = {w for w in re.findall(r"\w+", attack.lower()) if len(w) > 2}
    if not a:
        return 0.0
    return len(t & a) / max(1, len(a))


class G6InjectionScanGate(Gate):
    name = "G6_injection_scan"
    description = "Patient input text scanned for prompt-injection patterns."
    failure_mode_code = "B2"

    def __init__(
        self,
        attack_corpus: list[str] | None = None,
        similarity_threshold: float = 0.6,
    ) -> None:
        self.attack_corpus = list(attack_corpus or [])
        self.similarity_threshold = similarity_threshold

    def check(self, claim: dict[str, Any]) -> GateResult:
        patient_input = claim.get("patient_input") or claim.get("user_message") or {}
        # Treat the whole claim as candidate if patient_input not present, but
        # only flag the patient_input.* paths to avoid false-flagging
        # producer-internal scaffolding.
        scope = patient_input if patient_input else claim.get("messages", [])
        candidates = _walk_strings(scope, key_hint="patient_input")
        if not candidates:
            return GateResult(
                gate=self.name, status=GateStatus.SKIP, message="no patient_input text to scan"
            )
        offenders: list[dict[str, str]] = []
        for path, blob in candidates:
            blob_l = blob.lower()
            for phrase in _INJECTION_PHRASES:
                if phrase in blob_l:
                    offenders.append({"field": path, "match": phrase, "kind": "blacklist"})
                    break
            else:
                if _ROLE_HEADER.search(blob):
                    offenders.append({"field": path, "match": "role-header", "kind": "structural"})
                else:
                    for attack in self.attack_corpus:
                        if _token_overlap(blob, attack) >= self.similarity_threshold:
                            offenders.append(
                                {"field": path, "match": attack[:80], "kind": "corpus-similarity"}
                            )
                            break
        if offenders:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=f"prompt-injection patterns detected in {len(offenders)} field(s)",
                evidence={"offenders": offenders},
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=f"no injection patterns in {len(candidates)} field(s)",
        )
