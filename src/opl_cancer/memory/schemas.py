"""Insight card + evidence + reviewer + auditor schemas. Spec §5.2."""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ClaimLayer(str, Enum):
    ESTABLISHED = "established"
    EXPLORATORY = "exploratory"
    SPECULATIVE = "speculative"


class EvidenceType(str, Enum):
    PMID = "pmid"
    DATASET = "dataset"
    GUIDELINE = "guideline"
    TRIAL = "trial"
    KB = "knowledge_base"


class Evidence(BaseModel):
    type: EvidenceType
    id: str = Field(min_length=1)
    quote: str = ""
    extras: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _pmid_quote_required(self) -> "Evidence":
        """Safety eval S6: PMID-type evidence must have a non-empty quote."""
        if self.type == EvidenceType.PMID and not self.quote:
            raise ValueError("PMID evidence must have a non-empty quote (S6)")
        return self


class ProducedBy(BaseModel):
    executor_task: str
    model: str
    prompt_version: str
    run_id: str


class ReviewedBy(BaseModel):
    reviewer_model: str
    verdict: Literal["pass", "fail", "needs_revision"]
    challenges: list[str] = Field(default_factory=list)
    review_prompts_used: list[str] = Field(default_factory=list)


class AuditedBy(BaseModel):
    auditor_run: str
    permission_level: int = Field(ge=0, le=4)
    clearances: list[str] = Field(default_factory=list)
    risk_card_id: str | None = None


class WithdrawStatus(BaseModel):
    reason: str
    withdrawn_at: str
    evidence: str = ""


class InsightCard(BaseModel):
    """Single patient-facing claim, append-only versioned. Spec §5.2."""

    id: str
    version: int = Field(ge=1)
    claim: str
    claim_layer: ClaimLayer
    evidence: list[Evidence] = Field(min_length=1)
    produced_by: ProducedBy
    reviewed_by: ReviewedBy
    audited_by: AuditedBy
    provenance_hash: str
    created_at: str
    patient_surfaced_at: str | None = None
    patient_acknowledged_at: str | None = None
    withdraw_status: WithdrawStatus | None = None
    supersedes: str | None = None
    on_chain_receipt: str | None = None  # always None in v0 (no chain integration)

    @field_validator("provenance_hash")
    @classmethod
    def _hash_must_be_sha256(cls, v: str) -> str:
        if not v.startswith("sha256:") or len(v) != 7 + 64:
            raise ValueError("provenance_hash must be sha256:<64 hex chars>")
        return v
