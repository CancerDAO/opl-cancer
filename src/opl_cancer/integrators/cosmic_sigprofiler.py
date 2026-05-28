"""COSMIC SigProfilerAssignment wrapper. v2.2 ADR-0022 — F_BIO family.

source_skill: BioTender-max/awesome-bio-agent-skills/bio-somatic-signatures
original_license: CC0-1.0

Single-base substitution (SBS) signature extraction per COSMIC v3.x.
SigProfilerAssignment fits a sample's SBS96 mutation matrix to the COSMIC
reference signatures and returns per-signature weights.

Heavy dep — `SigProfilerAssignment` requires reference matrices on first
run. Lazy-import; live mode requires explicit install via the `[bio]`
extras group. Mock mode is the default for unit tests.

Key format: ``vcf:<vcf_path>`` (or ``maf:<maf_path>``).
"""
from __future__ import annotations

import importlib
from typing import Any

from .base import Integrator, IntegratorError
from .cache import IntegratorCache


# Curated SBS interpretation table — small but covers the clinically actionable
# signatures (MMR / HRD / smoking / UV / POLE / APOBEC / temozolomide-resistance
# / mutator-phenotype). Etiology strings are PMID-anchored in the task prompt.
SBS_INTERPRETATION: dict[str, dict[str, str]] = {
    "SBS1": {
        "etiology": "Spontaneous deamination of 5-methylcytosine (clock-like; age)",
        "actionability": "informational",
    },
    "SBS2": {
        "etiology": "APOBEC cytidine deaminase activity (C>T at TCW)",
        "actionability": "may suggest APOBEC-driven mutagenesis; CHK1/ATR-i interest",
    },
    "SBS3": {
        "etiology": "Defective homologous-recombination DNA-damage repair (BRCA1/2; HRD)",
        "actionability": "PARP-i sensitivity signal; pairs with HRD score",
    },
    "SBS4": {
        "etiology": "Tobacco smoking (C>A on bulky-adduct strand)",
        "actionability": "informational; ICI responsiveness signal in NSCLC",
    },
    "SBS5": {
        "etiology": "Clock-like (unknown etiology; ubiquitous low-level)",
        "actionability": "informational",
    },
    "SBS6": {
        "etiology": "Defective DNA mismatch-repair (MMR deficiency; MSI-H tumours)",
        "actionability": "MSI-H confirmation; ICI / pembrolizumab signal",
    },
    "SBS7a": {
        "etiology": "Ultraviolet light exposure (CC>TT at dipyrimidine)",
        "actionability": "informational; melanoma context",
    },
    "SBS7b": {
        "etiology": "Ultraviolet light exposure (alternative spectrum)",
        "actionability": "informational; melanoma context",
    },
    "SBS10a": {
        "etiology": "POLE-exonuclease-domain mutation (hyper-mutator)",
        "actionability": "ICI signal even when MSS; TMB often very high",
    },
    "SBS10b": {
        "etiology": "POLE-exonuclease-domain mutation (alternative spectrum)",
        "actionability": "ICI signal even when MSS",
    },
    "SBS11": {
        "etiology": "Temozolomide treatment (alkylating agent)",
        "actionability": "post-TMZ mutator; informs resistance interpretation in GBM",
    },
    "SBS13": {
        "etiology": "APOBEC cytidine deaminase activity (alternative spectrum)",
        "actionability": "APOBEC mutagenesis confirmation with SBS2",
    },
    "SBS15": {
        "etiology": "Defective mismatch-repair (alternative spectrum to SBS6)",
        "actionability": "MMR-deficiency confirmation",
    },
    "SBS18": {
        "etiology": "Reactive oxygen species / oxidative stress (C>A at GpCpG)",
        "actionability": "informational; neuroblastoma context",
    },
    "SBS44": {
        "etiology": "Defective mismatch-repair (alternative spectrum)",
        "actionability": "MMR-deficiency confirmation",
    },
}


def interpret_signature(sbs_id: str) -> dict[str, Any]:
    """Return etiology + actionability for an SBS id; falls back to unannotated."""
    if sbs_id in SBS_INTERPRETATION:
        return {"sbs_id": sbs_id, **SBS_INTERPRETATION[sbs_id]}
    return {
        "sbs_id": sbs_id,
        "etiology": f"Unannotated signature {sbs_id} (see COSMIC v3.x)",
        "actionability": "consult COSMIC + literature",
    }


def _dominant(signatures: dict[str, float]) -> str:
    if not signatures:
        return ""
    return max(signatures.items(), key=lambda kv: kv[1])[0]


class CosmicSigProfilerIntegrator(Integrator):
    """Wrapper around SigProfilerAssignment.

    family = ``F_BIO``. TTL 30 days.
    """

    family = "F_BIO"
    ttl_seconds = 30 * 24 * 3600

    def __init__(
        self,
        cache: IntegratorCache | None = None,
        *,
        mock_mode: bool = False,
        mock_signatures: dict[str, float] | None = None,
    ) -> None:
        super().__init__(cache=cache)
        self.mock_mode = mock_mode
        self.mock_signatures: dict[str, float] = dict(mock_signatures or {})

    async def fetch(self, key: str) -> dict[str, Any]:
        if ":" not in key:
            raise IntegratorError(f"SigProfiler: expected vcf:<path> or maf:<path>, got {key!r}")
        kind, path = key.split(":", 1)
        if kind not in ("vcf", "maf"):
            raise IntegratorError(
                f"SigProfiler: kind must be 'vcf' or 'maf', got {kind!r}"
            )

        if self.mock_mode:
            sigs = self.mock_signatures
            dom = _dominant(sigs)
            return {
                "signatures": dict(sigs),
                "dominant_signature": dom,
                "signature_sum": sum(sigs.values()),
                "interpretation": interpret_signature(dom),
                "engine": "sigprofiler-mock",
                "provenance": f"mock_mode=True; input={key}",
            }

        # Live mode — requires SigProfilerAssignment importable. Lazy-import
        # since the package downloads reference matrices on first run.
        try:
            spa = importlib.import_module("SigProfilerAssignment")
        except (ImportError, ModuleNotFoundError) as e:
            raise IntegratorError(
                "SigProfiler: SigProfilerAssignment not installed. "
                "Install via `pip install SigProfilerAssignment` (heavy dep — "
                "downloads ~1.5 GB reference). Or pass mock_mode=True for tests. "
                "No silent fallback (memory:feedback_no_offline_only)."
            ) from e
        # Also handle the monkeypatched None case
        if spa is None:
            raise IntegratorError(
                "SigProfiler: SigProfilerAssignment is registered as None "
                "(test monkeypatch?). Live mode requires the real package."
            )
        # Production wiring delegated to a subclass / compute container
        raise IntegratorError(
            "SigProfiler: live wiring requires NativeAnalysisRunner integration; "
            "override _run_live() in a compute-container subclass."
        )


__all__ = [
    "CosmicSigProfilerIntegrator",
    "SBS_INTERPRETATION",
    "interpret_signature",
]
