"""v2.1 P0-#5: profile.json conforms to JSON Schema."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

SCHEMA = json.loads(Path("schemas/profile.schema.json").read_text())


def test_valid_profile_passes():
    profile = {
        "patient_id_hash": "abc",
        "prior_lines": 2,
        "concurrent_meds": ["aspirin", "metformin"],
        "egfr_ml_min": 75,
        "lvef_pct": 60,
        "age_years": 55,
        "active_irae": {"organ": "thyroid", "grade": 2},
    }
    jsonschema.validate(profile, SCHEMA)


def test_missing_required_fails():
    profile = {"prior_lines": 2}  # missing patient_id_hash
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(profile, SCHEMA)


def test_invalid_grade_fails():
    profile = {
        "patient_id_hash": "abc",
        "active_irae": {"organ": "thyroid", "grade": 9},
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(profile, SCHEMA)
