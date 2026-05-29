"""Tests for v2.5 GateFamily framework — RFC 0001 §2.5."""
from __future__ import annotations


from opl_cancer.validators import all_families, families_by_id
from opl_cancer.validators.gate_families import (
    GateFamily,
    ProvenanceFamily,
    ReproducibilityFamily,
    SafetyDisclosureFamily,
    ScopeIsolationFamily,
    StatisticalValidityFamily,
    TemporalRecencyFamily,
)
from opl_cancer.validators.gates import (
    G1PMIDExistenceGate,
    G2PMIDQuoteMatchGate,
    G30ClaimPMIDAnchoredGate,
)


EXPECTED_FAMILY_IDS = {
    "provenance",
    "statistical-validity",
    "temporal-recency",
    "scope-isolation",
    "safety-disclosure",
    "reproducibility",
    "reasoning-quality",  # v2.7.1 ADR-0026 (P1) — clinical-reasoning quality
}


# ─── gate families exist ───────────────────────────────────────────────────


def test_all_families_exist() -> None:
    fams = all_families()
    ids = {f.family_id for f in fams}
    assert ids == EXPECTED_FAMILY_IDS


def test_families_by_id_lookup() -> None:
    idx = families_by_id()
    assert isinstance(idx["provenance"], ProvenanceFamily)
    assert isinstance(idx["statistical-validity"], StatisticalValidityFamily)
    assert isinstance(idx["temporal-recency"], TemporalRecencyFamily)
    assert isinstance(idx["scope-isolation"], ScopeIsolationFamily)
    assert isinstance(idx["safety-disclosure"], SafetyDisclosureFamily)
    assert isinstance(idx["reproducibility"], ReproducibilityFamily)


def test_families_are_gatefamily_subclasses() -> None:
    for fam in all_families():
        assert isinstance(fam, GateFamily)


# ─── ProvenanceFamily migration ────────────────────────────────────────────


def test_g1_g2_g30_class_attrs_family_id_provenance() -> None:
    """v2.5 inheriting gates tag themselves with family_id='provenance'."""
    assert G1PMIDExistenceGate.family_id == "provenance"
    assert G2PMIDQuoteMatchGate.family_id == "provenance"
    assert G30ClaimPMIDAnchoredGate.family_id == "provenance"


def test_provenance_family_lists_migrated_gate_classes() -> None:
    prov = ProvenanceFamily()
    classes = prov.migrated_gate_classes()
    assert G1PMIDExistenceGate in classes
    assert G2PMIDQuoteMatchGate in classes
    assert G30ClaimPMIDAnchoredGate in classes


def test_provenance_family_bind_gates_for_citation_claim() -> None:
    """For a claim that carries PMID evidence, ProvenanceFamily binds all 3 gates."""
    prov = ProvenanceFamily()
    claim = {
        "id": "c1",
        "text": "Olaparib improves PFS in BRCA-mutant ovarian cancer.",
        "evidence": [
            {"type": "pmid", "id": "30068454", "quote": "olaparib improved PFS"},
        ],
        "manuscript_path": None,
    }
    method = {"id": "literature_synthesis", "applicable_gate_families": ["provenance"]}
    classes = prov.bind_gates(method, claim)
    # bind_gates returns a list of gate classes (not instances — instantiation
    # may require integrator handles the caller must supply)
    assert G1PMIDExistenceGate in classes
    assert G2PMIDQuoteMatchGate in classes
    assert G30ClaimPMIDAnchoredGate in classes


def test_provenance_family_applies_to_method_when_family_listed() -> None:
    prov = ProvenanceFamily()
    method_yes = {"id": "x", "applicable_gate_families": ["provenance", "reproducibility"]}
    method_no = {"id": "y", "applicable_gate_families": ["statistical-validity"]}
    claim = {"id": "c"}
    assert prov.applies_to(method_yes, claim) is True
    assert prov.applies_to(method_no, claim) is False


# ─── other families stubbed for M1 ─────────────────────────────────────────


def test_unmigrated_families_return_empty_classes() -> None:
    """M1 deferred: the 5 non-provenance families exist but don't bind concrete
    gates yet. They MUST return [] (not raise), so callers degrade gracefully."""
    for fam in [
        StatisticalValidityFamily(),
        TemporalRecencyFamily(),
        ScopeIsolationFamily(),
        SafetyDisclosureFamily(),
        ReproducibilityFamily(),
    ]:
        method = {"id": "x", "applicable_gate_families": [fam.family_id]}
        assert fam.bind_gates(method, {"id": "c"}) == []
        # but applies_to still works:
        assert fam.applies_to(method, {"id": "c"}) is True


# ─── gates_registry.yaml integrity ────────────────────────────────────────


def test_gates_registry_yaml_maps_all_33_gates() -> None:
    """Each G1-G33 has a family entry in gates_registry.yaml.

    Note: 35 files exist on disk because G27 also exports redact_text/scan_text
    helpers, but the registry covers 33 distinct gate IDs G1-G33."""
    from opl_cancer.validators.gate_families import load_gates_registry

    reg = load_gates_registry()
    gate_ids = set(reg.keys())
    # All 33 gates G1..G33 must be tagged
    for n in range(1, 34):
        assert f"G{n}" in gate_ids, f"G{n} missing from gates_registry.yaml"
    # Every tag must be a valid family ID
    for gid, entry in reg.items():
        fam = entry["family"]
        assert fam in EXPECTED_FAMILY_IDS, f"{gid} → unknown family {fam!r}"


def test_provenance_registry_entries_match_migrated_classes() -> None:
    """G1/G2/G30 entries in the registry have family=provenance."""
    from opl_cancer.validators.gate_families import load_gates_registry

    reg = load_gates_registry()
    assert reg["G1"]["family"] == "provenance"
    assert reg["G2"]["family"] == "provenance"
    assert reg["G30"]["family"] == "provenance"


def test_backward_compat_all_gates_still_register() -> None:
    """v2.4 backward-compat: all_gate_classes() still returns ≥ 33."""
    from opl_cancer.validators.mechanical_gates import all_gate_classes

    assert len(all_gate_classes()) >= 33


def test_g1_existing_api_unchanged() -> None:
    """G1 keeps its v2.4 public API (zero breakage)."""
    assert G1PMIDExistenceGate.name == "G1_pmid_existence"
    assert G1PMIDExistenceGate.failure_mode_code == "A1"
    # __init__ still takes a PubMedIntegrator arg
    import inspect

    sig = inspect.signature(G1PMIDExistenceGate.__init__)
    assert "pubmed" in sig.parameters
