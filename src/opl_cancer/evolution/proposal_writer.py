"""ProposalWriter — write EvolutionCandidates to proposals/iter_<N>/.

ADR-0020 §What we drop #5: NEVER auto-applies anything. NEVER touches
baseline files in src/ or prompts/. The repository sees this output as a
PR-style diff bundle awaiting human review.

Filesystem layout produced:
    <out_root>/iter_<N>/
        README.md              ← analyzer summary + how to review
        status.yaml            ← per-proposal status, requires_double_signoff
        prompt_patches.diff    ← concatenated unified diffs (prompt_patch)
        skill_additions/
            <slug>/SKILL.md.proposed
            <slug>/clinical_anchor.txt
        tool_proposals.jsonl   ← review-only JSONL
        rejected/
            <slug>.md          ← auto-blocked proposals with reason
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from .models import EvolutionCandidates, EvolutionProposal


_FORBIDDEN_PARENTS = (
    "src/opl_cancer",
    "prompts",
    "tests",
    "models.yaml",
    "pyproject.toml",
    "scripts",
    "validators",
)


def _safety_check_out_root(out_root: Path) -> None:
    """Refuse to write into any baseline path.

    The check is path-substring based — works regardless of /tmp/ prefix
    so test paths like /tmp/.../src/opl_cancer also trigger it.
    """
    abs_str = str(out_root.resolve()) + "/"
    for forbidden in _FORBIDDEN_PARENTS:
        if f"/{forbidden}/" in abs_str:
            raise ValueError(
                f"ProposalWriter refuses to write into baseline path {abs_str!r} "
                f"(contains {forbidden!r}). Per ADR-0020, output must go under "
                f"proposals/ — never into src/prompts/tests/scripts/etc."
            )


def _slugify(text: str, max_len: int = 50) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in text.lower())
    safe = "-".join(p for p in safe.split("-") if p)
    return safe[:max_len] or "proposal"


def write_proposals(
    candidates: EvolutionCandidates,
    out_root: Path,
) -> dict[str, list[str]]:
    """Write the proposals under ``out_root/iter_<N>/``.

    Returns a manifest dict: {"prompt_patches": [...], "skill_additions": [...],
    "tool_proposals": [...], "rejected": [...]} of relative paths written.
    """
    out_root = Path(out_root)
    _safety_check_out_root(out_root)

    iter_dir = out_root / f"iter_{candidates.iter_n:03d}"
    iter_dir.mkdir(parents=True, exist_ok=True)
    rejected_dir = iter_dir / "rejected"
    skills_dir = iter_dir / "skill_additions"

    manifest: dict[str, list[str]] = {
        "prompt_patches": [],
        "skill_additions": [],
        "tool_proposals": [],
        "rejected": [],
    }

    prompt_patches: list[str] = []
    tool_proposals_jsonl: list[str] = []
    status_records: list[dict] = []

    for p in candidates.proposals:
        if p.status == "blocked":
            rejected_dir.mkdir(exist_ok=True)
            slug = _slugify(p.proposal_id + "-" + p.summary)
            fpath = rejected_dir / f"{slug}.md"
            fpath.write_text(
                _render_rejected(p),
                encoding="utf-8",
            )
            manifest["rejected"].append(str(fpath.relative_to(out_root)))
            status_records.append(_status_record(p))
            continue

        if p.kind == "prompt_patch":
            prompt_patches.append(_render_prompt_patch_block(p))
            manifest["prompt_patches"].append(p.proposal_id)
        elif p.kind == "skill_addition":
            slug = _slugify(p.proposal_id + "-" + p.summary)
            skill_dir = skills_dir / slug
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md.proposed").write_text(
                p.proposed_diff or _render_skill_stub(p),
                encoding="utf-8",
            )
            (skill_dir / "clinical_anchor.txt").write_text(
                p.clinical_anchor or "",
                encoding="utf-8",
            )
            manifest["skill_additions"].append(str(skill_dir.relative_to(out_root)))
        elif p.kind == "tool_proposal":
            tool_proposals_jsonl.append(
                json.dumps(
                    {
                        "proposal_id": p.proposal_id,
                        "summary": p.summary,
                        "rationale": p.rationale,
                        "proposed_diff": p.proposed_diff,
                        "target_path": p.target_path,
                        "status": p.status,
                    },
                    ensure_ascii=False,
                )
            )
            manifest["tool_proposals"].append(p.proposal_id)

        status_records.append(_status_record(p))

    if prompt_patches:
        (iter_dir / "prompt_patches.diff").write_text(
            "\n\n".join(prompt_patches), encoding="utf-8"
        )
    # Always write a tool_proposals.jsonl (possibly empty) so reviewers know to check
    (iter_dir / "tool_proposals.jsonl").write_text(
        "\n".join(tool_proposals_jsonl) + ("\n" if tool_proposals_jsonl else ""),
        encoding="utf-8",
    )

    (iter_dir / "status.yaml").write_text(
        yaml.safe_dump(
            {
                "iter_n": candidates.iter_n,
                "analyzer_model": candidates.analyzer_model,
                "used_heuristic_fallback": candidates.used_heuristic_fallback,
                "analysis_summary": candidates.analysis_summary,
                "proposals": status_records,
            },
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    (iter_dir / "README.md").write_text(
        _render_readme(candidates, manifest), encoding="utf-8"
    )

    return manifest


# ---- helpers ----


def _status_record(p: EvolutionProposal) -> dict:
    return {
        "proposal_id": p.proposal_id,
        "kind": p.kind,
        "summary": p.summary,
        "target_path": p.target_path,
        "status": p.status,
        "requires_double_signoff": p.requires_double_signoff,
        "required_signoffs": p.required_signoffs,
        "invariant_impact": {
            "touches_henry_l3_l4": p.invariant_impact.touches_henry_l3_l4,
            "touches_g7_imperative_voice": p.invariant_impact.touches_g7_imperative_voice,
            "touches_g13_reviewer_split": p.invariant_impact.touches_g13_reviewer_split,
            "touches_persona_prefix": p.invariant_impact.touches_persona_prefix,
            "touches_claim_layer_enforcement": p.invariant_impact.touches_claim_layer_enforcement,
            "touches_retraction_db_logic": p.invariant_impact.touches_retraction_db_logic,
        },
        "regression_gate_status": p.regression_gate_status,
        "clinical_anchor": p.clinical_anchor,
    }


def _render_prompt_patch_block(p: EvolutionProposal) -> str:
    header = (
        f"# === Proposal {p.proposal_id} ===\n"
        f"# Summary: {p.summary}\n"
        f"# Target: {p.target_path}\n"
        f"# Rationale: {p.rationale}\n"
        f"# Status: {p.status}\n"
        f"# Requires double signoff: {p.requires_double_signoff}\n"
    )
    return header + (p.proposed_diff or "# (no diff body)\n")


def _render_skill_stub(p: EvolutionProposal) -> str:
    return (
        f"---\n"
        f"name: {p.proposal_id}\n"
        f"description: {p.summary}\n"
        f"clinical_anchor: {p.clinical_anchor}\n"
        f"status: pending_review\n"
        f"---\n\n"
        f"# {p.summary}\n\n"
        f"{p.rationale}\n"
    )


def _render_rejected(p: EvolutionProposal) -> str:
    reasons = "\n".join(f"- {r}" for r in p.rejected_by)
    return (
        f"# REJECTED: {p.proposal_id}\n\n"
        f"**Kind:** {p.kind}\n"
        f"**Summary:** {p.summary}\n\n"
        f"## Rejection reasons\n\n{reasons or '- (auto-block by InvariantGate)'}\n\n"
        f"## Original rationale\n\n{p.rationale}\n"
    )


def _render_readme(c: EvolutionCandidates, manifest: dict) -> str:
    lines = [
        f"# Evolution proposals — iter_{c.iter_n:03d}",
        "",
        f"Analyzer: `{c.analyzer_model}`  ·  Heuristic fallback: `{c.used_heuristic_fallback}`",
        "",
        "## Analysis summary",
        "",
        c.analysis_summary or "(none)",
        "",
        "## Manifest",
        "",
        f"- prompt_patches: {len(manifest['prompt_patches'])}",
        f"- skill_additions: {len(manifest['skill_additions'])}",
        f"- tool_proposals: {len(manifest['tool_proposals'])}",
        f"- rejected (auto-blocked): {len(manifest['rejected'])}",
        "",
        "## Review protocol (ADR-0020)",
        "",
        "1. Read `status.yaml` for the per-proposal verdict + `requires_double_signoff` flags.",
        "2. For each `pending` proposal: open the corresponding file under `prompt_patches.diff` / `skill_additions/<slug>/` / `tool_proposals.jsonl`.",
        "3. Any proposal with `requires_double_signoff: true` requires BOTH `sid` AND `henry` signoff before merge.",
        "4. Skill proposals without `clinical_anchor` are already auto-rejected under `rejected/`.",
        "5. To approve: manually edit baseline files + update `status.yaml` to `status: approved` + add to `approved_by`. NEVER let this tool auto-apply.",
        "",
        "## Hard rules (do not override)",
        "",
        "- This directory is the ONLY place evolution may write. Baseline files in `src/`, `prompts/`, `models.yaml`, etc., are off-limits to this tool.",
        "- Approved patches land via a normal PR with at least 1 medical-expert reviewer.",
        "- Wave 3 hard-gate regression checks (ADR-0011) are deferred; `regression_gate_status: not_yet_implemented` is expected until that lands.",
    ]
    return "\n".join(lines) + "\n"
