"""Patient case loader — reads profile + readiness + 11-bucket files into context dict.

Spec §3 (Patient directory schema) + P1-T28. The returned dict is the
``context`` argument passed to :func:`opl_cancer.orchestrator.dispatch.dispatch_wave`
and consumed by Expert task prompts (Jinja2 ``render(**context)``).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_BUCKET_KEY_BY_NAME: dict[str, str] = {
    "01_当前状态": "current_status",
    "02_NGS报告": "ngs_report",
    "03_病理": "pathology_report",
    "04_影像": "imaging_report",
    "05_实验室": "labs",
    "06_治疗历史": "treatment_history_doc",
    "07_用药": "medication_list",
    "08_症状": "symptoms",
    "09_患者反馈": "patient_feedback",
    "10_其他": "other_documents",
    "11_诊断证明": "diagnosis_certificate",
}


class PatientCaseLoader:
    """Read ``patients/<code>/`` into a single dict-context.

    Files read:
    - ``profile.json``       (required — FileNotFoundError if missing)
    - ``readiness.json``     (optional, defaults to ``{}``)
    - ``case_text.md``       (optional, defaults to ``""``)
    - ``timeline.md``        (optional, included if present)
    - 11 buckets ``01_当前状态/`` ~ ``11_诊断证明/`` — each ``.txt`` + ``.md``
      file concatenated into one string per bucket
    """

    def __init__(self, patient_root: Path) -> None:
        self.root = Path(patient_root)

    def load(self) -> dict[str, Any]:
        profile_path = self.root / "profile.json"
        if not profile_path.exists():
            raise FileNotFoundError(f"profile.json not at {profile_path}")
        profile = json.loads(profile_path.read_text(encoding="utf-8"))

        readiness_path = self.root / "readiness.json"
        readiness: dict[str, Any] = (
            json.loads(readiness_path.read_text(encoding="utf-8"))
            if readiness_path.exists()
            else {}
        )

        case_text_path = self.root / "case_text.md"
        case_text = (
            case_text_path.read_text(encoding="utf-8")
            if case_text_path.exists()
            else ""
        )

        timeline_path = self.root / "timeline.md"
        timeline = (
            timeline_path.read_text(encoding="utf-8")
            if timeline_path.exists()
            else ""
        )

        bucket_contents: dict[str, str] = {}
        for bucket_dir, key in _BUCKET_KEY_BY_NAME.items():
            d = self.root / bucket_dir
            if not d.exists():
                bucket_contents[key] = ""
                continue
            chunks: list[str] = []
            files = sorted(d.rglob("*.txt")) + sorted(d.rglob("*.md"))
            for p in files:
                chunks.append(p.read_text(encoding="utf-8", errors="replace"))
            bucket_contents[key] = "\n\n".join(chunks)

        return {
            "patient_code": profile.get("patient_code", self.root.name),
            "profile": profile,
            "readiness": readiness,
            "case_text": case_text,
            "timeline": timeline,
            **bucket_contents,
        }
