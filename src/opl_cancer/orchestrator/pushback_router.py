"""v2.1 P2-#19: patient_pushback_handling auto-triggered on keywords or
sniffer halt.

When the patient or caregiver says something like "are you really
running it?" or "真的在跑吗?" the SKILL main thread should invoke the
``patient_pushback_handling`` task package rather than reflexively
defending. This module provides:

* ``should_trigger_pushback(text)`` — returns True if the text contains a
  pushback cue.
* ``log_trigger(log_path, reason, excerpt, source)`` — appends one JSONL
  row to ``pushback_trigger_log.jsonl``.

Wave runners also call ``log_trigger`` when ``fakery_sniffer`` halts a
wave (P1-#9 hook), so the audit log captures both keyword and automated
triggers in a single stream.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

# Pushback cue keywords — English + Chinese variants. Word-bounded to avoid
# false hits (e.g. "actually" inside "factually").
_TRIGGER_RE = re.compile(
    r"(\bactually\b|\breally\b|真的|真在跑|真的在跑|fake|编的|hallucinat)",
    re.IGNORECASE,
)


def should_trigger_pushback(text: str) -> bool:
    """Return True if ``text`` contains a pushback cue."""
    if not text:
        return False
    return bool(_TRIGGER_RE.search(text))


def log_trigger(
    log_path: Path,
    *,
    reason: str,
    excerpt: str,
    source: str,
) -> None:
    """Append one JSONL row to ``log_path``. Creates parent dirs if needed."""
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "excerpt": excerpt,
        "source": source,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
