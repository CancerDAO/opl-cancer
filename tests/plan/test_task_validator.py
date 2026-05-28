"""v2.1 P0-#6: task_validator rejects unknown task_package at plan emit."""
from __future__ import annotations

import pytest

from opl_cancer.plan.task_validator import UnknownTaskPackage, validate_task_packages


def test_valid_task_passes():
    validate_task_packages(
        [
            {
                "task_id": "t1",
                "expert": "rosa",
                "task_package": "pathology_interpretation",
            }
        ]
    )


def test_typo_raises_with_suggestion():
    with pytest.raises(UnknownTaskPackage) as exc:
        validate_task_packages(
            [
                {
                    "task_id": "t1",
                    "expert": "rosa",
                    "task_package": "pathology_interpret",  # missing -ation
                }
            ]
        )
    msg = str(exc.value)
    assert "pathology_interpretation" in msg
    assert "did you mean" in msg.lower() or "Did you mean" in msg


def test_empty_task_list_no_error():
    validate_task_packages([])
