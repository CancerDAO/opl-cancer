# Subagent File-Write Contract (v1.5 P0-7)

This document is the canonical template every expert / wave subagent
must follow when writing its report artifact. It is referenced by
SKILL.md Step 5 (Wave 1 expert fanout), Step 7 (Wave 3 analysis), and
Step 8 (Wave 4 validation).

**Why it exists.** In the PT-EXAMPLE-A run, 5 of 10 Wave-1 subagents
returned their report inline (as the agent's final message text)
instead of writing it to the expected file path. The main thread had
to re-land them, doubling the wall-time and creating ambiguity about
which version was canonical (docs/ANTI_PATTERNS_v1.4.md F12).

**What changed in v1.5.** Every subagent prompt now uses the standard
output contract below — primary path with the `Write` tool, fallback
path with Bash heredoc — so any harness configuration that restricts
Write produces an artifact via Bash, not as a chat message.

---

## The contract (paste verbatim into subagent prompts)

```
OUTPUT CONTRACT — DO NOT SKIP

You MUST write your full report to this exact path:

    {{ report_path }}

Use the following procedure in order:

1. (PRIMARY) Use the `Write` tool with file_path={{ report_path }} and
   content=<your full markdown report>. The Write tool creates parent
   directories if needed.

2. (FALLBACK) If the Write tool is not available in your environment
   OR returns an error, fall back to Bash with a heredoc:

       mkdir -p "$(dirname {{ report_path }})"
       cat > {{ report_path }} <<'OPL_REPORT_EOF'
       <your full markdown report goes here, verbatim>
       OPL_REPORT_EOF

   Use a unique-enough sentinel like OPL_REPORT_EOF so no content
   line collides. The orchestrator will validate the resulting file.

3. (CONFIRMATION) After writing, return a short JSON envelope as your
   final message, NOT the full report content:

   ```json
   {
     "task": "{{ task_package }}",
     "expert": "{{ expert_id }}",
     "report_path": "{{ report_path }}",
     "report_bytes": <integer file size in bytes>,
     "report_sha256_short": "<first 12 hex chars of sha256>",
     "status": "ok",
     "notes": "optional one-line summary; do NOT inline the report"
   }
   ```

DO NOT:
  - Return the full report content as a chat message.
  - Truncate the report because it "feels long" — the orchestrator
    expects the full audited content at the path.
  - Write to a different path than {{ report_path }} (the orchestrator
    glues paths into the run manifest).
  - Skip the fallback if Write tool fails. Silent skips are the AP-12
    pattern v1.5 closes.

IF YOU CANNOT WRITE AT ALL (both Write and Bash fail):
  Return the JSON envelope with status="write_failed" and notes=<exact
  error encountered>. The orchestrator will surface this to the user
  loudly — no silent skip per memory:feedback_no_offline_only.
```

---

## Where to find ``{{ report_path }}`` for each wave

| Wave   | Default path |
|--------|--------------|
| Wave 1 | `<patient_dir>/triggers/<run_id>/tasks/w1_{ord}_{expert}/report.md` |
| Wave 2 | `<patient_dir>/triggers/<run_id>/tasks/w2_{expert}/report.md` |
| Wave 3 | `<patient_dir>/triggers/<run_id>/tasks/w3_{slug}/report.md` |
| Wave 4 | `<patient_dir>/triggers/<run_id>/tasks/w4_{expert}/report.md` |
| Henry  | `<patient_dir>/triggers/<run_id>/tasks/henry/report.md` |

The orchestrator (SKILL.md Step 5..8) is responsible for computing the
exact `report_path` and passing it into the subagent prompt. Subagents
must use the path they are given verbatim — do not reinterpret.

## Validation by the orchestrator

After each subagent completes, the orchestrator MUST:

1. Confirm the file at `report_path` exists with size > 0.
2. Re-compute sha256 first-12-chars; compare to the envelope's claim.
3. If mismatch: re-dispatch the subagent with a "you returned an
   inconsistent envelope" suffix. Cap re-dispatch at 1 retry.
4. If the file is missing AND the envelope says `status="ok"`: this is
   the AP-12 pattern — the subagent claimed completion that wasn't
   true. Surface to user immediately with the original envelope as
   evidence; do not silently re-write.

## Why the JSON envelope (not just "the file is on disk")

The harness sees only the final message; if a subagent forgets to
write to disk but happens to put the same content in chat, the
orchestrator could be fooled into thinking the artifact landed. The
envelope's `report_bytes` + `report_sha256_short` make the claim
falsifiable against the filesystem — the orchestrator audits in one
hash step. This matches `memory:feedback_no_false_completion`.

## Test fixture

A smoke fixture for this contract lives at
`tests/test_safety/test_subagent_file_write_contract.py`. It asserts:

- The contract document is present at `prompts/safety/`.
- It contains the canonical sentinel marker (`OPL_REPORT_EOF`).
- It enumerates the 5 path templates above.
- The JSON envelope shape includes `report_path`, `report_bytes`,
  `report_sha256_short`, `status`.
