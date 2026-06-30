"""Terminal progress dashboard — the OPL run-console frame (numbers = script).

OPL runs long (multi-wave, 20-expert). This renders the FIXED multi-line box the
host agent prints at each phase beat + heartbeat, so the operator always sees
where the run is, what it's doing, and the ETA. The DETERMINISTIC frame (bar,
phase chips, counts) is computed here; the one-line prose `current_detail` is
supplied by the active phase / dispatched expert (the prose = prompt boundary,
ADR-0041). Left-border-only style so CJK width never misaligns a right border.

Canonical contract used by SKILL.md "## 输出格式（终端）" + every expert /
task-package, which specialise only the `current_detail` line.
"""
from __future__ import annotations

# Canonical patient-journey phases: (short chip label, long/lay gloss).
PHASES: tuple[tuple[str, str], ...] = (
    ("整理", "整理病历 / organize records"),
    ("就绪", "就绪评估 / readiness"),
    ("规划", "规划团队 / plan the team"),
    ("Wave1 查证据", "世界已知检索 / world-known retrieval"),
    ("Wave2 假设", "假设联赛 / hypothesis tournament"),
    ("Wave3 数据", "数据证据 / data-evidence"),
    ("Wave4 验证", "假设验证 / validation"),
    ("审核", "Henry 审核 / audit"),
    ("交付", "交付报告 / deliver"),
)
N_PHASES = len(PHASES)


def phase_index(name: str) -> int:
    """Resolve a phase by its short label (or a unique substring); -1 if none."""
    n = (name or "").strip().lower()
    for i, (short, _long) in enumerate(PHASES):
        if n == short.lower() or n in short.lower() or n in _long.lower():
            return i
    return -1


def _bar(done: int, total: int, width: int = 18) -> str:
    done = max(0, min(done, total))
    filled = round(width * done / total) if total else 0
    return "█" * filled + "░" * (width - filled)


def _chips(idx: int) -> str:
    out = []
    for i, (short, _long) in enumerate(PHASES):
        mark = "✓" if i < idx else ("▶" if i == idx else "○")
        out.append(f"{mark}{short}")
    return " ".join(out)


def render(
    *,
    run_id: str,
    phase_idx: int,
    current_detail: str = "",
    last_detail: str = "",
    eta: str = "",
    title: str = "OPL for Cancer",
) -> str:
    """Render the dashboard box. ``phase_idx`` is 0-based into PHASES.

    A ``phase_idx`` past the last phase renders as fully complete.
    """
    idx = max(0, min(int(phase_idx), N_PHASES))
    done = idx  # phases fully completed before the current one
    # at/after the final phase, show the bar full
    bar_done = N_PHASES if idx >= N_PHASES else done
    pos = min(idx + 1, N_PHASES)
    eta_part = f" · ⏱ {eta}" if eta else ""
    lines = [
        f"╭─ {title} ▸ {run_id} " + "─" * 6,
        f"│ [{_bar(bar_done, N_PHASES)}] {pos}/{N_PHASES}{eta_part}",
        f"│ {_chips(min(idx, N_PHASES - 1))}",
    ]
    if current_detail:
        lines.append(f"│ ▸ 当前 / now: {current_detail}")
    if last_detail:
        lines.append(f"│ ▸ 刚完成 / done: {last_detail}")
    lines.append("╰" + "─" * 44)
    return "\n".join(lines)
