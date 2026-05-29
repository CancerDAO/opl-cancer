"""Gate families — v2.5 compositional foundation (RFC 0001 §2.5).

Six families bind concrete gates to method primitives by capability rather
than by hand-wired registries.

v2.5 ships:
- ABC + 6 concrete family classes
- ProvenanceFamily fully migrated (G1 / G2 / G30 inherit + register)
- Registry YAML tagging every existing G1-G33 with its family
- Remaining 5 families stub bind_gates → [] for M1 to expand

Backward compat: G1/G2/G30 keep their existing public API; the family_id
class attribute is a pure addition.
"""
from __future__ import annotations

from abc import ABC
from pathlib import Path
from typing import Any

import yaml

from .mechanical_gates import Gate


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_REGISTRY_YAML = Path(__file__).resolve().parent / "gates_registry.yaml"


# ─── ABC ──────────────────────────────────────────────────────────────────


class GateFamily(ABC):
    """A gate family groups concrete Gate classes by validation capability.

    family_id MUST be one of the six closed-set IDs (see RFC 0001 §2.5):
        provenance / statistical-validity / temporal-recency
        / scope-isolation / safety-disclosure / reproducibility
    """

    family_id: str = ""
    description: str = ""

    def applies_to(self, method: dict[str, Any], claim: dict[str, Any]) -> bool:
        """True if this family should bind any gates for (method, claim).

        Default rule: method declares this family in its applicable_gate_families.
        Subclasses may add claim-level predicates.
        """
        fams = method.get("applicable_gate_families", []) or []
        return self.family_id in fams

    def bind_gates(
        self, method: dict[str, Any], claim: dict[str, Any]
    ) -> list[type[Gate]]:
        """Return the list of concrete Gate CLASSES this family binds.

        v2.5 default = []. Subclasses override.
        Note: returns classes, not instances; callers instantiate with their
        own integrator handles (PubMed, PaperQA, …) — preserves existing API.
        """
        return []

    def migrated_gate_classes(self) -> list[type[Gate]]:
        """Concrete gate classes that already declare family_id == this family.

        v2.5: only ProvenanceFamily returns a populated list (G1/G2/G30).
        """
        from .gates import (  # local import to avoid cycle at module init
            G1PMIDExistenceGate,
            G2PMIDQuoteMatchGate,
            G30ClaimPMIDAnchoredGate,
        )

        candidates: list[type[Gate]] = [
            G1PMIDExistenceGate,
            G2PMIDQuoteMatchGate,
            G30ClaimPMIDAnchoredGate,
        ]
        return [c for c in candidates if getattr(c, "family_id", None) == self.family_id]


# ─── concrete families ────────────────────────────────────────────────────


class ProvenanceFamily(GateFamily):
    """Every claim has an evidence anchor (PMID / NCT / KG node / SHA)."""

    family_id = "provenance"
    description = (
        "Every claim must carry a verifiable evidence anchor — PMID existence, "
        "quote-retrieval match, or run_id SHA — before publication."
    )

    def bind_gates(
        self, method: dict[str, Any], claim: dict[str, Any]
    ) -> list[type[Gate]]:
        if not self.applies_to(method, claim):
            return []
        # v2.5 always binds the 3 migrated gates when the family applies.
        return list(self.migrated_gate_classes())


class StatisticalValidityFamily(GateFamily):
    """Every inference declares assumptions + test + MCC. M1 migration."""

    family_id = "statistical-validity"
    description = (
        "Every statistical inference declares its assumptions, test choice, "
        "and multiple-comparison correction strategy."
    )


class TemporalRecencyFamily(GateFamily):
    """Guideline / drug / trial citation ≤ 18 months stale. M1 migration."""

    family_id = "temporal-recency"
    description = (
        "Guideline / drug / trial citations must be ≤ 18 months stale or "
        "explicitly flagged as historical reference."
    )


class ScopeIsolationFamily(GateFamily):
    """Three-tier (established / exploratory / speculative) non-leakage. M1."""

    family_id = "scope-isolation"
    description = (
        "Speculative, exploratory, and established claims are kept in "
        "non-leaking three-tier scopes per ADR-0021."
    )


class SafetyDisclosureFamily(GateFamily):
    """L3/L4 high-stakes claim emits a risk-card. M1 migration."""

    family_id = "safety-disclosure"
    description = (
        "Level-3 / Level-4 claims emit explicit risk-disclosure cards before "
        "patient delivery; never silent execution."
    )


class ReproducibilityFamily(GateFamily):
    """Any analysis bit-exact rerun. M1 migration."""

    family_id = "reproducibility"
    description = (
        "Every analysis can be bit-exact rerun from declared inputs + code "
        "hash + dataset hash."
    )


class ReasoningQualityFamily(GateFamily):
    """v2.7.1 ADR-0026 (P1) — clinical-reasoning quality of the synthesised output.

    Distinct from the six structural families: these gates check that the
    *recommendation reasoning* is coherent — a headline regimen is not gated on
    an unknown biomarker (G39), a recommended drug is reconciled with the
    patient's comorbidities (G40), standard-of-care completeness is recorded
    (G41), evidence tiers are not conflated (G42), and skepticism is applied
    symmetrically (G43). They operate on structured fields the claim producer
    emits (schemas/claim.v2.schema.json), never on hardcoded clinical judgment.
    """

    family_id = "reasoning-quality"
    description = (
        "The synthesised recommendation's reasoning is coherent: no headline "
        "gated on an unknown biomarker, drug×comorbidity reconciled, SoC "
        "completeness recorded, evidence tiers not conflated, skepticism symmetric."
    )

    def bind_gates(
        self, method: dict[str, Any], claim: dict[str, Any]
    ) -> list[type[Gate]]:
        if not self.applies_to(method, claim):
            return []
        return list(self.migrated_gate_classes())

    def migrated_gate_classes(self) -> list[type[Gate]]:
        from .gates import (  # local import to avoid cycle at module init
            G39BiomarkerContingencyGate,
            G40DrugComorbiditySafetyGate,
            G41SoCCompletenessGate,
            G42TierDisciplineGate,
            G43EpistemicSymmetryGate,
        )

        candidates: list[type[Gate]] = [
            G39BiomarkerContingencyGate,
            G40DrugComorbiditySafetyGate,
            G41SoCCompletenessGate,
            G42TierDisciplineGate,
            G43EpistemicSymmetryGate,
        ]
        return [c for c in candidates if getattr(c, "family_id", None) == self.family_id]


# ─── registry helpers ─────────────────────────────────────────────────────


_FAMILY_SINGLETONS: dict[str, GateFamily] = {
    "provenance": ProvenanceFamily(),
    "statistical-validity": StatisticalValidityFamily(),
    "temporal-recency": TemporalRecencyFamily(),
    "scope-isolation": ScopeIsolationFamily(),
    "safety-disclosure": SafetyDisclosureFamily(),
    "reproducibility": ReproducibilityFamily(),
    "reasoning-quality": ReasoningQualityFamily(),  # v2.7.1 ADR-0026 (P1)
}


def all_families() -> list[GateFamily]:
    """Return one instance of each gate family (six structural + reasoning-quality)."""
    return list(_FAMILY_SINGLETONS.values())


def families_by_id() -> dict[str, GateFamily]:
    """Return the family registry keyed by family_id."""
    return dict(_FAMILY_SINGLETONS)


def load_gates_registry() -> dict[str, dict[str, Any]]:
    """Load gates_registry.yaml — every existing G1-G33 mapped to its family."""
    with _REGISTRY_YAML.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    out: dict[str, dict[str, Any]] = {}
    for gid, entry in (data.get("gates") or {}).items():
        out[gid] = dict(entry or {})
    return out


__all__ = [
    "GateFamily",
    "ProvenanceFamily",
    "StatisticalValidityFamily",
    "TemporalRecencyFamily",
    "ScopeIsolationFamily",
    "SafetyDisclosureFamily",
    "ReproducibilityFamily",
    "ReasoningQualityFamily",
    "all_families",
    "families_by_id",
    "load_gates_registry",
]
