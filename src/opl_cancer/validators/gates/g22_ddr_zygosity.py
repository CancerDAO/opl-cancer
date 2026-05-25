"""G22: DDR / HRR claim must declare zygosity and cite the matching trial subgroup.

Spec §7 G22 / §6.5 F7 (new v1.3.1).

Failure mode F7 — PARPi / HRD-axis claim that conflates biallelic vs
monoallelic DDR loss. The published evidence is sharply zygosity-dependent:

  * BRCA1 / BRCA2 biallelic loss → PROfound, PROpel, MAGNITUDE positive
    subgroups (HR for OS / rPFS clearly < 1.0).
  * ATM monoallelic loss → PROfound subgroup G NEGATIVE (HR > 1.0 in some
    splits; underpowered in others).
  * CHEK2 / FANCL / PALB2 / RAD51C / RAD51D — zygosity-stratified evidence
    is sparse; PARPi claim depends on which biomarker definition was used.

A claim that recommends or discusses PARPi sensitivity, HRD-axis activity,
or platinum-cross-resistance MUST emit, for each DDR gene under discussion:

  * ``ddr_gene``       — gene symbol (HUGO; uppercased).
  * ``ddr_zygosity``   — one of: biallelic | monoallelic | unknown | not_applicable.
  * ``trial_subgroup`` — at least one trial subgroup reference + outcome
    direction (e.g. PROfound BRCA1/2-biallelic OS HR 0.69; PROfound ATM
    monoallelic OS HR ~1.04 ns).
  * ``pmid``           — PMID for the subgroup the claim cites.

If ANY of these fields is absent on a DDR-related claim, G22 BLOCKs. The gate
emits an actionable hint listing the canonical zygosity-by-trial pairings so
the LLM can rewrite without guesswork.

Code introduced for v1.3.1 EVAL panel feedback (Patient #9 E3 — DDR claim
collapsed BRCA2 biallelic and ATM monoallelic into a single "HRR-positive"
label).
"""
from __future__ import annotations

import re
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


# HUGO symbols of DDR / HRR pathway members whose PARPi / HRD-axis claims are
# zygosity-dependent in published trial evidence.
DDR_GENES: frozenset[str] = frozenset(
    {
        "BRCA1", "BRCA2", "ATM", "CHEK1", "CHEK2", "PALB2", "RAD51", "RAD51B",
        "RAD51C", "RAD51D", "RAD52", "RAD54L", "BARD1", "BRIP1", "FANCA",
        "FANCC", "FANCD2", "FANCE", "FANCF", "FANCG", "FANCI", "FANCL",
        "FANCM", "MRE11A", "MRE11", "NBN", "MUS81", "EME1", "BLM", "WRN",
        "RECQL4", "RECQL5", "XRCC2", "XRCC3", "DNA2", "POLD1", "POLE",
    }
)

# Tokens that indicate the claim is invoking PARPi / HRD-axis / DDR territory.
_DDR_TRIGGER_TOKENS = (
    "parpi", "parp inhibitor", "olaparib", "rucaparib", "niraparib", "talazoparib",
    "veliparib", "pamiparib", "fluzoparib", "senaparib",
    "hrd", "hrr", "hrd score", "hrd-positive", "hrr-positive",
    "platinum-sensitivity", "platinum sensitivity",
    "ddr", "ddr loss", "ddr deficiency",
    "synthetic lethality",
    "profound", "propel", "magnitude", "talapro", "polo trial",
    "bracelet", "study-08",
)

_ALLOWED_ZYGOSITY = {"biallelic", "monoallelic", "unknown", "not_applicable"}


# Disease / lineage contexts where a DDR-gene incidental finding does NOT
# imply the claim is about PARPi sensitivity / HRD axis. v1.3.2 carve-out
# (round-2 EVAL Patients #16 pediatric ALL ATM het + #20 NPC ATM het):
# the prior over-trigger logic FAIL'd whenever a DDR gene was mentioned, even
# in haematological / lymphoma / NPC / thyroid contexts where no PARPi
# discussion was on the table.
_NON_DDR_LINEAGE_CONTEXTS: frozenset[str] = frozenset(
    {
        # Pediatric haem
        "pediatric_all", "pediatric all", "儿童 all", "儿童急淋",
        "pediatric_aml", "pediatric aml", "儿童 aml",
        # Adult haem (PARPi not currently SOC class)
        "aml", "all", "急性髓系白血病", "急性淋巴细胞白血病",
        "lymphoma", "non-hodgkin", "hodgkin", "dlbcl", "follicular lymphoma",
        "cll", "mcl", "mantle cell", "multiple myeloma", "mds",
        # Head & neck / NPC
        "npc", "nasopharyngeal", "nasopharyngeal carcinoma", "鼻咽癌",
        # Endocrine
        "thyroid", "thyroid cancer", "甲状腺",
        # Pediatric brain (DIPG / pHGG)
        "dipg", "diffuse intrinsic pontine glioma", "pediatric glioma",
        "pediatric brain", "儿童脑瘤", "儿童 dipg",
    }
)

# Drug / class tokens that DO indicate the claim is about PARPi / DDR-axis
# *therapy*. If a DDR gene appears but NONE of these tokens are present AND
# the cancer-context is in _NON_DDR_LINEAGE_CONTEXTS, G22 SKIPs rather than
# FAILing — the gene mention is incidental, not a therapy claim.
_DDR_THERAPY_TOKENS: frozenset[str] = frozenset(
    {
        # PARP inhibitors
        "olaparib", "niraparib", "rucaparib", "talazoparib",
        "veliparib", "pamiparib", "fluzoparib", "senaparib",
        "parpi", "parp inhibitor", "parp-inhibitor",
        # ATR / WEE1 inhibitors
        "atr inhibitor", "atri", "ceralasertib", "berzosertib",
        "wee1 inhibitor", "adavosertib",
        # Platinum (DDR-axis cross-resistance)
        "platinum", "carboplatin", "cisplatin", "oxaliplatin",
        # DDR-axis trial / context
        "profound", "propel", "magnitude", "talapro", "polo trial",
        "olympia", "bracelet", "study-08", "hudson", "mediola-lung",
        "solo1", "solo2", "solo-1", "solo-2",
    }
)


def _detect_cancer_context(claim: dict[str, Any]) -> str | None:
    """Return the lineage-context token if any from _NON_DDR_LINEAGE_CONTEXTS hits
    the claim text. Used for the v1.3.2 over-trigger carve-out.
    """
    text_fields = [
        claim.get("cancer_type", ""),
        claim.get("diagnosis", ""),
        claim.get("claim", ""),
        claim.get("delivery_text", ""),
        claim.get("delivery_markdown", ""),
        claim.get("pi_prose", ""),
        claim.get("summary", ""),
        claim.get("rationale", ""),
    ]
    profile = claim.get("profile") or {}
    if isinstance(profile, dict):
        diag = profile.get("diagnosis") or {}
        if isinstance(diag, dict):
            text_fields.extend(
                [diag.get("histology", ""), diag.get("primary_site", "")]
            )
    haystack_lower = " \n ".join(str(f) for f in text_fields if f).lower()
    # Sort by length descending so more-specific contexts (e.g. "pediatric all")
    # match before generic ("all"). Avoids the carve-out resolving to the bare
    # "all" token when the disease is actually "pediatric ALL".
    for ctx in sorted(_NON_DDR_LINEAGE_CONTEXTS, key=len, reverse=True):
        if ctx in haystack_lower:
            return ctx
    return None


def _claim_has_ddr_therapy_token(claim: dict[str, Any]) -> bool:
    """Return True iff the claim mentions a PARPi / ATR-i / platinum / DDR-axis
    therapy token (or canonical DDR trial). When True, G22 must FAIL on a
    missing zygosity declaration even in haematological context.
    """
    text_fields = [
        claim.get("claim", ""),
        claim.get("delivery_text", ""),
        claim.get("delivery_markdown", ""),
        claim.get("pi_prose", ""),
        claim.get("summary", ""),
        claim.get("rationale", ""),
    ]
    for ev in claim.get("evidence", []) or []:
        if isinstance(ev, dict):
            for k in ("quote", "summary", "ref", "result_text"):
                v = ev.get(k)
                if v:
                    text_fields.append(str(v))
    haystack_lower = " \n ".join(str(f) for f in text_fields if f).lower()
    return any(tok in haystack_lower for tok in _DDR_THERAPY_TOKENS)


def _claim_is_ddr_relevant(claim: dict[str, Any]) -> bool:
    """Return True iff this claim invokes DDR / HRR / PARPi territory.

    Heuristic — match any of:
      * any evidence entry mentions a DDR gene symbol (uppercased) in `quote`
        or `summary` or `ref`
      * any text field contains a DDR trigger token (case-insensitive)
    """
    text_fields = [
        claim.get("claim", ""),
        claim.get("delivery_text", ""),
        claim.get("delivery_markdown", ""),
        claim.get("pi_prose", ""),
        claim.get("summary", ""),
        claim.get("rationale", ""),
    ]
    for ev in claim.get("evidence", []) or []:
        if isinstance(ev, dict):
            for k in ("quote", "summary", "ref", "result_text"):
                v = ev.get(k)
                if v:
                    text_fields.append(str(v))
    haystack = " \n ".join(str(f) for f in text_fields if f)
    haystack_lower = haystack.lower()
    for tok in _DDR_TRIGGER_TOKENS:
        if tok in haystack_lower:
            return True
    # Also fire if any DDR gene symbol appears as a standalone token in the
    # claim text — guards against "BRCA2 reversion" without explicit PARPi token.
    for g in DDR_GENES:
        if re.search(rf"\b{re.escape(g)}\b", haystack):
            return True
    return False


class G22DDRZygosityGate(Gate):
    name = "G22_ddr_zygosity"
    description = (
        "DDR / HRR / PARPi claims must declare ddr_gene + ddr_zygosity + "
        "trial_subgroup + pmid; zygosity ∈ {biallelic, monoallelic, unknown, "
        "not_applicable}."
    )
    failure_mode_code = "F7"

    def check(self, claim: dict[str, Any]) -> GateResult:
        if not _claim_is_ddr_relevant(claim):
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message="claim does not invoke DDR / HRR / PARPi territory",
            )

        # v1.3.2 lineage-context carve-out (Patient #16 pediatric ALL ATM het,
        # #20 NPC ATM het). If the claim mentions a DDR gene but (a) does NOT
        # mention any PARPi / ATR-i / platinum / DDR-trial therapy token AND
        # (b) the cancer context is in the haem / NPC / pediatric-brain
        # lineage list — the gene mention is incidental, not a therapy claim.
        # G22 SKIPs with a disease-context-awareness hint rather than FAILing.
        cancer_ctx = _detect_cancer_context(claim)
        has_therapy_token = _claim_has_ddr_therapy_token(claim)
        if cancer_ctx and not has_therapy_token:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message=(
                    f"G22 SKIP (lineage-context carve-out) — DDR gene mentioned in "
                    f"{cancer_ctx!r} context without any PARPi / ATR-i / platinum / "
                    "DDR-trial therapy token. Incidental gene mention, not a therapy "
                    "claim. Disease-context awareness: prostate → PROfound/PROpel; "
                    "ovarian → SOLO1/SOLO2/PRIMA; breast → OlympiA; pancreatic → "
                    "POLO; NSCLC → HUDSON/MEDIOLA-LUNG. Pediatric ALL / AML / NPC / "
                    "DIPG do NOT currently have PARPi-as-SOC trial subgroups."
                ),
                evidence={
                    "cancer_context_detected": cancer_ctx,
                    "ddr_therapy_token_present": False,
                    "carve_out_version": "v1.3.2",
                },
            )

        evidence = claim.get("evidence", []) or []
        ddr_entries: list[dict[str, Any]] = []
        for ev in evidence:
            if not isinstance(ev, dict):
                continue
            # Accept either a top-level ddr_gene/ddr_zygosity on the evidence
            # entry, OR a nested ddr block.
            ddr_block = ev.get("ddr") if isinstance(ev.get("ddr"), dict) else ev
            if ddr_block.get("ddr_gene") or ddr_block.get("ddr_zygosity"):
                ddr_entries.append(ddr_block)

        if not ddr_entries:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    "DDR / HRR / PARPi claim missing ddr_gene + ddr_zygosity on any "
                    "evidence entry. Rewrite: every DDR-axis claim must declare "
                    "{ddr_gene, ddr_zygosity ∈ {biallelic, monoallelic, unknown, "
                    "not_applicable}, trial_subgroup, pmid}. Canonical pairings "
                    "(disease-context-aware — DO NOT default to PROfound for "
                    "non-prostate): prostate → PROfound subgroup A (BRCA1/2 biallelic "
                    "OS HR 0.69); ovarian → SOLO1 (BRCA1/2 PFS HR 0.30) + SOLO2 + "
                    "PRIMA (HRD+); breast → OlympiA (BRCA1/2 germline iDFS HR 0.58); "
                    "pancreatic → POLO (BRCA1/2 germline PFS HR 0.53); NSCLC → "
                    "HUDSON / MEDIOLA-LUNG. ATM monoallelic → PROfound subgroup-G "
                    "OS HR ≈1.04 ns. CHEK2 / PALB2 / RAD51C / RAD51D — "
                    "zygosity-stratified evidence sparse."
                ),
                evidence={
                    "required_keys": ["ddr_gene", "ddr_zygosity", "trial_subgroup", "pmid"],
                    "allowed_zygosity": sorted(_ALLOWED_ZYGOSITY),
                    "ddr_genes_recognised": sorted(DDR_GENES),
                },
            )

        violations: list[str] = []
        for i, entry in enumerate(ddr_entries):
            gene = (entry.get("ddr_gene") or "").upper().strip()
            zyg = (entry.get("ddr_zygosity") or "").lower().strip()
            sub = entry.get("trial_subgroup")
            pmid = entry.get("pmid")

            if not gene:
                violations.append(f"entry[{i}]: ddr_gene missing")
            elif gene not in DDR_GENES:
                violations.append(
                    f"entry[{i}]: ddr_gene={gene!r} not in recognised DDR panel "
                    f"(add to G22.DDR_GENES if intentional)"
                )
            if not zyg:
                violations.append(f"entry[{i}]: ddr_zygosity missing")
            elif zyg not in _ALLOWED_ZYGOSITY:
                violations.append(
                    f"entry[{i}]: ddr_zygosity={zyg!r} ∉ {sorted(_ALLOWED_ZYGOSITY)}"
                )
            if not sub:
                violations.append(
                    f"entry[{i}]: trial_subgroup missing — must reference the specific "
                    f"trial subgroup whose evidence supports this claim (e.g. "
                    f"'PROfound subgroup A: BRCA1/2-biallelic OS HR 0.69')"
                )
            if not pmid:
                violations.append(f"entry[{i}]: pmid missing for the cited trial subgroup")

        if violations:
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message="G22 DDR-zygosity violations — " + "; ".join(violations),
                evidence={
                    "ddr_entries_checked": len(ddr_entries),
                    "violations": violations,
                    "allowed_zygosity": sorted(_ALLOWED_ZYGOSITY),
                },
            )

        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=(
                f"G22 OK — {len(ddr_entries)} DDR evidence entry/entries declare "
                "ddr_gene + ddr_zygosity + trial_subgroup + pmid"
            ),
            evidence={"ddr_entries_checked": len(ddr_entries)},
        )
