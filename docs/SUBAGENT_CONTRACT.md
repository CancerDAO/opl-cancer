# OPL Subagent File-Write Contract (v2.1)

OPL dispatches expert work to forked subagents. There are two execution paths.

## Path 1 (preferred): OPL-specific agent types

`agents/opl-experts.yml` declares 21 forked subagent types
(`opl-rosa`, …, `opl-julius`, `opl-henry`).

Each grants `Write` scoped to:

```
patients/<id>/triggers/<run_id>/tasks/**   (the 20 experts)
patients/<id>/triggers/<run_id>/audit/**   (Henry, the auditor)
```

To install:

```bash
opl preflight --install-agents
```

This copies `agents/opl-experts.yml` to `~/.claude/agents/opl-experts.yml`.
Inside the agent, the subagent writes its report directly to the canonical
path.

## Path 2 (fallback): general-purpose + inline return

If `opl-*` agent types are unavailable (Claude Code older version, or user
opted out), the main thread dispatches a `general-purpose` agent. Because
`Write` is blocked under `general-purpose`, the contract is:

1. Subagent prompt asks for the report content as a structured return value.
2. Subagent does NOT attempt to write.
3. Main thread receives the report payload, then itself writes to the
   canonical path via the harness `Write` tool.

The main thread is responsible for path validation, dedup, and
overwrite-guard.

## Detection at runtime

`opl preflight` prints:

- `[ok] OPL agent types installed at ~/.claude/agents/opl-experts.yml`
  → Path 1 in use
- `[warn] OPL agent types not installed — will fall back to general-purpose + inline return`
  → Path 2 in use

## Rationale (ADR-0021)

Through v2.0.x the dispatcher pretended file-writes succeeded under
`general-purpose` even though the subagent had no Write tool. The expert
report would land nowhere; the next wave would read an empty file and
generate a placeholder report on top. The fakery sniffer (v2.1 P1-#9) would
then halt the wave, leaving a stuck pipeline. Splitting the path
explicitly — and making `opl preflight` surface which path is active —
gives both modes deterministic semantics.
