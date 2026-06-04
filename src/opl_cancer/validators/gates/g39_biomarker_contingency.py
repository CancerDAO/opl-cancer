"""G39: biomarker_contingency — a headline regimen must not be gated on an UNKNOWN biomarker.

v2.7.0 (ADR-0026 P1/P2, session 0d1017d4 KRAS-G12C/MSS mCRC findings).
Cross-model **Finding 1 (CRITICAL)**: the brief's headline regimen (anti-EGFR)
was contingent on a biomarker the report itself admitted was UNKNOWN
(NRAS/BRAF status not tested). Presenting that as the top recommendation is
undeliverable and possibly net-harmful — the patient/clinician reads a
confident headline that silently assumes a yet-unmeasured biomarker is
favourable, with the dependency buried in caveats.

G39 closes that hole. It is a **no-LLM, mechanical** gate operating purely on
the structured ``claim.regimen`` object (schemas/claim.v2.schema.json). The LLM
(via the producer prompt) makes the clinical judgment — it records which
biomarkers a regimen requires (``required_biomarkers``), the required state, and
the patient's KNOWN state. G39 does NOT re-make that call; it mechanically
checks the recorded judgment is coherent:

  A regimen presented as HEADLINE (``regimen.is_headline`` true OR
  ``regimen.rank == 1``) must NOT depend on a biomarker whose
  ``patient_state`` is unknown / untested / empty, and any KNOWN patient_state
  must actually SATISFY the regimen's ``required_state``.

If a headline regimen has a required biomarker that is unresolved (or resolved
against it), G39 FAILs and BLOCKs (Fork A: biomarker-contingency is a SAFETY
gate). The remedy the LLM must apply: either resolve the biomarker (order the
test / record the known state) or demote the regimen below a contingency banner
(``is_headline=false`` and ``rank>1``, clearly labelled "IF <state> is
confirmed, consider …"). A clearly-labelled *contingent* option gated on an
unknown biomarker is legitimate and does NOT fire.

SKIP (non-blocking) when the claim has no ``regimen`` field — G39 cannot judge a
claim that proposes no regimen. A regimen with no ``required_biomarkers`` PASSes
(nothing to be contingent on).
"""
from __future__ import annotations

from typing import Any

from ..mechanical_gates import Gate, GateResult, GateStatus

# Tokens (case-insensitive, trimmed) that mean "the patient's state for this
# biomarker is NOT known". These describe the ABSENCE of a measurement — not a
# clinical keyword list (no-hardcoded-keyword-list policy): the LLM
# decides and records patient_state; G39 only recognises the canonical
# "not-measured" sentinels the schema documents (null / 'unknown' / 'untested'
# / empty). Anything else is treated as a KNOWN state and compared structurally
# to required_state.
_UNKNOWN_STATES = frozenset(
    {"", "unknown", "untested", "not tested", "not_tested", "n/a", "na", "pending", "未知", "未查", "未检测", "待查"}
)


def _is_unknown(patient_state: Any) -> bool:
    """True if patient_state is null / a documented not-measured sentinel."""
    if patient_state is None:
        return True
    return str(patient_state).strip().lower() in _UNKNOWN_STATES


def _is_headline(regimen: dict[str, Any]) -> bool:
    """A regimen is headline if is_headline is truthy OR rank == 1."""
    if regimen.get("is_headline") is True:
        return True
    return regimen.get("rank") == 1


def _state_satisfied(required_state: Any, patient_state: Any) -> bool:
    """Structural (not clinical) match: known patient_state must equal the
    required_state (case-insensitive, trimmed). This is a coherence check on
    the LLM's own recorded states, never an independent clinical re-call —
    if the producer wrote required 'MSI-H' but patient 'MSS', that is an
    internally-incoherent headline and G39 catches it."""
    return str(required_state).strip().lower() == str(patient_state).strip().lower()


class G39BiomarkerContingencyGate(Gate):
    """A headline / top-ranked regimen must not hinge on an unknown biomarker."""

    name = "G39_biomarker_contingency"
    description = (
        "A headline (is_headline true OR rank==1) treatment regimen must NOT be "
        "gated on a biomarker whose patient_state is unknown/untested, nor on a "
        "known biomarker state that fails the regimen's required_state. Stops the "
        "'headline anti-EGFR contingent on untested NRAS/BRAF' failure mode "
        "(session 0d1017d4 Finding 1). The regimen must drop below a contingency "
        "banner or the biomarker must be resolved. Mechanical on claim.regimen."
    )
    failure_mode_code = "A5-HEADLINE-ON-UNKNOWN-BIOMARKER"
    family_id = "reasoning-quality"

    def check(self, claim: dict[str, Any]) -> GateResult:
        regimen = claim.get("regimen")
        if not isinstance(regimen, dict):
            return GateResult(
                gate=self.name,
                status=GateStatus.SKIP,
                message="G39 SKIP — claim has no regimen object to judge.",
            )

        required = regimen.get("required_biomarkers")
        if not isinstance(required, list) or not required:
            return GateResult(
                gate=self.name,
                status=GateStatus.PASS,
                message=(
                    "G39 OK — regimen declares no required_biomarkers; nothing to "
                    "be contingent on."
                ),
                evidence={"is_headline": _is_headline(regimen)},
            )

        headline = _is_headline(regimen)
        if not headline:
            # A clearly-labelled contingent/secondary regimen gated on an
            # unknown biomarker is legitimate — G39 only blocks headlines.
            return GateResult(
                gate=self.name,
                status=GateStatus.PASS,
                message=(
                    f"G39 OK — regimen is contingent/secondary (is_headline="
                    f"{regimen.get('is_headline')!r}, rank={regimen.get('rank')!r}); "
                    f"its {len(required)} biomarker dependency(ies) need not be "
                    "resolved to be presented."
                ),
                evidence={"is_headline": False, "required_count": len(required)},
            )

        violations: list[dict[str, Any]] = []
        for bm in required:
            if not isinstance(bm, dict):
                continue
            gene = bm.get("gene")
            required_state = bm.get("required_state")
            patient_state = bm.get("patient_state")
            if _is_unknown(patient_state):
                violations.append({
                    "gene": gene,
                    "required_state": required_state,
                    "patient_state": patient_state,
                    "reason": "patient_state is unknown/untested for a headline regimen",
                })
            elif not _state_satisfied(required_state, patient_state):
                violations.append({
                    "gene": gene,
                    "required_state": required_state,
                    "patient_state": patient_state,
                    "reason": "known patient_state does not satisfy required_state",
                })

        if violations:
            sample = "; ".join(
                f"{v['gene']} requires {v['required_state']!r} but patient_state="
                f"{v['patient_state']!r} ({v['reason']})"
                for v in violations[:4]
            )
            return GateResult(
                gate=self.name,
                status=GateStatus.FAIL,
                block=True,
                message=(
                    f"G39 FAIL — headline regimen is contingent on "
                    f"{len(violations)} unresolved biomarker(s): {sample}. Either "
                    "resolve the biomarker (record a known, satisfying patient_state) "
                    "or demote the regimen below a contingency banner "
                    "(is_headline=false, rank>1, clearly labelled 'IF confirmed …')."
                ),
                evidence={
                    "is_headline": True,
                    "rank": regimen.get("rank"),
                    "violations": violations[:20],
                    "required_count": len(required),
                },
            )

        return GateResult(
            gate=self.name,
            status=GateStatus.PASS,
            message=(
                f"G39 OK — headline regimen's {len(required)} required "
                "biomarker(s) all have a known patient_state satisfying the "
                "required_state."
            ),
            evidence={"is_headline": True, "required_count": len(required)},
        )
