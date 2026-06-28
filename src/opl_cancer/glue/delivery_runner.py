"""v2.2 P1-#16 — atomic Henry audit + dual brief delivery.

CLI wiring: ``cli.py deliver`` invokes this module's ``run_atomic_delivery`` to
write the patient-delivery package as ONE all-or-nothing transaction (Henry
audit → plain brief → PI brief, with rollback on any failure). This is the
*delivery transaction*; the sibling ``delivery_gate_runner.py`` is the separate
*gate-sweep wiring* that fires the G34-G43 delivery-integrity / reasoning-quality
gates over an (already-written) package.

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

from opl_cancer.glue.ledger_persist import persist_run_to_ledger
from opl_cancer.validators.fakery_sniffer import scan_text
from opl_cancer.validators.henry import HenryAuditError, HenryAuditor
from opl_cancer.validators.permission_levels import Level


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
    # v2.6.0 B5-semantic: existence is not evidence. A hollow run (empty `{}`
    # plan, empty hypothesis/analysis/validation arrays, trivial wave-1 report)
    # must be refused — the README promise is "refuses to ship when upstream
    # waves haven't produced REAL evidence", not "when files are absent".
    if not missing:
        missing.extend(_hollow_upstream(run_root))
    return missing


# Wave file → the top-level array key whose non-emptiness signals real content.
_WAVE_CONTENT_KEYS: dict[str, tuple[str, ...]] = {
    "wave2_hypotheses.json": ("hypotheses", "top_k"),
    "wave3_data_evidence.json": ("analysis_runs", "validations", "results"),
    "wave4_validation.json": ("validations", "verdicts"),
}


def _hollow_upstream(run_root: Path) -> list[str]:
    """Detect upstream artifacts that exist but carry no real evidence."""
    hollow: list[str] = []
    # plan.json must be a non-empty object with at least a goal or tasks/dag.
    plan_p = run_root / "plan.json"
    try:
        plan = json.loads(plan_p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        plan = None
    if not isinstance(plan, dict) or not any(
        plan.get(k) for k in ("goal", "tasks", "method_dag", "waves")
    ):
        hollow.append(f"plan hollow: {plan_p} has no goal/tasks/method_dag/waves content")

    # wave-1 reports must carry more than a bare header.
    reports = list(run_root.glob("tasks/w1_*/report.md"))
    if reports and all(
        len(_strip_md(r.read_text(encoding="utf-8"))) < 30 for r in reports
    ):
        hollow.append("wave1 hollow: every w1 report.md is a trivial/empty stub")

    # at least one present wave2/3/4 file must have a non-empty content array.
    present = [(n, run_root / n) for n in _WAVE_CONTENT_KEYS if (run_root / n).exists()]
    if present and not any(_has_content(p, _WAVE_CONTENT_KEYS[n]) for n, p in present):
        hollow.append(
            "wave2/3/4 hollow: present wave files carry only empty arrays "
            "(no hypotheses / analysis_runs / validations)"
        )
    return hollow


def _strip_md(text: str) -> str:
    return "".join(
        ln.strip() for ln in text.splitlines() if not ln.lstrip().startswith("#")
    ).strip()


def _has_content(path: Path, keys: tuple[str, ...]) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and any(data.get(k) for k in keys)


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
        finalize: bool = False,
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
        # v2.6.0: finalize=False renders the honest scaffold (the patient-facing
        # prose is owned by the SKILL main thread per ADR-2026-04-22). finalize=True
        # audits the *already-filled* briefs: it never renders, requires a
        # placeholder-clean brief, and runs the REAL Henry audit over the
        # LLM-produced claims manifest.
        self.finalize = bool(finalize)
        self._written: list[Path] = []

    # ── Stage hooks (override-friendly for tests) ────────────────────────

    def _build_auditor(self) -> HenryAuditor:
        outstanding_dir = self.out_dir / "outstanding"
        outstanding_dir.mkdir(parents=True, exist_ok=True)
        try:
            return HenryAuditor(
                serious_risks_path=self.serious_risks_path,
                outstanding_dir=outstanding_dir,
            )
        except HenryAuditError as exc:
            raise DeliveryFailure(
                f"Henry audit cannot start — {exc}. The contract forbids "
                "falling back to a hardcoded 'pass' (B1 / ADR-0021)."
            ) from exc

    def _scaffold_audit(self, placeholder_findings: list[dict[str, Any]]) -> dict[str, Any]:
        """v2.6.0: HONEST audit record for the scaffold (pre-fill) path.

        The patient-facing prose has not been written yet (the SKILL main
        thread owns it). We construct the auditor so a missing catalogue still
        fails loud, but we do NOT claim a real per-claim audit ran — because it
        did not. ``henry_real_audit`` is False and ``status`` advertises the
        brief is pending fill. The placeholder language the (CJK-aware) sniffer
        found is surfaced so nothing downstream mistakes the scaffold for a
        finished, audited brief (ADR-0021 Invariant 3 + discipline rule #1).
        """
        self._build_auditor()  # fail-loud on missing catalogue
        return {
            "audit_version": "v2.6.0",
            "opl_version": "2.6.0",
            "status": "scaffold_pending_fill",
            "henry_real_audit": False,
            "brief_complete": False,
            "claims_audited": 0,
            "gates_run": 0,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "serious_risks_catalogue": str(self.serious_risks_path),
            "pending_acks": [],
            "placeholder_findings": placeholder_findings,
            "upstream_artifacts": self._upstream_inventory(),
            "notes": [
                "v2.6.0: scaffold emitted; patient-facing prose is filled by the "
                "SKILL main thread, then `opl deliver --finalize` runs the REAL "
                "Henry audit (audit_claim) over the LLM-produced claims manifest.",
                "henry_real_audit is intentionally False here — no claim was audited.",
            ],
        }

    def _finalize_audit(self) -> dict[str, Any]:
        """v2.6.0: REAL Henry audit over the LLM-produced claims manifest.

        Runs ``HenryAuditor.audit_claim`` for every structured claim in
        ``<run_root>/claims.json`` (or ``<out_dir>/claims.json``). The runner
        stays *mechanical* — it never parses drugs/levels out of free text
        (that is LLM judgment, owned by the LLM/expert layer, not the runner). It
        consumes the claims the expert/main-thread layer already produced and
        runs the deterministic catalogue lookup + risk-card + ack loop.
        """
        auditor = self._build_auditor()
        claims = self._load_claims_manifest()
        layer3: list[str] = []
        audited = 0
        for c in claims:
            try:
                level = Level(int(c.get("level", 0)))
            except (ValueError, TypeError):
                level = Level.L0_INFORMATION
            res = auditor.audit_claim(
                claim_id=str(c.get("claim_id", f"claim-{audited}")),
                claim_text=str(c.get("claim_text", "")),
                level=level,
                drugs_mentioned=list(c.get("drugs_mentioned", []) or []),
                reviewer_challenges=list(c.get("reviewer_challenges", []) or []),
                epistemic_gaps=list(c.get("epistemic_gaps", []) or []),
                alternatives=list(c.get("alternatives", []) or []),
            )
            layer3.extend(res.layer3_serious_risks)
            audited += 1
        pending = auditor.list_pending()
        return {
            "audit_version": "v2.6.0",
            "opl_version": "2.6.0",
            "status": "pass" if not pending else "pending_acks",
            "henry_real_audit": True,
            "brief_complete": True,
            "claims_audited": audited,
            "gates_run": 4 if audited else 0,  # L1-L4 actually ran per claim
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "serious_risks_catalogue": str(self.serious_risks_path),
            "pending_acks": pending,
            "layer3_serious_risks": sorted(set(layer3)),
            "upstream_artifacts": self._upstream_inventory(),
            "notes": [
                "v2.6.0: real audit — HenryAuditor.audit_claim ran over the "
                f"{audited}-claim manifest; serious risks resolved from catalogue.",
            ],
        }

    def _load_claims_manifest(self) -> list[dict[str, Any]]:
        """Read the structured claims the LLM/expert layer produced.

        Looks at ``<run_root>/claims.json`` then ``<out_dir>/claims.json``.
        Absent / malformed → empty list (a real audit with zero claims is
        honestly reported as claims_audited=0; it is NOT faked into a pass)."""
        for candidate in (self.run_root / "claims.json", self.out_dir / "claims.json"):
            if candidate.exists():
                try:
                    data = json.loads(candidate.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    return []
                claims = data.get("claims", data) if isinstance(data, dict) else data
                return [c for c in claims if isinstance(c, dict)] if isinstance(claims, list) else []
        return []

    def _scan_briefs_for_placeholders(self) -> list[dict[str, Any]]:
        """Run the (CJK-aware) fakery sniffer over the two rendered briefs.

        Returns a list of {file, line, excerpt, pattern} dicts — empty means the
        briefs are placeholder-clean and safe to ship as a finished deliverable.
        """
        findings: list[dict[str, Any]] = []
        for name in (self.PLAIN_BRIEF_FILE, self.PI_BRIEF_FILE):
            p = self.out_dir / name
            if not p.exists():
                continue
            for f in scan_text(p.read_text(encoding="utf-8")):
                findings.append(
                    {
                        "file": name,
                        "line": f.line_number,
                        "excerpt": f.excerpt[:200],
                        "pattern": f.pattern,
                    }
                )
        return findings

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

    # ── Mode runners (v2.6.0) ───────────────────────────────────────────────

    def _write(self, name: str, text: str) -> Path:
        path = self.out_dir / name
        path.write_text(text, encoding="utf-8")
        self._written.append(path)
        return path

    def _commit_manifest(self, audit: dict[str, Any], missing: list[str]) -> dict[str, Any]:
        payload = {
            "status": audit.get("status"),
            "out_dir": str(self.out_dir),
            "written_files": [str(p) for p in self._written],
            "henry_audit_status": audit.get("status"),
            "henry_real_audit": audit.get("henry_real_audit", False),
            "brief_complete": audit.get("brief_complete", False),
            "claims_audited": audit.get("claims_audited", 0),
            "placeholder_findings": audit.get("placeholder_findings", []),
            "upstream_missing": missing if self.allow_missing_upstream else [],
        }
        manifest = {"atomic_commit": True, "generated_at": datetime.now(timezone.utc).isoformat(), **payload}
        (self.out_dir / self.MANIFEST_FILE).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return payload

    def _run_scaffold(self, missing: list[str]) -> dict[str, Any]:
        """Default path: render the honest scaffold, sniff it, report truthfully."""
        plain_md = self._render_plain_brief({"audit_version": "v2.6.0", "pending_acks": [], "upstream_artifacts": self._upstream_inventory()})
        self._write(self.PLAIN_BRIEF_FILE, plain_md)
        pi_md = self._render_pi_brief({"audit_version": "v2.6.0", "status": "scaffold_pending_fill", "gates_run": 0, "serious_risks_catalogue": str(self.serious_risks_path), "pending_acks": [], "upstream_artifacts": self._upstream_inventory()})
        self._write(self.PI_BRIEF_FILE, pi_md)

        placeholder_findings = self._scan_briefs_for_placeholders()
        audit = self._scaffold_audit(placeholder_findings)
        self._write(self.HENRY_AUDIT_FILE, json.dumps(audit, ensure_ascii=False, indent=2))
        return self._commit_manifest(audit, missing)

    def _run_finalize(self, missing: list[str]) -> dict[str, Any]:
        """Finalize path: audit the *already-filled* briefs. Never renders.

        Refuses (DeliveryFailure) if the briefs are absent or still contain
        placeholder language — a scaffold can never be finalized. Otherwise runs
        the REAL Henry audit over the LLM-produced claims manifest.
        """
        plain = self.out_dir / self.PLAIN_BRIEF_FILE
        pi = self.out_dir / self.PI_BRIEF_FILE
        if not plain.exists() or not pi.exists():
            raise DeliveryFailure(
                "Cannot finalize — patient_plain_brief.md / patient_pi_brief.md not "
                "found. Run `opl deliver` (scaffold) first, fill the briefs, then finalize."
            )
        placeholder_findings = self._scan_briefs_for_placeholders()
        if placeholder_findings:
            raise DeliveryFailure(
                "Cannot finalize — briefs still contain placeholder/scaffold language "
                f"({len(placeholder_findings)} hits, e.g. {placeholder_findings[0]['excerpt']!r}). "
                "The SKILL main thread must fill the scaffold before finalize (ADR-0021 Inv-3)."
            )
        audit = self._finalize_audit()
        self._write(self.HENRY_AUDIT_FILE, json.dumps(audit, ensure_ascii=False, indent=2))
        return self._commit_manifest(audit, missing)

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
            result = self._run_finalize(missing) if self.finalize else self._run_scaffold(missing)
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

        # A1 / ADR-0027 — compounding spine. Persist the run's hypotheses,
        # tournament rounds and delivered claims into the patient research
        # ledger so the next run starts warm and never re-proposes a falsified
        # direction. Best-effort here; G54 verifies at attest that it happened
        # (a silent failure leaves an empty ledger, which G54 BLOCKS on).
        try:
            result["ledger_persisted"] = persist_run_to_ledger(self.run_root)
        except Exception as exc:  # pragma: no cover — defensive; gate is the backstop
            result["ledger_persisted"] = {"error": str(exc)}
        return result

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
    finalize: bool = False,
) -> dict[str, Any]:
    """Top-level wrapper for cli.py. Same atomicity contract as DeliveryRunner."""
    return DeliveryRunner(
        out_dir=out_dir,
        dry_run=dry_run,
        allow_missing_upstream=allow_missing_upstream,
        finalize=finalize,
    ).run()


__all__ = [
    "DeliveryRunner",
    "DeliveryFailure",
    "DeliveryArtifactsMissing",
    "run_atomic_delivery",
    "verify_upstream_artifacts",
]
