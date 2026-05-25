"""G23: Recency band — WARN when a fast-moving topic cites a PMID > 18 months old.

Spec §7 G23 / §6.5 F8 (new v1.3.1).

Failure mode F8 — claim in a fast-moving subspecialty cites an old PMID and
implicitly understates how much the standard has moved. Examples (Patient
#9 E4): PSMA-RLT cohort evidence from 2021 cited as "current" in a 2026
discussion where SPLASH / ENZA-p / PSMAfore have all since reported;
AR-V7-based ARSI-resistance decisions cited from 2019 splice-variant data
when 2024-2025 reanalysis revised the prevalence and clinical correlation.

G23 is a WARN gate — it does NOT block render. Its purpose is to surface a
"consider recent updates" caveat into the patient brief whenever a claim's
PMID is older than the recency window AND the claim's topic falls inside the
fast-moving list. The patient sees the caveat; Reviewer can decide whether
to add a fresh PMID before render.

The fast-moving list is maintained here, not in a config file, so the gate
ships self-contained:

  * PSMA-RLT (Lu-177-PSMA-617 / actinium-225-PSMA): Pluvicto post-marketing
    + PSMAfore + SPLASH + ENZA-p + PSMAddition (3-9 months iteration).
  * Lu-177 more broadly (DOTATATE NETTER-2 + tandem TAT trials).
  * AR-V7 splice-variant ARSI-resistance: serial reanalysis post-2023.
  * CAR-T (BCMA / CD19 / GPRC5D / claudin-18.2): KarMMA + CARTITUDE +
    OPTIMUM + cilta-cel / ide-cel post-marketing each shift the line-of-
    therapy lattice quarterly.
  * BTK-degrader (NX-2127 / NX-5948 / BGB-16673): pivotal data 2024-2025.
  * KRAS-G12C: sotorasib / adagrasib resistance + combinations evolving;
    KRAS-G12D / G12V agents emerged 2025.
  * MET-amp (osimertinib resistance subgroup): savolitinib / tepotinib /
    capmatinib combination data 2024-2025.
  * BRCA-reversion: rapidly expanding ctDNA-detectable reversion landscape.
  * Bispecific T-cell engagers (BiTE / TCE in solid tumour): tarlatamab + ...
  * Antibody-drug conjugates (ADC): T-DXd post-DESTINY-Breast-06 +
    Dato-DXd + patritumab-DXd + ifinatamab-DXd.

Recency window default: 18 months.
"""
from __future__ import annotations

import datetime as _dt
import re
from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus


# Topics where the standard-of-care or pivotal-evidence base iterates faster
# than 18 months. Match is substring-based, case-insensitive.
FAST_MOVING_TOPICS: tuple[str, ...] = (
    "psma-rlt",
    "psma rlt",
    "psma-617",
    "lu-177",
    "lu177",
    "lutetium-177",
    "177lu",
    "actinium-225",
    "ac-225",
    "ac225",
    "ar-v7",
    "ar v7",
    "androgen receptor splice variant",
    "ar splice variant",
    "car-t",
    "car t",
    "cart cell",
    "chimeric antigen receptor",
    "bcma car",
    "cd19 car",
    "gprc5d",
    "claudin 18.2",
    "claudin-18.2",
    "btk degrader",
    "btk-degrader",
    "nx-2127",
    "nx-5948",
    "bgb-16673",
    "kras g12c",
    "kras-g12c",
    "sotorasib",
    "adagrasib",
    "kras g12d",
    "kras g12v",
    "met amp",
    "met-amp",
    "met amplification",
    "savolitinib",
    "tepotinib",
    "capmatinib",
    "brca reversion",
    "brca-reversion",
    "reversion mutation",
    "tarlatamab",
    "bispecific t-cell engager",
    "bite solid tumor",
    "t-dxd",
    "trastuzumab deruxtecan",
    "dato-dxd",
    "datopotamab deruxtecan",
    "patritumab deruxtecan",
    "ifinatamab deruxtecan",
    # v1.3.3 round-3 verification extensions (Patient #23 ATR-i + BRCA-reversion).
    # DDR-targeting agents (ATR-i + CHK1-i + WEE1-i + Polθ-i)
    "atr",
    "atr inhibitor",
    "atr-inhibitor",
    "atr-i",
    "atri",
    "ceralasertib",
    "azd6738",
    "berzosertib",
    "m6620",
    "vx-970",
    "elimusertib",
    "bay1895344",
    "camonsertib",
    "rp-3500",
    "atrn-119",
    "chk1",
    "chk1 inhibitor",
    "chk1-inhibitor",
    "prexasertib",
    "ly2606368",
    "adavosertib",
    "azd1775",
    "wee1",
    "wee1 inhibitor",
    "wee1-inhibitor",
    "novobiocin",
    "polq",
    "polq inhibitor",
    "polθ inhibitor",
    "art4215",
    "art-4215",
    # v1.3.2 round-2 EVAL extensions (Patient #13 LM-IT-IO + HA-WBRT,
    # #16 menin-i for KMT2A-r pediatric ALL/AML, #20 NPC EBV-CTL).
    # menin inhibitors (KMT2A-r / NPM1-mutant AML)
    "menin",
    "menin inhibitor",
    "menin-inhibitor",
    "revumenib",
    "ziftomenib",
    "bleximenib",
    "kmt2a-r",
    "kmt2a rearranged",
    "kmt2a-rearranged",
    "mll-r",
    "mll rearranged",
    "npm1-mutant aml",
    "npm1-mut aml",
    # EBV-specific cellular therapy / NPC
    "ebv",
    "ebv-ctl",
    "ebv-specific t cell",
    "ebv specific t cell",
    "ebvst",
    "tab-cel",
    "tabelecleucel",
    "lmp1",
    "lmp2",
    "ebna",
    "nasopharyngeal carcinoma",
    "npc",
    # LM-axis (leptomeningeal) radiation / intrathecal IO
    "ha-wbrt",
    "hippocampal avoidance wbrt",
    "hippocampal-avoidance wbrt",
    "nrg-cc003",
    "nrg cc003",
    "intrathecal immunotherapy",
    "it-nivolumab",
    "it nivolumab",
    "it-pembrolizumab",
    "it pembrolizumab",
    "craniospinal proton",
    "radiosurgery lm",
    "lm proton",
    # Solid-tumour BiTE
    "tarlatamab",
    "bite",
    "bispecific t-cell engager",
    # KRAS non-G12C
    "kras g12d",
    "kras-g12d",
    "mrtx1133",
    "kras g12v",
    "kras-g12v",
    # BTK pirtobrutinib / nemtabrutinib (non-covalent BTK)
    "btk degrader",
    "btk-degrader",
    "pirtobrutinib",
    "nemtabrutinib",
)


# Regex to find PubMed publication year inside an evidence entry. We look at:
#   * evidence[i].year                — explicit integer field
#   * evidence[i].pub_date            — "2021 Jun" / "2021-06" / "2021"
#   * evidence[i].quote / .summary    — fall-back regex year hunt
_YEAR_RE = re.compile(r"\b(19[5-9][0-9]|20[0-4][0-9])\b")


def _evidence_year(ev: dict[str, Any]) -> int | None:
    """Return the publication year of an evidence entry, or None if unknown.

    Resolution order:
      1. ev["year"] (int or coerce-able)
      2. ev["pub_date"] (regex hunt for 4-digit year)
      3. ev["quote"] / ev["summary"] (last-resort regex hunt)
    """
    year_raw = ev.get("year")
    if year_raw is not None:
        try:
            return int(year_raw)
        except (TypeError, ValueError):
            pass
    pub_date = ev.get("pub_date") or ev.get("publication_date") or ev.get("date")
    if pub_date:
        m = _YEAR_RE.search(str(pub_date))
        if m:
            return int(m.group(1))
    for k in ("quote", "summary"):
        v = ev.get(k)
        if v:
            m = _YEAR_RE.search(str(v))
            if m:
                return int(m.group(1))
    return None


def _claim_topic_matches_fast_moving(claim: dict[str, Any]) -> tuple[bool, list[str]]:
    """Return (matched, matched_tokens). Substring scan over claim text.

    matched_tokens is included in the WARN message so reviewers see which
    topic flagged.
    """
    text_fields = [
        claim.get("claim", ""),
        claim.get("delivery_text", ""),
        claim.get("delivery_markdown", ""),
        claim.get("pi_prose", ""),
        claim.get("summary", ""),
        claim.get("rationale", ""),
        claim.get("topic", ""),
    ]
    for ev in claim.get("evidence", []) or []:
        if isinstance(ev, dict):
            for k in ("quote", "summary", "ref", "result_text"):
                v = ev.get(k)
                if v:
                    text_fields.append(str(v))
    haystack_lower = " \n ".join(str(f) for f in text_fields if f).lower()
    matched = [t for t in FAST_MOVING_TOPICS if t in haystack_lower]
    return (bool(matched), matched)


class G23RecencyBandGate(Gate):
    name = "G23_recency_band"
    description = (
        "WARN when a claim in a fast-moving subspecialty (PSMA-RLT / Lu-177 / "
        "AR-V7 / CAR-T / BTK-degrader / KRAS-G12C / MET-amp / BRCA-reversion / "
        "ADC / BiTE) cites a PMID older than the recency window (default 18 mo)."
    )
    failure_mode_code = "F8"

    def __init__(
        self,
        recency_months: int = 18,
        now: _dt.date | None = None,
    ) -> None:
        self.recency_months = int(recency_months)
        self.now = now or _dt.date.today()

    def check(self, claim: dict[str, Any]) -> GateResult:
        matched_topic, matched_tokens = _claim_topic_matches_fast_moving(claim)
        if not matched_topic:
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message="claim topic not in fast-moving list",
            )

        evidence = claim.get("evidence", []) or []
        stale: list[dict[str, Any]] = []
        # Window cut-off as fractional-year.
        cutoff_year_float = self.now.year + (self.now.month - 1) / 12.0 - (
            self.recency_months / 12.0
        )

        for i, ev in enumerate(evidence):
            if not isinstance(ev, dict):
                continue
            # Only PMID-typed evidence is scope; dataset / cohort entries are
            # exempt (they don't have a publication recency in the same sense).
            ev_type = str(ev.get("type", "")).lower()
            if ev_type not in ("pmid", "publication", "article", ""):
                continue
            year = _evidence_year(ev)
            if year is None:
                continue
            if year < cutoff_year_float:
                stale.append(
                    {
                        "evidence_index": i,
                        "pmid": ev.get("id") or ev.get("pmid"),
                        "year": year,
                        "age_months_estimate": int(round((self.now.year - year) * 12)),
                    }
                )

        if not stale:
            return GateResult(
                gate=self.name,
                status=GateStatus.PASS,
                message=(
                    f"G23 OK — claim topic {matched_tokens!r} is fast-moving but all "
                    f"PMID-evidence falls inside the {self.recency_months}-month window"
                ),
                evidence={
                    "matched_topics": matched_tokens,
                    "recency_months": self.recency_months,
                },
            )

        return GateResult(
            gate=self.name,
            status=GateStatus.FAIL,
            block=False,  # WARN — never blocks; informs reviewer + patient brief
            message=(
                f"G23 WARN — fast-moving topic {matched_tokens!r} cites "
                f"{len(stale)} PMID(s) older than {self.recency_months} months. "
                "Consider recent updates: PSMA-RLT/Lu-177 (SPLASH / ENZA-p / "
                "PSMAfore 2024-2025); AR-V7 (post-2023 reanalysis); CAR-T (CARTITUDE-4 "
                "/ OPTIMUM); BTK-degrader (NX-2127 / NX-5948 / BGB-16673 2024-2025); "
                "KRAS-G12C (post-CodeBreak-resistance + G12D / G12V emerging); "
                "MET-amp (savolitinib + tepotinib combinations); BRCA-reversion "
                "(ctDNA detection); ADC (T-DXd / Dato-DXd post-DESTINY). Reviewer "
                "may add fresh PMID before render OR carry the caveat into the "
                "patient brief."
            ),
            evidence={
                "matched_topics": matched_tokens,
                "recency_months": self.recency_months,
                "stale_evidence_entries": stale,
                "reviewer_action": "add_fresh_pmid_or_carry_caveat",
            },
        )
