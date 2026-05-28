"""MethodPrimitive dataclass — v2.5 compositional foundation (RFC 0001 §2.2).

A method primitive is a typed, reusable analytical operation that the planner
can compose into a DAG. v2.5 ships 8 seed primitives across 4 domains; M4
expands to ~50.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MethodPrimitive:
    """One reusable analytical method that the TaskComposer may stitch into a DAG.

    Fields:
        id: stable kebab-or-snake identifier, must be unique across the registry.
        domain: one of {statistical, bioinformatics, clinical-research, pharmacology}.
        display_name: human-readable name.
        inputs: dict describing the required inputs (free-schema; JSON-Schema in M4).
        outputs: dict describing the produced outputs.
        assumptions: list of natural-language assumptions the method relies on.
        applicable_gate_families: subset of the 6 gate families that bind to this method.
        implementation_ref: dotted path to the implementation (e.g.
            "opl_cancer.integrators.lifelines_km:cox_fit") or "TBD" when not yet wired.
        literature_refs: PMIDs / DOIs / NCT IDs anchoring the method.
        fast_path_task_package: optional name of an existing prompts/tasks/<x>.md
            that implements this primitive (so the planner can recycle the v2.4
            recipe before composing from scratch).
    """

    id: str
    domain: str
    display_name: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    assumptions: list[str]
    applicable_gate_families: list[str]
    implementation_ref: str
    literature_refs: list[str]
    fast_path_task_package: str | None = None

    # cached source path for provenance — set by the loader, not required
    source_path: str | None = field(default=None, compare=False)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MethodPrimitive):
            return NotImplemented
        return (
            self.id == other.id
            and self.domain == other.domain
            and self.display_name == other.display_name
            and self.inputs == other.inputs
            and self.outputs == other.outputs
            and self.assumptions == other.assumptions
            and self.applicable_gate_families == other.applicable_gate_families
            and self.implementation_ref == other.implementation_ref
            and self.literature_refs == other.literature_refs
            and self.fast_path_task_package == other.fast_path_task_package
        )

    def __hash__(self) -> int:  # pragma: no cover - convenience
        return hash(self.id)


VALID_DOMAINS = {"statistical", "bioinformatics", "clinical-research", "pharmacology"}
VALID_GATE_FAMILIES = {
    "provenance",
    "statistical-validity",
    "temporal-recency",
    "scope-isolation",
    "safety-disclosure",
    "reproducibility",
}
