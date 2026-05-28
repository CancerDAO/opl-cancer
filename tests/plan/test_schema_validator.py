"""v2.1 P0-#5: schema_validator hard-fails on profile↔trigger field mismatch."""
from __future__ import annotations

import pytest

from opl_cancer.plan.schema_validator import (
    ProfileTriggerMismatch,
    validate_profile,
)


def test_valid_profile_no_error():
    validate_profile({
        "patient_id_hash": "x",
        "prior_lines": 0,
        "concurrent_meds": [],
    })


def test_unknown_trigger_field_raises():
    """A key that isn't in schema OR in TRIGGER_KEYS must hard-fail in
    strict mode."""
    with pytest.raises(ProfileTriggerMismatch) as exc:
        validate_profile(
            {
                "patient_id_hash": "x",
                "prior_lines": 0,
                "concurrent_meds": [],
                "active_irrae": True,  # typo for active_irae
            },
            strict_triggers=True,
        )
    assert "active_irrae" in str(exc.value)


def test_unknown_field_allowed_when_strict_false():
    """Without strict_triggers, unknown keys pass (additionalProperties=true)."""
    validate_profile(
        {
            "patient_id_hash": "x",
            "active_irrae": True,
        },
        strict_triggers=False,
    )
