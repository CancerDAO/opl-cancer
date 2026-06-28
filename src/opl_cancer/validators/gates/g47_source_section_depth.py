"""G47: source_section_depth — read the paper, not the abstract.

B2 / ADR-0030 (research-team iteration). 'The appendix is where the bodies are
buried; the limitations paragraph is the most honest one.' For an N=1 patient
past standard-of-care, the subgroup forest plot in a trial supplement and the
trial's exclusion criteria decide whether a cited trial APPLIES to them. OPL is
PMID-anchored but abstract-deep: PubMed parses title+abstract only and the
PaperQA2 corpus was never populated, so G2 quote-match is satisfiable by an
abstract substring — an 'established' headline HR can pass every gate while the
patient's exact subgroup showed no benefit or was excluded.

G47 caps any `established` claim that leans on PMIDs but has no evidence entry
read at full-text / supplementary / subgroup-table depth. Machine-verifiable via
the ``source_section`` enum on each evidence entry; BLOCKS (cap to exploratory).
Pure-guideline established claims (no PMID evidence) are exempt — they don't rest
on a paper whose appendix could void them.

Evidence entry field (schemas/claim.v2.schema.json):
    evidence[].source_section: abstract | full_text | supplementary |
        subgroup_table | limitations
"""
from __future__ import annotations

from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

_DEEP = {"full_text", "supplementary", "subgroup_table", "limitations"}


class G47SourceSectionDepthGate(Gate):
    """An established claim leaning on PMIDs must read at least one deep, not abstract-only."""

    name = "G47_source_section_depth"
    description = (
        "An 'established' patient-facing claim that leans on PMIDs must carry at "
        "least one evidence entry read at full-text/supplement/subgroup depth — "
        "not abstract-only. Otherwise a headline HR can be sold as established "
        "while the patient's exact subgroup showed no benefit or was excluded "
        "(the appendix is where the bodies are buried). BLOCKS (cap to "
        "exploratory). Pure-guideline established claims are exempt."
    )
    failure_mode_code = "B2-ABSTRACT-DEEP-ESTABLISHED"
    family_id = "statistical-validity"

    def check(self, claim: dict[str, Any]) -> GateResult:
        if claim.get("claim_layer") != "established":
            return GateResult(
                gate=self.name, status=GateStatus.SKIP,
                message="G47 SKIP — claim is not 'established'.",
            )
        evidence = claim.get("evidence")
        pmid_entries = [
            e for e in evidence if isinstance(e, dict) and e.get("type") == "pmid"
        ] if isinstance(evidence, list) else []
        if not pmid_entries:
            return GateResult(
                gate=self.name, status=GateStatus.SKIP,
                message=(
                    "G47 SKIP — established claim rests on no PMID evidence "
                    "(e.g. guideline-only); no paper whose appendix could void it."
                ),
            )
        deep = [e for e in pmid_entries if e.get("source_section") in _DEEP]
        if not deep:
            sections = sorted({str(e.get("source_section")) for e in pmid_entries})
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=True,
                message=(
                    "G47 FAIL — established claim "
                    f"{claim.get('claim_id', '?')!r} rests only on abstract-level "
                    f"PMID evidence (source_section seen: {sections}). Read the full "
                    "text / supplement / subgroup table to confirm it applies to "
                    "THIS patient's subgroup, or cap the claim to 'exploratory'. An "
                    "abstract HR is not evidence the patient is in the benefiting "
                    "subgroup."
                ),
                evidence={"claim_id": claim.get("claim_id"), "sections_seen": sections},
            )
        return GateResult(
            gate=self.name, status=GateStatus.PASS,
            message=(
                f"G47 OK — established claim read deep: {len(deep)}/{len(pmid_entries)} "
                "PMID source(s) at full-text/supplement/subgroup depth."
            ),
            evidence={"deep_sources": len(deep), "pmid_sources": len(pmid_entries)},
        )
