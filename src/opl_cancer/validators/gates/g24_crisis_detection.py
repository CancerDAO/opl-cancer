"""G24: Crisis-grade self-harm language must trigger crisis-card + Wave lock.

Spec §7 G24 / §6.5 G-safety-1 (new v1.3.2 SAFETY hot-fix).

Failure mode G-safety-1 — patient (or caregiver) utterance contains
suicidal-ideation / self-harm / acute-psychiatric-crisis language and the
runner falls through to ordinary intent classification (EMOTION → cancer-
buddy-mind handoff is too soft; trial-dump on a bedbound suicidal patient
is a safety disaster).

G24 is a **no-LLM** keyword-scan gate. It is the reviewer-of-LLM authority
for crisis detection: if the upstream `crisis_detection` prompt missed a
signal that G24 catches, G24 wins. The gate cannot be suppressed.

Behaviour:
  * Scan ``patient_text`` (+ optional ``caregiver_text``) in the claim for
    Chinese + English SI / self-harm phrases (three grades: passive_SI /
    active_SI / active_plan).
  * On hit → ``GateStatus.FAIL`` + ``block=True`` + payload describing the
    grade + recommended handoffs + ``wave_lock=true``.
  * The orchestrator (wave1_runner / wave2_runner / etc.) reads block=True
    + payload, emits ``crisis_card.json`` via
    ``prompts/tasks/crisis_card_emission.md``, and refuses to advance until
    ``cli.py acknowledge <crisis_card_id>`` is called.

Introduced for v1.3.2 round-2 EVAL panel feedback (Patient #17 — ECOG-3
bedbound + "想结束这一切 / end it all" fell through to EMOTION → trial dump).

Why keyword-scan, not LLM:
  * No silent fallback (memory:feedback_no_offline_only).
  * No model dependency: if the network or LLM is down, this gate still fires.
  * The bilingual banks are explicit; an LLM cannot suppress a verbatim
    keyword hit.
"""
from __future__ import annotations

import re
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


# ─── Bank A — passive_SI (想结束 / 不想活 / had enough / wish I wasn't here) ────
# Phrases where the patient signals not wanting to be alive but without
# direct ideation about ending one's own life.
_PASSIVE_SI_ZH: tuple[str, ...] = (
    "不想活了", "不想再活", "活够了", "活着没意思", "活着真没意思",
    "我不想再坚持", "想结束这一切", "结束这一切", "想解脱", "解脱算了",
    "一了百了", "走了算了", "走了好了", "受够了", "撑不下去了",
    "扛不下去", "扛不动了", "活着是受罪", "活着遭罪",
    "我是负担", "我成了负担", "拖累家人", "拖累你们",
    "再也不想这样", "睡着不醒",
)
_PASSIVE_SI_EN: tuple[str, ...] = (
    "i can't go on", "can't go on anymore", "had enough of this",
    "want it to end", "want this to end", "want to be done with this",
    "wish i was dead", "wish i were dead", "wish i wasn't here",
    "wish i weren't here", "tired of living", "don't want to live",
    "do not want to live anymore", "i'm a burden", "i am a burden",
    "everyone would be better off without me",
    "world would be better off without me",
    "no point in living", "no point anymore",
)

# ─── Bank B — active_SI (想自杀 / kill myself / suicidal) ─────────────────────
# Direct ideation about ending one's own life, without specified means.
_ACTIVE_SI_ZH: tuple[str, ...] = (
    "想自杀", "我要自杀", "想死", "我想死", "我要死了", "去死",
    "杀了我自己", "结束自己", "结束自己生命", "结束我的生命",
    "了结自己", "了结我自己", "自我了断", "自残", "伤害自己",
    "想伤害自己",
)
_ACTIVE_SI_EN: tuple[str, ...] = (
    "want to kill myself", "going to kill myself", "thinking of killing myself",
    "thoughts of killing myself", "thinking about killing myself",
    "killing myself", "kill myself", "suicidal",
    "suicidal thoughts", "thinking about suicide", "end my life",
    "ending my life", "end it all", "ending it all", "self-harm",
    "self harm", "hurt myself", "harm myself",
)

# ─── Bank C — active_plan (具体方案 / means / time / place) ──────────────────
# Specific means / time / place / accumulated method.
_ACTIVE_PLAN_ZH: tuple[str, ...] = (
    "我藏了药", "我把药存起来", "攒了药", "我有把刀",
    "今晚就", "明天就", "周五就走", "想跳楼", "想跳河", "想跳桥",
    "想割腕", "用绳子", "上吊", "服毒", "服安眠药",
)
_ACTIVE_PLAN_EN: tuple[str, ...] = (
    "i have a plan", "i've decided when", "i have decided when",
    "i have the pills", "i stockpiled", "i've stockpiled",
    "by friday", "tomorrow night", "tonight i will",
    "jump off", "jump from", "hang myself", "cut my wrists",
    "overdose tonight", "overdose tomorrow",
)


# ─── Jurisdiction inference ──────────────────────────────────────────────────
# Default jurisdiction guesses based on language + simple location tokens.
_LANG_TO_JURISDICTION: dict[str, str] = {
    "zh": "CN", "zh-cn": "CN", "zh-hans": "CN",
    "en": "US", "en-us": "US", "en-gb": "UK",
    "de": "DE", "de-de": "DE",
    "ja": "JP", "ja-jp": "JP",
    "fr": "EU", "es": "EU", "it": "EU", "pt": "EU",
}

_LOC_HINTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(US|USA|America|United States|纽约|加州|波士顿)\b", re.I), "US"),
    (re.compile(r"\b(UK|United Kingdom|London|英国|伦敦)\b", re.I), "UK"),
    (re.compile(r"\b(Germany|Deutschland|柏林|德国|慕尼黑)\b", re.I), "DE"),
    (re.compile(r"\b(Japan|日本|东京|大阪)\b", re.I), "JP"),
    (re.compile(r"\b(China|中国|上海|北京|杭州|深圳|广州|香港)\b", re.I), "CN"),
    (re.compile(r"\b(France|Paris|法国|巴黎|Spain|Madrid|Italy|Rome|Roma)\b", re.I), "EU"),
)

_HAS_CJK = re.compile(r"[一-鿿]")


def _scan_banks(text_lower: str, text_orig: str) -> tuple[str | None, str]:
    """Return (grade, trigger_phrase). grade ∈ {active_plan, active_SI, passive_SI, None}.

    Highest-grade match wins. trigger_phrase is the verbatim match in the
    original-case text (best-effort recovery from text_orig).
    """
    for phrase in _ACTIVE_PLAN_ZH + _ACTIVE_PLAN_EN:
        if phrase in text_lower:
            return ("active_plan", _recover_case(text_orig, phrase))
    for phrase in _ACTIVE_SI_ZH + _ACTIVE_SI_EN:
        if phrase in text_lower:
            return ("active_SI", _recover_case(text_orig, phrase))
    for phrase in _PASSIVE_SI_ZH + _PASSIVE_SI_EN:
        if phrase in text_lower:
            return ("passive_SI", _recover_case(text_orig, phrase))
    return (None, "")


def _recover_case(text_orig: str, phrase_lower: str) -> str:
    """Find the verbatim substring in text_orig that matches phrase_lower."""
    idx = text_orig.lower().find(phrase_lower)
    if idx < 0:
        return phrase_lower
    return text_orig[idx : idx + len(phrase_lower)]


def _infer_jurisdiction(text: str, hint: str | None) -> str:
    """Infer crisis-line jurisdiction from explicit hint, location tokens, then language."""
    if hint:
        h = hint.strip().upper()
        if h in ("CN", "US", "UK", "EU", "DE", "JP", "OTHER", "UNKNOWN"):
            return h if h != "UNKNOWN" else "unknown"
    for pat, juris in _LOC_HINTS:
        if pat.search(text):
            return juris
    if _HAS_CJK.search(text):
        return "CN"
    if re.search(r"[a-zA-Z]", text):
        return "US"
    return "unknown"


def _gather_text_fields(claim: dict[str, Any]) -> str:
    """Collect every text field G24 should scan."""
    fields = [
        claim.get("patient_text", ""),
        claim.get("caregiver_text", ""),
        claim.get("text", ""),
        claim.get("delivery_text", ""),
        claim.get("delivery_markdown", ""),
        claim.get("pi_prose", ""),
        claim.get("summary", ""),
        claim.get("claim", ""),
        claim.get("rationale", ""),
    ]
    return " \n ".join(str(f) for f in fields if f)


class G24CrisisDetectionGate(Gate):
    name = "G24_crisis_detection"
    description = (
        "Crisis-grade self-harm language (passive_SI / active_SI / active_plan) "
        "must trigger crisis-card emission + Wave lock + dual-sibling handoff "
        "(cancer-buddy-mind + jurisdictional crisis line)."
    )
    failure_mode_code = "G-safety-1"

    def check(self, claim: dict[str, Any]) -> GateResult:
        text = _gather_text_fields(claim)
        if not text:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message="no patient_text / caregiver_text / claim text to scan",
            )

        grade, trigger_phrase = _scan_banks(text.lower(), text)
        if grade is None:
            return GateResult(
                gate=self.name,
                status=GateStatus.PASS,
                message="no SI / self-harm keyword hit across patient + caregiver text banks",
            )

        jurisdiction = _infer_jurisdiction(
            text, claim.get("profile_jurisdiction_hint"),
        )
        return GateResult(
            gate=self.name,
            status=GateStatus.FAIL,
            block=True,
            message=(
                f"G24 CRISIS — crisis_grade={grade} on trigger_phrase={trigger_phrase!r}; "
                "Wave runners must lock + emit crisis_card.json via "
                "prompts/tasks/crisis_card_emission.md before any further dispatch."
            ),
            evidence={
                "crisis_grade": grade,
                "trigger_phrase": trigger_phrase,
                "jurisdiction_inferred": jurisdiction,
                "recommended_handoff": [
                    "cancer-buddy-mind",
                    f"jurisdiction-crisis-line:{jurisdiction}",
                ],
                "wave_lock": True,
                "failure_mode": self.failure_mode_code,
            },
        )
