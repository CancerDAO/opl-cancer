"""Append-only JSONL provenance journal. Spec §2.6 L5."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


class ProvenanceJournal:
    """One JSONL file per trigger run; cross-trigger index sits in memory/provenance/."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            f.write("\n")

    def iter_records(self) -> Iterator[dict[str, Any]]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)
