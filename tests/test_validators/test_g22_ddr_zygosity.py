"""Test G22 DDR-zygosity gate (v1.3.1 EVAL panel Patient #9 E3)."""
from opl_cancer.validators.gates.g22_ddr_zygosity import G22DDRZygosityGate
from opl_cancer.validators.mechanical_gates import GateStatus


def test_g22_skip_non_ddr_claim() -> None:
    """Claim unrelated to DDR / HRR / PARPi → SKIP."""
    gate = G22DDRZygosityGate()
    claim = {"claim": "EGFR L858R sensitises to osimertinib", "evidence": []}
    r = gate.check(claim)
    assert r.status == GateStatus.SKIP


def test_g22_block_parpi_claim_missing_zygosity() -> None:
    """PARPi claim with no ddr_gene/ddr_zygosity → BLOCK."""
    gate = G22DDRZygosityGate()
    claim = {
        "claim": "Patient HRR-positive; olaparib indicated.",
        "evidence": [{"type": "pmid", "id": "31157963", "quote": "PROfound trial"}],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert "ddr_gene" in r.message
    assert "ddr_zygosity" in r.message


def test_g22_pass_brca2_biallelic_with_full_evidence() -> None:
    """Properly annotated BRCA2-biallelic claim → PASS."""
    gate = G22DDRZygosityGate()
    claim = {
        "claim": "BRCA2 biallelic loss supports olaparib per PROfound subgroup A.",
        "evidence": [
            {
                "type": "pmid",
                "id": "32343890",
                "quote": "PROfound subgroup A: HR 0.69 [95% CI 0.55-0.86]",
                "ddr_gene": "BRCA2",
                "ddr_zygosity": "biallelic",
                "trial_subgroup": "PROfound subgroup A: BRCA1/2 biallelic OS HR 0.69",
                "pmid": "32343890",
            }
        ],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g22_block_atm_monoallelic_missing_trial_subgroup() -> None:
    """ATM monoallelic claim without trial_subgroup → BLOCK."""
    gate = G22DDRZygosityGate()
    claim = {
        "claim": "ATM mutation → olaparib indicated.",
        "evidence": [
            {
                "type": "pmid",
                "id": "32343890",
                "ddr_gene": "ATM",
                "ddr_zygosity": "monoallelic",
                # trial_subgroup intentionally missing
                "pmid": "32343890",
            }
        ],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True
    assert "trial_subgroup missing" in r.message


def test_g22_block_invalid_zygosity_token() -> None:
    """ddr_zygosity outside the allowed set → BLOCK."""
    gate = G22DDRZygosityGate()
    claim = {
        "claim": "BRCA2 mutated → PARPi.",
        "evidence": [
            {
                "type": "pmid",
                "id": "32343890",
                "ddr_gene": "BRCA2",
                "ddr_zygosity": "heterozygous",  # not in allowed set
                "trial_subgroup": "PROfound A",
                "pmid": "32343890",
            }
        ],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


def test_g22_fires_on_brca_reversion_without_parpi_token() -> None:
    """Standalone BRCA2 mention → also DDR-relevant (zygosity required)."""
    gate = G22DDRZygosityGate()
    claim = {
        "claim": "BRCA2 reversion mutation detected.",
        "evidence": [],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.FAIL
    assert r.block is True


def test_g22_lineage_carveout_pediatric_all_atm_het_no_parpi() -> None:
    """v1.3.2 — pediatric ALL ATM het without PARPi mention → SKIP (lineage carve-out)."""
    gate = G22DDRZygosityGate()
    claim = {
        "cancer_type": "pediatric ALL R/R KMT2A-r",
        "claim": "Germline ATM heterozygous variant identified; counsel family.",
        "evidence": [],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.SKIP
    assert "lineage-context carve-out" in r.message
    assert r.evidence["cancer_context_detected"] in ("pediatric_all", "pediatric all")


def test_g22_lineage_carveout_npc_atm_het_no_parpi() -> None:
    """v1.3.2 — NPC ATM het without PARPi mention → SKIP (lineage carve-out)."""
    gate = G22DDRZygosityGate()
    claim = {
        "cancer_type": "nasopharyngeal carcinoma",
        "claim": "ATM monoallelic variant on germline panel; surveillance recommended.",
        "evidence": [],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.SKIP
    assert "lineage-context carve-out" in r.message


def test_g22_no_carveout_when_therapy_token_present_in_pediatric_all() -> None:
    """v1.3.2 — pediatric ALL + olaparib mention → still FAIL (therapy claim wins)."""
    gate = G22DDRZygosityGate()
    claim = {
        "cancer_type": "pediatric ALL",
        "claim": "Consider olaparib given ATM mutation.",
        "evidence": [{"type": "pmid", "id": "12345"}],
    }
    r = gate.check(claim)
    # Therapy token present overrides the lineage carve-out → must FAIL on
    # missing zygosity declaration.
    assert r.status == GateStatus.FAIL
    assert r.block is True


def test_g22_pass_nsclc_brca2_biallelic_olaparib_with_full_evidence() -> None:
    """v1.3.2 — NSCLC BRCA2 biallelic + olaparib + proper subgroup → PASS."""
    gate = G22DDRZygosityGate()
    claim = {
        "cancer_type": "NSCLC",
        "claim": "BRCA2 biallelic + olaparib per HUDSON-LUNG subgroup.",
        "evidence": [
            {
                "type": "pmid",
                "id": "34567890",
                "ddr_gene": "BRCA2",
                "ddr_zygosity": "biallelic",
                "trial_subgroup": "HUDSON-LUNG BRCA2-biallelic NSCLC arm",
                "pmid": "34567890",
            }
        ],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g22_pass_prostate_brca2_olaparib_profound_subgroup_a() -> None:
    """v1.3.2 — prostate BRCA2 + olaparib + PROfound subgroup A → PASS."""
    gate = G22DDRZygosityGate()
    claim = {
        "cancer_type": "mCRPC",
        "claim": "BRCA2 biallelic prostate → olaparib per PROfound subgroup A.",
        "evidence": [
            {
                "type": "pmid",
                "id": "32343890",
                "ddr_gene": "BRCA2",
                "ddr_zygosity": "biallelic",
                "trial_subgroup": "PROfound subgroup A: BRCA1/2 biallelic OS HR 0.69 [0.55-0.86]",
                "pmid": "32343890",
            }
        ],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS


def test_g22_evidence_dict_under_ddr_key_also_accepted() -> None:
    """Nested ddr block on the evidence entry is honoured."""
    gate = G22DDRZygosityGate()
    claim = {
        "claim": "olaparib activity in BRCA1 biallelic mCRPC per PROpel.",
        "evidence": [
            {
                "type": "pmid",
                "id": "35179323",
                "ddr": {
                    "ddr_gene": "BRCA1",
                    "ddr_zygosity": "biallelic",
                    "trial_subgroup": "PROpel HRR+ subgroup",
                    "pmid": "35179323",
                },
            }
        ],
    }
    r = gate.check(claim)
    assert r.status == GateStatus.PASS
