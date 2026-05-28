"""Tests for v2.5 RoleTaxonomy — RFC 0001 §2.1."""
from __future__ import annotations

import pytest

from opl_cancer.experts.role_taxonomy import (
    FAST_PATH_ROLES,
    ExpertRole,
    RoleCompositionNotYetImplemented,
    compose_role,
    load_taxonomy,
)


# 20 expected fast-path persona names (the existing v2.4 roster)
EXPECTED_FAST_PATH_NAMES = {
    "rosa", "bert", "vince", "rick", "heddy",
    "mary", "aviv", "tyler", "iain", "ted",
    "riad", "jen", "kieren", "mark", "hong",
    "frances", "dennis", "steve", "maya", "julius",
}


def test_fast_path_roles_covers_all_twenty() -> None:
    assert set(FAST_PATH_ROLES.keys()) == EXPECTED_FAST_PATH_NAMES


def test_each_fast_path_entry_is_expertrole() -> None:
    for name, role in FAST_PATH_ROLES.items():
        assert isinstance(role, ExpertRole), f"{name} is not ExpertRole"
        assert role.discipline
        assert role.subspecialty
        assert role.method_specialty
        assert role.bridging_role


def test_compose_role_matches_fast_path_for_known_name() -> None:
    """v2.5 stub behaviour: compose_role on a known persona name returns the
    cached FAST_PATH entry."""
    rosa = compose_role(constraints={"persona_name": "rosa"})
    assert rosa == FAST_PATH_ROLES["rosa"]
    assert rosa.discipline == "pathology"


def test_compose_role_matches_fast_path_for_discipline_subspecialty() -> None:
    """If constraints match exactly one FAST_PATH role on (discipline,subspecialty),
    return it."""
    role = compose_role(
        constraints={
            "discipline": "pathology",
            "subspecialty": "surgical_pathology",
        }
    )
    # Rosa is surgical_pathology
    assert role == FAST_PATH_ROLES["rosa"]


def test_compose_role_raises_for_novel_constraint() -> None:
    """v2.5 stub: any constraint not matching a FAST_PATH role raises
    RoleCompositionNotYetImplemented — real LLM composition is M2."""
    with pytest.raises(RoleCompositionNotYetImplemented):
        compose_role(
            constraints={
                "discipline": "neuro-oncology",
                "subspecialty": "pediatric_DIPG",
                "method_specialty": "bayesian_adaptive_trials",
                "bridging_role": "NMPA_regulatory",
            }
        )


def test_taxonomy_yaml_loads_valid_enumerations() -> None:
    tax = load_taxonomy()
    # 4 axes
    assert {"discipline", "subspecialty", "method_specialty", "bridging_role"} <= set(tax.keys())
    # Seeded with ≥ 8 enum values per axis (RFC says ~30; we ship ≥ 8 minimum)
    for axis in ("discipline", "subspecialty", "method_specialty", "bridging_role"):
        assert len(tax[axis]) >= 8, f"{axis} only {len(tax[axis])} values"


def test_each_fast_path_role_uses_known_taxonomy_values() -> None:
    """Every FAST_PATH_ROLES tuple value must be present in the taxonomy."""
    tax = load_taxonomy()
    for name, role in FAST_PATH_ROLES.items():
        assert role.discipline in tax["discipline"], f"{name} discipline {role.discipline}"
        # subspecialty / method_specialty / bridging_role may be more open-set
        # in v2.5, so we relax to membership-in-union-of-axes:
        all_terms = set().union(
            tax["subspecialty"], tax["method_specialty"], tax["bridging_role"]
        )
        for term in (role.subspecialty, role.method_specialty, role.bridging_role):
            assert term in all_terms, f"{name} term {term!r} not in taxonomy"


def test_expertrole_is_frozen_and_hashable() -> None:
    r = ExpertRole(
        discipline="x", subspecialty="y", method_specialty="z", bridging_role="w"
    )
    # frozen dataclass — assignment should fail
    with pytest.raises((AttributeError, TypeError)):
        r.discipline = "other"  # type: ignore[misc]
    # hashable (used in lookup tables)
    {r}


def test_persona_template_file_exists() -> None:
    """The parametric persona prompt template is shipped under prompts/experts/."""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent.parent
    template = repo_root / "prompts" / "experts" / "_template.md"
    assert template.is_file(), f"missing {template}"
    text = template.read_text(encoding="utf-8")
    # Jinja-style placeholders for all four axes
    for placeholder in ("{{discipline}}", "{{subspecialty}}", "{{method_specialty}}", "{{bridging_role}}"):
        assert placeholder in text, f"placeholder {placeholder} missing from _template.md"
