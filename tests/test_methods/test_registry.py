"""Tests for v2.5 MethodRegistry — RFC 0001 §2.2."""
from __future__ import annotations

import pytest

from opl_cancer.methods import MethodPrimitive, MethodRegistry


SEED_IDS = {
    "cox_proportional_hazards",
    "kaplan_meier",
    "conformal_prediction",
    "deseq2_differential_expression",
    "gsea_enrichment",
    "recist_response_assessment",
    "acmg_germline_classification",
    "popPK_NONMEM_proxy",
}


def test_registry_loads_eight_seed_primitives() -> None:
    reg = MethodRegistry()
    reg.load_all()
    assert {p.id for p in reg.all()} >= SEED_IDS


def test_each_primitive_has_required_fields() -> None:
    reg = MethodRegistry()
    reg.load_all()
    for prim in reg.all():
        assert prim.id
        assert prim.domain in {"statistical", "bioinformatics", "clinical-research", "pharmacology"}
        assert prim.display_name
        assert isinstance(prim.inputs, dict)
        assert isinstance(prim.outputs, dict)
        assert isinstance(prim.assumptions, list)
        assert isinstance(prim.applicable_gate_families, list)
        # gate families come from the closed set of six (provenance / statistical-validity /
        # temporal-recency / scope-isolation / safety-disclosure / reproducibility)
        for fam in prim.applicable_gate_families:
            assert fam in {
                "provenance",
                "statistical-validity",
                "temporal-recency",
                "scope-isolation",
                "safety-disclosure",
                "reproducibility",
            }
        assert isinstance(prim.literature_refs, list)


def test_find_by_domain() -> None:
    reg = MethodRegistry()
    reg.load_all()
    stat = reg.find_by_domain("statistical")
    stat_ids = {p.id for p in stat}
    assert {"cox_proportional_hazards", "kaplan_meier", "conformal_prediction"} <= stat_ids

    bio = reg.find_by_domain("bioinformatics")
    bio_ids = {p.id for p in bio}
    assert {"deseq2_differential_expression", "gsea_enrichment"} <= bio_ids


def test_find_by_capability() -> None:
    """Capability is a free-form keyword search across id + display_name + assumptions."""
    reg = MethodRegistry()
    reg.load_all()
    hits = reg.find_by_capability("survival")
    hit_ids = {p.id for p in hits}
    # at least one of the survival methods should match
    assert {"cox_proportional_hazards", "kaplan_meier"} & hit_ids


def test_find_by_gate_family() -> None:
    reg = MethodRegistry()
    reg.load_all()
    prov_methods = reg.find_by_gate_family("provenance")
    # every method declares provenance as applicable (literature_refs)
    assert len(prov_methods) >= 1
    stat_val = reg.find_by_gate_family("statistical-validity")
    stat_val_ids = {p.id for p in stat_val}
    assert "cox_proportional_hazards" in stat_val_ids


def test_unknown_id_raises() -> None:
    reg = MethodRegistry()
    reg.load_all()
    with pytest.raises(KeyError):
        reg.get("not_a_real_method")


def test_acmg_primitive_cross_links_to_task_package() -> None:
    """v2.5 wires existing task packages as fast-path entries via the
    `fast_path_task_package` field (cross-links the ACMG primitive to the
    v2.2 `acmg_germline_classification.md` package)."""
    reg = MethodRegistry()
    reg.load_all()
    acmg = reg.get("acmg_germline_classification")
    assert acmg.fast_path_task_package == "acmg_germline_classification"


def test_primitive_dataclass_immutable_equality() -> None:
    a = MethodPrimitive(
        id="x",
        domain="statistical",
        display_name="X",
        inputs={},
        outputs={},
        assumptions=[],
        applicable_gate_families=["provenance"],
        implementation_ref="TBD",
        literature_refs=[],
    )
    b = MethodPrimitive(
        id="x",
        domain="statistical",
        display_name="X",
        inputs={},
        outputs={},
        assumptions=[],
        applicable_gate_families=["provenance"],
        implementation_ref="TBD",
        literature_refs=[],
    )
    assert a == b
