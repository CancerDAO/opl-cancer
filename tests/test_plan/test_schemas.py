"""Test Plan / Task / WaveAssignment schemas."""
import pytest
from pydantic import ValidationError

from opl_cancer.plan.schemas import Plan, Task, WaveAssignment


def test_minimum_plan_with_one_task() -> None:
    t = Task(
        id="t_001", expert="bert",
        task_package="molecular_ngs_interpretation",
        sub_goal="Identify actionable variants",
        dependencies=[],
    )
    plan = Plan(
        run_id="run_test", patient_code="anon_001",
        goal="Find actionable variants",
        waves=[WaveAssignment(wave_number=1, task_ids=["t_001"])],
        tasks=[t],
    )
    assert plan.tasks[0].expert == "bert"
    assert plan.waves[0].wave_number == 1


def test_task_with_dependency_must_reference_existing_task() -> None:
    with pytest.raises(ValidationError):
        Plan(
            run_id="r", patient_code="p", goal="g",
            waves=[WaveAssignment(wave_number=1, task_ids=["a"])],
            tasks=[
                Task(id="a", expert="rosa", task_package="x", sub_goal="g",
                     dependencies=["NONEXISTENT"]),
            ],
        )


def test_waves_must_be_sequential_no_gaps() -> None:
    with pytest.raises(ValidationError):
        Plan(
            run_id="r", patient_code="p", goal="g",
            waves=[
                WaveAssignment(wave_number=1, task_ids=["t1"]),
                WaveAssignment(wave_number=3, task_ids=["t2"]),  # gap
            ],
            tasks=[
                Task(id="t1", expert="rosa", task_package="x", sub_goal="g", dependencies=[]),
                Task(id="t2", expert="bert", task_package="y", sub_goal="g", dependencies=[]),
            ],
        )


def test_expert_name_lowercase_constraint() -> None:
    """All 18 expert names are lowercase first names (spec §2.2.X)."""
    with pytest.raises(ValidationError):
        Task(id="x", expert="Bert", task_package="x", sub_goal="g", dependencies=[])
