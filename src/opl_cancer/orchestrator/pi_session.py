"""PI (Sid) session state machine — single conversational surface. Spec §4 + §6.1."""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Iterator, Literal

from pydantic import BaseModel, Field


class IntentClass(str, Enum):
    NEW_GOAL = "new_goal"
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
        t = patient_text.lower()
        if any(k in t for k in ("感觉", "害怕", "担心", "焦虑")):
            return IntentClass.EMOTION
        if any(k in t for k in ("为什么", "drill", "解释", "证据")):
            return IntentClass.DRILL_DOWN
        if any(k in t for k in ("偏好", "设置", "调整")):
            return IntentClass.PREFERENCE_UPDATE
        if patient_text.startswith(("hi", "hello", "你好")) and len(patient_text) < 20:
            return IntentClass.SMALL_TALK
        return IntentClass.NEW_GOAL

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
