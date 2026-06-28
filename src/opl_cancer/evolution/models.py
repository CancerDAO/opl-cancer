"""Pydantic schemas for evolution layer. ADR-0020.

TraceDigest: compact JSON summary of a completed run. Bounded ~100KB. Fed to
the EvolutionAnalyzer AFTER PII/PHI scrubbing.

EvolutionProposal: a single proposed change. Always written under
``proposals/iter_<N>/``; NEVER auto-applied to baseline.

InvariantImpact: static-analysis flags marking which OPL safety surfaces a
proposal touches. Hits → ``requires_double_signoff = True`` automatically.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Trace digest
# ---------------------------------------------------------------------------


class WaveSummary(BaseModel):
    """Per-Wave bucket inside the digest."""

    wave: int = Field(ge=1, le=5)
    tasks_completed: int = 0
    tasks_skipped: int = 0
    artifact_paths: list[str] = Field(default_factory=list)
    duration_seconds: float | None = None
    errors: list[str] = Field(default_factory=list)


class HypothesisStrategyCount(BaseModel):
    """Wave 2 strategy distribution — drives novelty assessment."""

    strategy: str
    count: int = 0
    speculative_with_testability: int = 0


class TraceDigest(BaseModel):
    """Bounded summary of a completed run.

    Per ADR-0020 §What we copy #1. Read by ``collector.collect_trace_digest``,
    scrubbed by ``scrubber.scrub`` BEFORE being passed to any LLM call.
    """

    run_id: str
    patient_code_scrubbed: str = "[SCRUBBED]"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    waves: list[WaveSummary] = Field(default_factory=list)
    hypothesis_strategies: list[HypothesisStrategyCount] = Field(default_factory=list)
    evidence_tier_distribution: dict[str, int] = Field(default_factory=dict)  # E/X/S counts
    retraction_db_hits: list[str] = Field(default_factory=list)
    henry_verdict_counts: dict[str, int] = Field(default_factory=dict)  # pass/needs_revision/fail/etc
    novelty_gate_stats: dict[str, int] = Field(default_factory=dict)  # surfaced/blocked/etc
    integrator_latency_p50_ms: dict[str, float] = Field(default_factory=dict)
    notable_issues: list[str] = Field(default_factory=list)  # max 20 entries
    # D4/ADR-0037 — the REAL failure tail the re-aimed loop learns from: reviewer
    # fails, falsified Wave-4 verdicts, G14 low cohort-match. Each item is
    # {kind, ref, reason}. Richer than the coarse keyword-grepped wave errors.
    strange_tail: list[dict[str, str]] = Field(default_factory=list)
    digest_byte_size_estimate: int = 0  # set by collector after serialise; cap ~100KB

    def is_scrubbed(self) -> bool:
        """Cheap heuristic — explicit marker that scrubber has run."""
        return self.patient_code_scrubbed != "" and self.patient_code_scrubbed.startswith("[SCRUB")


# ---------------------------------------------------------------------------
# Proposals
# ---------------------------------------------------------------------------


ProposalKind = Literal["prompt_patch", "skill_addition", "tool_proposal"]
ProposalStatus = Literal["pending", "approved", "rejected", "blocked"]


class InvariantImpact(BaseModel):
    """Static-analysis report on which OPL safety surfaces a proposal touches.

    Per ADR-0020 §What we add #10. Hits drive auto-flag of
    ``requires_double_signoff``.
    """

    touches_henry_l3_l4: bool = False
    touches_g7_imperative_voice: bool = False
    touches_g13_reviewer_split: bool = False
    touches_persona_prefix: bool = False
    touches_claim_layer_enforcement: bool = False
    touches_retraction_db_logic: bool = False
    extra_flags: list[str] = Field(default_factory=list)

    def any_safety_hit(self) -> bool:
        return any(
            [
                self.touches_henry_l3_l4,
                self.touches_g7_imperative_voice,
                self.touches_g13_reviewer_split,
                self.touches_persona_prefix,
                self.touches_claim_layer_enforcement,
                self.touches_retraction_db_logic,
            ]
        )


class EvolutionProposal(BaseModel):
    """One proposed change. Lives at proposals/iter_<N>/<kind>/<slug>/.

    NEVER auto-applied. Repository commit hook + manual review is the gate.
    """

    proposal_id: str  # short slug e.g. "p001-aviv-add-synergy-strategy"
    kind: ProposalKind
    summary: str  # one-sentence
    rationale: str  # 2-5 sentences, MUST cite which TraceDigest field triggered it
    proposed_diff: str = ""  # unified diff for prompt_patch; SMILES/code/SKILL.md content for others
    target_path: str = ""  # baseline file the patch would apply to (informational only)
    invariant_impact: InvariantImpact = Field(default_factory=InvariantImpact)
    status: ProposalStatus = "pending"
    requires_double_signoff: bool = False
    required_signoffs: list[str] = Field(default_factory=list)  # ["sid", "henry", "bert", ...]
    approved_by: list[str] = Field(default_factory=list)
    rejected_by: list[str] = Field(default_factory=list)
    clinical_anchor: str = ""  # CSCO/NCCN/PMID/NCT — MANDATORY for skill_addition
    regression_gate_status: Literal["not_yet_implemented", "pass", "fail"] = "not_yet_implemented"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    iter_n: int = 0  # which evolution iteration produced this

    def is_auto_rejected(self) -> bool:
        """Skill proposals without clinical_anchor are auto-rejected."""
        if self.kind == "skill_addition" and not self.clinical_anchor.strip():
            return True
        return False


class EvolutionCandidates(BaseModel):
    """Output of EvolutionAnalyzer — list of proposals + summary."""

    iter_n: int
    proposals: list[EvolutionProposal] = Field(default_factory=list)
    analysis_summary: str = ""
    analyzer_model: str = ""
    used_heuristic_fallback: bool = False
