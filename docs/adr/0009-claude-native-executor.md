# ADR-0009: Claude-native executor (token from CC subscription, no ANTHROPIC_API_KEY)

**Date**: 2026-05-25

## Status

Accepted (v1.4.1 partial fix; v1.5 full architectural rewrite).

## Context

v1.4.0 preflight 强制 `ANTHROPIC_API_KEY OR MINIMAX_API_KEY`,把主 executor LLM call 走 `src/opl_cancer/llm/anthropic_client.py` 直接 HTTP 到 api.anthropic.com。用户已经付 Claude Code subscription(主线程 Opus 4.7),却被要求再付一份 Anthropic API。违反 PRD §0 telos "让全世界每一个人" — paywall 不该卡在 OPL 入口。

一个 CancerDAO 姊妹工具 v4.0 用 claude-native 模式("All LLM tokens come from the user's Claude Code subscription"),OPL 应对齐。

## Decision

**Main executor 走 Claude Code 主线程**(token 从 user CC subscription 出);**Reviewer pool 用外部 non-Anthropic API key**(G13 cross-model 强制,reviewer ≠ Anthropic,所以 MiniMax / GPT-5 / Gemini)。

## v1.4.1(本次 partial fix,2026-05-25)

- `cli.py preflight`:不再 hard-fail on missing `ANTHROPIC_API_KEY`;改 warn-only on missing reviewer-pool key
- `SKILL.md` Step 0:文档化 Claude-native paradigm — 主 executor = CC 主线程,reviewer = 外部 model
- `.env.example`:ANTHROPIC_API_KEY 标 optional(只用于 out-of-band Python CLI runs);MINIMAX/OPENAI/GEMINI 任一作为 reviewer 推荐
- Python wave runners(`src/opl_cancer/glue/wave{1,2,3,4}_runner.py` + `llm/anthropic_client.py`)**保留不变** — 它们走 standalone HTTP,适合 CI / batch / 第三方 reproduce。但 SKILL.md-driven 的 patient 触发路径**不依赖**这些 — 主线程 Claude 接管 Wave 编排。

## v1.5 full rewrite(待 fresh session)

- 改造 `src/opl_cancer/glue/wave1_runner.py` 等:把 Python-driven LLM call 路径标记为 `--backend=python-http`(可选,for batch / reproduce);默认 `--backend=claude-native` 让 wave 编排走 SKILL.md + Agent(subagent_type=...) dispatch
- 18 expert × task package portfolio:每个 expert 作为 forked subagent spec(`agents/opl-<expert>.md`)注册到 `~/.claude/agents/`,SKILL.md 用 Agent 工具派发
- `cli.py wave1/wave2/...` subcommand 改成 "prepare run_dir + dump plan,**不调 LLM**";真 LLM call 在 SKILL.md 上下文里由主线程 Claude 完成
- `models.yaml` executor_model 标 `provider: "claude-code-main-thread"`,API base 标 `null`(不发起 HTTP)
- Reviewer client 路径不变(MiniMax/GPT/Gemini 通过 HTTP)
- Migration guide:旧 `Wave1Runner.run()` 入口标 deprecated,但保留 6 个月给 batch / CI 用户

## Consequences

- (+) 用户**不再需要 Anthropic API key** — 跟 CancerDAO 其它姊妹工具对齐
- (+) 真 patient 触发路径**只付 CC subscription**(~$1-3 per Wave run)+ 选一个便宜 reviewer key(MiniMax 几乎免费,GPT 按量,Gemini 按量)
- (+) 北极星 "让全世界每一个人" 不被 paywall 卡住 — 学生 / 罕见癌种 / 跨境就医患者更易触达
- (+) G13 cross-model reviewer 真实可信(executor 是 Anthropic main thread,reviewer 必定是 non-Anthropic)
- (−) v1.4.1 仍是 partial:Python wave runner 路径 fallback 时还得 ANTHROPIC_API_KEY;真正的 claude-native rewrite(全 SKILL.md-driven Wave 编排)留 v1.5
- (−) v1.5 重写工作量预估 30-60 文件 surgery(wave runners + glue + dispatch + agent specs);需 fresh session 做

## Related

- PRD §0 telos
- ADR-0002 main-thread-only dispatch
- ADR-0008 round-2 v1.3.2 deferred backlog(D11/D12 也归到 v1.5)
- A CancerDAO internal predecessor v4.0 claude-native precedent
