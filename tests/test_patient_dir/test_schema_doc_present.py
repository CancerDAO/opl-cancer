"""Test that patients/SCHEMA.md documents required directory structure."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_patients_schema_doc_exists() -> None:
    assert (REPO_ROOT / "patients" / "SCHEMA.md").exists()


def test_schema_doc_lists_required_subdirs() -> None:
    text = (REPO_ROOT / "patients" / "SCHEMA.md").read_text()
    required = ["profile.json", "memory/", "pi_session/", "triggers/", "inbox/"]
    for r in required:
        assert r in text, f"SCHEMA.md missing reference to {r}"
