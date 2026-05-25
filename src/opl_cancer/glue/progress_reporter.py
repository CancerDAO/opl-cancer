"""ProgressReporter — plain-language stage + heartbeat emitter. v1.5.1.

A run can take 30-90 minutes. Without a periodic plain-language
status update the patient + family stare at a frozen screen and start
to doubt whether anything is happening (retro feedback 2026-05-25).

This helper:

  * Tracks the 5 canonical stages (准备 / 想办法 / 查数据 / 审核 / 写报告)
  * Emits a stage-start message at every stage transition
  * Emits a heartbeat message every ``heartbeat_interval_s`` seconds
    (default 60s) during a long stage
  * Computes ETA ranges from a baked-in default + (optionally) a
    persisted history file ``triggers/_history/wave_timings.json``
  * Appends every emitted message to ``progress.jsonl`` for audit
  * Provides a callback (``on_emit``) so the orchestrator (Skill prompt
    layer, or the wave1_runner / wave3_runner Python code) can route
    the user-facing string to the chat surface

Contract document: ``prompts/tasks/progress_message_rendering.md``.

The Python runners (Wave1Runner / Wave3Runner) accept an optional
``reporter`` argument. When None (default, back-compat with v1.5), no
heartbeats fire — the orchestrator at the prompt level must emit
them. When provided, the runner calls ``reporter.start_stage(...)``
+ ``reporter.heartbeat(...)`` + ``reporter.end_stage(...)`` at the
relevant points.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable


# Canonical 5-stage labels — never use Wave 1..5 in user-facing text.
STAGE_LABELS: dict[int, dict[str, str]] = {
    1: {"zh": "准备", "en": "Getting ready"},
    2: {"zh": "想办法", "en": "Brainstorming"},
    3: {"zh": "查数据", "en": "Cross-checking"},
    4: {"zh": "审核", "en": "Double-checking"},
    5: {"zh": "写报告", "en": "Writing up"},
}

# Default ETA ranges (minutes). Calibrated from the PT-EXAMPLE-A run +
# the synthetic golden set. Override per-stage via the history file.
_DEFAULT_ETA_MIN: dict[int, tuple[int, int]] = {
    1: (5, 8),
    2: (8, 15),
    3: (5, 12),
    4: (3, 6),
    5: (2, 4),
}

# Heartbeat cadence. Patients should not wait more than this long
# without a visible update.
DEFAULT_HEARTBEAT_INTERVAL_S = 60.0

# Internal-jargon ban list — anything in this set is replaced with the
# lay translation when present in `internal_detail`-derived user text.
# The orchestrator should not be feeding internal codes to the chat,
# but this is the belt-and-suspenders layer.
_JARGON_BAN: tuple[str, ...] = (
    "Wave 1", "Wave 2", "Wave 3", "Wave 4", "Wave 5",
    "hypothesis tournament", "Elo tournament", "Elo rating",
    "meta-analysis", "I² heterogeneity", "I²=",
    "ctDNA", "log2FC", "log2fc", "subgroup_match_fraction",
    "retrieval", "integrator", "rate-limit",
    "G7", "G13", "G14", "G17", "G25", "G26", "G27",
    "RC-001", "RC-NEW-",
    "H01", "H02", "H03", "H04", "H05",
    "VAF",
)


@dataclass
class ProgressEvent:
    ts: str
    stage: int
    stage_label_zh: str
    stage_label_en: str
    phase: str  # start | heartbeat | end | delay | block
    user_message: str
    internal_detail: str
    eta_min: tuple[int, int]
    elapsed_s: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "stage": self.stage,
            "stage_label_zh": self.stage_label_zh,
            "stage_label_en": self.stage_label_en,
            "phase": self.phase,
            "user_message": self.user_message,
            "internal_detail": self.internal_detail,
            "eta_min": list(self.eta_min),
            "elapsed_s": self.elapsed_s,
        }


@dataclass
class ProgressReporter:
    """Stage + heartbeat emitter.

    Args:
        log_path: where to append the JSONL audit trail. If None, no
            persistence — useful for unit tests.
        on_emit: optional callback that receives the user-facing
            string. The orchestrator wires this to the chat surface.
        language: "zh" / "en" / "bilingual". Defaults to bilingual so
            both labels are always shown.
        heartbeat_interval_s: how often to surface a heartbeat during
            a long stage (default 60s).
        eta_overrides: per-stage ETA ranges overriding the default.
    """

    log_path: Path | None = None
    on_emit: Callable[[str], None] | None = None
    language: str = "bilingual"
    heartbeat_interval_s: float = DEFAULT_HEARTBEAT_INTERVAL_S
    eta_overrides: dict[int, tuple[int, int]] = field(default_factory=dict)

    _stage_start_ts: dict[int, float] = field(default_factory=dict, init=False)
    _last_emit_ts: dict[int, float] = field(default_factory=dict, init=False)
    _events: list[ProgressEvent] = field(default_factory=list, init=False)

    def eta_for(self, stage: int) -> tuple[int, int]:
        return self.eta_overrides.get(stage, _DEFAULT_ETA_MIN.get(stage, (1, 5)))

    def _label_block(self, stage: int) -> str:
        zh = STAGE_LABELS[stage]["zh"]
        en = STAGE_LABELS[stage]["en"]
        if self.language == "zh":
            return f"[{stage}/5 {zh}]"
        if self.language == "en":
            return f"[{stage}/5 {en}]"
        return f"[{stage}/5 {zh} / {en}]"

    def _now(self) -> tuple[str, float]:
        t = time.monotonic()
        iso = datetime.now(timezone.utc).isoformat()
        return iso, t

    def _emit(self, event: ProgressEvent) -> ProgressEvent:
        self._events.append(event)
        self._last_emit_ts[event.stage] = time.monotonic()
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        if self.on_emit:
            self.on_emit(event.user_message)
        return event

    def _scrub_jargon(self, text: str) -> str:
        """Trip-wire: if banned jargon appears in `text`, prepend a
        warning. The orchestrator is expected to feed lay-language
        text; this is just a safety net so leaks are visible."""
        leaks = [j for j in _JARGON_BAN if j.lower() in text.lower()]
        if leaks:
            sample = ", ".join(leaks[:3])
            return f"{text}  [jargon-leak:{sample}]"
        return text

    # ─── public API ─────────────────────────────────────────────

    def start_stage(
        self, stage: int, action_zh: str | None = None
    ) -> ProgressEvent:
        """Emit a stage-start message.

        ``action_zh`` is a short plain-language verb phrase, e.g.
        "整理您的病历 + 查指南 + 找匹配的临床试验". If None, uses a
        sensible default per stage.
        """
        if stage not in STAGE_LABELS:
            raise ValueError(f"unknown stage {stage}; expected 1..5")
        iso, t = self._now()
        self._stage_start_ts[stage] = t
        eta = self.eta_for(stage)
        default_action = {
            1: "整理您的病历 + 查指南 + 找匹配的临床试验",
            2: "列出 10-20 种可能的方案, 让它们互相比一比",
            3: "在公开数据库里对照您的肿瘤特征",
            4: "一条一条核对证据, 把不稳的标记出来",
            5: "同时写两份: 简单版给您 + 专业版给医生",
        }[stage]
        action = action_zh or default_action
        user_msg = (
            f"{self._label_block(stage)} 团队正在 {action}。"
            f"大概 {eta[0]}-{eta[1]} 分钟。"
        )
        user_msg = self._scrub_jargon(user_msg)
        return self._emit(
            ProgressEvent(
                ts=iso,
                stage=stage,
                stage_label_zh=STAGE_LABELS[stage]["zh"],
                stage_label_en=STAGE_LABELS[stage]["en"],
                phase="start",
                user_message=user_msg,
                internal_detail=f"action={action!r}; eta={eta}",
                eta_min=eta,
                elapsed_s=0,
            )
        )

    def heartbeat(
        self,
        stage: int,
        progress_zh: str,
        force: bool = False,
    ) -> ProgressEvent | None:
        """Emit a heartbeat during a long stage.

        Called periodically by the runner. The reporter checks whether
        ``heartbeat_interval_s`` has elapsed since the last emit for
        this stage; if not, returns None unless ``force=True``.

        ``progress_zh`` is a short plain-language description of what's
        happening right now, e.g. "在公开数据库里跑了 45/71 个查询".
        """
        if stage not in STAGE_LABELS:
            raise ValueError(f"unknown stage {stage}; expected 1..5")
        iso, t = self._now()
        last = self._last_emit_ts.get(stage, self._stage_start_ts.get(stage, t))
        if not force and (t - last) < self.heartbeat_interval_s:
            return None
        eta = self.eta_for(stage)
        elapsed_s = int(t - self._stage_start_ts.get(stage, t))
        elapsed_min = elapsed_s / 60.0
        remaining_low = max(0, int(eta[0] - elapsed_min))
        remaining_high = max(remaining_low, int(eta[1] - elapsed_min))
        if remaining_high == 0:
            remaining_high = 1
        user_msg = (
            f"{self._label_block(stage)} 还在 {progress_zh}。"
            f"预计还需要 {remaining_low}-{remaining_high} 分钟。"
        )
        user_msg = self._scrub_jargon(user_msg)
        return self._emit(
            ProgressEvent(
                ts=iso,
                stage=stage,
                stage_label_zh=STAGE_LABELS[stage]["zh"],
                stage_label_en=STAGE_LABELS[stage]["en"],
                phase="heartbeat",
                user_message=user_msg,
                internal_detail=progress_zh,
                eta_min=eta,
                elapsed_s=elapsed_s,
            )
        )

    def end_stage(
        self,
        stage: int,
        summary_zh: str,
        next_stage_preview_zh: str | None = None,
    ) -> ProgressEvent:
        """Emit a stage-end message.

        ``summary_zh`` is a one-sentence plain-language summary of what
        was found. ``next_stage_preview_zh`` is an optional hint of
        what the next stage will do; for stage 5 (final), this can be
        None or "完成 — 报告已生成".
        """
        if stage not in STAGE_LABELS:
            raise ValueError(f"unknown stage {stage}; expected 1..5")
        iso, t = self._now()
        elapsed_s = int(t - self._stage_start_ts.get(stage, t))
        eta = self.eta_for(stage)
        next_block = ""
        if next_stage_preview_zh:
            next_block = f" 下一步: {next_stage_preview_zh}。"
        user_msg = (
            f"{self._label_block(stage)} ✓ {summary_zh}.{next_block}"
        )
        user_msg = self._scrub_jargon(user_msg)
        return self._emit(
            ProgressEvent(
                ts=iso,
                stage=stage,
                stage_label_zh=STAGE_LABELS[stage]["zh"],
                stage_label_en=STAGE_LABELS[stage]["en"],
                phase="end",
                user_message=user_msg,
                internal_detail=f"summary={summary_zh!r}; elapsed_s={elapsed_s}",
                eta_min=eta,
                elapsed_s=elapsed_s,
            )
        )

    def delay(
        self,
        stage: int,
        reason_zh: str,
        new_eta_min: int,
    ) -> ProgressEvent:
        """Emit a delay message when a stage is taking >2× its
        original ETA. Offer a skip / simplify option in the prompt.
        """
        iso, t = self._now()
        elapsed_s = int(t - self._stage_start_ts.get(stage, t))
        user_msg = (
            f"{self._label_block(stage)} 这一阶段比平时慢, 原因是 "
            f"{reason_zh}。还需要大约 {new_eta_min} 分钟。"
            "如果不想等, 您可以告诉我跳过或简化这一步。"
        )
        user_msg = self._scrub_jargon(user_msg)
        return self._emit(
            ProgressEvent(
                ts=iso,
                stage=stage,
                stage_label_zh=STAGE_LABELS[stage]["zh"],
                stage_label_en=STAGE_LABELS[stage]["en"],
                phase="delay",
                user_message=user_msg,
                internal_detail=reason_zh,
                eta_min=(new_eta_min, new_eta_min),
                elapsed_s=elapsed_s,
            )
        )

    def block(
        self,
        stage: int,
        reason_zh: str,
        options_zh: list[str],
    ) -> ProgressEvent:
        """Emit a hard-blocker message. Requires user choice.
        ``options_zh`` is a list of plain-language options.
        """
        iso, t = self._now()
        elapsed_s = int(t - self._stage_start_ts.get(stage, t))
        opts_block = ""
        for i, opt in enumerate(options_zh, start=1):
            opts_block += f"\n  ({chr(96 + i)}) {opt}"
        user_msg = (
            f"{self._label_block(stage)} 暂停 — {reason_zh}。"
            f"\n请您选: {opts_block}"
        )
        user_msg = self._scrub_jargon(user_msg)
        return self._emit(
            ProgressEvent(
                ts=iso,
                stage=stage,
                stage_label_zh=STAGE_LABELS[stage]["zh"],
                stage_label_en=STAGE_LABELS[stage]["en"],
                phase="block",
                user_message=user_msg,
                internal_detail=f"reason={reason_zh!r}; options={options_zh}",
                eta_min=(0, 0),
                elapsed_s=elapsed_s,
            )
        )

    # ─── audit / test helpers ────────────────────────────────────

    def events(self) -> Iterable[ProgressEvent]:
        return list(self._events)

    def messages(self) -> list[str]:
        return [e.user_message for e in self._events]
