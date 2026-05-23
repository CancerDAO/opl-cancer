"""Test PI (Sid) session state machine — spec §4 + §6.1."""
from pathlib import Path

from opl_cancer.orchestrator.pi_session import (
    ConversationTurn,  # noqa: F401  re-export check
    IntentClass,
    PatientPreferences,  # noqa: F401  re-export check
    PISession,
)


def test_pi_session_initializes_with_patient_code(tmp_path: Path) -> None:
    s = PISession(patient_code="anon_001", session_dir=tmp_path)
    assert s.patient_code == "anon_001"
    assert s.persona_name == "sid"


def test_pi_session_appends_conversation_turn(tmp_path: Path) -> None:
    s = PISession(patient_code="p", session_dir=tmp_path)
    s.append_turn(role="patient", content="我想了解我的 NGS 结果")
    s.append_turn(role="pi", content="好,让我调 Bert 看看。")
    turns = list(s.iter_conversation())
    assert len(turns) == 2
    assert turns[0].role == "patient"
    assert turns[1].role == "pi"


def test_pi_session_classifies_intent_skeleton(tmp_path: Path) -> None:
    s = PISession(patient_code="p", session_dir=tmp_path)
    intent = s.classify_intent_stub("我想了解我的 NGS 结果")
    assert intent in IntentClass


def test_pi_session_preferences_default_then_update(tmp_path: Path) -> None:
    s = PISession(patient_code="p", session_dir=tmp_path)
    assert s.preferences.depth == "technical"
    s.update_preferences({"depth": "patient_friendly", "language": "zh-CN"})
    assert s.preferences.depth == "patient_friendly"


def test_pi_session_persists_across_instances(tmp_path: Path) -> None:
    s1 = PISession(patient_code="p", session_dir=tmp_path)
    s1.append_turn(role="patient", content="hi")
    s1.persist()
    s2 = PISession(patient_code="p", session_dir=tmp_path)
    s2.load()
    assert len(list(s2.iter_conversation())) == 1
