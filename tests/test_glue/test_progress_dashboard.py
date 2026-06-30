"""Terminal progress dashboard — deterministic frame."""
from __future__ import annotations

from opl_cancer.glue.progress_dashboard import (
    N_PHASES,
    PHASES,
    phase_index,
    render,
)


def test_phase_index_resolves_by_label_and_substring() -> None:
    assert phase_index("整理") == 0
    assert phase_index("Wave1 查证据") == 3
    assert phase_index("wave1") == 3       # substring, case-insensitive
    assert phase_index("交付") == N_PHASES - 1
    assert phase_index("nope") == -1


def test_render_marks_done_current_pending() -> None:
    out = render(run_id="run-x", phase_idx=3,
                 current_detail="Bert 解读 NGS — 3/20", last_detail="Vince 完成", eta="~12–18 min")
    assert "✓整理" in out and "✓就绪" in out and "✓规划" in out  # before = ✓
    assert "▶Wave1 查证据" in out                                 # current = ▶
    assert "○Wave2 假设" in out and "○交付" in out               # after = ○
    assert "4/9" in out                                          # 0-based idx 3 → 4/9
    assert "Bert 解读 NGS — 3/20" in out
    assert "Vince 完成" in out
    assert "~12–18 min" in out


def test_bar_progresses_with_phase() -> None:
    early = render(run_id="r", phase_idx=0)
    late = render(run_id="r", phase_idx=8)
    assert early.count("█") < late.count("█")


def test_final_phase_renders_full_bar() -> None:
    out = render(run_id="r", phase_idx=N_PHASES)  # past last → complete
    assert "░" not in out.splitlines()[1]  # bar line fully filled
    assert f"{N_PHASES}/{N_PHASES}" in out


def test_optional_detail_lines_omitted_when_empty() -> None:
    out = render(run_id="r", phase_idx=2)
    assert "当前" not in out and "刚完成" not in out


def test_phases_are_nine() -> None:
    assert N_PHASES == 9 == len(PHASES)
