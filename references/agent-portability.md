# Agent portability — running OPL on Claude Code, Codex, Cursor, OpenCode, …

> **Superseded/extended by v2 — see [`v2-paradigm.md`](v2-paradigm.md).** Counts in this doc are already v2-current (20 experts, 42 gates G1–G43 with G38 reserved, 29 integrator modules); the portability contract itself is unchanged by the v2 paradigm shift.

OPL for Cancer is an **agent-agnostic skill**: it installs via
`npx skills add CancerDAO/opl-cancer-skill` into whatever agent(s) the
[vercel-labs/skills](https://github.com/vercel-labs/skills) CLI detects. This doc
is the contract that makes the SKILL.md run identically across hosts. It exists
because v2.6.0 and earlier hardcoded Claude-Code assumptions (`~/.claude` paths,
"executor is Anthropic, no key"); v2.6.1 removes them.

## 1. The skill directory is NOT `~/.claude`

`npx skills add` installs into **each detected agent's own skill dir**, e.g.:

| Agent | Typical install dir |
|---|---|
| Claude Code | `~/.claude/skills/opl-cancer/` (global) or `./.claude/skills/opl-cancer/` (project) |
| Codex | `~/.codex/skills/opl-cancer/` (or AGENTS.md-discovered) |
| Cursor | `./.cursor/skills/opl-cancer/` |
| OpenCode | the OpenCode skill dir |
| 30+ others | `<agent>/skills/opl-cancer/` |

**Never hardcode `~/.claude`.** In SKILL.md, `<skill_dir>` = the directory that
contains `SKILL.md` itself (resolve it from your agent's skill path). All harness
commands are invoked through the **`opl-cancer` console entry point**, which after
the one-time `pip install -e "<skill_dir>"` is on `PATH` and is therefore
independent of which agent dir the skill lives in.

## 2. One-time bootstrap (any agent / OS)

```bash
pip install -e "<skill_dir>"     # installs the harness + the `opl-cancer` command
opl-cancer preflight --json      # path-free from here on
```

`scripts/cli.py` is a fallback shim: `python "<skill_dir>/scripts/cli.py" <cmd>`
puts `src/` on `sys.path`, and on missing runtime deps it attempts one
`pip install -e <skill_dir>` then prints the exact command (exit 3) — it never
emits a raw `ModuleNotFoundError` traceback (v2.6.1 first-run fix).

## 3. Executor + reviewer LLM contract (host-aware)

The 5-Wave reasoning (Sid + the 20 experts + Henry's prose) runs on the **host
agent's own LLM** — OPL does not bundle a model.

- **Claude Code**: executor = main-thread Opus (CC subscription, no `ANTHROPIC_API_KEY`).
- **Codex / Cursor / OpenCode / other**: executor = *that host's* model (GPT / Gemini / …).
  Set `OPL_EXECUTOR_PROVIDER` ∈ `{anthropic, openai, google, minimax}` so preflight
  and gate **G13** know the true executor family.

**G13 (reviewer ≠ executor)** must be computed against the *actual* executor
family, not a hardcoded "Anthropic" constant. Provide a reviewer key whose family
differs from the executor (`MINIMAX_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY`
/ `ANTHROPIC_API_KEY`). For a patient-facing run, preflight should **fail closed**
if it cannot prove `reviewer_family ≠ executor_family`.

## 4. Tool-name mapping (CC names → host primitives)

SKILL.md uses Claude Code tool names by convention. Non-CC agents map them:

| SKILL.md term (CC) | Codex / Cursor / OpenCode equivalent |
|---|---|
| `Write` tool | host file-write tool, or `Bash` heredoc (`cat > file <<'EOF' … EOF`) — see `prompts/safety/subagent_file_write_contract.md` |
| `Bash` tool | host shell/exec tool |
| "fork a subagent" / main-thread dispatch | host's sub-agent / task primitive; if none, run the task package inline on the main thread |
| "main-thread orchestrator" | the host agent's own loop reading SKILL.md |

If the host lacks sub-agent dispatch, expert task packages run **sequentially on
the main thread** — slower but functionally equivalent; no behavior is CC-exclusive.

## 5. What is genuinely portable vs host-specific

- **Portable**: the Python harness (`opl-cancer` CLI — plan / waves state / deliver /
  finalize / audit), all gates, integrators, schemas, prompts, the delivery contract.
- **Host-specific**: which LLM is the executor, sub-agent dispatch, tool names —
  all covered by §3–§4 above.

> Canonical reconciliation: where `references/architecture.md` says experts speak
> "via an ordinary LLM API call" and SKILL.md says "on the main thread, no key",
> **this document is authoritative**: on Claude Code it is the main thread (no key);
> on other hosts it is that host's model (set `OPL_EXECUTOR_PROVIDER`).
