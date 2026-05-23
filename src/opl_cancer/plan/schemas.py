"""Plan / Task / WaveAssignment schemas. Spec §4 lifecycle."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


# 18 named experts from spec §2.2.X (lowercase first names)
KNOWN_EXPERTS = frozenset({
    "rosa", "bert", "vince", "rick", "heddy", "mary", "aviv", "tyler",
    "iain", "ted", "riad", "jen", "kieren", "mark", "hong", "frances",
    "dennis", "steve",
})


class Task(BaseModel):
    """Single sub-goal assigned to one expert. Spec §4."""

    id: str = Field(min_length=1)
    expert: str
    task_package: str
    sub_goal: str
    dependencies: list[str] = Field(default_factory=list)

    @field_validator("expert")
    @classmethod
    def _expert_lowercase_known(cls, v: str) -> str:
        if v != v.lower():
            raise ValueError(f"expert name must be lowercase, got {v!r}")
        if v not in KNOWN_EXPERTS:
            raise ValueError(f"unknown expert {v!r}; one of {sorted(KNOWN_EXPERTS)}")
        return v


class WaveAssignment(BaseModel):
    """Group of tasks to run in parallel within a wave. Spec §4."""

    wave_number: int = Field(ge=1)
    task_ids: list[str] = Field(min_length=1)


class Plan(BaseModel):
    """Sid-produced top-level plan. Spec §4."""

    run_id: str
    patient_code: str
    goal: str
    waves: list[WaveAssignment]
    tasks: list[Task]

    @model_validator(mode="after")
    def _check_consistency(self) -> "Plan":
        task_ids = {t.id for t in self.tasks}

        # Dependencies must reference existing tasks
        for t in self.tasks:
            for d in t.dependencies:
                if d not in task_ids:
                    raise ValueError(f"task {t.id} depends on unknown task {d}")

        # Wave numbers must be sequential 1..N with no gaps
        wave_nums = sorted(w.wave_number for w in self.waves)
        if wave_nums != list(range(1, len(wave_nums) + 1)):
            raise ValueError(f"waves must be sequential 1..N, got {wave_nums}")

        # All wave task_ids must reference existing tasks
        for w in self.waves:
            for tid in w.task_ids:
                if tid not in task_ids:
                    raise ValueError(f"wave {w.wave_number} references unknown task {tid}")

        return self
