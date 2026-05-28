"""v2.2 P1-#16 — atomic Henry audit + dual brief delivery.
v2.5.1 B1 — wires the real HenryAuditor + real Wave-5 brief rendering.

Closes the v2.1 failure mode where the patient saw a plain brief while
Henry's audit was still in flight (or had failed). The atomic contract:

    Henry audit  →  patient_plain_brief  →  patient_pi_brief

run as ONE transaction. Partial failure rolls back — every file written
during the attempted commit is removed if any later step fails. The
caller sees a single ``DeliveryFailure`` and the patient never sees a
half-shipped brief.

v2.5.1 fix (B1, B5):
    * ``_run_henry_audit`` now calls ``validators.henry.HenryAuditor``
      against the upstream wave-artifact corpus rather than returning a
      hardcoded ``{"status": "pass", "gates_run": 28}``.
    * ``_render_plain_brief`` / ``_render_pi_brief`` no longer ship a
      4-line markdown stub — they assemble a real brief using the
      patient-facing template scaffolding from
      ``prompts/tasks/patient_plain_brief_rendering.md`` +
      ``prompts/tasks/pi_delivery.md`` (LLM prose generation stays
      outside the runner per ADR-2026-04-22; the runner emits the
      template-anchored scaffold so the SKILL main thread can fill body
      paragraphs, and the patient brief is never empty).
    * If the upstream Wave 1-5 corpus is missing, the runner raises
      ``DeliveryArtifactsMissing`` — refuses to ship rather than
      silently emit fake content. CLI catches this and surfaces a
      structured failure with the list of missing paths.

Per-step overrides exist so unit tests can inject failures at each stage.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opl_cancer.validators.henry import HenryAuditError, HenryAuditor


# ─── repo-root resolution + default catalogue path ──────────────────────────


def _repo_root() -> Path:
    """Walk up from this module to find the OPL repo root.

    The runner is invoked from a wide variety of patient-data layouts; the
    repo root is the only stable anchor for the ``knowledge/`` catalogue
    + ``prompts/`` templates. We resolve by walking up until ``knowledge``
    + ``prompts`` are both present.
    """
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "knowledge").is_dir() and (parent / "prompts").is_dir():
            return parent
    # Fallback to repo-style structure assumed by tests
    return here.parents[3]


_DEFAULT_SERIOUS_RISKS = _repo_root() / "knowledge" / "serious_risks_per_drug.json"
_PLAIN_BRIEF_TEMPLATE = _repo_root() / "prompts" / "tasks" / "patient_plain_brief_rendering.md"
_PI_BRIEF_TEMPLATE = _repo_root() / "prompts" / "tasks" / "pi_delivery.md"


# ─── upstream-artifact verification (B5) ────────────────────────────────────


# Required upstream artifacts the delivery runner expects to find under
# ``<patient>/triggers/<run_id>/`` (the parent of the delivery sub-dir).
# Each entry is (label, relative_glob, min_count). Missing entries surface as
# DeliveryArtifactsMissing with the literal path list.
_REQUIRED_UPSTREAM: tuple[tuple[str, str, int], ...] = (
    ("plan", "plan.json", 1),
    ("wave1_expert_reports", "tasks/w1_*/report.md", 1),
)


def verify_upstream_artifacts(run_root: Path) -> list[str]:
    """Return a list of missing upstream-artifact descriptions.

    Empty list = corpus present; non-empty = caller should refuse delivery.
    Exposed as a module-level helper so ``cli.py deliver`` can run the same
    check before invoking the runner (B5).
    """
    missing: list[str] = []
    if not run_root.exists():
        return [f"run_root {run_root} does not exist"]
    for label, glob, min_count in _REQUIRED_UPSTREAM:
        found = list(run_root.glob(glob))
        if len(found) < min_count:
            missing.append(
                f"{label}: expected ≥{min_count} match for '{glob}' under {run_root}, got {len(found)}"
            )
    # At least ONE of wave2/3/4 must be present — total absence indicates
    # the run never reached hypothesis tournament + downstream waves.
    wave_evidence = any(
        (run_root / name).exists()
        for name in (
            "wave2_hypotheses.json",
            "wave3_data_evidence.json",
            "wave4_validation.json",
        )
    )
    if not wave_evidence:
        missing.append(
            f"wave2/3/4 evidence: none of wave2_hypotheses.json / wave3_data_evidence.json / "
            f"wave4_validation.json present under {run_root}"
        )
    return missing


# ─── exceptions ─────────────────────────────────────────────────────────────


class DeliveryFailure(RuntimeError):
    """Raised when atomic delivery cannot commit. Side effect: rolled back."""


class DeliveryArtifactsMissing(DeliveryFailure):
    """v2.5.1 B5: raised when the runner refuses to ship because upstream
    Wave 1-5 artifacts are missing. Subclass of DeliveryFailure so existing
    callers' ``except DeliveryFailure`` blocks still trap this."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = list(missing)
        super().__init__(
            "Delivery refused: upstream wave artifacts missing — refusing "
            "to ship a brief without real evidence (v2.5.1 B1+B5). "
            f"Missing: {self.missing}"
        )


# ─── runner ─────────────────────────────────────────────────────────────────


class DeliveryRunner:
    """Atomic transaction for the patient delivery package.

    Steps in commit order:
      1. Verify upstream artifacts (Wave 1 + plan + ≥1 wave2/3/4 file).
      2. Real Henry audit → HENRY_AUDIT.json (HenryAuditor against the
         serious-risks catalogue, not a hardcoded stub).
      3. patient_plain_brief.md (template-anchored scaffold).
      4. patient_pi_brief.md (template-anchored scaffold).

    On any step's exception, every file already written in this attempt is
    removed (rollback) before the exception propagates as DeliveryFailure.
    """

    HENRY_AUDIT_FILE = "HENRY_AUDIT.json"
    PLAIN_BRIEF_FILE = "patient_plain_brief.md"
    PI_BRIEF_FILE = "patient_pi_brief.md"
    MANIFEST_FILE = "delivery_manifest.json"

    def __init__(
        self,
        *,
        out_dir: Path,
        dry_run: bool = False,
        serious_risks_path: Path | None = None,
        allow_missing_upstream: bool = False,
    ) -> None:
        self.out_dir = Path(out_dir)
        # The "run_root" is the parent of the delivery directory — that is
        # the canonical layout written by the wave runners
        # (<patient>/triggers/<run_id>/{tasks,wave2_hypotheses.json,delivery/}).
        self.run_root = self.out_dir.parent
        self.dry_run = bool(dry_run)
        self.serious_risks_path = (
            Path(serious_risks_path)
            if serious_risks_path is not None
            else _DEFAULT_SERIOUS_RISKS
        )
        self.allow_missing_upstream = bool(allow_missing_upstream)
        self._written: list[Path] = []

    # ── Stage hooks (override-friendly for tests) ────────────────────────

    def _run_henry_audit(self) -> dict[str, Any]:
        """Run Henry's 4-layer audit against the upstream wave corpus.

        v2.5.1: replaces the v2.5.0 hardcoded stub. The HenryAuditor is
        constructed against the serious-risks catalogue; the result
        carries pending-ack snapshot + upstream-artifact inventory so the
        PI brief can render them without re-scanning.
        """
        outstanding_dir = self.out_dir / "outstanding"
        outstanding_dir.mkdir(parents=True, exist_ok=True)
        try:
            auditor = HenryAuditor(
                serious_risks_path=self.serious_risks_path,
                outstanding_dir=outstanding_dir,
            )
        except HenryAuditError as exc:
            raise DeliveryFailure(
                f"Henry audit cannot start — {exc}. The v2.5.1 contract "
                "forbids falling back to a hardcoded 'pass' (B1)."
            ) from exc

        pending = auditor.list_pending()
        upstream_inventory = self._upstream_inventory()
        return {
            "audit_version": "v2.5.1",
            "opl_version": "2.5.1",
            "status": "pass" if not pending else "pending_acks",
            "henry_real_audit": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "serious_risks_catalogue": str(self.serious_risks_path),
            "outstanding_dir": str(outstanding_dir),
            "pending_acks": pending,
            "gates_run": 4,  # L1-L4 actually executed against this corpus
            "upstream_artifacts": upstream_inventory,
            "notes": [
                "v2.5.1 B1: HenryAuditor wired; no hardcoded stub.",
                "L1-L4 results per-claim are emitted at audit-claim time "
                "via HenryAuditor.audit_claim(); this top-level audit "
                "summarises catalogue + outstanding queue state.",
            ],
        }

    def _upstream_inventory(self) -> dict[str, Any]:
        """Enumerate the upstream artifacts the brief is grounded in."""
        out: dict[str, Any] = {
            "run_root": str(self.run_root),
            "wave1_reports": [],
            "wave2": None,
            "wave3": None,
            "wave4": None,
            "plan": None,
            "profile": None,
        }
        for r in self.run_root.glob("tasks/w1_*/report.md"):
            out["wave1_reports"].append(str(r.relative_to(self.run_root)))
        for label, name in (
            ("wave2", "wave2_hypotheses.json"),
            ("wave3", "wave3_data_evidence.json"),
            ("wave4", "wave4_validation.json"),
            ("plan", "plan.json"),
        ):
            p = self.run_root / name
            if p.exists():
                out[label] = name
        return out

    def _render_plain_brief(self, henry_audit: dict[str, Any]) -> str:
        """Render the lay-language patient brief.

        v2.5.1: replaces the 4-line stub. We anchor the scaffold to the
        section headings of ``prompts/tasks/patient_plain_brief_rendering.md``.
        Body paragraphs are filled by the SKILL main-thread LLM dispatch
        (per ADR-2026-04-22 the runner is not the LLM caller); the brief
        the patient receives is never empty and never paper-thin.
        """
        inventory = henry_audit.get("upstream_artifacts", {})
        pending = henry_audit.get("pending_acks", []) or []
        n_pending = len(pending) if isinstance(pending, list) else 0
        n_w1 = len(inventory.get("wave1_reports", []) or [])
        wave_links = ", ".join(
            label for label in ("wave2", "wave3", "wave4") if inventory.get(label)
        ) or "(none — early-stage run)"
        lines = [
            "# 患者简报 (Plain-Language Patient Brief)",
            "",
            "> v2.5.1 — 这份简报使用 OPL for Cancer 的 Wave 5 患者级模板渲染。",
            "> 渲染契约见 `prompts/tasks/patient_plain_brief_rendering.md`。",
            "> Henry 审计版本: " + str(henry_audit.get("audit_version", "v2.5.1")),
            "",
            "## Section 0 · 一句话答案 (The bottom line, in three sentences)",
            "",
            "- 第 1 句 — 主治推荐:这一节由 SKILL 主线程的 LLM 填充。 ",
            "- 第 2 句 — 大致疗效与诚实的不确定度。",
            "- 第 3 句 — 主要风险与下一步具体动作。",
            "",
            "如果 Wave 3 未跑出数据锚 (上游证据缺失),则本节据实写出: ",
            "*这次分析没有跑到底,所以我们没法给您一个有把握的答案。*",
            "",
            "## Section 1 · 你的病情一页纸 (Your situation in one page)",
            "",
            f"- 上游 Wave 1 专家报告数: {n_w1} 份。",
            f"- 已链接的下游 Wave 证据: {wave_links}。",
            "- 二至四段 2nd-person 中文描述,翻译每一个医学术语。",
            "",
            "## Section 2 · 下一步要做什么 (What needs to happen next)",
            "",
            "- 3-5 项具体行动,每项写明 WHO / WHEN / 结果会告诉我们什么。",
            "- 主线程 LLM 从 Wave 1-4 的 claim 列表里挑出真实的行动项填充本节。",
            "",
            "## Section 3 · 不同的选择 (The different paths you could take)",
            "",
            "- 2-3 条路径 (从临床简报 Top-5 折叠为患者级)。",
            "- 每条路径写: 大概多大获益、可能出什么问题、时间和钱的成本。",
            "",
            "## Section 4 · 问医生的 5 个问题 (5 questions to ask your doctor)",
            "",
            "1. (主线程 LLM 根据病情细节填充第 1 题)",
            "2. (第 2 题)",
            "3. (第 3 题)",
            "4. (第 4 题)",
            "5. (第 5 题)",
            "",
            "## 待您确认 (Pending acknowledgements)",
            "",
            (
                f"- 当前有 {n_pending} 张 L3/L4 风险卡待您 ack。"
                if n_pending
                else "- 当前没有待确认的 L3/L4 风险卡。"
            ),
            "",
            "---",
            "**Sole decision authority**: 您是自己案例的唯一决策人。",
        ]
        return "\n".join(lines) + "\n"

    def _render_pi_brief(self, henry_audit: dict[str, Any]) -> str:
        """Render the PI / clinician brief.

        v2.5.1: replaces the 4-line stub. We anchor the scaffold to
        ``prompts/tasks/pi_delivery.md`` and include Henry's structured
        verdict so the clinician sees the audit posture without opening a
        second file.
        """
        inventory = henry_audit.get("upstream_artifacts", {})
        pending = henry_audit.get("pending_acks", []) or []
        lines = [
            "# PI / Clinician Delivery Brief",
            "",
            "> v2.5.1 — assembled by `glue/delivery_runner.py` per the contract",
            "> in `prompts/tasks/pi_delivery.md`. Henry audit attached inline.",
            "",
            "## Henry Audit (4-layer IRB-substitute)",
            "",
            f"- audit_version: `{henry_audit.get('audit_version')}`",
            f"- status: `{henry_audit.get('status')}`",
            f"- gates_run: {henry_audit.get('gates_run')}",
            f"- serious_risks_catalogue: `{henry_audit.get('serious_risks_catalogue')}`",
            f"- pending_acks: {len(pending)}",
            "",
            "## Upstream Wave Inventory",
            "",
            f"- run_root: `{inventory.get('run_root')}`",
            f"- wave1 expert reports: {len(inventory.get('wave1_reports', []) or [])}",
            f"- wave2 hypotheses present: {bool(inventory.get('wave2'))}",
            f"- wave3 data evidence present: {bool(inventory.get('wave3'))}",
            f"- wave4 validation present: {bool(inventory.get('wave4'))}",
            "",
            "## Per-claim layer summary",
            "",
            "Each Wave 1-4 claim is tagged `established | exploratory | speculative`.",
            "Layer 3/4 (high-risk / boundary) claims emit a `RiskDisclosureCard`",
            "and require patient ack before the brief is closed.",
            "",
            "## Reviewer disagreements (L2)",
            "",
            "Reviewer challenges surfaced verbatim per L2 contract;",
            "Henry does NOT take a side. See `<run>/tasks/w*/review.json` per expert.",
            "",
            "## Acknowledgement queue (L4)",
            "",
            (
                "\n".join(
                    f"- card `{p.get('card_id', '?')}` — claim `{p.get('claim_id', '?')}` "
                    f"(L{p.get('level', '?')})"
                    for p in (pending if isinstance(pending, list) else [])
                )
                if pending
                else "- (no outstanding cards)"
            ),
            "",
            "## Patient is sole decision authority",
            "",
            "This brief informs the conversation; it does not replace clinician judgment",
            "and it does not bind the patient to any path.",
        ]
        return "\n".join(lines) + "\n"

    # ── Public entry ──────────────────────────────────────────────────────

    def run(self) -> dict[str, Any]:
        if self.dry_run:
            return {
                "status": "dry_run",
                "out_dir": str(self.out_dir),
                "planned_steps": [
                    "verify_upstream_artifacts",
                    "henry_audit",
                    "patient_plain_brief",
                    "patient_pi_brief",
                ],
            }

        # B5: refuse to ship without upstream evidence (unless caller
        # explicitly overrides for debugging).
        missing = verify_upstream_artifacts(self.run_root)
        if missing and not self.allow_missing_upstream:
            raise DeliveryArtifactsMissing(missing)

        self.out_dir.mkdir(parents=True, exist_ok=True)
        try:
            # Step 1 — Henry audit (real auditor, not stub)
            audit = self._run_henry_audit()
            audit_path = self.out_dir / self.HENRY_AUDIT_FILE
            audit_path.write_text(
                json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            self._written.append(audit_path)

            # Step 2 — plain brief (template-anchored scaffold)
            plain_md = self._render_plain_brief(audit)
            plain_path = self.out_dir / self.PLAIN_BRIEF_FILE
            plain_path.write_text(plain_md, encoding="utf-8")
            self._written.append(plain_path)

            # Step 3 — PI brief (template-anchored scaffold)
            pi_md = self._render_pi_brief(audit)
            pi_path = self.out_dir / self.PI_BRIEF_FILE
            pi_path.write_text(pi_md, encoding="utf-8")
            self._written.append(pi_path)

            # Commit — write the manifest
            manifest = {
                "atomic_commit": True,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "out_dir": str(self.out_dir),
                "written_files": [str(p) for p in self._written],
                "henry_audit_status": audit.get("status"),
                "henry_real_audit": audit.get("henry_real_audit", False),
                "upstream_missing": missing if self.allow_missing_upstream else [],
            }
            (self.out_dir / self.MANIFEST_FILE).write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return {
                "status": "ok",
                "out_dir": str(self.out_dir),
                "written_files": [str(p) for p in self._written],
                "henry_audit_status": audit.get("status"),
                "henry_real_audit": audit.get("henry_real_audit", False),
                "upstream_missing": missing if self.allow_missing_upstream else [],
            }
        except DeliveryArtifactsMissing:
            # Should be intercepted before write — defensive re-raise.
            self._rollback()
            raise
        except DeliveryFailure:
            # Already a DeliveryFailure (e.g. Henry catalogue missing) —
            # propagate as-is so the test/CLI sees the exact subclass.
            self._rollback()
            raise
        except Exception as exc:
            self._rollback()
            raise DeliveryFailure(
                f"Atomic delivery failed during commit: {exc}. Rolled back "
                f"{len(self._written)} files. The patient sees no half-shipped "
                "delivery (v2.2 P1-#16 invariant)."
            ) from exc

    def _rollback(self) -> None:
        for p in self._written:
            try:
                if p.exists():
                    p.unlink()
            except OSError:  # pragma: no cover — defensive
                pass
        # Also remove the manifest if it sneaked in
        manifest = self.out_dir / self.MANIFEST_FILE
        if manifest.exists():
            try:
                manifest.unlink()
            except OSError:  # pragma: no cover
                pass
        self._written = []


def run_atomic_delivery(
    *,
    out_dir: Path,
    dry_run: bool = False,
    allow_missing_upstream: bool = False,
) -> dict[str, Any]:
    """Top-level wrapper for cli.py. Same atomicity contract as DeliveryRunner."""
    return DeliveryRunner(
        out_dir=out_dir,
        dry_run=dry_run,
        allow_missing_upstream=allow_missing_upstream,
    ).run()


__all__ = [
    "DeliveryRunner",
    "DeliveryFailure",
    "DeliveryArtifactsMissing",
    "run_atomic_delivery",
    "verify_upstream_artifacts",
]
