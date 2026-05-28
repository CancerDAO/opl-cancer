"""CPIC pharmacogenomics wrapper. v2.2 ADR-0022 — F_BIO family (optional skill).

source_skill: BioTender-max/awesome-bio-agent-skills/bio-pharmacogenomics
original_license: CC0-1.0

CPIC (Clinical Pharmacogenetics Implementation Consortium, cpicpgx.org) is
the canonical pharmacogene→drug→action guideline authority. Each guideline
carries a CPIC level (A / B / C / D) indicating evidence strength + action
imperative.

v2.2 ships a curated table covering the oncology-adjacent gene-drug pairs:
* DPYD × fluoropyrimidines (5-FU, capecitabine)
* TPMT / NUDT15 × thiopurines (mercaptopurine, azathioprine)
* UGT1A1 × irinotecan
* CYP2D6 × tamoxifen / codeine
* CYP2C19 × clopidogrel / voriconazole

Live cpicpgx.org API lookup is a v2.3 stretch goal. v2.2 is reference-only —
Mary remains advisory; dose-recommendation engine is out of scope.

Key format: ``gene:<GENE>:drug:<DRUG>:phenotype:<PHENOTYPE>``
"""
from __future__ import annotations

from typing import Any

from .base import Integrator, IntegratorError
from .cache import IntegratorCache


# Curated CPIC table. Keys: (gene, drug, phenotype) → action record.
CPIC_TABLE: dict[str, dict[str, dict[str, dict[str, Any]]]] = {
    "DPYD": {
        "fluorouracil": {
            "Poor Metabolizer": {
                "recommendation": "Avoid use of fluorouracil. If no alternative, reduce starting dose by 50% with TDM.",
                "recommendation_level": "A",
                "cpic_guideline": "Amstutz 2018 (PMID: 29152729)",
            },
            "Intermediate Metabolizer": {
                "recommendation": "Reduce starting dose by 25-50%; titrate based on toxicity / labs.",
                "recommendation_level": "A",
                "cpic_guideline": "Amstutz 2018 (PMID: 29152729)",
            },
            "Normal Metabolizer": {
                "recommendation": "Standard dose.",
                "recommendation_level": "A",
                "cpic_guideline": "Amstutz 2018 (PMID: 29152729)",
            },
        },
        "capecitabine": {
            "Poor Metabolizer": {
                "recommendation": "Avoid capecitabine. Severe / fatal toxicity risk.",
                "recommendation_level": "A",
                "cpic_guideline": "Amstutz 2018 (PMID: 29152729)",
            },
            "Intermediate Metabolizer": {
                "recommendation": "Reduce starting dose by 25-50%; close monitoring.",
                "recommendation_level": "A",
                "cpic_guideline": "Amstutz 2018 (PMID: 29152729)",
            },
        },
    },
    "TPMT": {
        "mercaptopurine": {
            "Poor Metabolizer": {
                "recommendation": "Reduce dose by ~10-fold; or switch to a non-thiopurine agent.",
                "recommendation_level": "A",
                "cpic_guideline": "Relling 2019 (PMID: 30447069)",
            },
            "Intermediate Metabolizer": {
                "recommendation": "Reduce starting dose by 30-70%; monitor counts closely.",
                "recommendation_level": "A",
                "cpic_guideline": "Relling 2019 (PMID: 30447069)",
            },
        },
        "azathioprine": {
            "Poor Metabolizer": {
                "recommendation": "Reduce dose substantially or switch to alternative.",
                "recommendation_level": "A",
                "cpic_guideline": "Relling 2019 (PMID: 30447069)",
            },
        },
    },
    "NUDT15": {
        "mercaptopurine": {
            "Poor Metabolizer": {
                "recommendation": "Reduce starting dose by ~80%; or switch agent. Common in East-Asian / Hispanic populations.",
                "recommendation_level": "A",
                "cpic_guideline": "Relling 2019 (PMID: 30447069)",
            },
        },
    },
    "UGT1A1": {
        "irinotecan": {
            "Poor Metabolizer": {
                "recommendation": "Reduce starting dose by ~25-30% (UGT1A1*28/*28 homozygous). Monitor for severe neutropenia + diarrhoea.",
                "recommendation_level": "B",
                "cpic_guideline": "FDA label + emerging CPIC draft",
            },
        },
    },
    "CYP2D6": {
        "tamoxifen": {
            "Poor Metabolizer": {
                "recommendation": "Consider aromatase inhibitor alternative in postmenopausal women if clinically appropriate.",
                "recommendation_level": "A",
                "cpic_guideline": "Goetz 2018 (PMID: 29385237)",
            },
            "Intermediate Metabolizer": {
                "recommendation": "Avoid moderate-to-strong CYP2D6 inhibitors; consider AI alternative.",
                "recommendation_level": "A",
                "cpic_guideline": "Goetz 2018 (PMID: 29385237)",
            },
        },
        "codeine": {
            "Poor Metabolizer": {
                "recommendation": "Avoid codeine (no analgesia). Use alternative analgesic.",
                "recommendation_level": "A",
                "cpic_guideline": "Crews 2021 (PMID: 33387367)",
            },
            "Ultrarapid Metabolizer": {
                "recommendation": "Avoid codeine (toxic morphine accumulation). Use alternative analgesic.",
                "recommendation_level": "A",
                "cpic_guideline": "Crews 2021 (PMID: 33387367)",
            },
        },
    },
    "CYP2C19": {
        "clopidogrel": {
            "Poor Metabolizer": {
                "recommendation": "Use alternative antiplatelet (prasugrel / ticagrelor) if not contraindicated.",
                "recommendation_level": "A",
                "cpic_guideline": "Lee 2022 (PMID: 35034351)",
            },
        },
        "voriconazole": {
            "Poor Metabolizer": {
                "recommendation": "Use alternative azole (isavuconazole) OR TDM-guided dosing.",
                "recommendation_level": "A",
                "cpic_guideline": "Moriyama 2017 (PMID: 27981572)",
            },
        },
    },
}


def lookup_cpic(*, gene: str, drug: str, phenotype: str) -> dict[str, Any]:
    """Lookup a CPIC recommendation. Raises ValueError if unknown."""
    if gene not in CPIC_TABLE:
        raise ValueError(
            f"CPIC: unknown gene {gene!r}. Known: {sorted(CPIC_TABLE)}"
        )
    drug_map = CPIC_TABLE[gene]
    if drug not in drug_map:
        raise ValueError(
            f"CPIC: gene {gene!r} has no entry for drug {drug!r}. "
            f"Known drugs for {gene}: {sorted(drug_map)}"
        )
    phenotype_map = drug_map[drug]
    if phenotype not in phenotype_map:
        # Tolerate phenotype absent — return informational instead of raise
        return {
            "gene": gene,
            "drug": drug,
            "phenotype": phenotype,
            "recommendation": f"No CPIC entry for {gene} {phenotype!r} × {drug}. Consult cpicpgx.org.",
            "recommendation_level": "C",
            "cpic_guideline": "no_entry",
        }
    rec = phenotype_map[phenotype]
    return {"gene": gene, "drug": drug, "phenotype": phenotype, **rec}


class CpicIntegrator(Integrator):
    """CPIC reference table wrapper. v2.2 is offline-table; cpicpgx.org
    API binding is a v2.3 stretch goal.

    family = ``F_BIO``. TTL 90 days (CPIC guidelines refresh quarterly).
    """

    family = "F_BIO"
    ttl_seconds = 90 * 24 * 3600

    async def fetch(self, key: str) -> dict[str, Any]:
        parts = key.split(":")
        if len(parts) != 6 or parts[0] != "gene" or parts[2] != "drug" or parts[4] != "phenotype":
            raise IntegratorError(
                "CPIC: expected gene:<GENE>:drug:<DRUG>:phenotype:<PHENOTYPE>, "
                f"got {key!r}"
            )
        gene, drug, phenotype = parts[1], parts[3], parts[5]
        try:
            rec = lookup_cpic(gene=gene, drug=drug, phenotype=phenotype)
        except ValueError as e:
            raise IntegratorError(str(e)) from e
        rec["engine"] = "cpic-table-v2.2"
        return rec


__all__ = ["CpicIntegrator", "CPIC_TABLE", "lookup_cpic"]
