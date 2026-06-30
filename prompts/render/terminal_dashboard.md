# OPL Terminal Progress Dashboard — shared template + specialisation contract

The single source of truth for the run-console progress box that the host agent
prints throughout a long OPL run. SKILL.md "## 输出格式（终端）" points here;
every expert / task-package specialises ONLY the `current_detail` line.

## The frame is deterministic — render it, don't draw it

```python
from opl_cancer.glue.progress_dashboard import render, phase_index
print(render(
    run_id=run_id,
    phase_idx=phase_index("Wave1 查证据"),   # 0-based; see PHASES
    current_detail="Bert(遗传) 解读 NGS — 3/20 专家完成",
    last_detail="Vince(肿瘤) 下一线方案分析",
    eta="~12–18 min",
))
```

`render()` owns: the progress bar, the `i/9` counter, and the phase chips
(✓ done · ▶ current · ○ pending) over the 9 canonical phases in `PHASES`
(整理 · 就绪 · 规划 · Wave1 查证据 · Wave2 假设 · Wave3 数据 · Wave4 验证 ·
审核 · 交付). Never hand-draw the box or recount progress — the harness is the
single source so the frame never drifts (numbers = script, ADR-0041).

## When to print it (MANDATORY cadence)

1. **Phase start** — at the first beat of each of the 9 phases.
2. **Heartbeat** — at least every 60s during a long phase (refresh `current_detail`
   + ETA; keep the frame identical so it reads as an in-place update).
3. **Phase complete** — once, moving the ▶ to the next phase and the just-finished
   step into `刚完成 / done`.

## The ONE line each sub-skill specialises: `current_detail`

Format: `<专家名>(<角色>) <正在做什么> — <进度计数 if any>`. Lay language only —
NO `Wave/hypothesis tournament/Henry/Gxx/Elo/token/wall-time` in this line (the
Wave tags in the chips are the run-console view and are allowed; this line is the
human-readable detail). Per-expert examples:

| phase | expert / package | `current_detail` example |
|---|---|---|
| Wave1 查证据 | bert (遗传) | `Bert(遗传) 解读 NGS 驱动突变 — 3/20 专家完成` |
| Wave1 查证据 | rosa (病理) | `Rosa(病理) 复核 IHC + 分期 — 5/20 专家完成` |
| Wave1 查证据 | vince (肿瘤) | `Vince(肿瘤) 梳理下一线方案 — 8/20 专家完成` |
| Wave1 查证据 | rick (试验) | `Rick(试验) 匹配可入组临床试验 — 11/20` |
| Wave2 假设 | co-sci 生成 | `生成候选研究方向 + 内部打分 — 第 2 轮` |
| Wave3 数据 | aviv (生信) | `Aviv(生信) 在公开数据库对照肿瘤特征 — 45/71 查询` |
| Wave4 验证 | tyler / aviv | `用实测数据验证假设 — 6/9 个有结论` |
| 审核 | henry | `Henry 逐条核对证据 + 安全红线` |
| 交付 | sid | `Sid 把结论翻成大白话、组织交付包` |

ETA is always a **range**, never a single number. If a phase is skip-able and
skipped, show it as ✓ with a `当前` note ("本例无需此步") rather than hiding it.

## Boundary

This template renders progress only — it never decides gate verdicts, never
edits a claim, never invents a count. The counts come from the harness
(`observe` / artifact state); the prose detail comes from the active expert.
