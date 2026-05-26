"""OPL evolution layer — trace-digest post-mortem proposal generator.

ADR-0020: borrowed architecture from EvoMaster, 3 medical red lines enforced.
This package NEVER modifies baseline prompts / src / models.yaml — output is
strictly under ``proposals/iter_<N>/`` for human review.
"""
from __future__ import annotations

from .models import (
    EvolutionProposal,
    InvariantImpact,
    ProposalKind,
    ProposalStatus,
    TraceDigest,
)

__all__ = [
    "EvolutionProposal",
    "InvariantImpact",
    "ProposalKind",
    "ProposalStatus",
    "TraceDigest",
]
