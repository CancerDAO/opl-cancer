"""PI (Sid) session state machine — single conversational surface. Spec §4 + §6.1.

P4: classify_intent_llm replaces P0 keyword stub (no-hardcoded-keyword-list policy).
"""
from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from opl_cancer._llm_contract import LLMClient  # transitional shim


class IntentClass(str, Enum):
    NEW_GOAL = "new_goal"
    HYPOTHESIS_REQUEST = "hypothesis_request"
    DRILL_DOWN = "drill_down"
    PREFERENCE_UPDATE = "preference_update"
    SMALL_TALK = "small_talk"
    EMOTION = "emotion"


class PatientPreferences(BaseModel):
    depth: Literal["technical", "patient_friendly"] = "technical"
    language: Literal["zh-CN", "en"] = "zh-CN"
    focus: list[str] = Field(default_factory=list)


class ConversationTurn(BaseModel):
    timestamp: str = ""
    role: Literal["patient", "pi"]
    content: str
    refs: list[str] = Field(default_factory=list)
    triggered_run_id: str | None = None


class PISession:
    """Per-patient long-lived session. One instance per active patient."""

    persona_name = "sid"

    def __init__(self, patient_code: str, session_dir: Path) -> None:
        self.patient_code = patient_code
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._turns: list[ConversationTurn] = []
        self.preferences = PatientPreferences()

    @property
    def conversation_path(self) -> Path:
        return self.session_dir / "conversation.jsonl"

    @property
    def preferences_path(self) -> Path:
        return self.session_dir / "preferences.json"

    def append_turn(self, *, role: Literal["patient", "pi"], content: str, **extra: object) -> None:
        turn = ConversationTurn(role=role, content=content, **extra)  # type: ignore[arg-type]
        self._turns.append(turn)
        with self.conversation_path.open("a", encoding="utf-8") as f:
            f.write(turn.model_dump_json() + "\n")

    def iter_conversation(self) -> Iterator[ConversationTurn]:
        return iter(self._turns)

    def update_preferences(self, updates: dict[str, object]) -> None:
        self.preferences = self.preferences.model_copy(update=updates)
        self.preferences_path.write_text(self.preferences.model_dump_json(indent=2))

    def classify_intent_stub(self, patient_text: str) -> IntentClass:
        """Keyword-based fallback. Retained for CI without API keys / quick smoke."""
        t = patient_text.lower()
        if any(k in t for k in ("假设", "想法", "新方向", "what if", "novel")):
            return IntentClass.HYPOTHESIS_REQUEST
        if any(k in t for k in ("感觉", "害怕", "担心", "焦虑")):
            return IntentClass.EMOTION
        if any(k in t for k in ("为什么", "drill", "解释", "证据")):
            return IntentClass.DRILL_DOWN
        if any(k in t for k in ("偏好", "设置", "调整")):
            return IntentClass.PREFERENCE_UPDATE
        if patient_text.startswith(("hi", "hello", "你好")) and len(patient_text) < 20:
            return IntentClass.SMALL_TALK
        return IntentClass.NEW_GOAL

    async def classify_intent_llm(
        self,
        patient_text: str,
        llm_client: "LLMClient",
        model_id: str,
        profile_json: str = "{}",
    ) -> IntentClass:
        """LLM-backed intent classification (P4 — replaces stub for live deployments).

        Raises on bad JSON / unknown intent (no silent degradation —
        no-silent-fallback policy + feedback_default_prompt_over_script).
        """
        from opl_cancer._llm_contract import LLMRequest, LLMResponseParseError  # transitional shim
        from opl_cancer.prompts_loader import PromptTemplate, find_prompts_root

        template = PromptTemplate.load(
            find_prompts_root() / "pi" / "intent_parser.md",
            version="pi_intent_parser@v0.1.0",
        )
        prompt_text = template.render(
            patient_text=patient_text,
            profile_json=profile_json,
        )
        req = LLMRequest(
            model=model_id,
            messages=[{"role": "user", "content": prompt_text}],
            max_tokens=512,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        resp = await llm_client.complete(req)
        try:
            data: dict[str, Any] = json.loads(resp.content)
        except json.JSONDecodeError as exc:
            raise LLMResponseParseError(
                f"intent_parser returned non-JSON: {resp.content[:200]!r}"
            ) from exc
        raw_intent = data.get("intent")
        if not isinstance(raw_intent, str):
            raise LLMResponseParseError(
                f"intent_parser JSON missing 'intent' key or wrong type: {data!r}"
            )
        try:
            return IntentClass(raw_intent.lower())
        except ValueError as exc:
            raise LLMResponseParseError(
                f"intent_parser returned unknown intent {raw_intent!r}; "
                f"expected one of {[e.value for e in IntentClass]}"
            ) from exc

    def persist(self) -> None:
        if not self.preferences_path.exists():
            self.preferences_path.write_text(self.preferences.model_dump_json(indent=2))

    def load(self) -> None:
        if self.conversation_path.exists():
            with self.conversation_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self._turns.append(ConversationTurn.model_validate_json(line))
        if self.preferences_path.exists():
            self.preferences = PatientPreferences.model_validate_json(
                self.preferences_path.read_text()
            )
