"""G56: value_source_binding — a cited efficacy number must live in its cited paper.

Closes the hole the jessie run-opl-20260629 third-party review found: G1 verifies a
PMID *exists*, G36 verifies the PMID is *on-topic* (an entity appears in it), but
NEITHER verifies that the **numeric value** a claim attributes to that PMID is
actually IN the paper. So a real headline number (e.g. ``mPFS 8.3 vs 4.3 months,
HR 0.49``) could be lifted from trial A and hung on real-but-wrong PMID B — and
sail through G1+G36 (B exists, an entity matches). The reviewers called this
*伪精度* (false precision), and judged it more dangerous than a hollow report
because it makes a careful reader trust a mis-bound number *because* it carries a
citation.

G56 is the binding check: for every claim that (a) cites ≥1 PMID and (b) asserts a
**headline efficacy number** (hazard ratio / median months / response %), each such
number must appear in at least ONE cited PMID's live record (title + abstract,
NCBI middle-dot normalised). A number cited against PMIDs but absent from all of
them is an UNSUPPORTED value → FAIL + BLOCK, surfacing the orphan number(s) so the
author rebinds it to the correct paper or removes it.

Scope guards (avoid false positives):
  * Only efficacy-context numbers are extracted (HR / "A vs B" / "N months|月" /
    "ORR N%") — patient-molecular values (VAF 36.1%, copy-number 4.57) are NOT
    efficacy-shaped and are skipped, and they anchor via ``[[src:]]`` (G35), not PMIDs.
  * Abstract-only fetch: a headline efficacy endpoint is in the abstract ~always;
    the rare full-text-only number that false-flags is cheaply fixed by tagging its
    evidence ``type`` non-pmid or adding the right PMID. Conservative by design.

Async, like G1/G36: call ``check_async``; the sync ``check`` raises. Wired into
``delivery_gate_runner._run_citation_gates`` so it fires on the same pmid-claims.
"""
from __future__ import annotations

import re
from typing import Any

from opl_cancer.integrators.base import IntegratorError

from ..mechanical_gates import Gate, GateResult, GateStatus

# A "headline efficacy number": HR/OR, an "A vs B" pair, a median in months, an
# ORR/DCR/response percentage. Captures the numeric token(s) in group(s).
_NUM = r"\d+(?:[.·]\d+)?"  # allow NCBI middle-dot 0·49
_EFFICACY_PATTERNS = [
    re.compile(rf"\bHR\s*[:=]?\s*({_NUM})", re.I),
    re.compile(rf"风险比\s*[:=]?\s*({_NUM})"),
    re.compile(rf"\b(?:OR|RR)\s*[:=]?\s*({_NUM})\b"),
    re.compile(rf"({_NUM})\s*vs\.?\s*({_NUM})"),                       # 8.3 vs 4.3
    re.compile(rf"({_NUM})\s*(?:个?月|months?|mo)\b", re.I),            # 10.5 months / 10.5 月
    re.compile(rf"(?:ORR|DCR|响应率|缓解率|应答率)\s*[:=]?\s*({_NUM})\s*%", re.I),
    re.compile(rf"({_NUM})\s*%\s*(?:ORR|DCR|response|缓解|应答)", re.I),
]
# Exclude numbers that are clearly patient-molecular (so VAF/copy-number/variant
# coords never get treated as efficacy claims even if they brush an efficacy regex).
_MOLECULAR_CONTEXT = re.compile(r"VAF|拷贝|copy[\s-]?number|\bCN\b|p\.[A-Z]|c\.\d|外显子|exon", re.I)


def _norm(text: str) -> str:
    return (text or "").replace("·", ".").lower()


def _extract_efficacy_numbers(claim_text: str) -> list[str]:
    """Return the set of efficacy-shaped numeric tokens asserted in the claim."""
    nums: set[str] = set()
    for pat in _EFFICACY_PATTERNS:
        for m in pat.finditer(claim_text):
            # skip a match sitting inside a molecular-value context window
            lo, hi = max(0, m.start() - 12), min(len(claim_text), m.end() + 4)
            if _MOLECULAR_CONTEXT.search(claim_text[lo:hi]):
                continue
            for g in m.groups():
                if g:
                    nums.add(g.replace("·", "."))
    # ignore trivial integers (0, 1, 2-digit counts like "12 patients") that are
    # not effect sizes — keep decimals + percentages-worthy values; a bare small
    # int rarely identifies a paper. Keep anything with a decimal point, or ≥3.
    return [n for n in nums if ("." in n or len(n.split(".")[0]) >= 2)]


def _number_present(num: str, haystack: str) -> bool:
    # token-boundaried so "8.3" doesn't match "18.3" or "8.30"... allow trailing
    # zeros being absent: match the exact decimal token with non-digit boundaries.
    return bool(re.search(rf"(?<!\d){re.escape(num)}(?!\d)", haystack))


class G56ValueSourceBindingGate(Gate):
    """Every cited headline efficacy number must appear in one of its cited PMIDs."""

    name = "G56_value_source_binding"
    description = (
        "A headline efficacy number (HR / median months / response %) attributed "
        "to PMID(s) must appear verbatim in at least one of those PMIDs' live "
        "records (title+abstract). An orphan number — cited but in none of its "
        "papers — is a mis-bound citation (伪精度) and BLOCKS delivery."
    )
    failure_mode_code = "AP-VALUE-MISBIND"
    family_id = "provenance"

    def __init__(self, pubmed: Any) -> None:
        self.pubmed = pubmed

    def check(self, claim: dict[str, Any]) -> GateResult:  # pragma: no cover
        raise NotImplementedError("G56 is async; call check_async()")

    async def check_async(self, claim: dict[str, Any]) -> GateResult:
        pmids = [
            str(e["id"]) for e in claim.get("evidence", [])
            if e.get("type") == "pmid" and e.get("id")
        ]
        if not pmids:
            return GateResult(gate=self.name, status=GateStatus.SKIP,
                              message="G56 SKIP — no PMID evidence.")
        # Read the claim's prose from whichever key the pipeline used. The
        # canonical wave-1 claim record carries it as ``text`` (wave1_runner
        # _collect_claims); the brief-extracted fallback uses ``claim_text``.
        # Reading only ``claim_text`` (the original bug) made G56 SKIP every
        # real claim → the 伪精度 gate was a silent no-op on the live path.
        claim_prose = next(
            (str(claim[k]) for k in ("claim_text", "text", "statement", "title")
             if claim.get(k)),
            "",
        )
        numbers = _extract_efficacy_numbers(claim_prose)
        if not numbers:
            return GateResult(gate=self.name, status=GateStatus.SKIP,
                              message="G56 SKIP — claim asserts no headline efficacy number.")
        combined = ""
        fetched: list[str] = []
        for p in pmids:
            try:
                rec = await self.pubmed.cached_fetch(f"PMID:{p}")
            except IntegratorError:
                continue
            fetched.append(p)
            combined += " " + _norm(" ".join(str(rec.get(k, "")) for k in ("title", "abstract", "journal")))
        if not fetched:
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=True,
                message=(f"G56 FAIL — none of the cited PMIDs {pmids} could be fetched; "
                         f"cannot confirm the value(s) {numbers} are bound to a real source."),
                evidence={"pmids": pmids, "numbers": numbers},
            )
        orphan = [n for n in numbers if not _number_present(n, combined)]
        if orphan:
            return GateResult(
                gate=self.name, status=GateStatus.FAIL, block=True,
                message=(
                    f"G56 FAIL — efficacy value(s) {orphan} are cited against "
                    f"PMID(s) {fetched} but appear in NONE of their records "
                    "(title/abstract). Either the number is hung on the wrong paper "
                    "(伪精度 / mis-binding) or it is full-text-only — rebind to the "
                    "paper that actually reports it, or move it off the PMID."
                ),
                evidence={"orphan_numbers": orphan, "cited_pmids": fetched,
                          "all_numbers": numbers, "claim_id": claim.get("claim_id")},
            )
        return GateResult(
            gate=self.name, status=GateStatus.PASS,
            message=(f"G56 OK — all {len(numbers)} efficacy value(s) bound to a "
                     f"cited PMID record ({len(fetched)} PMIDs checked)."),
            evidence={"numbers": numbers, "cited_pmids": fetched},
        )
