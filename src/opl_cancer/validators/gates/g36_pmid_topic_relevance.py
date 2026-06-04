"""G36: pmid_topic_relevance — a cited PMID must actually be about the claim.

v2.7.0 (ADR-0026 / session 0d1017d4 fix). The driving incident: 4 of 23 cited
PMIDs were *real, existing* papers about entirely unrelated topics —
PMID 32366523 (knee osteoarthritis), 33398099 (kefir microbiome), 21156285
(glioma), 27638862 (macrophage inflammasome) — cited on a KRAS-G12C / MSS-CRC
case. G1 (PMID existence) PASSED all four because the papers exist. The defect:
**existence ≠ relevance.** A digit-transposed or hallucinated-but-coincidentally-
real PMID slips straight through an existence check.

G36 closes that hole. For each cited PMID it fetches the live PubMed record
(title + abstract + journal — never the model's memory, per
no-silent-fallback policy) and verifies that at least one of the claim's
**structured topical entities** (gene / variant / drug / cancer-type, supplied
by the claim producer as ``claim['entities']``) actually appears in the fetched
record. Zero overlap ⇒ the PMID is off-topic ⇒ FAIL + BLOCK, surfacing the real
paper title so the reviewer sees *what the wrong PMID actually points to*.

Entities come from upstream (the expert/claim layer), never a hardcoded disease
keyword list (no-hardcoded-keyword-list policy). If a claim carries
PMIDs but no upstream-supplied ``entities``, the gate FAILs CLOSED rather than
silently skipping: it first attempts a *narrow, deterministic* fallback
derivation of structured tokens (HGNC-style gene symbols, protein-change /
exon variant notations, and an explicit drug/cancer-type list the claim may
carry in ``drugs`` / ``cancer_type``) from the claim's own text and fields. The
fallback is a last-resort relevance anchor, NOT a substitute for upstream
entity attachment. If neither upstream entities nor any derivable token exist,
the citation cannot be relevance-judged and is BLOCKED — an unjudgeable
citation must not ship (SKILL.md core principle #4 / no-silent-fallback policy).

Network-unreachable ⇒ the per-PMID check errors *closed* (treated as a relevance
failure for that PMID), never silently skipped — a medical agent must not ship a
citation it could not verify (SKILL.md core principle #4 / no-silent-fallback policy).

Async, like G1/G2: call ``check_async``; the sync ``check`` raises.
"""
from __future__ import annotations

import re
from typing import Any

from opl_cancer.integrators.base import IntegratorError

from ..mechanical_gates import Gate, GateResult, GateStatus

# An entity "appears" if its token sequence is found (case-insensitive) in the
# fetched text. Short tokens (≤2 chars) are ignored to avoid false matches.
_WORD_RE = re.compile(r"[A-Za-z0-9一-鿿][A-Za-z0-9一-鿿\-]*")


def _normalise(text: str) -> str:
    return " ".join(_WORD_RE.findall((text or "").lower()))


def _entity_present(entity: str, haystack: str) -> bool:
    ent = entity.strip().lower()
    if len(ent) <= 2:
        return False
    # token-boundary contains (so "ATM" matches "atm" but not "treatment")
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(ent)}(?![a-z0-9])", haystack))


# ── deterministic fallback entity derivation ────────────────────────────────
# Last-resort only: when upstream did not attach claim['entities']. We extract
# *structured* tokens that are safe to require in the cited paper's record:
#   * gene-symbol shaped tokens (e.g. KRAS, BRCA2, ATM, TP53, PIK3CA) — 2-7 chars
#     uppercase letters with optional trailing digits, the HGNC shape.
#   * protein-change / variant notations (e.g. G12C, V600E, exon 20).
# We deliberately do NOT keyword-match disease names here (that would be the
# hardcoded list no-hardcoded-keyword-list policy forbids); explicit
# drug / cancer-type strings, if present, come from the claim's own structured
# fields, not an inferred dictionary.
_GENE_SHAPE_RE = re.compile(r"\b([A-Z]{2,6}[0-9]{0,3}[A-Z]?)\b")
_VARIANT_SHAPE_RE = re.compile(
    r"\b([A-Z]\d{1,4}[A-Z*](?:fs)?|exon\s*\d{1,2}|c\.\d+[ACGT]>[ACGT]|p\.[A-Z]\d+[A-Z])\b",
    re.IGNORECASE,
)
# Tokens that *look* like gene symbols but are common English/clinical words —
# excluded so they cannot become spurious relevance anchors.
_GENE_SHAPE_STOPWORDS = frozenset({
    "DNA", "RNA", "MRNA", "FDA", "EMA", "NCCN", "ESMO", "ASCO", "NGS", "PCR",
    "CT", "MRI", "PET", "ECOG", "OS", "PFS", "ORR", "DCR", "AE", "SAE", "QOL",
    "PMID", "DOI", "ID", "USA", "UK", "EU", "WHO", "IRB", "PI", "MTB",
})


def _derive_entities_fallback(claim: dict[str, Any]) -> list[str]:
    """Best-effort structured tokens when upstream attached no ``entities``.

    Returns a de-duplicated list of gene-symbol / variant tokens plus any
    explicit drug / cancer-type strings carried on the claim's own fields.
    Empty list ⇒ nothing relevance-judgeable could be derived (caller blocks).
    """
    derived: list[str] = []
    seen: set[str] = set()

    def _add(tok: str) -> None:
        t = tok.strip()
        if t and t.lower() not in seen:
            seen.add(t.lower())
            derived.append(t)

    # explicit structured fields the claim producer may carry
    for field in ("drugs", "drug", "cancer_type", "cancer", "biomarker", "biomarkers"):
        val = claim.get(field)
        if isinstance(val, str):
            _add(val)
        elif isinstance(val, (list, tuple)):
            for v in val:
                if isinstance(v, str):
                    _add(v)

    # gene / variant shapes parsed from the claim text
    text = " ".join(
        str(claim.get(k, ""))
        for k in ("claim_text", "text", "statement", "title")
    )
    for m in _GENE_SHAPE_RE.findall(text):
        if m.upper() not in _GENE_SHAPE_STOPWORDS:
            _add(m)
    for m in _VARIANT_SHAPE_RE.findall(text):
        _add(m if isinstance(m, str) else m[0])
    return derived


class G36PMIDTopicRelevanceGate(Gate):
    """A cited PMID's PubMed record must mention ≥1 of the claim's entities."""

    name = "G36_pmid_topic_relevance"
    description = (
        "Each cited PMID's live PubMed record (title+abstract+journal) must "
        "mention at least one of the claim's structured topical entities "
        "(gene/variant/drug/cancer-type). Catches real-but-wrong-paper PMIDs "
        "(the knee-OA / kefir / glioma / macrophage citations from session "
        "0d1017d4) that G1 existence-checks miss."
    )
    failure_mode_code = "A1b-WRONG-PAPER-PMID"
    family_id = "provenance"

    def __init__(self, pubmed: Any) -> None:
        # `pubmed` is any object exposing `async cached_fetch(key)` returning a
        # dict with title/abstract/journal (PubMedIntegrator, or a test double).
        self.pubmed = pubmed

    def check(self, claim: dict[str, Any]) -> GateResult:  # pragma: no cover
        raise NotImplementedError("G36 is async; call check_async()")

    async def check_async(self, claim: dict[str, Any]) -> GateResult:
        pmids = [
            str(e["id"]) for e in claim.get("evidence", [])
            if e.get("type") == "pmid" and e.get("id")
        ]
        if not pmids:
            return GateResult(
                gate=self.name, status=GateStatus.SKIP,
                message="G36 SKIP — no PMID evidence to check.",
            )
        entities = [str(x) for x in (claim.get("entities") or []) if str(x).strip()]
        entities_source = "upstream"
        if not entities:
            # No upstream entities. Try a narrow deterministic fallback before
            # giving up — but if nothing relevance-judgeable can be derived, the
            # citation is UNJUDGEABLE and must NOT ship (fail-closed, same as the
            # unfetchable-PMID branch below). Never a silent SKIP.
            entities = _derive_entities_fallback(claim)
            entities_source = "derived_fallback"
            if not entities:
                return GateResult(
                    gate=self.name, status=GateStatus.FAIL, block=True,
                    message=(
                        "G36 FAIL — claim carries PMIDs but no structured 'entities' "
                        "to judge relevance against, and none could be derived from "
                        "the claim text/fields. An unjudgeable citation cannot ship. "
                        "Upstream (expert/source_verification) must attach claim['entities']."
                    ),
                    evidence={"pmids": pmids, "entities_source": "none"},
                )

        off_topic: list[dict[str, Any]] = []
        verified: list[str] = []
        for pmid in pmids:
            try:
                rec = await self.pubmed.cached_fetch(f"PMID:{pmid}")
            except IntegratorError as exc:
                # fail-closed: an un-fetchable PMID is an unverifiable citation.
                off_topic.append({
                    "pmid": pmid, "reason": f"unverifiable (fetch error: {exc})",
                    "real_title": None, "matched_entities": [],
                })
                continue
            haystack = _normalise(
                " ".join(str(rec.get(k, "")) for k in ("title", "abstract", "journal"))
            )
            matched = [e for e in entities if _entity_present(e, haystack)]
            if matched:
                verified.append(pmid)
            else:
                off_topic.append({
                    "pmid": pmid,
                    "reason": "no claim entity appears in the PubMed record",
                    "real_title": str(rec.get("title", ""))[:200],
                    "real_journal": str(rec.get("journal", ""))[:120],
                    "matched_entities": [],
                })

        if off_topic:
            sample = "; ".join(
                f"PMID:{o['pmid']} → {o.get('real_title') or o['reason']!r}"
                for o in off_topic[:4]
            )
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"G36 FAIL — {len(off_topic)} cited PMID(s) are off-topic or "
                    f"unverifiable for entities {entities}. None of the claim's "
                    f"entities appear in their PubMed records. {sample}"
                ),
                evidence={
                    "off_topic": off_topic, "entities": entities,
                    "verified": verified, "entities_source": entities_source,
                },
            )
        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=f"G36 OK — all {len(verified)} PMID(s) topically match claim entities.",
            evidence={
                "verified": verified, "entities": entities,
                "entities_source": entities_source,
            },
        )
